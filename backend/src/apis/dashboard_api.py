"""
Dashboard CRUD API

Provides endpoints for creating, reading, updating, deleting, listing,
and cloning dashboards used by the Dashboard Builder.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger

router = APIRouter(prefix="/api/v1/dashboards", tags=["Dashboards"])

_dashboard_service = None


def configure(dashboard_service):
    global _dashboard_service
    _dashboard_service = dashboard_service


def _svc():
    if not _dashboard_service:
        raise HTTPException(status_code=503, detail="Dashboard service not available")
    return _dashboard_service


@router.post("")
async def create_dashboard(request: Request):
    try:
        data = await request.json()
        result = await _svc().create(data)
        return result
    except Exception as e:
        logger.warning(f"Dashboard create failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_dashboards(
    search: str = Query(default="", description="Search by title or description"),
    tags: Optional[str] = Query(default=None, description="Comma-separated tags"),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    dashboards = await _svc().list_all(search=search, tags=tag_list)
    items = []
    for d in dashboards:
        items.append({
            "uid": d.get("uid", ""),
            "title": d.get("title", ""),
            "description": d.get("description"),
            "tags": d.get("tags", []),
            "panelCount": len(d.get("panels", [])),
            "createdAt": d.get("createdAt", ""),
            "updatedAt": d.get("updatedAt", ""),
            "createdBy": d.get("createdBy", ""),
        })
    return items


@router.get("/{uid}")
async def get_dashboard(uid: str):
    result = await _svc().get(uid)
    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return result


@router.put("/{uid}")
async def update_dashboard(uid: str, request: Request):
    try:
        data = await request.json()
        result = await _svc().update(uid, data)
        return result
    except ValueError as ve:
        detail = str(ve)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail)
        if "version conflict" in detail.lower():
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        logger.warning(f"Dashboard update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{uid}")
async def delete_dashboard(uid: str):
    await _svc().delete(uid)
    return {"status": "deleted", "uid": uid}


@router.post("/{uid}/clone")
async def clone_dashboard(uid: str):
    try:
        result = await _svc().clone(uid)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.warning(f"Dashboard clone failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
