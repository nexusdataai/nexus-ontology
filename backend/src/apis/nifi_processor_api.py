"""
NiFi processor catalog API (Flow Studio).

GET  /api/v1/nifi-processors
GET  /api/v1/nifi-processors/{processor_id}
POST /api/v1/nifi-processors/resync
GET  /api/v1/nifi-assets
GET  /api/v1/nifi-assets/{asset_id}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from src.services.flow_runtime.execution_policy import require_nifi_runtime_execution, runtime_execution_capabilities
from src.services.data_plane.nifi_processor_probe import (
    default_probe_request,
    probe_batch,
    probe_processor,
    read_processor_source,
)
from src.services.data_plane.nifi_processor_registry_service import (
    get_nifi_processor_registry_service,
)

router = APIRouter(prefix="/api/v1/nifi-processors", tags=["nifi-processors"])
assets_router = APIRouter(prefix="/api/v1/nifi-assets", tags=["nifi-assets"])


def _sanitize(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in item.items() if k not in {"PK", "SK", "GSI1PK", "GSI1SK"}}


class ProcessorProbeBody(BaseModel):
    params: Dict[str, Any] = Field(default_factory=dict)
    content: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class ProcessorProbeBatchBody(BaseModel):
    processor_ids: List[str] = Field(default_factory=list)


@router.get("")
async def list_processors(category: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    items = await get_nifi_processor_registry_service().list_processors(category)
    return {
        "total": len(items),
        "items": [_sanitize(i) for i in items],
        "capabilities": runtime_execution_capabilities(),
    }


@router.post("/probe-batch")
async def probe_processors_batch(body: ProcessorProbeBatchBody) -> Dict[str, Any]:
    require_nifi_runtime_execution()
    return probe_batch(body.processor_ids)


@router.get("/{processor_id}/source")
async def get_processor_source(processor_id: str = Path(...)) -> Dict[str, Any]:
    got = await get_nifi_processor_registry_service().get_processor(processor_id)
    if not got:
        raise HTTPException(status_code=404, detail=f"processor not found: {processor_id}")
    return read_processor_source(processor_id)


@router.get("/{processor_id}/probe-defaults")
async def get_processor_probe_defaults(processor_id: str = Path(...)) -> Dict[str, Any]:
    got = await get_nifi_processor_registry_service().get_processor(processor_id)
    if not got:
        raise HTTPException(status_code=404, detail=f"processor not found: {processor_id}")
    return {"processorId": processor_id, **default_probe_request(processor_id)}


@router.post("/{processor_id}/probe")
async def run_processor_probe(processor_id: str = Path(...), body: ProcessorProbeBody = ...) -> Dict[str, Any]:
    require_nifi_runtime_execution()
    got = await get_nifi_processor_registry_service().get_processor(processor_id)
    if not got:
        raise HTTPException(status_code=404, detail=f"processor not found: {processor_id}")
    return probe_processor(
        processor_id,
        params=body.params,
        content=body.content,
        attributes=body.attributes,
    )


@router.get("/{processor_id}")
async def get_processor(processor_id: str = Path(...)) -> Dict[str, Any]:
    got = await get_nifi_processor_registry_service().get_processor(processor_id)
    if not got:
        raise HTTPException(status_code=404, detail=f"processor not found: {processor_id}")
    return _sanitize(got)


@router.post("/resync")
async def resync_processors() -> Dict[str, Any]:
    written = await get_nifi_processor_registry_service().sync_from_seeds()
    return {"synced": written}


@assets_router.get("")
async def list_assets(kind: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    items = await get_nifi_processor_registry_service().list_assets(kind)
    return {"total": len(items), "items": [_sanitize(i) for i in items]}


@assets_router.get("/{asset_id}")
async def get_asset(asset_id: str = Path(...)) -> Dict[str, Any]:
    from src.repositories.foundry_workspace_repository import FoundryWorkspaceRepository

    got = FoundryWorkspaceRepository().get_nifi_asset(asset_id)
    if not got:
        items = await get_nifi_processor_registry_service().list_assets()
        got = next((a for a in items if a.get("assetId") == asset_id), None)
    if not got:
        raise HTTPException(status_code=404, detail=f"asset not found: {asset_id}")
    return _sanitize(got)