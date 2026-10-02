"""
Solution CRUD + association API

Endpoints under /api/v1/solutions:
- POST   /                          create solution
- GET    /                          list solutions
- GET    /{solutionId}              get solution with ordered views
- PUT    /{solutionId}              update solution metadata
- DELETE /{solutionId}              delete solution (and its view links)
- POST   /{solutionId}/views        link a view to the solution
- DELETE /{solutionId}/views/{viewId}
- POST   /{solutionId}/views/reorder
- GET    /by-app/{appId}            lookup by frontend appRegistry id
"""

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger

router = APIRouter(prefix="/api/v1/solutions", tags=["Solutions"])

_solution_service = None


def configure(solution_service):
    global _solution_service
    _solution_service = solution_service


def _svc():
    if not _solution_service:
        raise HTTPException(status_code=503, detail="Solution service not available")
    return _solution_service


@router.post("")
async def create_solution(request: Request):
    try:
        data = await request.json()
        return await _svc().create(data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.warning(f"Solution create failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_solutions(search: str = Query(default="", description="Search by name or description")):
    return await _svc().list_all(search=search)


@router.get("/by-app/{app_id}")
async def get_solution_by_app(app_id: str):
    result = await _svc().get_by_app_id(app_id)
    if not result:
        raise HTTPException(status_code=404, detail="Solution not found for app")
    return result


@router.get("/{solution_id}")
async def get_solution(solution_id: str):
    result = await _svc().get(solution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Solution not found")
    return result


@router.put("/{solution_id}")
async def update_solution(solution_id: str, request: Request):
    try:
        data = await request.json()
        return await _svc().update(solution_id, data)
    except ValueError as ve:
        detail = str(ve)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail)
        if "version conflict" in detail.lower():
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        logger.warning(f"Solution update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{solution_id}")
async def delete_solution(solution_id: str):
    await _svc().delete(solution_id)
    return {"status": "deleted", "solutionId": solution_id}


@router.post("/{solution_id}/views")
async def add_view_to_solution(solution_id: str, request: Request):
    try:
        data = await request.json()
        view_id = data.get("viewId") or data.get("view_id")
        if not view_id:
            raise ValueError("viewId is required")
        position = data.get("position")
        display_name = data.get("displayName") or data.get("display_name")
        return await _svc().add_view(solution_id, view_id, position=position, display_name=display_name)
    except ValueError as ve:
        detail = str(ve)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        logger.warning(f"Solution add_view failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{solution_id}/views/{view_id}")
async def remove_view_from_solution(solution_id: str, view_id: str):
    try:
        return await _svc().remove_view(solution_id, view_id)
    except Exception as e:
        logger.warning(f"Solution remove_view failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{solution_id}/views/reorder")
async def reorder_solution_views(solution_id: str, request: Request):
    try:
        data = await request.json()
        view_ids = data.get("viewIds") or data.get("view_ids") or []
        return await _svc().reorder_views(solution_id, list(view_ids))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.warning(f"Solution reorder_views failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
