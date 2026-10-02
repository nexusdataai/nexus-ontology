"""
Virtual Data API REST surface (Data Plane, Phase 2)

CRUD + invoke for the VDL API Registry (VDLAPI# rows in foundry-workspace).

  GET    /api/v1/vdl-apis
  GET    /api/v1/vdl-apis/{api_id}
  POST   /api/v1/vdl-apis
  PUT    /api/v1/vdl-apis/{api_id}
  DELETE /api/v1/vdl-apis/{api_id}
  POST   /api/v1/vdl-apis/{api_id}/invoke
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Path, Query
from loguru import logger
from pydantic import BaseModel

from src.models.vdl_api_models import (
    DirectSqlBinding,
    ImplBinding,
    InvokeResult,
    VdlApiSpec,
)
from src.services.data_plane import vdl_api_executor
from src.services.data_plane.vdl_api_registry_service import get_vdl_api_registry

router = APIRouter(prefix="/api/v1/vdl-apis", tags=["Virtual Data API Registry"])
vdl_logger = logger.bind(component="vdl-api")


class VdlApiCreate(BaseModel):
    api_id: str
    verb: str = "read"
    virtual_entity: str
    parameters_schema: Dict[str, Any] = {}
    impl: List[ImplBinding] = []
    direct_sql: Optional[DirectSqlBinding] = None
    risk_level: str = "read_only"
    description: str = ""
    tags: List[str] = []


class InvokeRequest(BaseModel):
    args: Dict[str, Any] = {}


def _to_row(spec: VdlApiSpec) -> Dict[str, Any]:
    return spec.model_dump()


@router.get("", summary="List every VDL API")
async def list_vdl_apis(
    virtual_entity: Optional[str] = Query(default=None),
    verb: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    items = await get_vdl_api_registry().list(virtual_entity=virtual_entity, verb=verb)
    return {"total": len(items), "items": [_to_row(s) for s in items]}


@router.get("/{api_id}", summary="Fetch one VDL API spec")
async def get_vdl_api(api_id: str = Path(...)) -> Dict[str, Any]:
    spec = await get_vdl_api_registry().get(api_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"vdl api not found: {api_id}")
    return _to_row(spec)


@router.post("", status_code=201, summary="Register / update a VDL API")
async def register_vdl_api(body: VdlApiCreate) -> Dict[str, Any]:
    spec = VdlApiSpec(**body.model_dump())
    await get_vdl_api_registry().register(spec)
    return _to_row(spec)


@router.put("/{api_id}", summary="Update a VDL API")
async def update_vdl_api(
    api_id: str = Path(...),
    body: VdlApiCreate = Body(...),
) -> Dict[str, Any]:
    if body.api_id != api_id:
        raise HTTPException(status_code=400, detail="path api_id and body api_id must match")
    return await register_vdl_api(body)


@router.delete("/{api_id}", status_code=204, summary="Remove a VDL API")
async def delete_vdl_api(api_id: str = Path(...)) -> None:
    ok = await get_vdl_api_registry().delete(api_id)
    if not ok:
        raise HTTPException(status_code=500, detail=f"failed to delete {api_id}")
    return None


@router.post("/{api_id}/invoke", summary="Resolve + execute a VDL API")
async def invoke_vdl_api(
    api_id: str = Path(...),
    body: InvokeRequest = Body(default_factory=InvokeRequest),
) -> InvokeResult:
    reg = get_vdl_api_registry()
    try:
        plan = await reg.resolve(api_id, body.args or {})
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return await vdl_api_executor.execute(plan)
