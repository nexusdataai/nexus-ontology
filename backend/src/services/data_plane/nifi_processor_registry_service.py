"""
NiFi processor catalog sync (NIFIPROC# / NIFIASSET# in foundry-workspace).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.constants.nifi_processor_seeds import (
    load_asset_seeds,
    load_processor_seeds,
    nexus_bundle_name,
)
from src.repositories.foundry_workspace_repository import (
    FoundryWorkspaceRepository,
    FoundryWorkspaceRepositoryError,
)
from src.constants.nifi_processor_seeds import live_processor_ids
from src.services.flow_runtime.execution_policy import nifi_runtime_execution_enabled


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _python_live_ids() -> set:
    if nifi_runtime_execution_enabled():
        import src.services.flow_processors  # noqa: F401
        from src.services.flow_runtime.processor import list_registered_processor_ids

        return set(list_registered_processor_ids())
    return live_processor_ids()


def _processors_from_seeds() -> List[Dict[str, Any]]:
    """In-memory catalog when Dynamo is empty or unreachable (local K3s)."""
    registered = _python_live_ids()
    items: List[Dict[str, Any]] = []
    for seed in load_processor_seeds():
        pid = seed["processorId"]
        runtime = "live" if pid in registered else seed.get("runtime", "stub")
        items.append(
            {
                "processorId": pid,
                "nifiClass": seed.get("nifiClass"),
                "bundle": seed.get("bundle"),
                "label": seed.get("label"),
                "category": "nexus",
                "description": seed.get("description"),
                "tags": seed.get("tags") or [],
                "properties": seed.get("properties") or [],
                "relationships": seed.get("relationships") or [],
                "runtime": runtime,
                "codeRef": "python://src.services.flow_processors" if runtime == "live" else "",
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
    if not out.get("category"):
        out["category"] = "nexus"
    return out


class NiFiProcessorRegistryService:
    _instance: Optional["NiFiProcessorRegistryService"] = None

    def __init__(self, repo: Optional[FoundryWorkspaceRepository] = None):
        self._repo = repo or FoundryWorkspaceRepository()

    @classmethod
    def get_instance(cls) -> "NiFiProcessorRegistryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def list_processors(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        try:
            items = self._repo.list_nifi_procs(category)
        except Exception as e:
            logger.warning(f"Processor registry list (DDB) failed: {e}")
        if not items:
            items = _processors_from_seeds()
        items = [_normalize_processor_row(i) for i in items]
        if category:
            wanted = category.lower()
            if wanted not in ("nifi", "nexus"):
                items = [i for i in items if str(i.get("category", "")).lower() == wanted]
        return items

    async def get_processor(self, processor_id: str) -> Optional[Dict[str, Any]]:
        try:
            got = self._repo.get_nifi_proc(processor_id)
            if got:
                return got
        except Exception as e:
            logger.warning(f"Processor get({processor_id}) DDB failed: {e}")
        for row in _processors_from_seeds():
            if row.get("processorId") == processor_id:
                return row
        return None

    async def list_assets(self, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        try:
            items = self._repo.list_nifi_assets(kind)
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
        return self._repo.put_nifi_proc(processor_id, attrs)

    async def upsert_asset(self, asset_id: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attrs = dict(attrs)
        attrs.setdefault("assetId", asset_id)
        attrs.setdefault("updatedAt", _now_iso())
        return self._repo.put_nifi_asset(asset_id, attrs)

    async def sync_from_seeds(self) -> Dict[str, int]:
        """Project harvested JSON seeds + live python registry into DDB."""
        registered = _python_live_ids()
        proc_written = 0
        for seed in load_processor_seeds():
            pid = seed["processorId"]
            runtime = "live" if pid in registered else seed.get("runtime", "stub")
            code_ref = f"python://src.services.flow_processors" if runtime == "live" else ""
            attrs: Dict[str, Any] = {
                "processorId": pid,
                "nifiClass": seed.get("nifiClass"),
                "bundle": nexus_bundle_name(seed.get("bundle")),
                "label": seed.get("label"),
                "category": seed.get("category", "nifi"),
                "description": seed.get("description"),
                "tags": seed.get("tags") or [],
                "properties": seed.get("properties") or [],
                "relationships": seed.get("relationships") or [],
                "runtime": runtime,
                "codeRef": code_ref,
                "source": "nifi-harvest",
            }
            try:
                await self.upsert_processor(pid, attrs)
                proc_written += 1
            except FoundryWorkspaceRepositoryError as e:
                logger.warning(f"NiFi proc sync failed for {pid}: {e}")

        asset_written = 0
        for asset in load_asset_seeds():
            aid = asset["assetId"]
            try:
                await self.upsert_asset(aid, dict(asset))
                asset_written += 1
            except FoundryWorkspaceRepositoryError as e:
                logger.warning(f"NiFi asset sync failed for {aid}: {e}")

        if proc_written:
            logger.info(f"NiFi processor catalog synced {proc_written} rows (NIFIPROC#)")
        return {"processors": proc_written, "assets": asset_written}


def get_nifi_processor_registry_service() -> NiFiProcessorRegistryService:
    return NiFiProcessorRegistryService.get_instance()