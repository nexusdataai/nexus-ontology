"""
Sourcing CPQ (Buy-Side) ReAct Tools for the AI Control Plane.

Tools that the agent can call to launch RFx, score bids, build award
scenarios, and draft contracts. Read-only tools query the Virtual Data
Layer; write-capable tools route through the connector runtime so writes
hit the Sourcing simulator with an Audit_Event trail.

Nine tools per plan:
  launch_rfx, recommend_vendor_panel, solicit_vendors,
  score_vendor_response, should_cost_model, run_award_scenario,
  recommend_award_split, draft_contract, convert_award_to_po.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from ..tool_registry import RiskLevel, Tool, ToolRegistry

cpq_buy_logger = logger.bind(component="cpq-buy-tools")


SHOULD_COST_VARIANCE_THRESHOLDS = {
    "auto_approve_max_pct": 0.0,
    "manager_max_pct": 5.0,
    "director_max_pct": 10.0,
    "vp_max_pct": 20.0,
}
CONCENTRATION_CEILING_PCT = 60.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _query(vq_service, entity: str, filters: List[Dict[str, Any]], limit: int = 50) -> List[Dict[str, Any]]:
    from src.models.mapping_rule_models import VirtualQueryRequest, VirtualFilter

    f_list = [VirtualFilter(field=f["field"], operator=f.get("operator", "eq"), value=f["value"]) for f in filters]
    try:
        resp = await vq_service.query_virtual_entity(
            VirtualQueryRequest(virtual_entity=entity, filters=f_list, limit=limit)
        )
        return list(resp.rows or [])
    except Exception as e:
        cpq_buy_logger.warning(f"Virtual query failed for {entity}: {e}")
        return []


# ---------------------------------------------------------------------------
# Launch / solicit
# ---------------------------------------------------------------------------


async def _launch_rfx(
    vq_service,
    category: str,
    plants: Optional[List[str]] = None,
    target_qty: Optional[float] = None,
    due_date: Optional[str] = None,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an RFx_Event row from a category and plant list."""
    event_id = f"RFX-{uuid.uuid4().hex[:6].upper()}"
    plants = plants or []
    close_date = due_date or (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")
    open_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    event_row = {
        "Event_ID": event_id,
        "Type": "RFQ",
        "Buyer_Plant_ID": plants[0] if plants else "",
        "Category": category,
        "Status": "Draft",
        "Open_Date": open_date,
        "Close_Date": close_date,
        "Owner_ID": "ai-copilot",
        "Title": title or f"RFQ for {category} {event_id[-4:]}",
    }

    from src.services.control_plane.connector_runtime import append_row, emit_audit, get_sim
    try:
        sim = await get_sim("sourcing")
        await append_row(sim, "sourcing_cpq", "RFx_Event", event_row)
        await emit_audit(
            actor="ai-copilot", verb="launch_rfx", target=event_id,
            payload=event_row, api_id="sourcing.rfx.create",
        )
        return {"launched": True, "event_id": event_id, "event": event_row,
                "next": "recommend_vendor_panel"}
    except Exception as e:
        cpq_buy_logger.warning(f"launch_rfx write failed: {e}")
        return {"launched": False, "reason": str(e)}


async def _recommend_vendor_panel(vq_service, event_id: str, top_n: int = 5) -> Dict[str, Any]:
    """Pick top vendor candidates from Source_List ∩ active Vendor_Master."""
    rfx_lines = await _query(vq_service, "RFx_Line", [{"field": "Event_ID", "value": event_id}], limit=50)
    material_ids = [r.get("Material_ID") for r in rfx_lines if r.get("Material_ID")]

    candidate_vendors: Dict[str, Dict[str, Any]] = {}
    for mid in material_ids:
        rows = await _query(vq_service, "Source_List", [{"field": "Material_ID", "value": mid}], limit=20)
        for row in rows:
            if row.get("Status") not in ("Active",):
                continue
            vendor_id = row.get("Vendor_ID")
            if not vendor_id:
                continue
            candidate_vendors.setdefault(vendor_id, {"Vendor_ID": vendor_id, "Materials": []})
            candidate_vendors[vendor_id]["Materials"].append(mid)

    # Hydrate with Vendor_Master attributes
    panel: List[Dict[str, Any]] = []
    for vendor_id, base in candidate_vendors.items():
        vendor_rows = await _query(vq_service, "Vendor_Master", [{"field": "Vendor_ID", "value": vendor_id}], limit=1)
        v = vendor_rows[0] if vendor_rows else {}
        if v.get("Status") not in ("Active",):
            continue
        risk = float(v.get("Risk_Score") or 50)
        if risk < 40:
            continue
        panel.append({
            **base,
            "Vendor_Name": v.get("Vendor_Name"),
            "Risk_Score": risk,
            "Rating": v.get("Rating"),
            "OTD_Pct": v.get("OTD_Pct"),
            "Country": v.get("Country"),
        })
    panel.sort(key=lambda p: (p.get("Risk_Score") or 0), reverse=True)
    return {"event_id": event_id, "candidate_count": len(panel), "panel": panel[:top_n]}


async def _solicit_vendors(vq_service, event_id: str, vendor_ids: List[str]) -> Dict[str, Any]:
    """Create RFx_Invitation rows for the panel."""
    from src.services.control_plane.connector_runtime import append_row, emit_audit, get_sim
    invitations: List[Dict[str, Any]] = []
    try:
        sim = await get_sim("sourcing")
        for vid in vendor_ids:
            inv_id = f"RFI-{uuid.uuid4().hex[:6].upper()}"
            inv = {
                "Invitation_ID": inv_id,
                "Event_ID": event_id,
                "Vendor_ID": vid,
                "Status": "Invited",
                "Invited_At": _now_iso(),
            }
            await append_row(sim, "sourcing_cpq", "RFx_Invitation", inv)
            invitations.append(inv)
        await emit_audit(
            actor="ai-copilot", verb="solicit_vendors", target=event_id,
            payload={"vendor_count": len(invitations)}, api_id="sourcing.rfx.invite",
        )
        return {"solicited": True, "event_id": event_id, "invitations": invitations}
    except Exception as e:
        cpq_buy_logger.warning(f"solicit_vendors failed: {e}")
        return {"solicited": False, "reason": str(e)}


# ---------------------------------------------------------------------------
# Score / model
# ---------------------------------------------------------------------------


async def _should_cost_model(vq_service, material_id: str, qty: float = 1000) -> Dict[str, Any]:
    """Build a bottom-up should-cost from Commodity_Price + labor + overhead + freight."""
    commodities = await _query(vq_service, "Commodity_Price", [], limit=50)
    materials = await _query(vq_service, "Material_Master", [{"field": "Material_ID", "value": material_id}], limit=1)
    material = materials[0] if materials else {}

    # naive: take first 1-3 commodities as inputs
    refs = [c.get("Commodity") or c.get("Commodity_Code") for c in commodities[:3] if c.get("Commodity") or c.get("Commodity_Code")]
    avg_commodity = (
        sum(float(c.get("Price_Per_Unit") or c.get("Price") or 0) for c in commodities[:3]) / max(1, min(3, len(commodities)))
    )

    labor = 0.18
    overhead = 0.22
    freight = 0.08
    modeled = round(avg_commodity * (1 + labor + overhead) + freight, 4)
    confidence = 0.7 if commodities else 0.4
    return {
        "material_id": material_id,
        "material_name": material.get("Material_Name") or material.get("Description"),
        "commodity_refs": refs,
        "labor_index": labor,
        "overhead": overhead,
        "freight": freight,
        "qty": qty,
        "modeled_cost_per_unit": modeled,
        "confidence": confidence,
    }


async def _score_vendor_response(vq_service, vendor_quote_id: str) -> Dict[str, Any]:
    """Composite score: price-vs-should-cost 40, lead time 15, risk 20,
    quality 15, sustainability 10."""
    vq_rows = await _query(vq_service, "Vendor_Quote", [{"field": "Vendor_Quote_ID", "value": vendor_quote_id}], limit=1)
    vq = vq_rows[0] if vq_rows else {}
    if not vq:
        return {"vendor_quote_id": vendor_quote_id, "score": 0, "reason": "vendor_quote_not_found"}

    vendor_id = vq.get("Vendor_ID")
    vendors = await _query(vq_service, "Vendor_Master", [{"field": "Vendor_ID", "value": vendor_id}], limit=1)
    vendor = vendors[0] if vendors else {}

    lines = await _query(vq_service, "Vendor_Quote_Line", [{"field": "Vendor_Quote_ID", "value": vendor_quote_id}], limit=50)
    if not lines:
        return {"vendor_quote_id": vendor_quote_id, "score": 0, "reason": "no_lines"}

    # Score per line then average
    line_scores: List[Dict[str, Any]] = []
    for ln in lines:
        rfx_line_id = ln.get("RFx_Line_ID")
        rfx_lines = await _query(vq_service, "RFx_Line", [{"field": "Line_ID", "value": rfx_line_id}], limit=1)
        rfx_line = rfx_lines[0] if rfx_lines else {}
        material_id = rfx_line.get("Material_ID") or ""
        scm = await _should_cost_model(vq_service, material_id, rfx_line.get("Qty_Target", 1000)) if material_id else {}
        modeled = float(scm.get("modeled_cost_per_unit") or 0)
        unit = float(ln.get("Unit_Price") or 0)
        price_score = 0
        if modeled > 0:
            price_score = max(0, min(100, ((modeled - unit) / modeled) * 100 + 50))

        lead_time = float(ln.get("Lead_Time_Days") or 90)
        lead_score = max(0, min(100, 100 - lead_time))
        risk_score_val = float(vendor.get("Risk_Score") or 50)
        compliance = (ln.get("Compliance_Flags") or "").split(",")
        sustainability_score = 100 if any(c.strip() == "certs_met" for c in compliance) else 0
        quality_score = 80  # placeholder; would use Quality_Inspection_Lot when wired

        composite = (
            price_score * 0.40 +
            lead_score * 0.15 +
            risk_score_val * 0.20 +
            quality_score * 0.15 +
            sustainability_score * 0.10
        )
        line_scores.append({
            "Line_ID": ln.get("Line_ID"),
            "RFx_Line_ID": rfx_line_id,
            "Unit_Price": unit,
            "Modeled_Cost": modeled,
            "Price_Score": round(price_score, 1),
            "Lead_Score": round(lead_score, 1),
            "Risk_Score": round(risk_score_val, 1),
            "Quality_Score": round(quality_score, 1),
            "Sustainability_Score": round(sustainability_score, 1),
            "Composite": round(composite, 1),
        })

    overall = round(sum(s["Composite"] for s in line_scores) / max(1, len(line_scores)), 1)
    return {
        "vendor_quote_id": vendor_quote_id,
        "vendor_id": vendor_id,
        "overall_score": overall,
        "line_scores": line_scores,
        "vendor_risk": vendor.get("Risk_Score"),
        "vendor_status": vendor.get("Status"),
    }


# ---------------------------------------------------------------------------
# Award scenarios
# ---------------------------------------------------------------------------


async def _run_award_scenario(vq_service, event_id: str, split_strategy: str = "cost_optimal") -> Dict[str, Any]:
    """Produce a Sourcing_Scenario for a strategy across submitted bids."""
    quotes = await _query(vq_service, "Vendor_Quote",
                          [{"field": "Event_ID", "value": event_id}, {"field": "Status", "operator": "in", "value": ["Submitted", "Under_Evaluation"]}],
                          limit=50)
    rfx_lines = await _query(vq_service, "RFx_Line", [{"field": "Event_ID", "value": event_id}], limit=50)

    scored: List[Dict[str, Any]] = []
    for q in quotes:
        score = await _score_vendor_response(vq_service, q.get("Vendor_Quote_ID"))
        scored.append({**q, "score": score.get("overall_score", 0), "scoring": score})

    if not scored:
        return {"event_id": event_id, "strategy": split_strategy, "scenarios": [], "reason": "no_bids"}

    # Build a single split per strategy.
    splits: List[Dict[str, Any]] = []
    if split_strategy == "diversified":
        top = sorted(scored, key=lambda s: s["score"], reverse=True)[:3]
        shares = [50, 30, 20]
        for i, s in enumerate(top):
            splits.append({"vendor_id": s.get("Vendor_ID"), "qty_pct": shares[i],
                           "unit_price": s["scoring"]["line_scores"][0]["Unit_Price"] if s["scoring"]["line_scores"] else 0,
                           "plant_id": rfx_lines[0].get("Plant_ID") if rfx_lines else ""})
    elif split_strategy == "risk_balanced":
        top = sorted(scored, key=lambda s: s["score"], reverse=True)[:2]
        shares = [60, 40]
        for i, s in enumerate(top):
            splits.append({"vendor_id": s.get("Vendor_ID"), "qty_pct": shares[i],
                           "unit_price": s["scoring"]["line_scores"][0]["Unit_Price"] if s["scoring"]["line_scores"] else 0,
                           "plant_id": rfx_lines[0].get("Plant_ID") if rfx_lines else ""})
    else:  # cost_optimal
        top = sorted(scored, key=lambda s: s["score"], reverse=True)[:1]
        for s in top:
            splits.append({"vendor_id": s.get("Vendor_ID"), "qty_pct": 100,
                           "unit_price": s["scoring"]["line_scores"][0]["Unit_Price"] if s["scoring"]["line_scores"] else 0,
                           "plant_id": rfx_lines[0].get("Plant_ID") if rfx_lines else ""})

    concentration = max((s["qty_pct"] for s in splits), default=100)
    avg_modeled = 0
    sample = scored[0]["scoring"]["line_scores"] if scored and scored[0].get("scoring", {}).get("line_scores") else []
    if sample:
        avg_modeled = sum(l["Modeled_Cost"] for l in sample) / len(sample)
    avg_unit = sum(sp["unit_price"] for sp in splits) / max(1, len(splits))
    modeled_savings = round(((avg_modeled - avg_unit) / avg_modeled * 100) if avg_modeled else 0, 2)

    avg_risk = 100 - (sum(s["score"] for s in scored[:3]) / max(1, min(3, len(scored))))
    scenario_id = f"SCN-{uuid.uuid4().hex[:6].upper()}"
    scenario_row = {
        "Scenario_ID": scenario_id,
        "Event_ID": event_id,
        "Name": split_strategy.replace("_", " ").title(),
        "Split_JSON": json.dumps(splits),
        "Modeled_Savings": modeled_savings,
        "Modeled_Risk_Score": round(avg_risk, 1),
        "Concentration_Pct": concentration,
        "Generated_At": _now_iso(),
    }

    from src.services.control_plane.connector_runtime import append_row, emit_audit, get_sim
    try:
        sim = await get_sim("sourcing")
        await append_row(sim, "sourcing_cpq", "Sourcing_Scenario", scenario_row)
        await emit_audit(
            actor="ai-copilot", verb="run_award_scenario", target=scenario_id,
            payload={"strategy": split_strategy, "concentration": concentration,
                     "modeled_savings": modeled_savings},
            api_id="sourcing.scenario.create",
        )
    except Exception as e:
        cpq_buy_logger.warning(f"run_award_scenario write failed: {e}")

    return {"event_id": event_id, "strategy": split_strategy,
            "scenario": scenario_row, "candidate_vendors": len(scored)}


async def _recommend_award_split(vq_service, event_id: str) -> Dict[str, Any]:
    """Run multiple strategies and pick the Pareto-optimal one."""
    strategies = ["cost_optimal", "risk_balanced", "diversified"]
    runs: List[Dict[str, Any]] = []
    for st in strategies:
        run = await _run_award_scenario(vq_service, event_id, st)
        runs.append(run)
    valid = [r for r in runs if r.get("scenario")]
    if not valid:
        return {"event_id": event_id, "recommended": None, "candidates": runs}

    # Pick the one with best savings within concentration ceiling.
    def _ok(r):
        s = r.get("scenario", {})
        return s.get("Concentration_Pct", 100) <= CONCENTRATION_CEILING_PCT

    filtered = [r for r in valid if _ok(r)] or valid
    filtered.sort(key=lambda r: r["scenario"].get("Modeled_Savings", 0), reverse=True)
    return {"event_id": event_id, "recommended": filtered[0], "candidates": valid}


# ---------------------------------------------------------------------------
# Draft / convert
# ---------------------------------------------------------------------------


async def _draft_contract(vq_service, award_id: str, template: str = "standard") -> Dict[str, Any]:
    """Compose a markdown contract draft for an approved sourcing award."""
    awards = await _query(vq_service, "Sourcing_Award", [{"field": "Award_ID", "value": award_id}], limit=1)
    award = awards[0] if awards else {}
    if not award:
        return {"award_id": award_id, "drafted": False, "reason": "award_not_found"}

    scenarios = await _query(vq_service, "Sourcing_Scenario", [{"field": "Scenario_ID", "value": award.get("Scenario_ID")}], limit=1)
    scenario = scenarios[0] if scenarios else {}
    try:
        split = json.loads(scenario.get("Split_JSON") or "[]")
    except Exception:
        split = []
    events = await _query(vq_service, "RFx_Event", [{"field": "Event_ID", "value": award.get("Event_ID")}], limit=1)
    event = events[0] if events else {}

    lines_md = "\n".join(
        f"| {sp.get('vendor_id', '?')} | {sp.get('qty_pct', 0)}% | ${float(sp.get('unit_price', 0)):.2f} | {sp.get('plant_id', '')} |"
        for sp in split
    )
    body = (
        f"# Supply Contract Draft\n\n"
        f"**Award ID:** {award_id}\n\n"
        f"**RFx Event:** {event.get('Title', award.get('Event_ID'))} ({event.get('Category', '')})\n\n"
        f"**Effective Date:** {_now_iso()[:10]}\n\n"
        f"## Award Split\n\n"
        f"| Vendor | Share | Unit Price | Plant |\n"
        f"|--------|-------|------------|-------|\n"
        f"{lines_md}\n\n"
        f"## Terms\n\n"
        f"- **Modeled Savings:** {scenario.get('Modeled_Savings', 0)}%\n"
        f"- **Risk Score:** {scenario.get('Modeled_Risk_Score', 0)}\n"
        f"- **Concentration:** {scenario.get('Concentration_Pct', 0)}%\n"
        f"- **Approval Chain:** {award.get('Approval_Chain_JSON', '[]')}\n"
    )
    return {"award_id": award_id, "drafted": True, "template": template,
            "format": "markdown", "body": body, "generated_at": _now_iso()}


async def _convert_award_to_po(vq_service, award_id: str) -> Dict[str, Any]:
    """Mark the award as Issued and emit kickoff for PO creation."""
    awards = await _query(vq_service, "Sourcing_Award", [{"field": "Award_ID", "value": award_id}], limit=1)
    award = awards[0] if awards else {}
    if not award:
        return {"award_id": award_id, "converted": False, "reason": "award_not_found"}
    if award.get("Status") not in ("Approved",):
        return {"award_id": award_id, "converted": False,
                "reason": f"award status is {award.get('Status')}, requires Approved"}

    from src.services.control_plane.connector_runtime import emit_audit, get_sim, update_one
    try:
        sim = await get_sim("sourcing")
        previous, _ = await update_one(
            sim, "sourcing_cpq", "Sourcing_Award", "Award_ID", award_id,
            {"Status": "Issued", "Issued_At": _now_iso()},
        )
        await emit_audit(
            actor="ai-copilot", verb="convert_award_to_po", target=award_id,
            payload={"previous_status": previous.get("Status"), "new_status": "Issued"},
            api_id="sourcing.award.issue",
        )
        return {"award_id": award_id, "converted": True, "new_status": "Issued",
                "next_workflow": "WORKFLOW_CONTRACT_GENERATION_V1_0"}
    except Exception as e:
        cpq_buy_logger.warning(f"convert_award_to_po failed: {e}")
        return {"award_id": award_id, "converted": False, "reason": str(e)}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_cpq_buy_tools(registry: ToolRegistry, virtual_query_service=None) -> None:
    if not virtual_query_service:
        cpq_buy_logger.warning("Virtual query service not available — Sourcing CPQ tools not registered")
        return

    registry.register(Tool(
        name="launch_rfx",
        description="Create an RFx_Event row for a category and plant list. Returns Event_ID and a hint to invite vendors.",
        parameters={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Spend category (Raw_Material, Packaging, Co_Packer, Logistics, Services, Equipment)"},
                "plants": {"type": "array", "items": {"type": "string"}, "description": "Buyer plant IDs"},
                "target_qty": {"type": "number", "description": "Aggregate target quantity (optional)"},
                "due_date": {"type": "string", "description": "Bidding close date (YYYY-MM-DD)"},
                "title": {"type": "string", "description": "Event title (optional)"},
            },
            "required": ["category"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _launch_rfx(virtual_query_service, **kw),
        connector_api="sourcing.rfx.create",
        tags=["cpq-buy", "rfx", "write"],
    ))

    registry.register(Tool(
        name="recommend_vendor_panel",
        description="Pick top vendor candidates for an RFx_Event from Source_List ∩ active Vendor_Master, ranked by risk score and certifications.",
        parameters={
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "RFx_Event ID"},
                "top_n": {"type": "integer", "description": "Number of panel candidates"},
            },
            "required": ["event_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _recommend_vendor_panel(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-buy", "vendor", "analyze"],
    ))

    registry.register(Tool(
        name="solicit_vendors",
        description="Create RFx_Invitation rows for the provided vendor panel. Write-capable.",
        parameters={
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "RFx_Event ID"},
                "vendor_ids": {"type": "array", "items": {"type": "string"}, "description": "Vendor_IDs to invite"},
            },
            "required": ["event_id", "vendor_ids"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _solicit_vendors(virtual_query_service, **kw),
        connector_api="sourcing.rfx.invite",
        tags=["cpq-buy", "rfx", "write"],
    ))

    registry.register(Tool(
        name="score_vendor_response",
        description=(
            "Score a Vendor_Quote on a composite scale: price-vs-should-cost 40, lead time 15, "
            "risk 20, quality 15, sustainability 10."
        ),
        parameters={
            "type": "object",
            "properties": {"vendor_quote_id": {"type": "string", "description": "Vendor_Quote_ID"}},
            "required": ["vendor_quote_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _score_vendor_response(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-buy", "bid", "score"],
    ))

    registry.register(Tool(
        name="should_cost_model",
        description="Build a bottom-up should-cost benchmark per unit for a material from Commodity_Price + labor + overhead + freight.",
        parameters={
            "type": "object",
            "properties": {
                "material_id": {"type": "string", "description": "Material_ID"},
                "qty": {"type": "number", "description": "Reference quantity"},
            },
            "required": ["material_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _should_cost_model(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-buy", "should-cost"],
    ))

    registry.register(Tool(
        name="run_award_scenario",
        description=(
            "Build a Sourcing_Scenario for an RFx_Event using a split strategy "
            "(cost_optimal | risk_balanced | diversified). Persists the scenario."
        ),
        parameters={
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "RFx_Event ID"},
                "split_strategy": {"type": "string", "description": "cost_optimal | risk_balanced | diversified"},
            },
            "required": ["event_id"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _run_award_scenario(virtual_query_service, **kw),
        connector_api="sourcing.scenario.create",
        tags=["cpq-buy", "award", "scenario", "write"],
    ))

    registry.register(Tool(
        name="recommend_award_split",
        description=(
            "Run all three split strategies and return the Pareto-optimal scenario subject "
            "to the 60% concentration ceiling from sourcing-award-policy."
        ),
        parameters={
            "type": "object",
            "properties": {"event_id": {"type": "string", "description": "RFx_Event ID"}},
            "required": ["event_id"],
        },
        risk_level=RiskLevel.LOW_RISK_WRITE,
        execute=lambda **kw: _recommend_award_split(virtual_query_service, **kw),
        connector_api="sourcing.scenario.create",
        tags=["cpq-buy", "award", "ai", "recommend"],
    ))

    registry.register(Tool(
        name="draft_contract",
        description="Compose a markdown contract draft for an approved Sourcing_Award with split, prices, and policy attachments.",
        parameters={
            "type": "object",
            "properties": {
                "award_id": {"type": "string", "description": "Sourcing_Award ID"},
                "template": {"type": "string", "description": "Template name (default 'standard')"},
            },
            "required": ["award_id"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _draft_contract(virtual_query_service, **kw),
        tool_kind="analyze",
        tags=["cpq-buy", "contract"],
    ))

    registry.register(Tool(
        name="convert_award_to_po",
        description="Mark a Sourcing_Award as Issued and kick off the procurement-order creation chain.",
        parameters={
            "type": "object",
            "properties": {"award_id": {"type": "string", "description": "Sourcing_Award ID"}},
            "required": ["award_id"],
        },
        risk_level=RiskLevel.HIGH_RISK_WRITE,
        execute=lambda **kw: _convert_award_to_po(virtual_query_service, **kw),
        connector_api="sourcing.award.issue",
        requires_approval=True,
        tags=["cpq-buy", "award", "write"],
    ))

    cpq_buy_tool_names = [
        "launch_rfx", "recommend_vendor_panel", "solicit_vendors",
        "score_vendor_response", "should_cost_model",
        "run_award_scenario", "recommend_award_split",
        "draft_contract", "convert_award_to_po",
    ]
    for tool_name in cpq_buy_tool_names:
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "supply-chain"

    cpq_buy_logger.info(f"Sourcing CPQ tools registered: {len(cpq_buy_tool_names)} tools (bucket=supply-chain)")
