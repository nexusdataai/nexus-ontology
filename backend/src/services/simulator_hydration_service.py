"""
Ensure remote nexus-simulator plugins return queryable rows on local/K3s clusters.

Common failure mode: S3 manifest + table catalogue load marks plugins ``loaded``
while Redis row cache is empty (TTL eviction, pod restart, or partial load).
Virtual Data Layer previews then succeed at the HTTP layer but return 0 rows,
and the UI falls back to a hard-coded ``sfdc_itxp2dev`` FDW path with a misleading
error.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger

from src.models.fdw_models import QueryRequest
from src.services.simulator_fdw_client import get_simulator_http_client, simulator_base_url

hydrate_logger = logger.bind(component="simulator-hydration")

# Registry key -> admin API prefix on nexus-simulator
_ADMIN_PREFIX: Dict[str, str] = {
    "sfdc": "/api/v1/sfdc-simulator",
    "oracle": "/api/v1/oracle-erp-simulator",
    "sap": "/api/v1/sap-simulator",
    "external": "/api/v1/external-simulator",
    "tpm": "/api/v1/tpm-simulator",
    "sourcing": "/api/v1/sourcing-simulator",
}

# Probe query used to detect empty Redis despite non-zero catalogue stats.
_PROBE: Dict[str, Tuple[str, str, str]] = {
    "sfdc": ("simulator", "sfdc_schema", "Account"),
    "oracle": ("oracle", "oracle_erp", "AR_Customer"),
    "sap": ("sap", "sap_s4hana", "Material_Master"),
    "external": ("external", "external_sources", "Invoice_Upload"),
    "tpm": ("tpm", "tpm_cpq", "Price_Book_Entry"),
    "sourcing": ("sourcing", "sourcing_cpq", "RFx_Event"),
}


async def _catalog(client: httpx.AsyncClient, base: str) -> List[Dict[str, Any]]:
    try:
        r = await client.get(f"{base}/api/v1/simulators", timeout=30.0)
        r.raise_for_status()
        body = r.json()
        return list(body.get("items") or [])
    except Exception as exc:
        hydrate_logger.warning("simulator catalog fetch failed: {}", exc)
        return []


async def _probe_rows(
    simulators: Dict[str, Any],
    service: str,
) -> Optional[int]:
    probe = _PROBE.get(service)
    if not probe:
        return None
    fdw_key, schema, table = probe
    sim = simulators.get(fdw_key)
    if sim is None or not hasattr(sim, "execute_query"):
        return None
    try:
        if hasattr(sim, "ensure_loaded"):
            await sim.ensure_loaded()
        resp = await sim.execute_query(
            QueryRequest(table=table, schema_name=schema, limit=1, offset=0)
        )
        return int(getattr(resp.metadata, "row_count", len(resp.rows or [])) or 0)
    except Exception as exc:
        hydrate_logger.debug("probe failed {}.{}: {}", schema, table, exc)
        return 0


def _needs_hydration(item: Dict[str, Any], probe_rows: Optional[int]) -> Tuple[bool, str]:
    table_count = int(item.get("table_count") or 0)
    tables_with_data = int(item.get("tables_with_data") or 0)
    total_rows = int(item.get("total_rows") or 0)

    if table_count == 0:
        return False, "no_catalogue"
    if tables_with_data == 0 or total_rows == 0:
        return True, "empty_catalogue_stats"
    if probe_rows is not None and probe_rows == 0:
        return True, "cache_miss_despite_manifest"
    return False, "ok"


async def _trigger_hydration(
    client: httpx.AsyncClient,
    base: str,
    service: str,
    item: Dict[str, Any],
    reason: str,
) -> bool:
    prefix = _ADMIN_PREFIX.get(service)
    if not prefix:
        return False
    has_bucket = bool(item.get("bucket"))
    action = "load" if has_bucket else "seed"
    path = f"{base}{prefix}/{action}"
    try:
        r = await client.post(path, timeout=60.0)
        r.raise_for_status()
        hydrate_logger.info(
            "Triggered simulator {} ({}) reason={}",
            service,
            action,
            reason,
        )
        return True
    except Exception as exc:
        hydrate_logger.warning("simulator hydrate POST failed {}: {}", service, exc)
        return False


async def ensure_simulators_hydrated(
    simulators: Optional[Dict[str, Any]] = None,
    *,
    base_url: Optional[str] = None,
    wait_seconds: float = 90.0,
) -> Dict[str, Any]:
    """
    Idempotent: reload or seed simulator plugins that have catalogue metadata
    but no queryable row cache. Safe to run on every ontology API startup.
    """
    if os.getenv("SIMULATOR_HYDRATION_ENABLED", "true").lower() == "false":
        return {"skipped": True, "reason": "disabled"}
    if os.getenv("SIMULATOR_ENABLED", "true").lower() == "false":
        return {"skipped": True, "reason": "simulator_disabled"}

    base = (base_url or simulator_base_url()).rstrip("/")
    if not base:
        return {"skipped": True, "reason": "no_simulator_base_url"}

    simulators = simulators or {}
    client = get_simulator_http_client()
    items = await _catalog(client, base)
    if not items:
        return {"skipped": True, "reason": "empty_catalog"}

    triggered: List[str] = []
    for item in items:
        svc = str(item.get("service") or "")
        probe = await _probe_rows(simulators, svc)
        need, reason = _needs_hydration(item, probe)
        if need and await _trigger_hydration(client, base, svc, item, reason):
            triggered.append(svc)

    if not triggered:
        return {"hydrated": [], "status": "already_queryable"}

    deadline = time.monotonic() + wait_seconds
    pending = set(triggered)
    while pending and time.monotonic() < deadline:
        await asyncio.sleep(3.0)
        for svc in list(pending):
            probe = await _probe_rows(simulators, svc)
            if probe and probe > 0:
                pending.discard(svc)
                hydrate_logger.info("Simulator {} probe ok ({} rows)", svc, probe)

    return {
        "hydrated": triggered,
        "pending_after_wait": sorted(pending),
        "status": "ok" if not pending else "partial",
    }