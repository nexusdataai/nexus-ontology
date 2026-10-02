"""
Tool output hints for the Journey Builder.

The Journey Builder canvas needs to suggest "what keys can I read out
of this tool's result?" so a user can wire the producing tool's output
into a consuming tool's input port. This module is the small static
catalogue that answers that question, plus a heuristic fallback so
even tools without an explicit entry surface something useful.

Hints are **documentation only**, not enforced types. The runtime
substitution engine in ``_param_substitution.py`` is dynamic, so the
hints just help authors pick a key path that is likely to resolve.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class OutputHint:
    """One suggested output path for a tool node.

    Attributes:
        key:    Dotted path against the result dict, e.g. ``results``,
                ``results.0.customer_id``. The Builder UI inserts
                ``${steps.<src>.<key>}`` verbatim, so the key is the
                exact substitution sub-path the runtime will walk.
        kind:   Free-form classifier surfaced as a small chip in the UI:
                ``scalar`` / ``scalar.id`` / ``array`` / ``object`` /
                ``status``.
        desc:   Human-readable description of the shape.
    """

    key: str
    kind: str = "scalar"
    desc: str = ""


def _scalar(key: str, desc: str = "") -> OutputHint:
    return OutputHint(key=key, kind="scalar", desc=desc)


def _scalar_id(key: str, desc: str = "") -> OutputHint:
    return OutputHint(key=key, kind="scalar.id", desc=desc)


def _array(key: str, desc: str = "") -> OutputHint:
    return OutputHint(key=key, kind="array", desc=desc)


def _status(key: str = "action", desc: str = "Action verb") -> OutputHint:
    return OutputHint(key=key, kind="status", desc=desc)


# ---------------------------------------------------------------------------
# Explicit per-tool hints
# ---------------------------------------------------------------------------
#
# Only the most frequently-chained tools have explicit entries; every
# other registered tool falls back to ``_heuristic_for_tool`` below.

TOOL_OUTPUT_HINTS: Dict[str, List[OutputHint]] = {
    # ---- C360 analyzers -------------------------------------------------
    "find_churning_customers": [
        _scalar("count", "Number of at-risk customers returned"),
        _array("results", "[{customer_id, churn_score, top_features, last_touch}]"),
        _scalar_id("results.0.customer_id", "Top at-risk customer id"),
        _scalar("results.0.churn_score", "Top at-risk churn score"),
    ],
    "find_upsell_candidates": [
        _scalar("count"),
        _array("results", "[{customer_id, upsell_score, recommended_sku, expected_uplift_usd}]"),
        _scalar_id("results.0.customer_id"),
        _scalar("results.0.recommended_sku", "Top upsell SKU"),
    ],
    "score_customer_lifetime_value": [
        _scalar("count"),
        _array("results", "[{customer_id, clv_usd, recurring_arr, tier}]"),
        _scalar("result.clv_usd", "Single-customer mode CLV (USD)"),
        _scalar("result.tier", "Tier label (Platinum/Gold/...)"),
    ],

    # ---- Inventory analyzers -------------------------------------------
    "find_excess_inventory_near_expiry": [
        _scalar("count"),
        _array("results", "[{material_id, qty, expiry_date, plant, writeoff_at_risk_usd}]"),
        _scalar_id("results.0.material_id"),
    ],
    "find_slow_movers": [
        _scalar("count"),
        _array("results", "[{material_id, weekly_velocity, on_hand_qty, plant}]"),
    ],
    "project_inventory_writeoff": [
        _scalar("projected_writeoff_usd"),
        OutputHint(key="by_category", kind="object", desc="{near_expiry, slow_movers, obsolete}"),
    ],

    # ---- Supply Chain Risk ---------------------------------------------
    "find_disrupted_lanes": [
        _scalar("count"),
        _array("results", "[{lane_id, from, to, disruption_score, cause}]"),
    ],
    "score_supplier_disruption_risk": [
        _scalar("count"),
        _array("results", "[{vendor_id, vendor_name, risk_score, drivers}]"),
        _scalar_id("result.vendor_id", "Single-vendor mode id"),
        _scalar("result.risk_score"),
    ],

    # ---- Production Quality --------------------------------------------
    "find_capa_recurrence": [
        _scalar("count"),
        _array("results", "[{root_cause_code, description, occurrences, linked_capas, lines_affected}]"),
    ],
    "score_oee_decline": [
        _scalar("count"),
        _array("results", "[{line_id, oee_pct, delta_30d_pct, drivers}]"),
        _scalar_id("result.line_id"),
        _scalar("result.oee_pct"),
    ],
    "predict_equipment_failure": [
        _scalar("count"),
        _array("results", "[{equipment_id, failure_probability, expected_failure_window, leading_signals}]"),
        _scalar_id("result.equipment_id"),
        _scalar("result.failure_probability"),
    ],

    # ---- Procurement ---------------------------------------------------
    "find_maverick_spend": [_scalar("count"), _array("results")],
    "find_renegotiation_candidates": [_scalar("count"), _array("results")],

    # ---- Demand Forecast -----------------------------------------------
    "find_volatile_skus": [_scalar("count"), _array("results")],
    "find_forecast_bias": [_scalar("count"), _array("results")],

    # ---- ESG -----------------------------------------------------------
    "find_co2_breach_facilities": [_scalar("count"), _array("results")],
    "find_compliance_breaches": [_scalar("count"), _array("results")],

    # ---- O2C read / analyze --------------------------------------------
    "match_order_delivery_invoice": [
        _scalar("match_status", "matched | quantity_mismatch | price_mismatch | missing_*"),
        _scalar_id("opportunity_id"),
        _scalar_id("invoice_id"),
        _scalar_id("delivery_id"),
        _scalar("order_amount"),
        _scalar("invoiced_amount"),
        _array("discrepancies"),
    ],
    "score_order_anomaly": [
        _scalar("opportunity_id"),
        _scalar("anomaly_score", "0-100"),
        _array("anomalies"),
        _scalar("payment_count"),
    ],
    "project_cash_flow": [
        _scalar("total_open_ar"),
        _scalar("dso"),
        _scalar("at_risk_amount"),
        _array("projected_weekly"),
        _scalar("total_payments"),
    ],
    "generate_o2c_alerts": [
        _array("alerts"),
        OutputHint(key="kpis", kind="object", desc="{dso, match_rate, leakage_rate, ...}"),
    ],

    # ---- Virtual query -------------------------------------------------
    "query_virtual_entity": [
        _scalar("entity"),
        _scalar("total"),
        _array("rows", "[{<row-shape from VDL>}]"),
        _scalar("rows.0", "First matching row"),
    ],
    "list_virtual_entities": [
        _scalar("total"),
        _array("entities"),
    ],
    "get_entity_schema": [
        _scalar("entity"),
        OutputHint(key="schema", kind="object", desc="Full virtual-entity schema"),
    ],

    # ---- O2C / C360 / Inventory mutators -------------------------------
    "place_credit_hold": [_status("action"), _scalar_id("account_id"), _scalar("reason")],
    "release_credit_hold": [_status("action"), _scalar_id("account_id"), _scalar("approved_by")],
    "create_dispute_case": [_status("action"), _scalar_id("case_id"), _scalar_id("invoice_id")],
    "update_invoice_status": [_status("action"), _scalar_id("invoice_id"), _scalar("new_status")],
    "send_dunning_notice": [_status("action"), _scalar_id("notice_id"), _scalar_id("invoice_id")],
    "process_credit_note": [_status("action"), _scalar_id("credit_note_id"), _scalar("amount")],
    "apply_promo_discount": [_status("action"), _scalar_id("promo_id"), _scalar("promo_code")],
    "assign_csm_outreach": [_status("action"), _scalar_id("task_id"), _scalar_id("account_id")],
    "bundle_skus_for_liquidation": [_status("action"), _scalar_id("kit_id"), _scalar("kit_sku")],
    "send_whatsapp_campaign": [_status("action"), _scalar_id("campaign_id"), _scalar("queued")],
    "send_email_campaign": [_status("action"), _scalar_id("campaign_id"), _scalar("queued")],
    "send_slack_alert": [_status("action"), _scalar("channel"), _scalar("message_ts")],
    "open_capa_workflow": [_status("action"), _scalar_id("capa_id"), _scalar("severity")],
    "schedule_predictive_maintenance": [_status("action"), _scalar_id("maintenance_order_id")],
    "block_supplier_orders": [_status("action"), _scalar_id("supplier_id"), _scalar("status")],
    "approve_purchase_order": [_status("action"), _scalar_id("po_id"), _scalar("status")],
    "record_payment": [_status("action"), _scalar_id("payment_id"), _scalar("amount")],
    "update_safety_stock": [_status("action"), _scalar_id("material_id"), _scalar_id("plant_id")],
    "update_production_order": [_status("action"), _scalar_id("production_order_id")],
    "update_account_health": [_status("action"), _scalar_id("account_id")],
    "update_opportunity_stage": [_status("action"), _scalar_id("opportunity_id")],
    "record_outcome": [_status("action"), _scalar_id("outcome_id"), _scalar("delta_value")],
    "record_action": [_status("action"), _scalar_id("action_id")],
}


# ---------------------------------------------------------------------------
# Heuristic fallback
# ---------------------------------------------------------------------------


def _heuristic_for_tool(tool_name: str, *, connector_api: Optional[str] = None,
                       risk_level: Optional[str] = None) -> List[OutputHint]:
    """Best-effort hints for tools without an explicit catalogue entry.

    Patterns:

    - ``find_*`` / ``score_*`` analyzers return ``{count, results[]}``.
    - ``discover_*`` / ``list_*`` return a list keyed on a noun.
    - ``query_*`` returns rows.
    - Mutator / notify tools (``connector_api`` set OR risk_level !=
      read_only) return ``{action, ...}``.
    - Everything else: empty list -- the UI shows a "manual key entry"
      affordance.
    """
    name = (tool_name or "").lower()
    if name.startswith("find_") or name.startswith("score_"):
        return [_scalar("count"), _array("results")]
    if name.startswith("discover_") or name.startswith("list_"):
        return [_array("results"), _scalar("count")]
    if name.startswith("query_"):
        return [_array("rows"), _scalar("total")]
    if connector_api or (risk_level and risk_level != "read_only"):
        return [_status("action")]
    return []


# ---------------------------------------------------------------------------
# Public API: build the full hints map for the Journey Builder UI
# ---------------------------------------------------------------------------


def build_hints_map(registry: object | None) -> Dict[str, List[Dict[str, str]]]:
    """Return ``{ tool_name: [{key, kind, desc}, ...] }`` for every
    registered tool. Explicit entries win; everything else falls back to
    ``_heuristic_for_tool``.

    The returned shape is plain dicts (not ``OutputHint`` dataclasses)
    so the HTTP handler can serialise it without an adapter.
    """
    out: Dict[str, List[Dict[str, str]]] = {}
    tools: List[object] = []
    if registry is not None:
        try:
            tools = list(registry.list_tools())
        except Exception:
            tools = []

    for t in tools:
        name = getattr(t, "name", None)
        if not name:
            continue
        if name in TOOL_OUTPUT_HINTS:
            hints = TOOL_OUTPUT_HINTS[name]
        else:
            hints = _heuristic_for_tool(
                name,
                connector_api=getattr(t, "connector_api", None),
                risk_level=getattr(getattr(t, "risk_level", None), "value", None)
                            or str(getattr(t, "risk_level", "") or ""),
            )
        out[name] = [{"key": h.key, "kind": h.kind, "desc": h.desc} for h in hints]

    # Surface every explicit-only entry too, even if the live registry
    # missed it (lets the UI render previews for known tools that have
    # not booted yet on this replica).
    for name, hints in TOOL_OUTPUT_HINTS.items():
        out.setdefault(name, [{"key": h.key, "kind": h.kind, "desc": h.desc} for h in hints])
    return out
