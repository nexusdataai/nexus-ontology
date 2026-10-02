"""
Trade CPQ (Sell-Side) ReAct Tools for the AI Control Plane.

Tools that the agent can call to configure, price, approve, and convert
trade quotes for the Trade CPQ module. Read-only tools query the
Virtual Data Layer; write-capable tools route through the connector
runtime so writes hit the TPM simulator with an Audit_Event trail.

The eleven tools match the plan in nexus-docs/docs/cpq/scope.md:
  configure_bundle, validate_configuration, check_serviceability,
  price_quote, apply_promotion, check_credit_and_margin,
  route_approval, generate_proposal_doc, convert_quote_to_order,
  suggest_upsell_crosssell, forecast_quote_win_probability.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from ..tool_registry import RiskLevel, Tool, ToolRegistry

cpq_sell_logger = logger.bind(component="cpq-sell-tools")


CHANNEL_TIER_MAX_DISCOUNT = {
    ("Modern_Trade", "Platinum"): 18,
    ("Modern_Trade", "Gold"): 15,
    ("Modern_Trade", "Silver"): 12,
    ("Modern_Trade", "Bronze"): 10,
    ("General_Trade", "Platinum"): 15,
    ("General_Trade", "Gold"): 12,
    ("General_Trade", "Silver"): 10,
    ("General_Trade", "Bronze"): 8,
    ("HORECA", "Platinum"): 20,
    ("HORECA", "Gold"): 20,
    ("HORECA", "Silver"): 20,
    ("HORECA", "Bronze"): 20,
    ("E-commerce", "Platinum"): 10,
    ("E-commerce", "Gold"): 10,
    ("E-commerce", "Silver"): 10,
    ("E-commerce", "Bronze"): 10,
}

MARGIN_FLOOR_PCT = 15.0
PROMO_STACK_CAP_PCT = 25.0
FEE_AUTO_APPROVE_CAP = 50_000.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tier_max_discount(channel: Optional[str], tier: Optional[str]) -> float:
    if not channel or not tier:
        return 12.0
    return float(CHANNEL_TIER_MAX_DISCOUNT.get((channel, tier), 10.0))


async def _query(vq_service, entity: str, filters: List[Dict[str, Any]], limit: int = 25) -> List[Dict[str, Any]]:
    from src.models.mapping_rule_models import VirtualQueryRequest, VirtualFilter

    f_list = [VirtualFilter(field=f["field"], operator=f.get("operator", "eq"), value=f["value"]) for f in filters]
    try:
        resp = await vq_service.query_virtual_entity(
            VirtualQueryRequest(virtual_entity=entity, filters=f_list, limit=limit)
        )
        return list(resp.rows or [])
    except Exception as e:
        cpq_sell_logger.warning(f"Virtual query failed for {entity}: {e}")
        return []


# ---------------------------------------------------------------------------
# Configure
# ---------------------------------------------------------------------------


async def _lookup_material(
    vq_service,
    query: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """Fuzzy-resolve free-text product descriptions (e.g. "Cola 330ml",
    "Energy drink", "PET bottle 1L") to Material_Master rows by matching
    name / category / pack_size / pack_config / brand tokens."""
    rows = await _query(vq_service, "Material_Master", [], limit=500)
    tokens = [t.strip().lower() for t in (query or "").replace(",", " ").split() if t.strip()]
    if not tokens:
        return {"query": query, "match_count": 0, "matches": []}

    scored: List[Dict[str, Any]] = []
    for r in rows:
        haystack_parts = [
            str(r.get("Material_Name") or ""),
            str(r.get("Description") or ""),
            str(r.get("Category") or ""),
            str(r.get("Brand") or ""),
            str(r.get("Pack_Size") or ""),
            str(r.get("Pack_Config") or ""),
            str(r.get("Sub_Category") or ""),
        ]
        haystack = " ".join(haystack_parts).lower()
        hits = sum(1 for t in tokens if t and t in haystack)
        if hits == 0:
            continue
        scored.append({
            "Material_ID": r.get("Material_ID"),
            "Material_Name": r.get("Material_Name") or r.get("Description"),
            "Category": r.get("Category"),
            "Pack_Size": r.get("Pack_Size"),
            "Pack_Config": r.get("Pack_Config"),
            "Status": r.get("Status"),
            "match_score": hits,
        })
    scored.sort(key=lambda m: m["match_score"], reverse=True)
    return {"query": query, "tokens": tokens,
            "match_count": len(scored), "matches": scored[:limit]}


async def _configure_bundle(
    vq_service,
    account_id: str,
    target_materials: Optional[List[str]] = None,
    material_query: Optional[str] = None,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble candidate offerings for an account.

    Either ``target_materials`` (list of Material_IDs) or ``material_query``
    (free-text like "Cola 330ml") may be provided. When a query is given
    we fuzzy-resolve it to Material_Master rows first, then find offerings
    whose components contain any resolved material AND whose channel
    eligibility matches the effective channel (``channel`` override wins
    over the account's Channel_Type).

    When no material hint is given we return all active eligible offerings.
    """
    target_materials = list(target_materials or [])
    accounts = await _query(vq_service, "Account", [{"field": "Account_ID", "value": account_id}], limit=1)
    acct = accounts[0] if accounts else {}
    account_channel = acct.get("Channel_Type")
    eff_channel = channel or account_channel
    account_status = acct.get("Status")

    resolved_query_materials: List[Dict[str, Any]] = []
    if material_query:
        lookup = await _lookup_material(vq_service, material_query, limit=20)
        resolved_query_materials = lookup.get("matches", [])
        target_materials.extend([m["Material_ID"] for m in resolved_query_materials if m.get("Material_ID")])

    offerings = await _query(vq_service, "Product_Offering", [], limit=300)
    eligible: List[Dict[str, Any]] = []
    skipped_channel = 0
    skipped_inactive = 0
    for off in offerings:
        if off.get("Status") not in ("Active",):
            skipped_inactive += 1
            continue
        elig = [e.strip() for e in (off.get("Channel_Eligibility") or "").split(",") if e.strip()]
        if eff_channel and elig and eff_channel not in elig:
            skipped_channel += 1
            continue
        eligible.append(off)

    matches: List[Dict[str, Any]] = []
    target_set = set(target_materials)
    for off in eligible:
        components = await _query(
            vq_service, "Offering_Component",
            [{"field": "Offering_ID", "value": off.get("Offering_ID")}], limit=20,
        )
        component_mats = {c.get("Material_ID") for c in components}
        overlap = component_mats.intersection(target_set)
        if overlap or not target_set:
            matches.append({
                "Offering_ID": off.get("Offering_ID"),
                "Name": off.get("Name"),
                "Type": off.get("Type"),
                "Channel_Eligibility": off.get("Channel_Eligibility"),
                "Match_Count": len(overlap),
                "Components": [
                    {"Material_ID": c.get("Material_ID"), "Qty": c.get("Qty"), "Role": c.get("Component_Role")}
                    for c in components
                ],
            })
    matches.sort(key=lambda m: m.get("Match_Count", 0), reverse=True)

    warnings: List[str] = []
    if not acct:
        warnings.append(f"Account {account_id} not found in CRM")
    elif account_status and account_status != "Active":
        warnings.append(f"Account {account_id} has Status={account_status}; quotes typically require Active accounts")
    if channel and account_channel and channel != account_channel:
        warnings.append(f"Channel override {channel} differs from account's Channel_Type={account_channel}; override applied")
    if material_query and not resolved_query_materials:
        warnings.append(f"Material query '{material_query}' did not match any Material_Master rows; returning all eligible offerings")

    return {
        "account_id": account_id,
        "account_status": account_status,
        "account_channel": account_channel,
        "effective_channel": eff_channel,
        "target_materials": target_materials,
        "resolved_materials": resolved_query_materials[:10],
        "candidate_count": len(matches),
        "top_candidates": matches[:5],
        "stats": {
            "offerings_scanned": len(offerings),
            "skipped_inactive": skipped_inactive,
            "skipped_channel_mismatch": skipped_channel,
            "eligible_after_channel_filter": len(eligible),
        },
        "warnings": warnings,
    }


async def _create_quote(
    vq_service,
    account_id: str,
    channel: Optional[str] = None,
    material_query: Optional[str] = None,
    target_materials: Optional[List[str]] = None,
    qty: int = 1,
    discount_pct: float = 0.0,
    validity_days: int = 30,
) -> Dict[str, Any]:
    """Create a brand-new Quote_Header (status=Draft) with one or more
    Quote_Lines derived from the resolved material/offering set.

    Sequence:
      1. Resolve material_query -> Material_IDs (if given).
      2. Run configure_bundle to find eligible offerings for the
         requested channel (defaults to account.Channel_Type).
      3. Pick the top candidate (or first if no hint) and write a
         Quote_Header + a single Quote_Line for it.

    Returns the new quote_id plus the configure result so the agent can
    chain to price_quote / route_approval next.
    """
    bundle = await _configure_bundle(
        vq_service,
        account_id=account_id,
        target_materials=target_materials,
        material_query=material_query,
        channel=channel,
    )
    candidates = bundle.get("top_candidates", [])
    chosen = candidates[0] if candidates else None
    if not chosen and not candidates:
        return {
            "created": False,
            "reason": "no_eligible_offerings",
            "configure_result": bundle,
        }

    quote_id = f"QT-{uuid.uuid4().hex[:6].upper()}"
    line_id = f"QTL-{uuid.uuid4().hex[:6].upper()}"
    now = _now_iso()
    validity_date = (datetime.now(timezone.utc) + timedelta(days=validity_days)).strftime("%Y-%m-%d")

    chosen_offering = chosen.get("Offering_ID") if chosen else None
    entries: List[Dict[str, Any]] = []
    list_price = 0.0
    unit_net = 0.0
    if chosen_offering:
        pb_entries = await _query(
            vq_service, "Price_Book_Entry",
            [{"field": "Offering_ID", "value": chosen_offering}], limit=5,
        )
        entries = pb_entries
        if pb_entries:
            list_price = float(pb_entries[0].get("List_Price") or 0)
            unit_net = list_price * (1 - float(discount_pct) / 100)
    total_net = round(unit_net * int(qty), 2)

    header = {
        "Quote_ID": quote_id,
        "Account_ID": account_id,
        "Owner_ID": "ai-copilot",
        "Status": "Draft",
        "Validity_Date": validity_date,
        "Total_Net": total_net,
        "Margin_Pct": 0.0,
        "Discount_Pct": float(discount_pct),
        "Approval_Chain_JSON": "[]",
        "Created_At": now,
        "Submitted_At": "",
    }
    line = {
        "Line_ID": line_id,
        "Quote_ID": quote_id,
        "Offering_ID": chosen_offering or "",
        "Qty": int(qty),
        "Unit_Price": round(unit_net, 2),
        "Discount_Pct": float(discount_pct),
        "Promotion_ID": "",
        "Listing_Fee": 0,
        "Slotting_Fee": 0,
        "Margin_Pct_Line": 0.0,
    }

    from src.services.control_plane.connector_runtime import append_row, emit_audit, get_sim
    try:
        sim = await get_sim("tpm")
        await append_row(sim, "tpm_cpq", "Quote_Header", header)
        await append_row(sim, "tpm_cpq", "Quote_Line", line)
        await emit_audit(
            actor="ai-copilot", verb="create_quote", target=quote_id,
            payload={"account_id": account_id, "channel": channel,
                     "offering_id": chosen_offering, "qty": qty,
                     "discount_pct": discount_pct},
            api_id="tpm.quote.create",
        )
        return {
            "created": True,
            "quote_id": quote_id,
            "header": header,
            "lines": [line],
            "configure_result": bundle,
            "price_book_entries_found": len(entries),
            "next": "Run price_quote, check_credit_and_margin, then route_approval on this quote_id",
        }
    except Exception as e:
        cpq_sell_logger.warning(f"create_quote failed: {e}")
        return {"created": False, "reason": str(e), "configure_result": bundle}


async def _validate_configuration(vq_service, quote_id: str) -> Dict[str, Any]:
    """Evaluate Configuration_Rule set against the quote context. Returns
    structured violations with severity."""
    headers = await _query(vq_service, "Quote_Header", [{"field": "Quote_ID", "value": quote_id}], limit=1)
    header = headers[0] if headers else {}
    if not header:
        return {"quote_id": quote_id, "violations": [], "reason": "quote_not_found"}

    lines = await _query(vq_service, "Quote_Line", [{"field": "Quote_ID", "value": quote_id}], limit=50)
    account = await _query(vq_service, "Account", [{"field": "Account_ID", "value": header.get("Account_ID")}], limit=1)
    channel = account[0].get("Channel_Type") if account else None

    rules = await _query(vq_service, "Configuration_Rule", [], limit=100)
    offerings_by_id: Dict[str, Dict[str, Any]] = {}
    for line in lines:
        if line.get("Offering_ID") and line.get("Offering_ID") not in offerings_by_id:
            offs = await _query(vq_service, "Product_Offering", [{"field": "Offering_ID", "value": line.get("Offering_ID")}], limit=1)
            if offs:
                offerings_by_id[line.get("Offering_ID")] = offs[0]

    violations: List[Dict[str, Any]] = []
    for line in lines:
        off = offerings_by_id.get(line.get("Offering_ID"), {})
        chan_elig = (off.get("Channel_Eligibility") or "").split(",")
        if channel and chan_elig and channel not in chan_elig:
            violations.append({
                "Line_ID": line.get("Line_ID"),
                "Type": "Channel_Eligibility",
                "Severity": "Error",
                "Description": f"Offering {off.get('Offering_ID')} not eligible for channel {channel}",
            })
        if line.get("Qty", 0) and line.get("Qty", 0) < 12 and channel == "Modern_Trade":
            violations.append({
                "Line_ID": line.get("Line_ID"),
                "Type": "MOQ",
                "Severity": "Error",
                "Description": "Modern Trade MOQ is 12 cases",
            })

    rule_summary = [{"Rule_ID": r.get("Rule_ID"), "Type": r.get("Type"), "Severity": r.get("Severity")} for r in rules[:10]]
    return {
        "quote_id": quote_id,
        "channel": channel,
        "lines_evaluated": len(lines),
        "rules_evaluated": len(rules),
        "rule_sample": rule_summary,
        "violations": violations,
        "blocking": any(v["Severity"] == "Error" for v in violations),
    }


async def _check_serviceability(vq_service, quote_id: str) -> Dict[str, Any]:
    """Verify each ship-to region has a Serviceability_Footprint that
    covers the quote's channel."""
    headers = await _query(vq_service, "Quote_Header", [{"field": "Quote_ID", "value": quote_id}], limit=1)
    header = headers[0] if headers else {}
    accounts = await _query(vq_service, "Account", [{"field": "Account_ID", "value": header.get("Account_ID")}], limit=1)
    account = accounts[0] if accounts else {}
    channel = account.get("Channel_Type")
    region = account.get("Region")
    if not (channel and region):
        return {"quote_id": quote_id, "covered": False, "reason": "missing_channel_or_region"}

    footprints = await _query(
        vq_service, "Serviceability_Footprint",
        [{"field": "Channel_Type", "value": channel}], limit=50,
    )
    eligible = [f for f in footprints if f.get("Region") == region]
    return {
        "quote_id": quote_id,
        "channel": channel,
        "region": region,
        "footprint_count": len(eligible),
        "min_sla_days": min((f.get("SLA_Days", 99) for f in eligible), default=None),
        "min_order_qty": min((f.get("Min_Order_Qty", 99999) for f in eligible), default=None),
        "covered": len(eligible) > 0,
    }


# ---------------------------------------------------------------------------
# Price
# ---------------------------------------------------------------------------


async def _price_quote(vq_service, quote_id: str, scenario: str = "default") -> Dict[str, Any]:
    """Build a pricing waterfall for the quote: list → channel/tier
    discount → campaign overlay → promo stacking → fees → net → margin."""
    headers = await _query(vq_service, "Quote_Header", [{"field": "Quote_ID", "value": quote_id}], limit=1)
    header = headers[0] if headers else {}
    if not header:
        return {"quote_id": quote_id, "waterfall": [], "reason": "quote_not_found"}

    lines = await _query(vq_service, "Quote_Line", [{"field": "Quote_ID", "value": quote_id}], limit=50)
    accounts = await _query(vq_service, "Account", [{"field": "Account_ID", "value": header.get("Account_ID")}], limit=1)
    account = accounts[0] if accounts else {}
    channel = account.get("Channel_Type")
    tier = account.get("Tier")
    tier_max = _tier_max_discount(channel, tier)

    waterfall: List[Dict[str, Any]] = []
    total_list = 0.0
    total_net = 0.0
    total_cost = 0.0
    for line in lines:
        offering_id = line.get("Offering_ID")
        qty = float(line.get("Qty", 0) or 0)
        entries = await _query(
            vq_service, "Price_Book_Entry",
            [{"field": "Offering_ID", "value": offering_id}], limit=10,
        )
        list_price = float(entries[0].get("List_Price") or line.get("Unit_Price") or 0) if entries else float(line.get("Unit_Price") or 0)
        floor_price = float(entries[0].get("Floor_Price") or 0) if entries else 0
        cost = float(entries[0].get("Cost_Snapshot") or 0) if entries else 0
        applied_discount = min(float(line.get("Discount_Pct") or 0), tier_max + 5)
        unit_net = list_price * (1 - applied_discount / 100)
        listing = float(line.get("Listing_Fee") or 0)
        slotting = float(line.get("Slotting_Fee") or 0)
        line_net = unit_net * qty + listing + slotting
        line_cost = cost * qty
        margin_pct = ((unit_net - cost) / unit_net * 100) if unit_net > 0 else 0
        total_list += list_price * qty
        total_net += line_net
        total_cost += line_cost
        waterfall.append({
            "Line_ID": line.get("Line_ID"),
            "Offering_ID": offering_id,
            "Qty": qty,
            "List_Price": list_price,
            "Tier_Max_Discount_Pct": tier_max,
            "Applied_Discount_Pct": applied_discount,
            "Unit_Net": round(unit_net, 2),
            "Listing_Fee": listing,
            "Slotting_Fee": slotting,
            "Floor_Price": floor_price,
            "Margin_Pct_Line": round(margin_pct, 2),
            "Below_Floor": unit_net < floor_price,
            "Line_Net": round(line_net, 2),
        })

    blended_margin = ((total_net - total_cost) / total_net * 100) if total_net > 0 else 0
    return {
        "quote_id": quote_id,
        "scenario": scenario,
        "channel": channel,
        "tier": tier,
        "tier_max_discount_pct": tier_max,
        "waterfall": waterfall,
        "totals": {
            "list_total": round(total_list, 2),
            "net_total": round(total_net, 2),
            "cost_total": round(total_cost, 2),
            "blended_margin_pct": round(blended_margin, 2),
            "below_margin_floor": blended_margin < MARGIN_FLOOR_PCT,
        },
    }


async def _apply_promotion(vq_service, quote_id: str, campaign_id: str) -> Dict[str, Any]:
    """Overlay a Campaign onto a quote; enforce stacking cap."""
    campaigns = await _query(vq_service, "Campaign", [{"field": "Campaign_ID", "value": campaign_id}], limit=1)
    campaign = campaigns[0] if campaigns else {}
    if not campaign:
        return {"quote_id": quote_id, "applied": False, "reason": "campaign_not_found"}

    existing = await _query(vq_service, "Quote_Promotion", [{"field": "Quote_ID", "value": quote_id}], limit=20)
    discount_total = sum(float(p.get("Value") or 0) for p in existing if p.get("Mechanic") == "Discount")
    new_value = float(campaign.get("Value") or 5.0)
    if campaign.get("Type") == "Discount" and (discount_total + new_value) > PROMO_STACK_CAP_PCT:
        return {
            "quote_id": quote_id,
            "applied": False,
            "reason": f"stacking cap {PROMO_STACK_CAP_PCT}% would be exceeded",
            "existing_discount_pct": discount_total,
            "requested_discount_pct": new_value,
        }

    promo_id = f"QPR-{uuid.uuid4().hex[:6].upper()}"
    promo_row = {
        "Promo_ID": promo_id,
        "Quote_ID": quote_id,
        "Campaign_ID": campaign_id,
        "Mechanic": campaign.get("Type", "Discount"),
        "Value": new_value,
        "Stacking_Group": "CAMPAIGN_DISC",
    }
    from src.services.control_plane.connector_runtime import append_row, emit_audit, get_sim
    try:
        sim = await get_sim("tpm")
        await append_row(sim, "tpm_cpq", "Quote_Promotion", promo_row)
        await emit_audit(
            actor="ai-copilot", verb="apply_promotion", target=promo_id,
            payload=promo_row, api_id="tpm.quote.promotion.apply",
        )
        applied = True
    except Exception as e:
        cpq_sell_logger.warning(f"apply_promotion write failed: {e}")
        applied = False

    return {"quote_id": quote_id, "applied": applied, "promo_id": promo_id, "promo": promo_row}


# ---------------------------------------------------------------------------
# Margin / credit / approval
# ---------------------------------------------------------------------------


async def _check_credit_and_margin(vq_service, quote_id: str) -> Dict[str, Any]:
    """Read AR_Customer credit limit + AR balance; compute blended
    margin; flag floor breaches and credit holds."""
    pricing = await _price_quote(vq_service, quote_id)
    headers = await _query(vq_service, "Quote_Header", [{"field": "Quote_ID", "value": quote_id}], limit=1)
    header = headers[0] if headers else {}
    customers = await _query(vq_service, "AR_Customer", [{"field": "Customer_ID", "value": header.get("Account_ID")}], limit=1)
    customer = customers[0] if customers else {}
    credit_limit = float(customer.get("Credit_Limit") or 0)
    ar_balance = float(customer.get("AR_Balance") or 0)
    credit_utilization = (ar_balance / credit_limit * 100) if credit_limit > 0 else 0
    on_hold = customer.get("Customer_Status") == "On_Hold" or credit_utilization > 80

    totals = pricing.get("totals", {})
    return {
        "quote_id": quote_id,
        "credit_limit": credit_limit,
        "ar_balance": ar_balance,
        "credit_utilization_pct": round(credit_utilization, 1),
        "on_hold_risk": on_hold,
        "blended_margin_pct": totals.get("blended_margin_pct"),
        "below_margin_floor": totals.get("below_margin_floor"),
        "net_total": totals.get("net_total"),
    }


def _build_approval_chain(
    *,
    discount_pct: float, tier_max: float, margin_pct: float,
    fees_total: float, configuration_errors: int,
) -> List[Dict[str, Any]]:
    chain: List[Dict[str, Any]] = []
    if discount_pct > tier_max and discount_pct - tier_max <= 5:
        chain.append({"role": "RegionalSalesManager", "status": "pending"})
    if (discount_pct - tier_max) > 5 or fees_total > FEE_AUTO_APPROVE_CAP or configuration_errors > 0:
        chain.append({"role": "CommercialDirector", "status": "pending"})
    if margin_pct < MARGIN_FLOOR_PCT:
        chain.append({"role": "CFO", "status": "pending"})
    return chain


async def _route_approval(vq_service, quote_id: str) -> Dict[str, Any]:
    """Compute and persist the approval chain on the quote."""
    headers = await _query(vq_service, "Quote_Header", [{"field": "Quote_ID", "value": quote_id}], limit=1)
    header = headers[0] if headers else {}
    if not header:
        return {"quote_id": quote_id, "routed": False, "reason": "quote_not_found"}

    accounts = await _query(vq_service, "Account", [{"field": "Account_ID", "value": header.get("Account_ID")}], limit=1)
    account = accounts[0] if accounts else {}
    tier = account.get("Tier")
    channel = account.get("Channel_Type")
    tier_max = _tier_max_discount(channel, tier)

    lines = await _query(vq_service, "Quote_Line", [{"field": "Quote_ID", "value": quote_id}], limit=50)
    fees_total = sum(float(l.get("Listing_Fee") or 0) + float(l.get("Slotting_Fee") or 0) for l in lines)
    discount_pct = float(header.get("Discount_Pct") or 0)
    margin_pct = float(header.get("Margin_Pct") or 0)

    validation = await _validate_configuration(vq_service, quote_id)
    error_count = sum(1 for v in validation.get("violations", []) if v.get("Severity") == "Error")

    chain = _build_approval_chain(
        discount_pct=discount_pct, tier_max=tier_max, margin_pct=margin_pct,
        fees_total=fees_total, configuration_errors=error_count,
    )
    auto = len(chain) == 0
    new_status = "Approved" if auto else "In_Review"

    from src.services.control_plane.connector_runtime import emit_audit, get_sim, update_one
    try:
        sim = await get_sim("tpm")
        previous, _ = await update_one(
            sim, "tpm_cpq", "Quote_Header", "Quote_ID", quote_id,
            {
                "Status": new_status,
                "Approval_Chain_JSON": json.dumps(chain),
                "Submitted_At": _now_iso(),
            },
        )
        await emit_audit(
            actor="ai-copilot", verb="route_approval", target=quote_id,
            payload={"chain": chain, "new_status": new_status},
            api_id="tpm.quote.approval.route",
        )
        return {"quote_id": quote_id, "routed": True, "auto_approved": auto,
                "approval_chain": chain, "new_status": new_status}
    except Exception as e:
        cpq_sell_logger.warning(f"route_approval failed: {e}")
        return {"quote_id": quote_id, "routed": False, "reason": str(e)}


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


async def _generate_proposal_doc(vq_service, quote_id: str, template: str = "standard") -> Dict[str, Any]:
    """Compose a proposal markdown document for the quote."""
    pricing = await _price_quote(vq_service, quote_id)
    headers = await _query(vq_service, "Quote_Header", [{"field": "Quote_ID", "value": quote_id}], limit=1)
    header = headers[0] if headers else {}
    accounts = await _query(vq_service, "Account", [{"field": "Account_ID", "value": header.get("Account_ID")}], limit=1)
    account = accounts[0] if accounts else {}

    lines_md = "\n".join(
        f"| {w['Line_ID']} | {w['Offering_ID']} | {w['Qty']} | ${w['List_Price']:.2f} | {w['Applied_Discount_Pct']:.1f}% | ${w['Unit_Net']:.2f} | ${w['Line_Net']:.2f} |"
        for w in pricing.get("waterfall", [])
    )
    totals = pricing.get("totals", {})
    body = (
        f"# Commercial Proposal\n\n"
        f"**Customer:** {account.get('Name', header.get('Account_ID'))} ({header.get('Account_ID')})\n\n"
        f"**Quote ID:** {quote_id}\n\n"
        f"**Validity:** {header.get('Validity_Date', '')}\n\n"
        f"## Pricing\n\n"
        f"| Line | Offering | Qty | List | Discount | Unit Net | Line Net |\n"
        f"|------|----------|-----|------|----------|----------|----------|\n"
        f"{lines_md}\n\n"
        f"**Total Net:** ${totals.get('net_total', 0):.2f}\n\n"
        f"**Blended Margin:** {totals.get('blended_margin_pct', 0):.1f}%\n"
    )
    return {
        "quote_id": quote_id,
        "template": template,
        "format": "markdown",
        "body": body,
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Convert
# ---------------------------------------------------------------------------


async def _convert_quote_to_order(vq_service, quote_id: str) -> Dict[str, Any]:
    """Move an Approved quote to Won_Converted; mark journey kickoff for
    the quote-to-order workflow."""
    headers = await _query(vq_service, "Quote_Header", [{"field": "Quote_ID", "value": quote_id}], limit=1)
    header = headers[0] if headers else {}
    if not header:
        return {"quote_id": quote_id, "converted": False, "reason": "quote_not_found"}
    if header.get("Status") != "Approved":
        return {"quote_id": quote_id, "converted": False, "reason": f"quote status is {header.get('Status')}, requires Approved"}

    from src.services.control_plane.connector_runtime import emit_audit, get_sim, update_one
    try:
        sim = await get_sim("tpm")
        previous, _ = await update_one(
            sim, "tpm_cpq", "Quote_Header", "Quote_ID", quote_id,
            {"Status": "Won_Converted"},
        )
        await emit_audit(
            actor="ai-copilot", verb="convert_quote_to_order", target=quote_id,
            payload={"previous_status": previous.get("Status"), "new_status": "Won_Converted"},
            api_id="tpm.quote.convert_to_order",
        )
        return {"quote_id": quote_id, "converted": True, "new_status": "Won_Converted",
                "next_workflow": "WORKFLOW_QUOTE_TO_ORDER_V1_0"}
    except Exception as e:
        cpq_sell_logger.warning(f"convert_quote_to_order failed: {e}")
        return {"quote_id": quote_id, "converted": False, "reason": str(e)}


# ---------------------------------------------------------------------------
# AI-First helpers
# ---------------------------------------------------------------------------


async def _suggest_upsell_crosssell(vq_service, quote_id: str, top_n: int = 5) -> Dict[str, Any]:
    """Recommend offerings to add based on Opportunity_Line_Item history
    for the same Account and Brand_Sentiment signals."""
    headers = await _query(vq_service, "Quote_Header", [{"field": "Quote_ID", "value": quote_id}], limit=1)
    header = headers[0] if headers else {}
    account_id = header.get("Account_ID")
    if not account_id:
        return {"quote_id": quote_id, "recommendations": []}

    historic_lines = await _query(
        vq_service, "Opportunity_Line_Item",
        [{"field": "Account_ID", "value": account_id}], limit=200,
    )
    counter: Dict[str, int] = {}
    for r in historic_lines:
        mid = r.get("Material_ID") or r.get("Product_ID")
        if mid:
            counter[mid] = counter.get(mid, 0) + 1
    historic_top = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:top_n * 2]

    current_lines = await _query(vq_service, "Quote_Line", [{"field": "Quote_ID", "value": quote_id}], limit=50)
    current_offering_ids = {l.get("Offering_ID") for l in current_lines}

    offerings = await _query(vq_service, "Product_Offering", [], limit=200)
    offering_index: Dict[str, Dict[str, Any]] = {}
    for off in offerings:
        if off.get("Status") == "Active":
            components = await _query(
                vq_service, "Offering_Component",
                [{"field": "Offering_ID", "value": off.get("Offering_ID")}], limit=10,
            )
            mats = [c.get("Material_ID") for c in components]
            offering_index[off.get("Offering_ID")] = {"offering": off, "materials": mats}

    recos: List[Dict[str, Any]] = []
    for oid, payload in offering_index.items():
        if oid in current_offering_ids:
            continue
        score = sum(counter.get(m, 0) for m in payload["materials"])
        if score > 0:
            recos.append({"Offering_ID": oid, "Name": payload["offering"].get("Name"),
                          "Score": score, "Materials": payload["materials"]})
    recos.sort(key=lambda r: r["Score"], reverse=True)

    return {
        "quote_id": quote_id,
        "account_id": account_id,
        "historic_top": historic_top[:top_n],
        "recommendations": recos[:top_n],
    }


async def _forecast_quote_win_probability(vq_service, quote_id: str) -> Dict[str, Any]:
    """Lightweight scoring: blends discount depth, margin, validity
    window, and historic win rate by tier."""
    headers = await _query(vq_service, "Quote_Header", [{"field": "Quote_ID", "value": quote_id}], limit=1)
    header = headers[0] if headers else {}
    if not header:
        return {"quote_id": quote_id, "win_probability": 0.0, "reason": "quote_not_found"}

    accounts = await _query(vq_service, "Account", [{"field": "Account_ID", "value": header.get("Account_ID")}], limit=1)
    tier = (accounts[0].get("Tier") if accounts else "Bronze") or "Bronze"

    tier_baseline = {"Platinum": 0.62, "Gold": 0.55, "Silver": 0.48, "Bronze": 0.40}.get(tier, 0.45)
    discount = float(header.get("Discount_Pct") or 0)
    margin = float(header.get("Margin_Pct") or 0)

    discount_lift = min(0.18, max(-0.2, (discount - 8) / 100))
    margin_penalty = 0 if margin >= MARGIN_FLOOR_PCT else (MARGIN_FLOOR_PCT - margin) / 100
    score = max(0.05, min(0.95, tier_baseline + discount_lift - margin_penalty))
    drivers = {
        "tier_baseline": round(tier_baseline, 2),
        "discount_lift": round(discount_lift, 3),
        "margin_penalty": round(margin_penalty, 3),
    }
    return {
        "quote_id": quote_id,
        "tier": tier,
        "discount_pct": discount,
        "margin_pct": margin,
        "win_probability": round(score, 3),
        "drivers": drivers,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_cpq_sell_tools(registry: ToolRegistry, virtual_query_service=None) -> None:
    if not virtual_query_service:
        cpq_sell_logger.warning("Virtual query service not available — Trade CPQ tools not registered")
        return

    registry.register(Tool(
        name="lookup_material",
        description=(
            "Fuzzy-resolve free-text product descriptions (e.g. 'Cola 330ml', "
            "'Energy drink', 'PET bottle 1L') to Material_Master rows. Match on "
            "name, description, category, brand, pack_size, pack_config. Returns "
            "ranked candidates. Use this FIRST when the user gives a product "
            "description rather than a Material_ID."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text product description"},
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _lookup_material(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-sell", "material", "lookup"],
    ))

    registry.register(Tool(
        name="configure_bundle",
        description=(
            "Assemble candidate Product_Offering bundles for an account. Accepts "
            "either a list of Material_IDs (target_materials) OR a free-text "
            "material_query (e.g. 'Cola 330ml'). Channel override wins over the "
            "account's Channel_Type. Returns ranked candidates plus warnings for "
            "inactive accounts and channel mismatches."
        ),
        parameters={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Salesforce Account ID"},
                "target_materials": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Optional list of Material_IDs the customer is interested in",
                },
                "material_query": {
                    "type": "string",
                    "description": "Optional free-text material description, e.g. 'Cola 330ml' or 'Energy drink 250ml'",
                },
                "channel": {"type": "string", "description": "Override channel (defaults to account Channel_Type)"},
            },
            "required": ["account_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _configure_bundle(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-sell", "configure", "analyze"],
    ))

    registry.register(Tool(
        name="create_quote",
        description=(
            "Create a brand-new Draft Quote_Header + initial Quote_Line for an "
            "account. Resolves material_query -> Material_IDs, picks the best "
            "matching active offering for the requested channel, persists the "
            "quote in the TPM simulator, and returns the new quote_id. Use this "
            "tool to START a quote when the user says 'build a quote', 'create "
            "a quote', or 'quote N units of X'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Salesforce Account ID"},
                "channel": {"type": "string", "description": "Optional channel override (e.g. 'HORECA', 'Modern_Trade')"},
                "material_query": {"type": "string", "description": "Free-text material description (e.g. 'Cola 330ml')"},
                "target_materials": {"type": "array", "items": {"type": "string"}, "description": "Optional explicit Material_IDs"},
                "qty": {"type": "integer", "description": "Quantity for the initial Quote_Line"},
                "discount_pct": {"type": "number", "description": "Initial discount percentage (e.g. 14 for 14%)"},
                "validity_days": {"type": "integer", "description": "Validity in days (default 30)"},
            },
            "required": ["account_id"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _create_quote(virtual_query_service, **kw),
        connector_api="tpm.quote.create",
        tags=["cpq-sell", "quote", "write"],
    ))

    registry.register(Tool(
        name="validate_configuration",
        description=(
            "Evaluate the Configuration_Rule set against a quote: channel eligibility, MOQ, pack/case, "
            "regional restrictions, and exclusion rules. Returns severities and blocking flag."
        ),
        parameters={
            "type": "object",
            "properties": {"quote_id": {"type": "string", "description": "Quote_ID to validate"}},
            "required": ["quote_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _validate_configuration(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-sell", "configure", "validate"],
    ))

    registry.register(Tool(
        name="check_serviceability",
        description=(
            "Confirm there is a Serviceability_Footprint covering the quote's ship-to region "
            "and channel; surface SLA and minimum-order-quantity."
        ),
        parameters={
            "type": "object",
            "properties": {"quote_id": {"type": "string", "description": "Quote_ID"}},
            "required": ["quote_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _check_serviceability(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-sell", "serviceability"],
    ))

    registry.register(Tool(
        name="price_quote",
        description=(
            "Build the pricing waterfall for a quote: list → tier discount → applied discount → "
            "unit net → fees → line net → margin. Flags floor breaches."
        ),
        parameters={
            "type": "object",
            "properties": {
                "quote_id": {"type": "string", "description": "Quote_ID"},
                "scenario": {"type": "string", "description": "Pricing scenario label (default)"},
            },
            "required": ["quote_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _price_quote(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-sell", "price"],
    ))

    registry.register(Tool(
        name="apply_promotion",
        description="Overlay a Salesforce Campaign as a Quote_Promotion; enforces 25% stacking cap per pricing-discount-policy.",
        parameters={
            "type": "object",
            "properties": {
                "quote_id": {"type": "string", "description": "Quote_ID"},
                "campaign_id": {"type": "string", "description": "Campaign_ID to apply"},
            },
            "required": ["quote_id", "campaign_id"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _apply_promotion(virtual_query_service, **kw),
        connector_api="tpm.quote.promotion.apply",
        tags=["cpq-sell", "promotion", "write"],
    ))

    registry.register(Tool(
        name="check_credit_and_margin",
        description="Inspect customer credit utilization and quote blended margin; flag floor breaches and credit-hold risk.",
        parameters={
            "type": "object",
            "properties": {"quote_id": {"type": "string", "description": "Quote_ID"}},
            "required": ["quote_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _check_credit_and_margin(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-sell", "credit", "margin"],
    ))

    registry.register(Tool(
        name="route_approval",
        description=(
            "Compute and persist the approval chain on the quote per cpq-quote-approval-policy. "
            "Auto-approves when within tier max, above margin floor, and below fee cap."
        ),
        parameters={
            "type": "object",
            "properties": {"quote_id": {"type": "string", "description": "Quote_ID"}},
            "required": ["quote_id"],
        },
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _route_approval(virtual_query_service, **kw),
        connector_api="tpm.quote.approval.route",
        requires_approval=False,
        tags=["cpq-sell", "approval", "write"],
    ))

    registry.register(Tool(
        name="generate_proposal_doc",
        description="Compose a markdown commercial proposal for the quote with pricing waterfall and customer header.",
        parameters={
            "type": "object",
            "properties": {
                "quote_id": {"type": "string", "description": "Quote_ID"},
                "template": {"type": "string", "description": "Template name (default 'standard')"},
            },
            "required": ["quote_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _generate_proposal_doc(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-sell", "document"],
    ))

    registry.register(Tool(
        name="convert_quote_to_order",
        description="Transition an Approved quote to Won_Converted and emit the kickoff event for quote-to-order.",
        parameters={
            "type": "object",
            "properties": {"quote_id": {"type": "string", "description": "Quote_ID"}},
            "required": ["quote_id"],
        },
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _convert_quote_to_order(virtual_query_service, **kw),
        connector_api="tpm.quote.convert_to_order",
        requires_approval=True,
        tags=["cpq-sell", "convert", "write"],
    ))

    registry.register(Tool(
        name="suggest_upsell_crosssell",
        description=(
            "Recommend additional offerings to add to a quote based on the account's historic "
            "Opportunity_Line_Item purchases and overlapping Material_Master."
        ),
        parameters={
            "type": "object",
            "properties": {
                "quote_id": {"type": "string", "description": "Quote_ID"},
                "top_n": {"type": "integer", "description": "Maximum recommendations to return"},
            },
            "required": ["quote_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _suggest_upsell_crosssell(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-sell", "ai", "recommend"],
    ))

    registry.register(Tool(
        name="forecast_quote_win_probability",
        description=(
            "Score the probability that a quote will close, blending account tier baseline, discount depth, "
            "margin floor proximity, and validity window."
        ),
        parameters={
            "type": "object",
            "properties": {"quote_id": {"type": "string", "description": "Quote_ID"}},
            "required": ["quote_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _forecast_quote_win_probability(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-sell", "ai", "forecast"],
    ))

    cpq_sell_tool_names = [
        "lookup_material", "create_quote",
        "configure_bundle", "validate_configuration", "check_serviceability",
        "price_quote", "apply_promotion", "check_credit_and_margin",
        "route_approval", "generate_proposal_doc", "convert_quote_to_order",
        "suggest_upsell_crosssell", "forecast_quote_win_probability",
    ]
    for tool_name in cpq_sell_tool_names:
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "supply-chain"

    cpq_sell_logger.info(f"Trade CPQ tools registered: {len(cpq_sell_tool_names)} tools (bucket=supply-chain)")
