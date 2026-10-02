"""
Data Source REST API (Data Plane, Phase 2)

  GET    /api/v1/data-sources
  GET    /api/v1/data-sources/{id}
  PUT    /api/v1/data-sources/{id}
  DELETE /api/v1/data-sources/{id}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Path
from pydantic import BaseModel

from src.services.data_plane.data_source_service import get_data_source_service

router = APIRouter(prefix="/api/v1/data-sources", tags=["Data Sources"])


class DataSourceRequest(BaseModel):
    dataPlaneId: Optional[str] = None
    type: str
    name: str
    schemaName: Optional[str] = None
    connectionRef: Optional[str] = None
    mode: Optional[str] = None  # simulator | real
    simulatorKey: Optional[str] = None
    verticals: List[str] = []
    description: str = ""


def _sanitize(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in item.items() if k not in {"PK", "SK", "GSI1PK", "GSI1SK"}}


@router.get("")
async def list_data_sources() -> Dict[str, Any]:
    items = await get_data_source_service().list()
    return {"total": len(items), "items": [_sanitize(i) for i in items]}


@router.get("/{data_source_id}")
async def get_data_source(data_source_id: str = Path(...)) -> Dict[str, Any]:
    got = await get_data_source_service().get(data_source_id)
    if not got:
        raise HTTPException(status_code=404, detail=f"data source not found: {data_source_id}")
    return _sanitize(got)


@router.put("/{data_source_id}")
async def put_data_source(
    data_source_id: str = Path(...),
    body: DataSourceRequest = Body(...),
) -> Dict[str, Any]:
    if body.mode is not None and body.mode not in ("simulator", "real"):
        raise HTTPException(status_code=400, detail="mode must be 'simulator' or 'real'")
    saved = await get_data_source_service().put(data_source_id, body.model_dump())
    return _sanitize(saved)


@router.delete("/{data_source_id}", status_code=204)
async def delete_data_source(data_source_id: str = Path(...)) -> None:
    await get_data_source_service().delete(data_source_id)
    return None
