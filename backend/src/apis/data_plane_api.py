"""
Data Plane REST API

Exposes CRUD endpoints for managing Data Plane configurations
and an explore endpoint that delegates to FDW services or returns
mock responses for CDC/ETL types.

Validates: Requirements 2.1-2.8, 3.2-3.6, 4.3, 4.4, 6.2, 6.4
"""

from typing import List

from fastapi import APIRouter, HTTPException
from loguru import logger

from src.models.data_plane_models import (
    DataPlaneCreateRequest,
    DataPlaneResponse,
    DataPlaneType,
    DataPlaneUpdateRequest,
)
from src.utils.data_plane_errors import (
    DataPlaneNotFoundError,
    DataPlaneStorageError,
    DataPlaneValidationError,
)

dp_logger = logger.bind(component="data-plane")

router = APIRouter(prefix="/api/data-planes", tags=["data-planes"])

_service = None


def configure(service):
    """Configure Data Plane API with service instance. Called during app startup."""
    global _service
    _service = service


def _check_service():
    if _service is None:
        raise HTTPException(status_code=503, detail={"error": "Data Plane service not initialized"})


@router.post("", response_model=DataPlaneResponse, status_code=201)
async def create_data_plane(request: DataPlaneCreateRequest):
    _check_service()
    try:
        return await _service.create(request)
    except DataPlaneValidationError as e:
        raise HTTPException(status_code=422, detail={"error": "Validation error", "detail": str(e)})
    except DataPlaneStorageError as e:
        dp_logger.error("Create failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.get("", response_model=List[DataPlaneResponse])
async def list_data_planes():
    _check_service()
    try:
        return await _service.list_all()
    except DataPlaneStorageError as e:
        dp_logger.error("List failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.get("/{data_plane_id}", response_model=DataPlaneResponse)
async def get_data_plane(data_plane_id: str):
    _check_service()
    try:
        return await _service.get(data_plane_id)
    except DataPlaneNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "Data plane not found", "detail": data_plane_id})
    except DataPlaneStorageError as e:
        dp_logger.error("Get failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.put("/{data_plane_id}", response_model=DataPlaneResponse)
async def update_data_plane(data_plane_id: str, request: DataPlaneUpdateRequest):
    _check_service()
    try:
        return await _service.update(data_plane_id, request)
    except DataPlaneNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "Data plane not found", "detail": data_plane_id})
    except DataPlaneValidationError as e:
        raise HTTPException(status_code=422, detail={"error": "Validation error", "detail": str(e)})
    except DataPlaneStorageError as e:
        dp_logger.error("Update failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.delete("/{data_plane_id}", status_code=204)
async def delete_data_plane(data_plane_id: str):
    _check_service()
    try:
        await _service.delete(data_plane_id)
    except DataPlaneNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "Data plane not found", "detail": data_plane_id})
    except DataPlaneStorageError as e:
        dp_logger.error("Delete failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Storage error", "detail": str(e)})


@router.get("/{data_plane_id}/explore")
async def explore_data_plane(data_plane_id: str):
    _check_service()
    try:
        dp = await _service.get(data_plane_id)
    except DataPlaneNotFoundError:
        raise HTTPException(status_code=404, detail={"error": "Data plane not found", "detail": data_plane_id})

    if dp.type == DataPlaneType.FDW:
        # Delegate to existing FDW services
        try:
            from src.apis.fdw_api import _discovery_service
            if _discovery_service is None:
                raise HTTPException(
                    status_code=502,
                    detail={"error": "FDW connection failed", "detail": "FDW services not available"},
                )
            servers = await _discovery_service.list_foreign_servers()
            return {"type": "FDW", "servers": [s.dict() if hasattr(s, "dict") else s for s in servers], "message": None}
        except HTTPException:
            raise
        except Exception as e:
            dp_logger.error("FDW explore failed", error=str(e))
            raise HTTPException(status_code=502, detail={"error": "FDW connection failed", "detail": str(e)})
    else:
        # CDC/ETL mock response
        return {
            "type": dp.type.value,
            "servers": [],
            "message": f"{dp.type.value} integration is not yet implemented. This is a placeholder.",
        }
