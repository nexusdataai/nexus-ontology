"""
Connector API Diagnostic helpers.

Pure helper functions that produce the six section reports that drive
the Connector API Workbench diagnostic view. No FastAPI imports - the
route handler in
``services/control_plane/connector_api_workbench_api.py`` is the only
caller.

Public surface:

  - summary(specs, registry, audit_counts, audit_24h, hints) -> dict
  - catalogue_health(specs, registry) -> dict
  - tool_mapping(specs, registry) -> dict
  - verification_hints(specs, hints) -> dict
  - audit_discipline(specs, audit_counts, audit_24h, audit_last_ts) -> dict
  - simulator_coverage(hints) -> list   [async, walks the simulators]

Each helper accepts already-fetched data so it stays unit-testable
without a live simulator. ``simulator_coverage`` is the one exception -
it walks ``connector_runtime.fetch_rows`` directly because the table
list is purely a function of the hints map.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from loguru import logger

from .connector_runtime import fetch_rows, get_sim

cad_logger = logger.bind(component="connector-apis-diagnostic")


_VALID_TARGET_SYSTEMS = {"oracle", "sap", "sfdc", "external"}
_VALID_RISK_LEVELS = {"read_only", "low_risk_write", "high_risk_write"}
_VALID_HTTP_METHODS = {"GET", "POST", "PATCH", "PUT", "DELETE"}


# ---------------------------------------------------------------------------
# Section 1 - Summary
# ---------------------------------------------------------------------------

def summary(
    specs: List[Any],
    registry: Any,
    audit_counts: Dict[str, int],
    audit_24h: Dict[str, int],
    hints: Dict[str, Any],
) -> Dict[str, Any]:
    """Aggregate KPIs across the whole connector API surface."""
    by_target: Dict[str, int] = {}
    by_risk: Dict[str, int] = {}

    callers_by_api = _build_callers_by_api(registry)
    orphan_apis = 0
    verified = 0
    for s in specs:
        ts = getattr(s, "target_system", "unknown")
        rl = getattr(s, "risk_level", "unknown")
        by_target[ts] = by_target.get(ts, 0) + 1
        by_risk[rl] = by_risk.get(rl, 0) + 1
        if not callers_by_api.get(s.api_id):
            orphan_apis += 1
        if audit_counts.get(s.api_id, 0) > 0:
            verified += 1

    total = len(specs)
    never = total - verified
    audit_24h_total = sum(audit_24h.values())
    hinted = sum(1 for s in specs if s.api_id in hints)

    if orphan_apis > 0:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "checked": total,
        "verified": verified,
        "never_invoked": never,
        "orphans": orphan_apis,
        "with_hint": hinted,
        "without_hint": total - hinted,
        "audit_events_24h": audit_24h_total,
        "by_target_system": by_target,
        "by_risk_level": by_risk,
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# Section 2 - Catalogue Health
# ---------------------------------------------------------------------------

def catalogue_health(specs: List[Any], registry: Any) -> Dict[str, Any]:
    """Per-spec well-formedness checks - same vocabulary as validate_connector_apis."""
    callers_by_api = _build_callers_by_api(registry)
    issues_by_api: Dict[str, List[Dict[str, str]]] = {}
    error_count = 0
    warning_count = 0

    def _issue(api_id: str, severity: str, code: str, message: str) -> None:
        nonlocal error_count, warning_count
        issues_by_api.setdefault(api_id, []).append({
            "severity": severity, "code": code, "message": message,
        })
        if severity == "error":
            error_count += 1
        else:
            warning_count += 1

    for s in specs:
        target = getattr(s, "target_system", "")
        if target not in _VALID_TARGET_SYSTEMS:
            _issue(s.api_id, "error", "invalid_target_system",
                   f"target_system '{target}' must be in {sorted(_VALID_TARGET_SYSTEMS)}")
        risk = getattr(s, "risk_level", "")
        if risk not in _VALID_RISK_LEVELS:
            _issue(s.api_id, "error", "invalid_risk_level",
                   f"risk_level '{risk}' must be in {sorted(_VALID_RISK_LEVELS)}")

        operation = getattr(s, "operation", "") or ""
        method, path = "", ""
        if " " in operation:
            method, path = operation.split(" ", 1)
        if method not in _VALID_HTTP_METHODS or not path.startswith("/"):
            _issue(s.api_id, "error", "invalid_operation",
                   f"operation '{operation}' must be '<METHOD> <PATH>'")

        req = getattr(s, "request_schema", {}) or {}
        res = getattr(s, "response_schema", {}) or {}
        if risk != "read_only" and not req:
            _issue(s.api_id, "warning", "empty_request_schema",
                   "write spec has no request_schema")
        if not res:
            _issue(s.api_id, "warning", "empty_response_schema",
                   "response_schema is empty")
        if not callers_by_api.get(s.api_id):
            _issue(s.api_id, "warning", "orphan_no_tool_caller",
                   "no registered tool references this connector_api")

    if error_count > 0:
        overall = "unhealthy"
    elif warning_count > 0:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "totals": {
            "checked": len(specs),
            "errors": error_count,
            "warnings": warning_count,
            "specs_with_issues": len(issues_by_api),
        },
        "issues_by_api": issues_by_api,
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# Section 3 - Tool Mapping
# ---------------------------------------------------------------------------

def tool_mapping(specs: List[Any], registry: Any) -> Dict[str, Any]:
    """Two-way map between Connector APIs and ReAct tools, plus orphan callouts."""
    spec_ids = {s.api_id for s in specs}
    by_api: Dict[str, List[str]] = {s.api_id: [] for s in specs}
    by_tool: List[Dict[str, Any]] = []
    orphan_tools: List[Dict[str, Any]] = []

    if registry is not None:
        try:
            for t in registry.list_tools():
                api_id = getattr(t, "connector_api", None)
                risk = _risk_value(getattr(t, "risk_level", None))
                row = {
                    "tool_id": t.name,
                    "risk_level": risk,
                    "connector_api": api_id,
                    "binding_status": (
                        "ok" if api_id and api_id in spec_ids
                        else "dangling" if api_id
                        else ("orphan" if risk != "read_only" else "read_only")
                    ),
                }
                by_tool.append(row)
                if api_id and api_id in spec_ids:
                    by_api[api_id].append(t.name)
                if risk != "read_only" and not api_id:
                    orphan_tools.append({"tool_id": t.name, "risk_level": risk})
        except Exception as e:
            cad_logger.warning("tool_mapping registry walk failed: {}", e)

    for k in by_api:
        by_api[k].sort()
    by_tool.sort(key=lambda r: r["tool_id"])

    orphan_apis = sorted([k for k, v in by_api.items() if not v])
    dangling_tools = sorted([
        r["tool_id"] for r in by_tool
        if r["binding_status"] == "dangling"
    ])

    if dangling_tools or orphan_tools:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "totals": {
            "tools": len(by_tool),
            "tools_with_binding": sum(1 for r in by_tool if r["binding_status"] == "ok"),
            "orphan_tools": len(orphan_tools),
            "dangling_tools": len(dangling_tools),
            "orphan_apis": len(orphan_apis),
        },
        "by_api": by_api,
        "by_tool": by_tool,
        "orphan_apis": orphan_apis,
        "orphan_tools": orphan_tools,
        "dangling_tools": dangling_tools,
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# Section 4 - Verification Hints
# ---------------------------------------------------------------------------

def verification_hints(specs: List[Any], hints: Dict[str, Any]) -> Dict[str, Any]:
    """Per-spec metadata about whether a verification hint is registered."""
    rows: List[Dict[str, Any]] = []
    non_verifiable: List[str] = []
    for s in specs:
        h = hints.get(s.api_id)
        if not h:
            non_verifiable.append(s.api_id)
            rows.append({
                "api_id": s.api_id,
                "has_hint": False,
                "mode": None,
                "schema": None,
                "table": None,
                "pk_col": None,
                "pk_arg": None,
                "has_companion": False,
            })
            continue
        rows.append({
            "api_id": s.api_id,
            "has_hint": True,
            "mode": h.get("mode"),
            "schema": h.get("schema"),
            "table": h.get("table") or _format_prefix_table(h),
            "pk_col": h.get("pk_col"),
            "pk_arg": h.get("pk_arg"),
            "has_companion": bool(h.get("companion_table") or h.get("companion_keys")),
        })
    rows.sort(key=lambda r: r["api_id"])

    overall = "healthy" if not non_verifiable else "degraded"
    return {
        "totals": {
            "checked": len(rows),
            "with_hint": sum(1 for r in rows if r["has_hint"]),
            "without_hint": len(non_verifiable),
        },
        "rows": rows,
        "non_verifiable_api_ids": sorted(non_verifiable),
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# Section 5 - Audit Discipline
# ---------------------------------------------------------------------------

def audit_discipline(
    specs: List[Any],
    audit_counts: Dict[str, int],
    audit_24h: Dict[str, int],
    audit_last_ts: Dict[str, Optional[str]],
) -> Dict[str, Any]:
    """Per-spec audit emission roll-up. Catches endpoints that never fire emit_audit."""
    rows: List[Dict[str, Any]] = []
    smell_counts: Dict[str, int] = {"ok": 0, "never_called": 0, "audit_missing": 0}

    for s in specs:
        total = int(audit_counts.get(s.api_id, 0) or 0)
        last24 = int(audit_24h.get(s.api_id, 0) or 0)
        last_ts = audit_last_ts.get(s.api_id)
        sim_writeback = bool(getattr(s, "simulator_writeback", True))
        risk = getattr(s, "risk_level", "")

        if total == 0:
            # Never called at all - likely benign (just hasn't been exercised)
            # except for read_only specs which don't write to the system anyway.
            smell = "never_called"
        elif last_ts is None:
            smell = "audit_missing"
        else:
            smell = "ok"

        # Specs that are writes + simulator_writeback but with zero events
        # past a smoke run are the real "audit missing" candidates.
        # Caller can refine by also passing a recent smoke result.
        if total == 0 and sim_writeback and risk != "read_only":
            smell = "never_called"

        rows.append({
            "api_id": s.api_id,
            "target_system": getattr(s, "target_system", ""),
            "risk_level": risk,
            "simulator_writeback": sim_writeback,
            "total_events": total,
            "events_24h": last24,
            "last_event_ts": last_ts,
            "smell": smell,
        })
        smell_counts[smell] = smell_counts.get(smell, 0) + 1

    rows.sort(key=lambda r: r["api_id"])

    if smell_counts.get("audit_missing", 0) > 0:
        overall = "unhealthy"
    elif smell_counts.get("never_called", 0) > 0:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "totals": {
            "checked": len(rows),
            **smell_counts,
        },
        "rows": rows,
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# Section 6 - Simulator Coverage
# ---------------------------------------------------------------------------

async def simulator_coverage(hints: Dict[str, Any]) -> Dict[str, Any]:
    """Per simulator table referenced by hints, count rows + flag empties."""
    # Build a {(sim_key, schema, table) -> list[api_id]} index over hints
    # (companion_tables are added too because they gate POST canary discovery).
    table_to_apis: Dict[Tuple[str, str, str], List[str]] = {}
    for api_id, h in hints.items():
        sim_key = h.get("sim_key")
        schema = h.get("schema")
        table = h.get("table")
        if sim_key and schema and table:
            table_to_apis.setdefault((sim_key, schema, table), []).append(api_id)
        companion = h.get("companion_table")
        if companion:
            table_to_apis.setdefault(tuple(companion), []).append(api_id)

    rows: List[Dict[str, Any]] = []
    blocking = 0
    sim_cache: Dict[str, Any] = {}
    for (sim_key, schema, table), apis in sorted(table_to_apis.items()):
        try:
            if sim_key not in sim_cache:
                sim_cache[sim_key] = await get_sim(sim_key)
            data = await fetch_rows(sim_cache[sim_key], schema, table)
            row_count = len(data)
        except Exception as e:
            cad_logger.debug("coverage fetch failed for {}.{}: {}", schema, table, e)
            row_count = 0
        is_blocking = row_count == 0
        if is_blocking:
            blocking += 1
        rows.append({
            "sim_key": sim_key,
            "schema": schema,
            "table": table,
            "row_count": row_count,
            "used_by_apis": sorted(set(apis)),
            "blocking": is_blocking,
        })

    overall = "unhealthy" if blocking > 0 else "healthy"
    return {
        "totals": {
            "tables": len(rows),
            "blocking": blocking,
        },
        "rows": rows,
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _build_callers_by_api(registry: Any) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    if registry is None:
        return out
    try:
        for t in registry.list_tools():
            cap = getattr(t, "connector_api", None)
            if cap:
                out.setdefault(cap, []).append(t.name)
    except Exception as e:
        cad_logger.debug("callers walk failed: {}", e)
    return out


def _risk_value(v: Any) -> str:
    if v is None:
        return ""
    try:
        return v.value  # enum
    except Exception:
        return str(v)


def _format_prefix_table(hint: Dict[str, Any]) -> Optional[str]:
    arg = hint.get("table_prefix_arg")
    suf = hint.get("table_suffix")
    if arg and suf:
        return f"{{{arg}}}{suf}"
    return None
