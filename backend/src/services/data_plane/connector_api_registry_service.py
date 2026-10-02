"""
Connector API Registry Service (Data Plane, Phase 2)

DDB-backed replacement for the in-memory ``_GLOBAL_CONNECTOR_APIS`` dict in
``src/services/control_plane/connector_apis.py``. The Python module is kept
as a bootstrap seed manifest so first-run environments still get the full
catalogue - subsequent reads come from ``CONNAPI#{api_id} / META`` rows in
the foundry-workspace table.

Public shape mirrors the legacy module:

  get(api_id)          -> ConnectorAPISpec | None
  list_all()           -> list[ConnectorAPISpec]
  list_for_system(sys) -> list[ConnectorAPISpec]
  register(spec)       -> upsert
  delete(api_id)

Caching: an in-process TTL cache (5 min default) fronts DDB. A Redis pub/sub
channel ``connector-api-invalidate`` (best-effort) flushes the cache
cross-pod after every write.

Feature flag: ``USE_DDB_CONNECTOR_REGISTRY`` (default true). Set to
``false`` to short-circuit back to the in-memory registry - useful during
Phase 2 rollout.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from loguru import logger

from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)
from src.services.control_plane.connector_apis import ConnectorAPISpec


_CACHE_TTL_SECS = int(os.getenv("CONNECTOR_REGISTRY_CACHE_TTL", "300"))
_USE_DDB = (os.getenv("USE_DDB_CONNECTOR_REGISTRY", "true").strip().lower() != "false")


def _spec_to_attrs(spec: ConnectorAPISpec) -> Dict[str, Any]:
    return {
        "apiId": spec.api_id,
        "target_system": spec.target_system,
        "operation": spec.operation,
        "description": spec.description,
        "request_schema": spec.request_schema or {},
        "response_schema": spec.response_schema or {},
        "simulator_writeback": bool(spec.simulator_writeback),
        "risk_level": spec.risk_level,
        "tags": list(spec.tags or []),
    }


def _attrs_to_spec(attrs: Dict[str, Any]) -> ConnectorAPISpec:
    return ConnectorAPISpec(
        api_id=str(attrs.get("apiId") or attrs.get("api_id") or ""),
        target_system=str(attrs.get("target_system") or ""),
        operation=str(attrs.get("operation") or ""),
        description=str(attrs.get("description") or ""),
        request_schema=dict(attrs.get("request_schema") or {}),
        response_schema=dict(attrs.get("response_schema") or {}),
        simulator_writeback=bool(attrs.get("simulator_writeback", True)),
        risk_level=str(attrs.get("risk_level") or "low_risk_write"),
        tags=list(attrs.get("tags") or []),
    )


class ConnectorApiRegistryService:
    """Async DDB-backed connector-API registry with TTL caching."""

    _instance: Optional["ConnectorApiRegistryService"] = None

    def __init__(self, repo: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repo or FoundryWorkspaceRepository()
        self._cache: Dict[str, ConnectorAPISpec] = {}
        self._cache_loaded_at: float = 0.0
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "ConnectorApiRegistryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Cache primitives
    # ------------------------------------------------------------------

    def _cache_fresh(self) -> bool:
        return (time.time() - self._cache_loaded_at) < _CACHE_TTL_SECS and bool(self._cache)

    async def _ensure_cache(self) -> None:
        if self._cache_fresh():
            return
        async with self._lock:
            if self._cache_fresh():
                return
            try:
                rows = self._repo.list_conn_apis()
            except FoundryWorkspaceRepositoryError as e:
                logger.warning(f"ConnectorApiRegistry list DDB failed: {e}")
                return
            new_cache: Dict[str, ConnectorAPISpec] = {}
            for row in rows:
                spec = _attrs_to_spec(row)
                if spec.api_id:
                    new_cache[spec.api_id] = spec
            self._cache = new_cache
            self._cache_loaded_at = time.time()

    def invalidate(self) -> None:
        """Drop the in-process cache. Call after remote writes (pub/sub)."""
        self._cache = {}
        self._cache_loaded_at = 0.0

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    async def get(self, api_id: str) -> Optional[ConnectorAPISpec]:
        await self._ensure_cache()
        return self._cache.get(api_id)

    async def list_all(self) -> List[ConnectorAPISpec]:
        await self._ensure_cache()
        return list(self._cache.values())

    async def list_for_system(self, target_system: str) -> List[ConnectorAPISpec]:
        await self._ensure_cache()
        return [s for s in self._cache.values() if s.target_system == target_system]

    # ------------------------------------------------------------------
    # Public write API
    # ------------------------------------------------------------------

    async def register(self, spec: ConnectorAPISpec) -> ConnectorAPISpec:
        try:
            self._repo.put_conn_api(spec.api_id, _spec_to_attrs(spec))
            self.invalidate()
            await self._broadcast_invalidate(spec.api_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"ConnectorApiRegistry register({spec.api_id}) failed: {e}")
            raise
        return spec

    async def delete(self, api_id: str) -> bool:
        try:
            self._repo.delete_conn_api(api_id)
            self.invalidate()
            await self._broadcast_invalidate(api_id)
        except FoundryWorkspaceRepositoryError as e:
            logger.error(f"ConnectorApiRegistry delete({api_id}) failed: {e}")
            return False
        return True

    async def bootstrap_if_empty(self, seed_specs: List[ConnectorAPISpec]) -> int:
        """Populate DDB with the given seed manifest if the registry is empty.

        Idempotent; returns the number of rows written. Safe to call at
        every gateway startup - a non-empty registry short-circuits.
        """
        try:
            existing = self._repo.list_conn_apis()
        except FoundryWorkspaceRepositoryError as e:
            logger.warning(f"ConnectorApiRegistry bootstrap list failed: {e}")
            return 0
        if existing:
            return 0
        written = 0
        for spec in seed_specs:
            try:
                self._repo.put_conn_api(spec.api_id, _spec_to_attrs(spec))
                written += 1
            except FoundryWorkspaceRepositoryError as e:
                logger.warning(f"ConnectorApiRegistry bootstrap seed {spec.api_id} failed: {e}")
        if written:
            self.invalidate()
            logger.info(f"ConnectorApiRegistry bootstrapped {written} seed specs into DDB")
        return written

    # ------------------------------------------------------------------
    # Audit event pass-through (Phase 2 dual-write from connector_runtime)
    # ------------------------------------------------------------------

    async def append_audit(self, api_id: str, event: Dict[str, Any]) -> None:
        try:
            iso_ts = str(event.get("event_ts") or event.get("iso_ts") or "")
            event_id = str(event.get("event_id") or event.get("id") or "")
            if not iso_ts or not event_id:
                # Skip if the caller didn't provide required primary keys.
                return
            self._repo.put_conn_api_audit(api_id, iso_ts, event_id, event)
        except FoundryWorkspaceRepositoryError as e:
            logger.debug(f"ConnectorApiRegistry audit persist failed({api_id}): {e}")

    async def list_audit(self, api_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            return self._repo.list_conn_api_audit(api_id, limit=limit)
        except FoundryWorkspaceRepositoryError as e:
            logger.debug(f"ConnectorApiRegistry list_audit({api_id}) failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Redis invalidation
    # ------------------------------------------------------------------

    async def _broadcast_invalidate(self, api_id: str) -> None:
        try:
            from src.services import redis_client
            r = await redis_client.get_redis()
            if r is not None:
                await r.publish("connector-api-invalidate", api_id)
        except Exception:
            # Non-fatal - other pods will refresh on TTL expiry.
            pass


def get_connector_api_registry() -> ConnectorApiRegistryService:
    return ConnectorApiRegistryService.get_instance()


def is_ddb_registry_enabled() -> bool:
    return _USE_DDB
