"""
Shared runtime helpers used by the per-system connector API routers.

Each router endpoint is a thin wrapper around:
  1. Locate the matching simulator (sap / oracle / sfdc / external)
  2. Read the target table via _get_table_data
  3. Apply the mutation (update / insert / delete)
  4. Persist via append_rows / write_table
  5. Emit an Audit_Event row to the external simulator
  6. Return the new row + a delta summary
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from loguru import logger

connector_logger = logger.bind(component="connector-runtime")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_simulators() -> Dict[str, Any]:
    try:
        from src.apis.fdw_api import _simulators
        return _simulators or {}
    except Exception:
        return {}


def _emit_runtime_log(
    level: str, message: str, details: Optional[Dict[str, Any]] = None,
    source: str = "connector_runtime",
) -> None:
    """Best-effort bridge to the active RunContext (Phase-2 Copilot
    Saved studio observability). No-op when no Copilot saved-journey
    run is active. Lazy import avoids a hard dependency on
    `run_context` from non-Copilot call paths."""
    try:
        from .run_context import emit as _emit
        _emit(level=level, message=message, details=details, source=source)
    except Exception:
        pass


async def get_sim(key: str):
    sims = _get_simulators()
    sim = sims.get(key)
    if sim is None:
        raise HTTPException(status_code=503, detail=f"simulator '{key}' not initialised")
    if hasattr(sim, "ensure_loaded"):
        try:
            await sim.ensure_loaded()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"simulator load failed: {e}")
    _emit_runtime_log("DEBUG", f"sim attached: {key}", details={"sim": key})
    return sim


async def fetch_rows(sim: Any, schema: str, table: str) -> List[Dict[str, Any]]:
    if not hasattr(sim, "_get_table_data"):
        raise HTTPException(status_code=500, detail="simulator missing _get_table_data")
    rows = await sim._get_table_data(schema, table)
    return list(rows or [])


async def replace_rows(sim: Any, schema: str, table: str, rows: List[Dict[str, Any]]) -> int:
    if hasattr(sim, "write_table"):
        return await sim.write_table(schema, table, rows)
    raise HTTPException(status_code=500, detail="simulator missing write_table")


async def append_row(sim: Any, schema: str, table: str, row: Dict[str, Any]) -> None:
    if hasattr(sim, "append_rows"):
        await sim.append_rows(schema, table, [row])
    else:
        existing = await fetch_rows(sim, schema, table)
        existing.append(row)
        await replace_rows(sim, schema, table, existing)
    _emit_runtime_log(
        "INFO", f"append_row -> {schema}.{table} (1 row)",
        details={
            "schema": schema, "table": table,
            "row_keys": sorted(list((row or {}).keys())),
        },
    )


async def update_one(
    sim: Any,
    schema: str,
    table: str,
    pk_col: str,
    pk_value: str,
    patch: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Find the single row whose pk matches, apply ``patch``, persist, and
    return ``(previous_row, new_row)``. Raises 404 if no match.
    """
    rows = await fetch_rows(sim, schema, table)
    target_idx = -1
    for i, r in enumerate(rows):
        if str(r.get(pk_col, "")) == str(pk_value):
            target_idx = i
            break
    if target_idx < 0:
        raise HTTPException(status_code=404, detail=f"{table} not found: {pk_col}={pk_value}")
    previous = dict(rows[target_idx])
    new_row = {**previous, **patch}
    rows[target_idx] = new_row
    await replace_rows(sim, schema, table, rows)
    return previous, new_row


async def emit_audit(
    actor: str,
    verb: str,
    target: str,
    payload: Optional[Dict[str, Any]] = None,
    api_id: Optional[str] = None,
) -> str:
    """Append a row to external_sources.Audit_Event and mirror into DDB.

    Dual-write behavior (Phase 2, data-organization spec):
    - Redis simulator table remains the canonical hot store so the
      existing workbench + smoke tests observe writes immediately.
    - When ``api_id`` is set, the same event is persisted under
      ``CONNAPI#{api_id}/AUDIT#{iso_ts}#{event_id}`` in DDB via the
      registry service, giving durable per-connector audit history.
    Both writes are best-effort - neither blocks the caller.
    """
    event_id = str(uuid.uuid4())
    row = {
        "event_id": event_id,
        "actor": actor,
        "verb": verb,
        "target": target,
        "payload": payload or {},
        "api_id": api_id,
        "event_ts": _now_iso(),
    }
    try:
        ext = await get_sim("external")
        await append_row(ext, "external_sources", "Audit_Event", row)
    except Exception as e:
        connector_logger.debug("audit write skipped: {}", e)

    if api_id:
        try:
            from src.services.data_plane.connector_api_registry_service import (
                get_connector_api_registry,
            )
            await get_connector_api_registry().append_audit(api_id, row)
        except Exception as e:
            connector_logger.debug("connector-api audit DDB write skipped: {}", e)

    _emit_runtime_log(
        "INFO", f"audit: {verb} {target}",
        details={
            "actor": actor, "verb": verb, "target": target,
            "api_id": api_id, "event_id": event_id,
        },
        source="audit",
    )
    return event_id


async def emit_alert(
    prefix: str,
    severity: str,
    title: str,
    message: str,
    entity_id: Optional[str] = None,
) -> str:
    alert_id = f"ALERT-{prefix}-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    row = {
        "alert_id": alert_id,
        "severity": severity,
        "title": title,
        "message": message,
        "entity_id": entity_id,
        "created_at": _now_iso(),
    }
    ext = await get_sim("external")
    await append_row(ext, "external_sources", f"{prefix}_Alert", row)
    _emit_runtime_log(
        ("ERROR" if severity.lower() in ("error", "critical", "high") else "WARNING"),
        f"alert [{prefix}/{severity}]: {title}",
        details={
            "prefix": prefix, "severity": severity, "title": title,
            "message": message, "entity_id": entity_id, "alert_id": alert_id,
        },
        source="alert",
    )
    return alert_id
