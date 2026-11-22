"""
Nexus data processor catalog sync (legacy Dynamo keys NIFIPROC# / NIFIASSET#).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.constants.flow_processor_seeds import (
    live_processor_ids,
    load_asset_seeds,
    load_processor_seeds,
    nexus_bundle_name,
)
from src.constants.registered_flow_processors import registered_flow_processor_ids
from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)
from src.services.flow_runtime.execution_policy import flow_runtime_execution_enabled
from src.services.flow_runtime.processor_ids import canonical_processor_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _python_live_ids() -> set:
    from src.services.flow_processors import ensure_all_processors_loaded
    from src.services.flow_runtime.processor import list_registered_processor_ids

    ensure_all_processors_loaded()
    return set(list_registered_processor_ids())


def _processors_from_seeds() -> List[Dict[str, Any]]:
    """In-memory catalog when Dynamo is empty or unreachable (local K3s)."""
    items: List[Dict[str, Any]] = []
    for seed in load_processor_seeds():
        pid = seed["processorId"]
        runtime = "live"
        items.append(
            {
                "processorId": pid,
                "bundle": seed.get("bundle"),
                "label": seed.get("label"),
                "category": "nexus",
                "description": seed.get("description"),
                "tags": [t for t in (seed.get("tags") or []) if t.lower() != "flowfile"],
                "properties": seed.get("properties") or [],
                "relationships": seed.get("relationships") or [{"name": "success"}, {"name": "failure"}],
                "runtime": runtime,
                "implementation": "python",
                "codeRef": "python://src.services.flow_processors",
                "source": "seed",
                "updatedAt": _now_iso(),
            }
        )
    return items


def _assets_from_seeds() -> List[Dict[str, Any]]:
    return [dict(a) for a in load_asset_seeds()]


def _normalize_processor_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    out["bundle"] = nexus_bundle_name(out.get("bundle"))
    out.pop("nifiClass", None)
    if out.get("processorId"):
        out["processorId"] = canonical_processor_id(str(out["processorId"]))
    cat = str(out.get("category") or "").lower()
    if not cat or cat in ("nifi", "legacy"):
        out["category"] = "nexus"
    return out


class NexusDataProcessorRegistryService:
    _instance: Optional["NexusDataProcessorRegistryService"] = None

    def __init__(self, repo: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repo or FoundryWorkspaceRepository()

    @classmethod
    def get_instance(cls) -> "NexusDataProcessorRegistryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def list_processors(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        allowed = registered_flow_processor_ids()
        items = [_normalize_processor_row(i) for i in _processors_from_seeds() if i["processorId"] in allowed]
        if category:
            wanted = category.lower()
            if wanted not in ("nexus",):
                items = [i for i in items if str(i.get("category", "")).lower() == wanted]
        return items

    async def get_processor(self, processor_id: str) -> Optional[Dict[str, Any]]:
        cid = canonical_processor_id(processor_id)
        if cid not in registered_flow_processor_ids():
            return None
        for row in _processors_from_seeds():
            if row.get("processorId") == cid:
                return row
        try:
            got = self._repo.get_data_processor_proc(cid) or self._repo.get_data_processor_proc(processor_id)
            if got:
                return _normalize_processor_row(got)
        except Exception as e:
            logger.warning(f"Processor get({processor_id}) DDB failed: {e}")
        return None

    async def list_assets(self, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        try:
            items = self._repo.list_data_flow_assets(kind)
        except Exception as e:
            logger.warning(f"Flow asset list (DDB) failed: {e}")
        if not items:
            items = _assets_from_seeds()
        if kind:
            wanted = kind.lower()
            items = [i for i in items if str(i.get("kind", "")).lower() == wanted]
        return items

    async def upsert_processor(self, processor_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attrs = dict(attrs)
        attrs.setdefault("processorId", processor_id)
        attrs.setdefault("updatedAt", _now_iso())
        return self._repo.put_data_processor_proc(processor_id, attrs)

    async def upsert_asset(self, asset_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attrs = dict(attrs)
        attrs.setdefault("assetId", asset_id)
        attrs.setdefault("updatedAt", _now_iso())
        return self._repo.put_data_flow_asset(asset_id, attrs)

    async def sync_from_seeds(self) -> Dict[str, int]:
        """Project JSON seeds + live python registry into DDB."""
        allowed = registered_flow_processor_ids()
        proc_written = 0
        for seed in load_processor_seeds():
            pid = seed["processorId"]
            if pid not in allowed:
                continue
            attrs: Dict[str, Any] = {
                "processorId": pid,
                "bundle": nexus_bundle_name(seed.get("bundle")),
                "label": seed.get("label"),
                "category": "nexus",
                "description": seed.get("description"),
                "tags": [t for t in (seed.get("tags") or []) if t.lower() != "flowfile"],
                "properties": seed.get("properties") or [],
                "relationships": seed.get("relationships") or [{"name": "success"}, {"name": "failure"}],
                "runtime": "live",
                "implementation": "python",
                "codeRef": "python://src.services.flow_processors",
                "source": "catalog",
            }
            try:
                await self.upsert_processor(pid, attrs)
                proc_written += 1
            except FoundryWorkspaceRepositoryError as e:
                logger.warning(f"Flow proc sync failed for {pid}: {e}")

        deleted = 0
        try:
            for row in self._repo.list_data_processor_procs():
                pid = canonical_processor_id(str(row.get("processorId") or ""))
                if pid and pid not in allowed:
                    self._repo.delete_data_processor_proc(pid)
                    deleted += 1
        except Exception as e:
            logger.warning(f"Processor registry cleanup failed: {e}")

        asset_written = 0
        for asset in load_asset_seeds():
            aid = asset["assetId"]
            try:
                await self.upsert_asset(aid, dict(asset))
                asset_written += 1
            except FoundryWorkspaceRepositoryError as e:
                logger.warning(f"Flow asset sync failed for {aid}: {e}")

        if proc_written or deleted:
            logger.info(f"Data processor catalog synced {proc_written} rows, removed {deleted} stale")
        return {"processors": proc_written, "assets": asset_written, "deleted": deleted}


def get_nexus_data_processor_registry_service() -> NexusDataProcessorRegistryService:
    return NexusDataProcessorRegistryService.get_instance()