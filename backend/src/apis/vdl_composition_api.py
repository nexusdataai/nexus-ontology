from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.models.vdl_composition_models import (
    VdlCompositionResponse,
    VdlCompositionUpsertRequest,
    VdlCompositionValidateResponse,
)
from src.services.vdl_composition_service import (
    VdlCompositionNotFoundError,
    VdlCompositionService,
    VdlCompositionStorageError,
)

router = APIRouter(prefix="/api/v1/vdl-compositions", tags=["vdl-compositions"])

_service: Optional[VdlCompositionService] = None


def configure(service: VdlCompositionService) -> None:
    global _service
    _service = service


def _check():
    if _service is None:
        raise HTTPException(status_code=503, detail={"error": "VDL composition service not initialized"})


@router.get("", response_model=List[VdlCompositionResponse])
async def list_compositions():
    _check()
    try:
        return await _service.list_all()
    except VdlCompositionStorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{virtual_entity}", response_model=VdlCompositionResponse)
async def get_composition(virtual_entity: str):
    _check()
    try:
        return await _service.get(virtual_entity)
    except VdlCompositionNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "Composition not found"})
    except VdlCompositionStorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{virtual_entity}", response_model=VdlCompositionResponse)
async def upsert_composition(virtual_entity: str, request: VdlCompositionUpsertRequest):
    _check()
    if request.virtual_entity != virtual_entity:
        raise HTTPException(status_code=422, detail="virtualEntity in body must match path")
    try:
        return await _service.upsert(request)
    except VdlCompositionStorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{virtual_entity}/validate", response_model=VdlCompositionValidateResponse)
async def validate_composition(
    virtual_entity: str,
    limit: int = Query(default=5, ge=1, le=100),
):
    _check()
    try:
        return await _service.validate(virtual_entity, limit=limit)
    except VdlCompositionNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "Composition not found"})
    except VdlCompositionStorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrate-from-mapping-rules")
async def migrate_from_mapping_rules():
    _check()
    try:
        return await _service.migrate_from_active_mapping_rules()
    except VdlCompositionStorageError as e:
        raise HTTPException(status_code=500, detail=str(e))