"""
Read-side helper for ``external_sources.Audit_Event`` lookups by ``api_id``.

Every ``connector_runtime.emit_audit`` call appends a row whose ``api_id``
field is the ConnectorAPISpec id.  The Workbench surface needs three
question shapes against that table:

  - recent_for_api(api_id, limit): last N events sorted desc by event_ts
  - count_for_api(api_id, since_iso): how many events exist (optionally
    filtered to events after ``since_iso``)
  - last_for_api(api_id): the single newest event (or None)

All three are O(N) scans across the in-memory simulator dataset, which
is small (canary+real ops together stay well under a few thousand
rows). No new storage or indexes are introduced.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from .connector_runtime import fetch_rows, get_sim

ai_logger = logger.bind(component="audit-index")

_AUDIT_SCHEMA = "external_sources"
_AUDIT_TABLE = "Audit_Event"


async def _load_all() -> List[Dict[str, Any]]:
    try:
        sim = await get_sim("external")
    except Exception as e:
        ai_logger.debug("external simulator unavailable: {}", e)
        return []
    try:
        return await fetch_rows(sim, _AUDIT_SCHEMA, _AUDIT_TABLE)
    except Exception as e:
        ai_logger.debug("Audit_Event fetch failed: {}", e)
        return []


def _api_id_of(row: Dict[str, Any]) -> Optional[str]:
    v = row.get("api_id")
    return str(v) if v is not None else None


async def recent_for_api(api_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    rows = await _load_all()
    matched = [r for r in rows if _api_id_of(r) == api_id]
    matched.sort(key=lambda r: str(r.get("event_ts", "")), reverse=True)
    return matched[: max(0, int(limit))]


async def count_for_api(api_id: str, since_iso: Optional[str] = None) -> int:
    rows = await _load_all()
    n = 0
    for r in rows:
        if _api_id_of(r) != api_id:
            continue
        if since_iso and str(r.get("event_ts", "")) <= since_iso:
            continue
        n += 1
    return n


async def last_for_api(api_id: str) -> Optional[Dict[str, Any]]:
    rows = await recent_for_api(api_id, limit=1)
    return rows[0] if rows else None


async def counts_for_apis(api_ids: List[str]) -> Dict[str, int]:
    """Bulk lookup: returns {api_id: count} in a single pass."""
    rows = await _load_all()
    out: Dict[str, int] = {a: 0 for a in api_ids}
    targets = set(api_ids)
    for r in rows:
        a = _api_id_of(r)
        if a in targets:
            out[a] = out.get(a, 0) + 1
    return out


async def counts_24h_for_apis(api_ids: List[str]) -> Dict[str, int]:
    """Bulk lookup: events recorded in the last 24h, returns {api_id: count}."""
    rows = await _load_all()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    out: Dict[str, int] = {a: 0 for a in api_ids}
    targets = set(api_ids)
    for r in rows:
        a = _api_id_of(r)
        if a not in targets:
            continue
        ts = str(r.get("event_ts", ""))
        if ts and ts > cutoff:
            out[a] = out.get(a, 0) + 1
    return out


async def latest_ts_for_apis(api_ids: List[str]) -> Dict[str, Optional[str]]:
    """Bulk lookup: returns {api_id: latest_event_ts_or_None}."""
    rows = await _load_all()
    out: Dict[str, Optional[str]] = {a: None for a in api_ids}
    targets = set(api_ids)
    for r in rows:
        a = _api_id_of(r)
        if a not in targets:
            continue
        ts = str(r.get("event_ts", "")) or None
        cur = out.get(a)
        if ts and (cur is None or ts > cur):
            out[a] = ts
    return out
