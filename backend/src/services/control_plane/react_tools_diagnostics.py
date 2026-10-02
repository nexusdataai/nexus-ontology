"""
ReAct Tools diagnostics service.

Three pure helper functions plus a curated canary-params catalogue that
power the ReAct Tools tab in the Diagnostics page:

    - validate_contracts(registry, connector_apis) -> ContractsReport
        Verifies every Tool's `parameters` JSON Schema is well-formed and
        cross-checks `connector_api` references + request_schema overlap.

    - validate_connector_apis(connector_apis) -> ConnectorAPIReport
        Verifies every ConnectorAPISpec is well-formed (target_system,
        operation, schemas) and counts caller tools per api_id.

    - run_canaries(registry, *, only_read_only) -> CanaryReport
        Invokes every tool with canary params from CANARY_PARAMS, records
        per-tool pass/fail/skip + duration_ms + result_preview. Read-only
        tools are safe; write tools tag themselves with
        ``actor='diagnostic-runner'`` so simulator audit rows stay
        filterable.

Pure-stdlib dependencies (no jsonschema, no FastAPI).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

rtd_logger = logger.bind(component="react-tools-diagnostics")

DIAGNOSTIC_ACTOR = "diagnostic-runner"

# ---------------------------------------------------------------------------
# Canary catalogue
# ---------------------------------------------------------------------------
#
# Per-tool default params for the smoke run. The map is authoritative for
# every tool currently registered in the live ToolRegistry. New tools
# without an entry will surface as ``status=skip, reason=no_canary_params``
# in the report - a forcing function for content authors.
#
# Diagnostic IDs (ACC-DIAG-1 / INV-DIAG-1 / OPP-DIAG-1 / DEL-DIAG-1) are
# intentional sentinels - they will not match production rows, which keeps
# pollution shapes predictable. Write tools that mutate-by-id will fail
# safely (no row to mutate -> tool returns an error structure that is
# captured as a fail/warn rather than corrupting real data).

CANARY_PARAMS: Dict[str, Dict[str, Any]] = {
    # --- read-only ---
    "discover_tables":             {"limit": 5},
    "discover_columns":            {"table_name": "Account"},
    "query_table":                 {"table_name": "Account", "limit": 1},
    "search_schema_knowledge":     {"query": "Account"},
    "search_enterprise_knowledge": {"query": "credit hold policy"},
    "query_virtual_entity":        {"entity_name": "Account", "limit": 1},
    "list_virtual_entities":       {},
    "get_entity_schema":           {"entity_name": "Account"},
    "get_inventory_position":      {"material_id": "MAT-DIAG-1"},
    "get_order_lifecycle":         {},
    "score_supplier_risk":         {},
    "match_order_delivery_invoice": {"opportunity_id": "OPP-DIAG-1"},
    "score_order_anomaly":         {"opportunity_id": "OPP-DIAG-1"},
    "project_cash_flow":           {},
    "generate_o2c_alerts":         {},
    "query_demand_forecast":       {},
    "simulate_promotion_impact":   {"sku": "SKU-DIAG-1", "region": "NA", "promotion_type": "discount"},
    "get_forecast_accuracy":       {},

    # --- writes (smoke; tagged with diagnostic actor) ---
    "create_forecast_override":    {
        "product_id": "PROD-DIAG-1", "region": "NA", "period": "2026-Q2",
        "override_qty": 1, "justification": "diagnostic canary",
    },
    "create_transfer_order":       {
        "from_plant": "PL-DIAG-1", "to_plant": "PL-DIAG-2",
        "material_id": "MAT-DIAG-1", "quantity": 1,
    },
    "hold_batch":                  {
        "batch_id": "BATCH-DIAG-1", "material_id": "MAT-DIAG-1", "reason": "diagnostic canary",
    },
    "update_customer_credit":      {
        "account_id": "ACC-DIAG-1", "new_credit_limit": 1000,
        "justification": "diagnostic canary",
    },
    "place_credit_hold":           {
        "account_id": "ACC-DIAG-1", "reason": "diagnostic canary",
    },
    "release_credit_hold":         {
        "account_id": "ACC-DIAG-1", "approved_by": DIAGNOSTIC_ACTOR,
    },
    "create_dispute_case":         {
        "opportunity_id": "OPP-DIAG-1", "invoice_id": "INV-DIAG-1",
    },
    "update_invoice_status":       {
        "invoice_id": "INV-DIAG-1", "new_status": "Open",
    },
    "send_dunning_notice":         {
        "invoice_id": "INV-DIAG-1", "customer_id": "ACC-DIAG-1", "days_overdue": 30,
    },
    "escalate_sla_breach":         {
        "opportunity_id": "OPP-DIAG-1", "sla_pct": 80.0,
    },
    "request_expedited_fulfillment": {
        "delivery_id": "DEL-DIAG-1",
    },
    "process_credit_note":         {
        "invoice_id": "INV-DIAG-1", "amount": 1.0,
    },
    "record_outcome":              {
        "action_id": "ACT-DIAG-1", "kpi_name": "DSO_Days",
        "kpi_before": 45.0, "kpi_after": 42.0,
    },
    "record_action":               {
        "action_type": "diagnostic_canary", "target_id": "OPP-DIAG-1", "status": "completed",
    },
    "update_account_terms":        {
        "customer_id": "ACC-DIAG-1", "payment_terms": "NET30",
    },
    "request_early_pay_discount":  {
        "invoice_id": "INV-DIAG-1", "discount_pct": 1.0,
    },

    # --- writes added by erp_writeback_tools ---
    "approve_purchase_order":      {
        "po_id": "PO-DIAG-1", "status": "Approved",
    },
    "record_payment":              {
        "invoice_id": "INV-DIAG-1", "customer_id": "ACC-DIAG-1",
        "amount": 1.0, "payment_method": "Wire",
    },
    "update_safety_stock":         {
        "material_id": "MAT-DIAG-1", "plant_id": "PL-DIAG-1",
        "safety_stock": 10, "reorder_point": 5,
    },
    "update_production_order":     {
        "production_order_id": "PROD-DIAG-1", "status": "Released",
    },
    "update_account_health":       {
        "account_id": "ACC-DIAG-1", "health_bucket": "Yellow",
    },
    "update_opportunity_stage":    {
        "opportunity_id": "OPP-DIAG-1", "stage": "Prospecting",
    },

    # --- writes added by customer_360 / inventory / production_quality /
    # notify modules (Phase 3). All call append_row, so no simulator
    # sentinel lookup is required for these canaries to pass.
    "apply_promo_discount":        {
        "name": "Diagnostic Promo", "discount_pct": 1.0,
        "promo_code": "DIAG-PROMO-1",
    },
    "assign_csm_outreach":         {
        "account_id": "ACC-DIAG-1", "subject": "Diagnostic CSM outreach",
        "priority": "Low",
    },
    "bundle_skus_for_liquidation": {
        "name": "Diagnostic Kit",
        "components": [{"sku": "SKU-DIAG-1", "quantity": 1}],
    },
    "open_capa_workflow":          {
        "subject": "Diagnostic CAPA", "severity": "low",
    },
    "schedule_predictive_maintenance": {
        "equipment_id": "EQ-DIAG-1", "scheduled_for": "2026-12-31T00:00:00Z",
        "maintenance_type": "Preventive",
    },
    "send_whatsapp_campaign":      {
        "template_id": "TMPL-DIAG-1",
        "recipients": [{"customer_id": "ACC-DIAG-1", "phone": "+10000000000"}],
    },
    "send_email_campaign":         {
        "subject": "Diagnostic email",
        "recipients": [{"customer_id": "ACC-DIAG-1", "email": "diag@example.com"}],
    },
    "send_slack_alert":            {
        "channel": "#diagnostic", "message": "diagnostic canary",
    },
}


# ---------------------------------------------------------------------------
# Contract validation
# ---------------------------------------------------------------------------

_VALID_TARGET_SYSTEMS = {"oracle", "sap", "sfdc", "external"}
_VALID_RISK_LEVELS = {"read_only", "low_risk_write", "high_risk_write"}
_VALID_HTTP_METHODS = {"GET", "POST", "PATCH", "PUT", "DELETE"}


def _issue(severity: str, code: str, message: str) -> Dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def validate_contracts(registry: Any, connector_apis: Any) -> Dict[str, Any]:
    """Validate every registered tool's contract against the live registries."""
    issues_by_tool: Dict[str, List[Dict[str, str]]] = {}
    error_count = 0
    warning_count = 0

    try:
        tools = list(registry.list_tools()) if registry is not None else []
    except Exception as e:
        rtd_logger.warning(f"registry.list_tools failed: {e}")
        tools = []

    try:
        known_apis = (
            {s.api_id: s for s in connector_apis.list_all()}
            if connector_apis is not None else {}
        )
    except Exception as e:
        rtd_logger.warning(f"connector_apis.list_all failed: {e}")
        known_apis = {}

    for tool in tools:
        problems: List[Dict[str, str]] = []
        params = getattr(tool, "parameters", None)

        if not isinstance(params, dict):
            problems.append(_issue("error", "missing_parameters", "Tool.parameters is not a dict"))
        else:
            ptype = params.get("type")
            if ptype != "object":
                problems.append(_issue(
                    "error", "parameters_type_not_object",
                    f"parameters.type should be 'object', got {ptype!r}",
                ))
            properties = params.get("properties")
            if not isinstance(properties, dict):
                problems.append(_issue(
                    "error", "missing_properties", "parameters.properties is missing or not a dict",
                ))
                properties = {}
            required = params.get("required") or []
            if not isinstance(required, list):
                problems.append(_issue("error", "required_not_list", "parameters.required must be a list"))
                required = []
            for r in required:
                if r not in properties:
                    problems.append(_issue(
                        "error", "required_not_in_properties",
                        f"required key '{r}' is not declared in properties",
                    ))
            for pname, pspec in properties.items():
                if not isinstance(pspec, dict):
                    problems.append(_issue(
                        "warning", "property_not_object",
                        f"property '{pname}' is not a JSON Schema object",
                    ))
                    continue
                has_type = "type" in pspec or "oneOf" in pspec or "anyOf" in pspec or "$ref" in pspec or "enum" in pspec
                if not has_type:
                    problems.append(_issue(
                        "warning", "property_missing_type",
                        f"property '{pname}' has no 'type' / oneOf / anyOf / enum",
                    ))

        cap_id = getattr(tool, "connector_api", None)
        if cap_id:
            api = known_apis.get(cap_id)
            if api is None:
                problems.append(_issue(
                    "error", "unknown_connector_api",
                    f"connector_api '{cap_id}' is not registered",
                ))
            else:
                req_schema = getattr(api, "request_schema", {}) or {}
                if isinstance(req_schema, dict) and req_schema and isinstance(params, dict):
                    req_keys = set(req_schema.keys())
                    tool_required = set(params.get("required") or [])
                    drift = sorted(tool_required - req_keys)
                    for k in drift:
                        problems.append(_issue(
                            "warning", "param_not_in_request_schema",
                            f"required tool param '{k}' not in connector_api '{cap_id}' request_schema",
                        ))

        if problems:
            issues_by_tool[tool.name] = problems
            error_count += sum(1 for p in problems if p["severity"] == "error")
            warning_count += sum(1 for p in problems if p["severity"] == "warning")

    overall = "healthy"
    if error_count > 0:
        overall = "unhealthy"
    elif warning_count > 0:
        overall = "degraded"

    return {
        "totals": {
            "checked": len(tools),
            "errors": error_count,
            "warnings": warning_count,
            "tools_with_issues": len(issues_by_tool),
        },
        "issues_by_tool": issues_by_tool,
        "overall": overall,
    }


async def validate_connector_apis(connector_apis: Any, registry: Any = None) -> Dict[str, Any]:
    """Walk every ConnectorAPISpec, validate well-formedness, count callers."""
    rows: List[Dict[str, Any]] = []
    issues_by_api: Dict[str, List[Dict[str, str]]] = {}
    error_count = 0
    warning_count = 0

    try:
        specs = list(connector_apis.list_all()) if connector_apis is not None else []
    except Exception as e:
        rtd_logger.warning(f"connector_apis.list_all failed: {e}")
        specs = []

    # Caller index: api_id -> tool names.
    callers: Dict[str, List[str]] = {}
    if registry is not None:
        try:
            for t in registry.list_tools():
                cap = getattr(t, "connector_api", None)
                if cap:
                    callers.setdefault(cap, []).append(t.name)
        except Exception as e:
            rtd_logger.warning(f"caller index build failed: {e}")

    # Audit-event stats: how many times each api_id has actually been
    # invoked (via tool or workbench) and when the most-recent call was.
    # Best-effort: missing simulator => empty maps (rows still render).
    audit_counts: Dict[str, int] = {}
    audit_last_ts: Dict[str, Optional[str]] = {}
    try:
        from src.services.control_plane import audit_index as _ai
        api_ids = [getattr(s, "api_id", "") for s in specs]
        audit_counts = await _ai.counts_for_apis(api_ids)
        audit_last_ts = await _ai.latest_ts_for_apis(api_ids)
    except Exception as e:
        rtd_logger.debug("audit-index lookup skipped: {}", e)
        audit_counts = {}
        audit_last_ts = {}

    for spec in specs:
        problems: List[Dict[str, str]] = []
        target = getattr(spec, "target_system", "")
        if target not in _VALID_TARGET_SYSTEMS:
            problems.append(_issue(
                "error", "invalid_target_system",
                f"target_system '{target}' must be one of {sorted(_VALID_TARGET_SYSTEMS)}",
            ))
        risk = getattr(spec, "risk_level", "")
        if risk not in _VALID_RISK_LEVELS:
            problems.append(_issue(
                "error", "invalid_risk_level",
                f"risk_level '{risk}' must be one of {sorted(_VALID_RISK_LEVELS)}",
            ))
        operation = getattr(spec, "operation", "") or ""
        method = ""
        path = ""
        if " " in operation:
            method, path = operation.split(" ", 1)
        if method not in _VALID_HTTP_METHODS or not path.startswith("/"):
            problems.append(_issue(
                "error", "invalid_operation",
                f"operation '{operation}' must be '<METHOD> <PATH>' with METHOD in {sorted(_VALID_HTTP_METHODS)} and PATH starting with /",
            ))
        req_schema = getattr(spec, "request_schema", {}) or {}
        res_schema = getattr(spec, "response_schema", {}) or {}
        if not req_schema:
            problems.append(_issue("warning", "empty_request_schema", "request_schema is empty"))
        if not res_schema:
            problems.append(_issue("warning", "empty_response_schema", "response_schema is empty"))

        callers_for = sorted(callers.get(spec.api_id, []))
        if not callers_for:
            problems.append(_issue(
                "warning", "orphan_no_tool_caller",
                "no registered tool references this connector_api",
            ))

        if problems:
            issues_by_api[spec.api_id] = problems
            error_count += sum(1 for p in problems if p["severity"] == "error")
            warning_count += sum(1 for p in problems if p["severity"] == "warning")

        api_audit_count = int(audit_counts.get(spec.api_id, 0) or 0)
        rows.append({
            "api_id": spec.api_id,
            "target_system": target,
            "operation": operation,
            "risk_level": risk,
            "description": getattr(spec, "description", "") or "",
            "tags": list(getattr(spec, "tags", []) or []),
            "has_request_schema": bool(req_schema),
            "has_response_schema": bool(res_schema),
            "tool_callers": callers_for,
            "tool_caller_count": len(callers_for),
            "simulator_writeback": bool(getattr(spec, "simulator_writeback", True)),
            "audit_count": api_audit_count,
            "last_invocation_ts": audit_last_ts.get(spec.api_id),
            "verified": api_audit_count > 0,
        })

    rows.sort(key=lambda r: r["api_id"])

    overall = "healthy"
    if error_count > 0:
        overall = "unhealthy"
    elif warning_count > 0:
        overall = "degraded"

    orphans = sorted([r["api_id"] for r in rows if r["tool_caller_count"] == 0])

    verified_count = sum(1 for r in rows if r.get("verified"))
    return {
        "totals": {
            "checked": len(rows),
            "errors": error_count,
            "warnings": warning_count,
            "orphans": len(orphans),
            "verified": verified_count,
            "never_invoked": len(rows) - verified_count,
            "by_target_system": _group_count(rows, "target_system"),
            "by_risk_level": _group_count(rows, "risk_level"),
        },
        "apis": rows,
        "issues_by_api": issues_by_api,
        "orphan_api_ids": orphans,
        "overall": overall,
    }


def _group_count(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in rows:
        v = str(r.get(key) or "unknown")
        out[v] = out.get(v, 0) + 1
    return out


# ---------------------------------------------------------------------------
# Canary execution
# ---------------------------------------------------------------------------

def _detect_negative_shape(result: Dict[str, Any]) -> Optional[str]:
    """Detect structured 'did-not-happen' shapes a tool may return without
    raising. Tools that wrap writes through ``_update_simulator_entity`` /
    ``_append_simulator_row`` surface their failures as
    ``{"updated": False, ...}`` or ``{"appended": False, ...}`` (possibly
    nested under ``simulator_update``); notify-style tools return
    ``{"action": "failed", "error": ...}``. Returns the failure message
    when a negative shape is detected, otherwise ``None``.
    """
    def _check(node: Any) -> Optional[str]:
        if not isinstance(node, dict):
            return None
        if node.get("action") == "failed":
            return str(node.get("error") or node.get("reason") or "action=failed")
        if node.get("updated") is False:
            return str(node.get("error") or node.get("reason") or "simulator update did not happen")
        if node.get("appended") is False:
            return str(node.get("error") or node.get("reason") or "simulator append did not happen")
        return None

    msg = _check(result)
    if msg:
        return msg
    for k in ("simulator_update", "invoice_update"):
        nested = result.get(k)
        msg = _check(nested)
        if msg:
            return f"{k}: {msg}"
    return None


def _preview(result: Any) -> str:
    if isinstance(result, dict):
        if "error" in result:
            return f"error: {str(result['error'])[:120]}"
        if "results" in result and isinstance(result["results"], list):
            return f"{len(result['results'])} results"
        if "count" in result:
            return f"count={result['count']}"
        if "rows" in result and isinstance(result["rows"], list):
            return f"{len(result['rows'])} rows"
        keys = list(result.keys())[:6]
        return "{" + ", ".join(keys) + "}"
    if isinstance(result, list):
        return f"{len(result)} items"
    s = str(result)
    return s if len(s) <= 120 else s[:117] + "..."


async def run_canaries(
    registry: Any,
    only_read_only: bool = False,
    tool_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Invoke every tool with its canary params; record per-tool result."""
    results: List[Dict[str, Any]] = []
    counts = {"pass": 0, "fail": 0, "skip": 0}
    started = time.monotonic()

    if registry is None:
        return {
            "totals": {"checked": 0, **counts, "duration_ms": 0},
            "results": [],
            "overall": "unhealthy",
            "error": "registry not configured",
        }

    try:
        tools = list(registry.list_tools())
    except Exception as e:
        return {
            "totals": {"checked": 0, **counts, "duration_ms": 0},
            "results": [],
            "overall": "unhealthy",
            "error": f"registry.list_tools failed: {e}",
        }

    # Order: read_only first so write side-effects come after the safe slice.
    def _risk_order(t: Any) -> int:
        try:
            v = t.risk_level.value if hasattr(t.risk_level, "value") else str(t.risk_level)
        except Exception:
            v = "read_only"
        return {"read_only": 0, "low_risk_write": 1, "high_risk_write": 2}.get(v, 9)

    tools.sort(key=lambda t: (_risk_order(t), t.name))

    selected = set(tool_ids or [])
    read_only_failures = 0

    for tool in tools:
        if selected and tool.name not in selected:
            continue
        risk = tool.risk_level.value if hasattr(tool.risk_level, "value") else str(tool.risk_level)
        if only_read_only and risk != "read_only":
            results.append({
                "tool_id": tool.name, "group": _infer_group(tool),
                "risk_level": risk, "status": "skip",
                "duration_ms": 0, "reason": "only_read_only_mode",
            })
            counts["skip"] += 1
            continue

        params = CANARY_PARAMS.get(tool.name)
        required = (tool.parameters or {}).get("required") or []
        if params is None:
            if required:
                results.append({
                    "tool_id": tool.name, "group": _infer_group(tool),
                    "risk_level": risk, "status": "skip",
                    "duration_ms": 0, "reason": "no_canary_params",
                    "missing_required": list(required),
                })
                counts["skip"] += 1
                continue
            params = {}

        # Tag write canaries with the diagnostic actor when the tool's
        # parameters define an `actor` field (best-effort; harmless if not).
        invoke_params = dict(params)
        if isinstance(tool.parameters, dict):
            tool_props = (tool.parameters.get("properties") or {})
            if "actor" in tool_props and "actor" not in invoke_params:
                invoke_params["actor"] = DIAGNOSTIC_ACTOR

        t0 = time.monotonic()
        status = "pass"
        result_value: Any = None
        error_msg: Optional[str] = None
        try:
            result_value = await registry.execute(tool.name, invoke_params)
        except Exception as e:
            status = "fail"
            error_msg = str(e)

        elapsed_ms = int((time.monotonic() - t0) * 1000)

        if status == "pass" and isinstance(result_value, dict) and "error" in result_value:
            status = "fail"
            error_msg = str(result_value["error"])

        if status == "pass" and isinstance(result_value, dict):
            neg_msg = _detect_negative_shape(result_value)
            if neg_msg:
                status = "fail"
                error_msg = neg_msg

        if status == "fail" and risk == "read_only":
            read_only_failures += 1

        # Surface the simulator-vs-real mode the tool actually used.
        # FDW tools propagate it as result["mode"]; virtual-query tools
        # nest it under metadata; otherwise leave None.
        executed_mode: Optional[str] = None
        if isinstance(result_value, dict):
            if isinstance(result_value.get("mode"), str):
                executed_mode = result_value["mode"]
            else:
                meta = result_value.get("metadata")
                if isinstance(meta, dict) and isinstance(meta.get("mode"), str):
                    executed_mode = meta["mode"]

        record: Dict[str, Any] = {
            "tool_id": tool.name,
            "group": _infer_group(tool),
            "risk_level": risk,
            "requires_approval": bool(getattr(tool, "requires_approval", False)),
            "connector_api": getattr(tool, "connector_api", None),
            "status": status,
            "duration_ms": elapsed_ms,
            "result_preview": _preview(result_value) if result_value is not None else (error_msg or ""),
            "marker": DIAGNOSTIC_ACTOR if risk != "read_only" else None,
            "mode": executed_mode,
            "params": invoke_params,
        }
        if error_msg and status == "fail":
            record["error"] = error_msg
        results.append(record)
        counts[status] += 1

    duration = int((time.monotonic() - started) * 1000)
    overall = "healthy"
    if read_only_failures > 0:
        overall = "unhealthy"
    elif counts["fail"] > 0:
        overall = "degraded"

    return {
        "totals": {
            "checked": len(results),
            **counts,
            "read_only_failures": read_only_failures,
            "duration_ms": duration,
        },
        "results": results,
        "overall": overall,
    }


def _infer_group(tool: Any) -> str:
    tags = list(getattr(tool, "tags", []) or [])
    if tags:
        return str(tags[0])
    name = tool.name
    if name.startswith("query_") or name in {"list_virtual_entities"}:
        return "virtual_query"
    if "rag" in name or "search_enterprise" in name:
        return "rag"
    if "fdw" in name or name in {"discover_tables", "discover_columns", "query_table"}:
        return "fdw"
    if any(k in name for k in (
        "hold", "credit", "dunning", "invoice", "case", "outcome",
        "discount", "expedite", "dispute", "payment", "credit_note",
    )):
        return "o2c"
    if "forecast" in name or "demand" in name or "promotion" in name:
        return "forecast"
    if "supplier" in name or "transfer" in name or "batch" in name:
        return "supply_chain"
    return "misc"


# ---------------------------------------------------------------------------
# Registry health
# ---------------------------------------------------------------------------

def registry_health(
    registry: Any,
    automation_indexer: Any = None,
    use_case_dry_run: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Snapshot of the live ToolRegistry with use-case usage counters."""
    out: Dict[str, Any] = {
        "totals": {
            "registered_tools": 0,
            "yaml_tools": 0,
            "yaml_only_orphans": 0,
            "registry_only_orphans": 0,
            "by_group": {},
            "by_risk_level": {},
        },
        "tools": [],
        "yaml_only_orphans": [],
        "registry_only_orphans": [],
        "overall": "healthy",
    }

    if registry is None:
        out["overall"] = "unhealthy"
        return out

    try:
        tools = list(registry.list_tools())
    except Exception:
        tools = []

    out["totals"]["registered_tools"] = len(tools)

    # Use-case usage counts.
    usage_by_tool: Dict[str, int] = {}
    if use_case_dry_run is None and automation_indexer is not None:
        try:
            # The dry_run is async; callers can pass the awaited result instead.
            # Skip silently when called sync without a precomputed report.
            use_case_dry_run = None
        except Exception:
            use_case_dry_run = None
    if use_case_dry_run:
        for uc in use_case_dry_run.get("use_cases", []):
            for tname in uc.get("tool_refs", []) or []:
                usage_by_tool[tname] = usage_by_tool.get(tname, 0) + 1

    # YAML coverage via the tool-catalogue helper if present.
    yaml_ids: set = set()
    if automation_indexer is not None:
        try:
            tools_yaml_root = getattr(automation_indexer, "_tools_yaml_root", None)
            if tools_yaml_root is not None and tools_yaml_root.exists():
                from src.models.automation_models import ToolDoc
                import yaml as _yaml
                for fpath in sorted(tools_yaml_root.rglob("*.yaml")):
                    try:
                        with fpath.open("r", encoding="utf-8") as f:
                            doc = ToolDoc(**(_yaml.safe_load(f) or {}))
                        yaml_ids.add(doc.tool_id)
                    except Exception:
                        continue
        except Exception:
            yaml_ids = set()

    out["totals"]["yaml_tools"] = len(yaml_ids)

    by_group: Dict[str, int] = {}
    by_risk: Dict[str, int] = {}

    for tool in tools:
        risk = tool.risk_level.value if hasattr(tool.risk_level, "value") else str(tool.risk_level)
        group = _infer_group(tool)
        by_group[group] = by_group.get(group, 0) + 1
        by_risk[risk] = by_risk.get(risk, 0) + 1
        out["tools"].append({
            "tool_id": tool.name,
            "display_name": tool.name.replace("_", " ").title(),
            "group": group,
            "description": getattr(tool, "description", "") or "",
            "risk_level": risk,
            "requires_approval": bool(getattr(tool, "requires_approval", False)),
            "cacheable": bool(getattr(tool, "cacheable", False)),
            "connector_api": getattr(tool, "connector_api", None),
            "tags": list(getattr(tool, "tags", []) or []),
            "parameters": tool.parameters,
            "yaml_present": tool.name in yaml_ids,
            "use_case_refs": usage_by_tool.get(tool.name, 0),
            "has_canary": tool.name in CANARY_PARAMS,
        })

    out["tools"].sort(key=lambda r: (r["group"], r["tool_id"]))
    out["totals"]["by_group"] = by_group
    out["totals"]["by_risk_level"] = by_risk

    registry_names = {t.name for t in tools}
    # Dynamic (Tool-Builder / DynamoDB-authored) tools live outside the
    # curated YAML catalogue by design; exclude them from the orphan
    # calculation so user-authored tools never push Registry Health to
    # ``degraded``. They still appear in the rendered ``tools`` list.
    static_registry_names = {
        t.name for t in tools if "dynamic" not in (getattr(t, "tags", []) or [])
    }
    yaml_only = sorted(yaml_ids - registry_names)
    registry_only = sorted(static_registry_names - yaml_ids)
    out["yaml_only_orphans"] = yaml_only
    out["registry_only_orphans"] = registry_only
    out["totals"]["yaml_only_orphans"] = len(yaml_only)
    out["totals"]["registry_only_orphans"] = len(registry_only)

    if yaml_only:
        out["overall"] = "unhealthy"
    elif registry_only:
        out["overall"] = "degraded"

    return out


# ---------------------------------------------------------------------------
# Single-tool execute (interactive Try-it)
# ---------------------------------------------------------------------------

async def execute_tool(
    registry: Any,
    tool_name: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Run one tool with caller-supplied params; return the same shape as run_canaries' result row."""
    if registry is None:
        return {"tool_id": tool_name, "status": "fail", "error": "registry not configured"}
    tool = registry.get(tool_name)
    if tool is None:
        return {"tool_id": tool_name, "status": "fail", "error": f"unknown tool: {tool_name}"}

    risk = tool.risk_level.value if hasattr(tool.risk_level, "value") else str(tool.risk_level)
    invoke = dict(params or {})
    if isinstance(tool.parameters, dict):
        tool_props = tool.parameters.get("properties") or {}
        if "actor" in tool_props and "actor" not in invoke:
            invoke["actor"] = DIAGNOSTIC_ACTOR

    t0 = time.monotonic()
    status = "pass"
    result_value: Any = None
    error_msg: Optional[str] = None
    try:
        result_value = await registry.execute(tool_name, invoke)
    except Exception as e:
        status = "fail"
        error_msg = str(e)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    if status == "pass" and isinstance(result_value, dict) and "error" in result_value:
        status = "fail"
        error_msg = str(result_value["error"])

    executed_mode: Optional[str] = None
    if isinstance(result_value, dict):
        if isinstance(result_value.get("mode"), str):
            executed_mode = result_value["mode"]
        else:
            meta = result_value.get("metadata")
            if isinstance(meta, dict) and isinstance(meta.get("mode"), str):
                executed_mode = meta["mode"]

    return {
        "tool_id": tool_name,
        "risk_level": risk,
        "status": status,
        "duration_ms": elapsed_ms,
        "result_preview": _preview(result_value) if result_value is not None else (error_msg or ""),
        "result": result_value,
        "marker": DIAGNOSTIC_ACTOR if risk != "read_only" else None,
        "mode": executed_mode,
        "params": invoke,
        "error": error_msg,
    }
