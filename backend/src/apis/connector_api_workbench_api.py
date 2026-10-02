"""
Connector API Workbench.

Cross-system surface that exercises every ``ConnectorAPISpec`` end-to-end
and verifies the simulator actually moved.

Routes:

  GET  /api/v1/connector-apis                        list with audit_count + tool_callers
  GET  /api/v1/connector-apis/diagnostic             composite diagnostic report (6 sections)
  POST /api/v1/connector-apis/smoke-test             drive every spec through invoke
  GET  /api/v1/connector-apis/{api_id}               full spec + recent audit events
  GET  /api/v1/connector-apis/{api_id}/canary-payload payload built from request_schema
  POST /api/v1/connector-apis/{api_id}/invoke        dispatch + before/after diff + verdict
  GET  /api/v1/connector-apis/{api_id}/events        recent audit events for the api

The invoke route forwards ``spec.operation`` over HTTP to
``SIMULATOR_BASE_URL`` (the standalone nexus-simulator service).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Body, HTTPException, Path, Query
from loguru import logger
from pydantic import BaseModel

from src.services.control_plane import (
    audit_index,
    connector_apis as _ca,
    connector_apis_diagnostic as _cad,
)
from src.services.control_plane.connector_runtime import fetch_rows, get_sim
from src.services.simulator_fdw_client import get_simulator_http_client, require_simulator_base_url

router = APIRouter(prefix="/api/v1/connector-apis", tags=["Connector API Workbench"])
wb_logger = logger.bind(component="connector-api-workbench")

DIAGNOSTIC_ACTOR = "diagnostic-runner"

_app: Any = None
_tool_registry: Any = None


def configure(app: Any, tool_registry: Any = None) -> None:
    """Wire the FastAPI app + tool registry once at startup."""
    global _app, _tool_registry
    _app = app
    _tool_registry = tool_registry
    # Bootstrap the DDB-backed Connector API Registry from the Python seed
    # manifest so first-run deployments have the full catalogue in DDB.
    # Idempotent - short-circuits if any CONNAPI# rows already exist.
    try:
        import asyncio as _asyncio
        from src.services.data_plane.connector_api_registry_service import (
            get_connector_api_registry,
            is_ddb_registry_enabled,
        )
        if is_ddb_registry_enabled():
            svc = get_connector_api_registry()
            _asyncio.get_event_loop().create_task(
                svc.bootstrap_if_empty(_ca._seed_specs())
            )
    except Exception as _e:
        wb_logger.debug("ConnectorApiRegistry bootstrap task scheduling failed: {}", _e)


# ---------------------------------------------------------------------------
# Verification hints - per-api_id snapshot recipe
# ---------------------------------------------------------------------------
#
# Each hint tells us how to look up the row affected by an api invocation
# so we can diff before/after and prove the simulator moved.
#
#   sim_key   - which simulator owns the table (oracle/sap/sfdc/external)
#   schema    - simulator schema name
#   table     - table name (or None for POST endpoints with prefix-suffixed tables)
#   pk_col    - column to match on
#   pk_arg    - field in the request body / path that supplies the pk value
#   mode      - "patch"  -> diff a single existing row
#               "post"   -> count delta + last appended row
#               "post_prefix" -> like post, but the table name is built from a
#                               prefix arg (e.g. external.alert.create)
#
# api_ids absent from this map degrade gracefully: invoke still hits the
# endpoint and emits audit, but verification.before/after stay null.

#
# Optional fields:
#   companion_table  - schema-qualified table to read REAL FK values from
#                      when the body has fields the table itself doesn't carry
#                      (e.g. credit_note.create needs invoice_id + customer_id
#                      from a real Oracle_AR_Invoice row).
#   companion_keys   - mapping of {body_field: column_in_companion_table}
_HINTS: Dict[str, Dict[str, Any]] = {
    # --- Oracle ---
    "oracle.invoice.status.set": {
        "sim_key": "oracle", "schema": "oracle_erp", "table": "Oracle_AR_Invoice",
        "pk_col": "Invoice_ID", "pk_arg": "invoice_id", "mode": "patch",
    },
    "oracle.credit_note.create": {
        "sim_key": "oracle", "schema": "oracle_erp", "table": "Oracle_AR_Credit_Note",
        "pk_col": "Credit_Note_ID", "mode": "post",
        "companion_table": ("oracle", "oracle_erp", "Oracle_AR_Invoice"),
        "companion_keys": {"invoice_id": "Invoice_ID", "customer_id": "Customer_ID"},
    },
    "oracle.payment.record": {
        "sim_key": "oracle", "schema": "oracle_erp", "table": "Oracle_AR_Payment",
        "pk_col": "Payment_ID", "mode": "post",
        "companion_table": ("oracle", "oracle_erp", "Oracle_AR_Invoice"),
        "companion_keys": {"invoice_id": "Invoice_ID", "customer_id": "Customer_ID"},
    },
    "oracle.invoice.discount.offer": {
        "sim_key": "oracle", "schema": "oracle_erp", "table": "Oracle_AR_Invoice",
        "pk_col": "Invoice_ID", "pk_arg": "invoice_id", "mode": "patch",
    },
    "oracle.customer.terms.set": {
        "sim_key": "oracle", "schema": "oracle_erp", "table": "Oracle_AR_Customer",
        "pk_col": "Customer_ID", "pk_arg": "customer_id", "mode": "patch",
    },
    "oracle.purchase_order.approve": {
        "sim_key": "oracle", "schema": "oracle_erp", "table": "Oracle_Purchase_Order",
        "pk_col": "PO_ID", "pk_arg": "po_id", "mode": "patch",
    },

    # --- SAP ---
    "sap.delivery.expedite": {
        "sim_key": "sap", "schema": "sap_s4hana", "table": "Delivery_Document",
        "pk_col": "Delivery_ID", "pk_arg": "delivery_id", "mode": "patch",
    },
    "sap.warehouse_transfer.create": {
        "sim_key": "sap", "schema": "sap_s4hana", "table": "Warehouse_Transfer",
        "pk_col": "Transfer_ID", "mode": "post",
        "companion_table": ("sap", "sap_s4hana", "Material_Plant"),
        "companion_keys": {"material_id": "Material_ID", "from_plant": "Plant_ID"},
    },
    "sap.batch.hold": {
        "sim_key": "sap", "schema": "sap_s4hana", "table": "Batch_Master",
        "pk_col": "Batch_ID", "pk_arg": "batch_id", "mode": "patch",
    },
    "sap.production_order.update": {
        "sim_key": "sap", "schema": "sap_s4hana", "table": "Production_Order",
        "pk_col": "Order_ID", "pk_arg": "production_order_id", "mode": "patch",
    },
    "sap.material_plant.reorder": {
        "sim_key": "sap", "schema": "sap_s4hana", "table": "Material_Plant",
        "pk_col": "Material_ID", "pk_arg": "material_id", "mode": "patch",
        "companion_keys": {"plant_id": "Plant_ID"},
    },

    # --- SFDC ---
    "sfdc.account.credit_hold.set": {
        "sim_key": "simulator", "schema": "sfdc_itxp2dev", "table": "Account",
        "pk_col": "Account_ID", "pk_arg": "account_id", "mode": "patch",
    },
    "sfdc.case.create": {
        "sim_key": "simulator", "schema": "sfdc_itxp2dev", "table": "Case",
        "pk_col": "Case_ID", "mode": "post",
        "companion_table": ("simulator", "sfdc_itxp2dev", "Account"),
        "companion_keys": {"account_id": "Account_ID"},
    },
    "sfdc.opportunity.update": {
        "sim_key": "simulator", "schema": "sfdc_itxp2dev", "table": "Opportunity",
        "pk_col": "Opportunity_ID", "pk_arg": "opportunity_id", "mode": "patch",
    },
    "sfdc.account.churn_risk.set": {
        "sim_key": "simulator", "schema": "sfdc_itxp2dev", "table": "Account",
        "pk_col": "Account_ID", "pk_arg": "account_id", "mode": "patch",
    },
    "sfdc.forecast_override.create": {
        "sim_key": "simulator", "schema": "sfdc_itxp2dev", "table": "Forecast_Override",
        "pk_col": "Override_ID", "mode": "post",
    },

    # --- External ---
    "external.dunning_notice.create": {
        "sim_key": "external", "schema": "external_sources", "table": "Dunning_Notice",
        "pk_col": "Notice_ID", "mode": "post",
    },
    "external.audit_event.create": {
        "sim_key": "external", "schema": "external_sources", "table": "Audit_Event",
        "pk_col": "event_id", "mode": "post",
    },
    "external.alert.create": {
        "sim_key": "external", "schema": "external_sources",
        "table_prefix_arg": "prefix", "table_suffix": "_Alert",
        "pk_col": "alert_id", "mode": "post_prefix",
    },
    "external.outcome.write": {
        "sim_key": "external", "schema": "external_sources",
        "table_prefix_arg": "prefix", "table_suffix": "_Outcome_Tracker",
        "pk_col": "outcome_id", "mode": "post_prefix",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _operation_parts(operation: str) -> Tuple[str, str]:
    if " " not in operation:
        raise HTTPException(status_code=500, detail=f"malformed operation: {operation!r}")
    method, path = operation.split(" ", 1)
    return method.upper(), path


def _substitute_path(path: str, body: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Replace ``{name}`` placeholders in path with body values; remove those
    keys from the body so they aren't double-sent.  Returns (resolved_path,
    remaining_body).
    """
    remaining = dict(body or {})
    out = path
    while True:
        i = out.find("{")
        if i < 0:
            break
        j = out.find("}", i + 1)
        if j < 0:
            break
        name = out[i + 1 : j]
        val = remaining.pop(name, None)
        if val is None:
            raise HTTPException(
                status_code=400,
                detail=f"missing path param {name!r} for {path}",
            )
        out = out[:i] + str(val) + out[j + 1 :]
    return out, remaining


def _canary_value(name: str, type_hint: str) -> Any:
    """Fabricate a safe canary value for a request_schema field."""
    t = (type_hint or "").rstrip("?").lower()
    optional_marker = type_hint.endswith("?") if isinstance(type_hint, str) else False
    if t == "boolean":
        return True if not optional_marker else True
    if t == "integer":
        return 1
    if t == "number":
        return 1.0
    if t == "object":
        return {"diagnostic": True}
    if t == "array" or t.startswith("array"):
        if "string" in t:
            return ["DIAG-1"]
        if "number" in t or "integer" in t:
            return [1]
        return []
    nl = name.lower()
    if "id" in nl:
        if "invoice" in nl: return "INV-DIAG-1"
        if "account" in nl or "customer" in nl: return "ACC-DIAG-1"
        if "opportunity" in nl: return "OPP-DIAG-1"
        if "case" in nl: return "CASE-DIAG-1"
        if "delivery" in nl: return "DEL-DIAG-1"
        if "batch" in nl: return "BATCH-DIAG-1"
        if "material" in nl or "sku" in nl: return "MAT-DIAG-1"
        if "plant" in nl: return "PL-DIAG-1"
        if "po" in nl: return "PO-DIAG-1"
        if "production_order" in nl: return "PROD-DIAG-1"
        if "transfer" in nl: return "WT-DIAG-1"
        if "action" in nl: return "ACT-DIAG-1"
        if "override" in nl: return "OV-DIAG-1"
        return f"{name.upper()}-DIAG-1"
    if "reason" in nl: return "diagnostic canary"
    if "prefix" in nl: return "DIAG"
    if "title" in nl: return "diagnostic canary"
    if "message" in nl: return "diagnostic canary"
    if "subject" in nl: return "diagnostic canary"
    if "description" in nl: return "diagnostic canary"
    if "method" in nl: return "Wire"
    if "terms" in nl: return "NET30"
    if "level" in nl: return "level_1"
    if "kpi" in nl: return "DSO_Days"
    if "verb" in nl: return "diagnostic"
    if "target" in nl: return "DIAG-TARGET-1"
    if "status" in nl: return "Open"
    if "stage" in nl: return "Prospecting"
    if "bucket" in nl: return "Yellow"
    if "region" in nl: return "NA"
    if "promotion_type" in nl: return "Discount"
    if "currency" in nl: return "USD"
    if "approved_by" in nl: return DIAGNOSTIC_ACTOR
    return f"DIAG-{name}"


async def _build_canary_payload(spec: Any) -> Dict[str, Any]:
    """
    Synthesise a default invocation payload for a ConnectorAPISpec.

    Strategy:
      1. Seed every request_schema key with a synthetic value (string/number/boolean).
      2. If a verification hint is registered, query the simulator for one real
         row from the target table and overwrite the pk + companion-key fields
         with REAL values that exist in the data.
      3. For PATCH endpoints, also overwrite mutable fields (status, etc.)
         with values DIFFERENT from the current row so the row_diff is non-empty.
      4. For POST endpoints whose body references existing FKs (e.g.
         credit_note.create needs an existing invoice_id+customer_id), use a
         configured ``companion_table`` to source those FKs.

    Returns the payload dict ready for direct dispatch through ``/invoke``.
    """
    out: Dict[str, Any] = {}
    req_schema = getattr(spec, "request_schema", {}) or {}
    for k, v in req_schema.items():
        out[k] = _canary_value(k, str(v))
    out.setdefault("actor", DIAGNOSTIC_ACTOR)

    hint = _HINTS.get(spec.api_id)
    if not hint:
        return out

    real_row: Optional[Dict[str, Any]] = None
    try:
        sim = await get_sim(hint["sim_key"])
        # For post-prefix tables, the table name depends on payload (prefix);
        # we still discover from the canonical companion_table when present.
        table_name = hint.get("table") or _resolve_table(hint, out)
        rows = await fetch_rows(sim, hint["schema"], table_name)
        if rows:
            real_row = dict(rows[0])
    except Exception as e:
        wb_logger.debug("canary discovery failed for {}: {}", spec.api_id, e)
        real_row = None

    # PATCH-style: pk_arg + companion_keys come from real_row (the target table).
    if real_row:
        if hint.get("pk_arg") and hint.get("pk_col") and hint["pk_arg"] in out:
            v = real_row.get(hint["pk_col"])
            if v is not None:
                out[hint["pk_arg"]] = v
        for body_key, col in (hint.get("companion_keys") or {}).items():
            if body_key not in out:
                continue
            v = real_row.get(col)
            if v is not None:
                out[body_key] = v

    # POST-style: pull FK values from a different "companion_table".
    companion = hint.get("companion_table")
    if companion:
        try:
            csim = await get_sim(companion[0])
            crows = await fetch_rows(csim, companion[1], companion[2])
            if crows:
                cr = crows[0]
                for body_key, col in (hint.get("companion_keys") or {}).items():
                    if body_key in out and col in cr:
                        out[body_key] = cr[col]
        except Exception as e:
            wb_logger.debug("canary companion discovery failed for {}: {}", spec.api_id, e)

    # PATCH mutability: pick a value DIFFERENT from current for the most common
    # mutable fields so the row_diff is non-empty.
    if hint.get("mode") == "patch" and real_row:
        out = _mutate_for_patch(out, req_schema, real_row)

    return out


_TOGGLE_VALUES = {
    # body_key  -> [(current_or_default, new_value), ...]
    "status": [
        ("Open", "Disputed"), ("Disputed", "Open"), ("Paid", "Open"),
        ("Approved", "Cancelled"), ("Draft", "Approved"), ("Cancelled", "Approved"),
        ("Confirmed", "Released"), ("Released", "Confirmed"),
    ],
    "payment_terms": [("Net 30", "Net 60"), ("Net 60", "Net 30"), ("Net 45", "Net 30")],
    "priority":     [("Standard", "Express"), ("Express", "Standard"), ("Critical", "Express")],
    "stage":        [("Closed_Won", "Negotiation"), ("Negotiation", "Closed_Won"),
                     ("Prospecting", "Qualified"), ("Qualified", "Prospecting")],
    "health_bucket": [("Green", "Yellow"), ("Yellow", "Red"), ("Red", "Green")],
}


def _mutate_for_patch(
    payload: Dict[str, Any],
    req_schema: Dict[str, Any],
    real_row: Dict[str, Any],
) -> Dict[str, Any]:
    """For PATCH ops, ensure the canary value differs from the current row."""
    # Map common body keys to row column names (case-insensitive heuristic)
    row_lc = {str(k).lower(): k for k in real_row.keys()}
    out = dict(payload)
    for body_key in list(payload.keys()):
        if body_key in {"actor"}:
            continue
        col_match = row_lc.get(body_key.lower()) or row_lc.get(body_key.lower().replace("_", ""))
        current = real_row.get(col_match) if col_match else None
        # Toggle if we have a known mapping for this field name
        if body_key in _TOGGLE_VALUES:
            choices = _TOGGLE_VALUES[body_key]
            for cur, new in choices:
                if str(current) == cur:
                    out[body_key] = new
                    break
            else:
                # Default: pick the first "new" value that differs from current
                for _, new in choices:
                    if str(current) != new:
                        out[body_key] = new
                        break
        # For numeric fields that map directly, increment by 1
        elif col_match and isinstance(current, (int, float)) and isinstance(payload[body_key], (int, float)):
            out[body_key] = current + 1
        # For boolean fields, flip
        elif col_match and isinstance(current, bool):
            out[body_key] = not current
    return out


def _resolve_table(hint: Dict[str, Any], body: Dict[str, Any]) -> str:
    if "table" in hint:
        return hint["table"]
    if "table_prefix_arg" in hint:
        prefix = body.get(hint["table_prefix_arg"]) or "DIAG"
        return f"{prefix}{hint.get('table_suffix','')}"
    raise HTTPException(status_code=500, detail="bad hint: no table")


async def _snapshot_row(hint: Dict[str, Any], body: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], int]:
    """Return (row_matching_pk, total_row_count) for the target table."""
    sim = await get_sim(hint["sim_key"])
    table = _resolve_table(hint, body)
    rows = await fetch_rows(sim, hint["schema"], table)
    pk_col = hint.get("pk_col")
    pk_arg = hint.get("pk_arg")
    pk_value = body.get(pk_arg) if pk_arg else None
    matched: Optional[Dict[str, Any]] = None
    if pk_value is not None and pk_col:
        for r in rows:
            if str(r.get(pk_col, "")) == str(pk_value):
                matched = dict(r)
                break
    return matched, len(rows)


async def _last_inserted_row(hint: Dict[str, Any], body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sim = await get_sim(hint["sim_key"])
    table = _resolve_table(hint, body)
    rows = await fetch_rows(sim, hint["schema"], table)
    return dict(rows[-1]) if rows else None


def _diff_keys(before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]) -> List[str]:
    if not before or not after:
        return []
    out: List[str] = []
    keys = set(before.keys()) | set(after.keys())
    for k in keys:
        if before.get(k) != after.get(k):
            out.append(k)
    out.sort()
    return out


def _callers_for(api_id: str) -> List[str]:
    if _tool_registry is None:
        return []
    try:
        return sorted(
            t.name for t in _tool_registry.list_tools()
            if getattr(t, "connector_api", None) == api_id
        )
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
async def list_apis(target_system: Optional[str] = Query(default=None)):
    """List every Connector API enriched with caller count + audit stats."""
    if target_system:
        specs = await _ca.list_for_system_async(target_system)
    else:
        specs = await _ca.list_all_async()
    api_ids = [s.api_id for s in specs]
    counts = await audit_index.counts_for_apis(api_ids)
    last_ts = await audit_index.latest_ts_for_apis(api_ids)
    out: List[Dict[str, Any]] = []
    for s in specs:
        callers = _callers_for(s.api_id)
        out.append({
            **_ca.to_dict(s),
            "tool_callers": callers,
            "tool_caller_count": len(callers),
            "audit_count": counts.get(s.api_id, 0),
            "last_invocation_ts": last_ts.get(s.api_id),
            "verified": (counts.get(s.api_id, 0) > 0),
            "has_verification_hint": s.api_id in _HINTS,
        })
    out.sort(key=lambda r: r["api_id"])
    totals = {
        "checked": len(out),
        "orphans": sum(1 for r in out if r["tool_caller_count"] == 0),
        "verified": sum(1 for r in out if r["verified"]),
        "never_invoked": sum(1 for r in out if not r["verified"]),
        "by_target_system": {},
        "by_risk_level": {},
    }
    for r in out:
        ts = r.get("target_system") or "unknown"
        rl = r.get("risk_level") or "unknown"
        totals["by_target_system"][ts] = totals["by_target_system"].get(ts, 0) + 1
        totals["by_risk_level"][rl] = totals["by_risk_level"].get(rl, 0) + 1
    return {"items": out, "totals": totals}


class SmokeTestRequest(BaseModel):
    only_systems: Optional[List[str]] = None
    skip_high_risk: bool = False


@router.get("/diagnostic")
async def diagnostic_report():
    """
    Composite static diagnostic. Powers Sections 1-4, 6, 7 of the
    Connector API Workbench. Smoke results live on /smoke-test.
    """
    specs = await _ca.list_all_async()
    api_ids = [s.api_id for s in specs]
    audit_counts = await audit_index.counts_for_apis(api_ids)
    audit_24h = await audit_index.counts_24h_for_apis(api_ids)
    audit_last_ts = await audit_index.latest_ts_for_apis(api_ids)

    return {
        "summary": _cad.summary(specs, _tool_registry, audit_counts, audit_24h, _HINTS),
        "catalogue_health": _cad.catalogue_health(specs, _tool_registry),
        "tool_mapping": _cad.tool_mapping(specs, _tool_registry),
        "verification_hints": _cad.verification_hints(specs, _HINTS),
        "audit_discipline": _cad.audit_discipline(specs, audit_counts, audit_24h, audit_last_ts),
        "simulator_coverage": await _cad.simulator_coverage(_HINTS),
    }


@router.post("/smoke-test")
async def smoke_test(body: SmokeTestRequest = Body(default_factory=SmokeTestRequest)):
    """
    Drive every spec through ``_invoke`` with a discovered canary payload.
    Returns aggregate verdicts. Tagged with ``actor=diagnostic-runner``.

    Body filters:
      only_systems    - optional [oracle|sap|sfdc|external]
      skip_high_risk  - omit specs with risk_level=high_risk_write
    """
    specs = await _ca.list_all_async()
    if body.only_systems:
        wanted = set(body.only_systems)
        specs = [s for s in specs if getattr(s, "target_system", "") in wanted]
    if body.skip_high_risk:
        specs = [s for s in specs if getattr(s, "risk_level", "") != "high_risk_write"]

    started = time.monotonic()
    results: List[Dict[str, Any]] = []
    counts = {"verified": 0, "no_change": 0, "audit_missing": 0, "http_error": 0}

    for spec in specs:
        try:
            payload = await _build_canary_payload(spec)
        except Exception as e:
            results.append({
                "api_id": spec.api_id,
                "verdict": "http_error",
                "http_error": f"canary build failed: {e}",
                "duration_ms": 0,
            })
            counts["http_error"] += 1
            continue
        try:
            row = await _invoke(spec.api_id, payload)
        except HTTPException as he:
            row = {
                "api_id": spec.api_id,
                "verdict": "http_error",
                "http_status": he.status_code,
                "http_error": str(he.detail),
                "duration_ms": 0,
            }
        except Exception as e:
            row = {
                "api_id": spec.api_id,
                "verdict": "http_error",
                "http_error": str(e),
                "duration_ms": 0,
            }
        results.append(row)
        v = row.get("verdict") or "http_error"
        counts[v] = counts.get(v, 0) + 1

    duration = int((time.monotonic() - started) * 1000)
    if counts["http_error"] > 0:
        overall = "unhealthy"
    elif counts["audit_missing"] > 0 or counts["no_change"] > 0:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "totals": {
            "checked": len(results),
            **counts,
            "duration_ms": duration,
        },
        "results": results,
        "overall": overall,
    }


@router.get("/{api_id}")
async def get_api(api_id: str = Path(...)):
    spec = await _ca.get_async(api_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"api_id not found: {api_id}")
    callers = _callers_for(api_id)
    audit = await audit_index.recent_for_api(api_id, limit=20)
    return {
        **_ca.to_dict(spec),
        "tool_callers": callers,
        "tool_caller_count": len(callers),
        "audit_count": await audit_index.count_for_api(api_id),
        "last_invocation_ts": (audit[0]["event_ts"] if audit else None),
        "recent_events": audit,
        "has_verification_hint": api_id in _HINTS,
    }


@router.get("/{api_id}/events")
async def get_events(api_id: str = Path(...), limit: int = Query(default=20, ge=1, le=200)):
    spec = await _ca.get_async(api_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"api_id not found: {api_id}")
    return {"events": await audit_index.recent_for_api(api_id, limit=limit)}


@router.get("/{api_id}/canary-payload")
async def get_canary_payload(api_id: str = Path(...)):
    spec = await _ca.get_async(api_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"api_id not found: {api_id}")
    return {"api_id": api_id, "payload": await _build_canary_payload(spec)}


class InvokeRequest(BaseModel):
    payload: Dict[str, Any] = {}


async def _invoke(api_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute one Connector API end-to-end with verification. Shared between
    the per-API ``POST /{api_id}/invoke`` route and the bulk
    ``POST /smoke-test`` route. Returns the same verdict shape as the
    public route.
    """
    spec = await _ca.get_async(api_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"api_id not found: {api_id}")
    try:
        sim_base = require_simulator_base_url()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not sim_base:
        raise HTTPException(status_code=503, detail="SIMULATOR_BASE_URL is not configured")

    method, path_template = _operation_parts(spec.operation)
    payload = dict(payload or {})
    payload.setdefault("actor", DIAGNOSTIC_ACTOR)
    resolved_path, body_remaining = _substitute_path(path_template, payload)

    hint = _HINTS.get(api_id)
    before_row: Optional[Dict[str, Any]] = None
    count_before = 0
    if hint:
        try:
            before_row, count_before = await _snapshot_row(hint, payload)
        except Exception as e:
            wb_logger.debug("before-snapshot failed for {}: {}", api_id, e)

    pre_audit_count = await audit_index.count_for_api(api_id)
    t0 = time.monotonic()

    http_status = 0
    response_body: Any = None
    http_error: Optional[str] = None
    try:
        client = get_simulator_http_client()
        req_kwargs: Dict[str, Any] = {}
        if method in {"POST", "PATCH", "PUT", "DELETE"}:
            req_kwargs["json"] = body_remaining
        resp = await client.request(method, f"{sim_base}{resolved_path}", **req_kwargs)
        http_status = resp.status_code
        try:
            response_body = resp.json()
        except Exception:
            response_body = resp.text
        if http_status >= 400:
            http_error = f"HTTP {http_status}"
    except Exception as e:
        http_error = str(e)
        wb_logger.warning("invoke failed for {}: {}", api_id, e)

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    after_row: Optional[Dict[str, Any]] = None
    count_after = count_before
    if hint:
        try:
            if hint["mode"] == "patch":
                after_row, count_after = await _snapshot_row(hint, payload)
            elif hint["mode"] in ("post", "post_prefix"):
                _, count_after = await _snapshot_row(hint, payload)
                after_row = await _last_inserted_row(hint, payload)
        except Exception as e:
            wb_logger.debug("after-snapshot failed for {}: {}", api_id, e)

    audit_event = await audit_index.last_for_api(api_id)
    post_audit_count = await audit_index.count_for_api(api_id)
    audit_appeared = post_audit_count > pre_audit_count

    if http_error or (http_status and http_status >= 400):
        verdict = "http_error"
    elif hint and hint["mode"] == "patch":
        diff_keys = _diff_keys(before_row, after_row)
        verdict = "verified" if diff_keys else "no_change"
    elif hint and hint["mode"] in ("post", "post_prefix"):
        verdict = "verified" if (count_after > count_before) else "no_change"
    else:
        verdict = "verified" if audit_appeared else "audit_missing"

    if verdict in ("verified", "no_change") and not audit_appeared:
        verdict = "audit_missing"

    return {
        "api_id": api_id,
        "operation": spec.operation,
        "request": {
            "method": method,
            "path": resolved_path,
            "body": body_remaining,
            "full_payload": payload,
        },
        "http_status": http_status,
        "response": response_body,
        "http_error": http_error,
        "verification": {
            "before": before_row,
            "after": after_row,
            "row_diff": _diff_keys(before_row, after_row) if hint and hint["mode"] == "patch" else [],
            "row_count_before": count_before,
            "row_count_after": count_after,
            "audit_event": audit_event,
            "audit_appeared": audit_appeared,
            "table": (_resolve_table(hint, payload) if hint else None),
            "schema": (hint.get("schema") if hint else None),
            "mode": (hint.get("mode") if hint else None),
        },
        "duration_ms": elapsed_ms,
        "verdict": verdict,
        "marker": DIAGNOSTIC_ACTOR,
    }


@router.post("/{api_id}/invoke")
async def invoke_api(api_id: str = Path(...), body: InvokeRequest = Body(default_factory=InvokeRequest)):
    """Dispatch a connector API end-to-end and return verification."""
    return await _invoke(api_id, body.payload or {})


# ---------------------------------------------------------------------------
# Registry CRUD (Phase 2)
#
# Backed by ``ConnectorApiRegistryService`` which writes to ``CONNAPI#``
# rows in foundry-workspace DDB. Legacy in-memory registry stays as a
# read-fallback but every write goes through DDB.
# ---------------------------------------------------------------------------


class ConnectorApiCreate(BaseModel):
    api_id: str
    target_system: str
    operation: str
    description: str
    request_schema: Dict[str, Any] = {}
    response_schema: Dict[str, Any] = {}
    simulator_writeback: bool = True
    risk_level: str = "low_risk_write"
    tags: List[str] = []


@router.post("", status_code=201)
async def register_api(body: ConnectorApiCreate):
    from src.services.control_plane.connector_apis import ConnectorAPISpec
    from src.services.data_plane.connector_api_registry_service import (
        get_connector_api_registry,
    )
    spec = ConnectorAPISpec(
        api_id=body.api_id,
        target_system=body.target_system,
        operation=body.operation,
        description=body.description,
        request_schema=body.request_schema or {},
        response_schema=body.response_schema or {},
        simulator_writeback=body.simulator_writeback,
        risk_level=body.risk_level,
        tags=list(body.tags or []),
    )
    await get_connector_api_registry().register(spec)
    return _ca.to_dict(spec)


@router.put("/{api_id}")
async def update_api(api_id: str = Path(...), body: ConnectorApiCreate = Body(...)):
    if body.api_id != api_id:
        raise HTTPException(status_code=400, detail="path api_id and body api_id must match")
    return await register_api(body)


@router.delete("/{api_id}", status_code=204)
async def delete_api(api_id: str = Path(...)):
    from src.services.data_plane.connector_api_registry_service import (
        get_connector_api_registry,
    )
    ok = await get_connector_api_registry().delete(api_id)
    if not ok:
        raise HTTPException(status_code=500, detail=f"failed to delete {api_id}")
    return None
