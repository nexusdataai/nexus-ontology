"""
View CRUD + tab management API

Endpoints under /api/v1/views:
- POST   /                        create view
- GET    /                        list views
- GET    /{viewId}                get view with ordered tabs
- PUT    /{viewId}                update view metadata
- DELETE /{viewId}                delete view (and its solution backrefs + tab links)
- POST   /{viewId}/tabs           add tab
- PUT    /{viewId}/tabs/{tabId}   update tab
- DELETE /{viewId}/tabs/{tabId}   remove tab
- POST   /{viewId}/tabs/reorder   reorder tabs
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger

router = APIRouter(prefix="/api/v1/views", tags=["Views"])

_view_service = None


def configure(view_service):
    global _view_service
    _view_service = view_service


def _svc():
    if not _view_service:
        raise HTTPException(status_code=503, detail="View service not available")
    return _view_service


@router.post("")
async def create_view(request: Request):
    try:
        data = await request.json()
        return await _svc().create(data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.warning(f"View create failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_views(
    search: str = Query(default="", description="Search by name or description"),
    tags: Optional[str] = Query(default=None, description="Comma-separated tags"),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return await _svc().list_all(search=search, tags=tag_list)


@router.get("/{view_id}")
async def get_view(view_id: str):
    result = await _svc().get(view_id)
    if not result:
        raise HTTPException(status_code=404, detail="View not found")
    return result


@router.put("/{view_id}")
async def update_view(view_id: str, request: Request):
    try:
        data = await request.json()
        return await _svc().update(view_id, data)
    except ValueError as ve:
        detail = str(ve)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail)
        if "version conflict" in detail.lower():
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        logger.warning(f"View update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{view_id}")
async def delete_view(view_id: str):
    await _svc().delete(view_id)
    return {"status": "deleted", "viewId": view_id}


@router.post("/{view_id}/tabs")
async def add_tab(view_id: str, request: Request):
    try:
        data = await request.json()
        return await _svc().add_tab(view_id, data)
    except ValueError as ve:
        detail = str(ve)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        logger.warning(f"View add_tab failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{view_id}/tabs/{tab_id}")
async def update_tab(view_id: str, tab_id: str, request: Request):
    try:
        data = await request.json()
        return await _svc().update_tab(view_id, tab_id, data)
    except ValueError as ve:
        detail = str(ve)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        logger.warning(f"View update_tab failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{view_id}/tabs/{tab_id}")
async def remove_tab(view_id: str, tab_id: str):
    try:
        return await _svc().remove_tab(view_id, tab_id)
    except Exception as e:
        logger.warning(f"View remove_tab failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{view_id}/tabs/reorder")
async def reorder_tabs(view_id: str, request: Request):
    try:
        data = await request.json()
        tab_ids = data.get("tabIds") or data.get("tab_ids") or []
        return await _svc().reorder_tabs(view_id, list(tab_ids))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.warning(f"View reorder_tabs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
