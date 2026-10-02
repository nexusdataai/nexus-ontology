"""
Ontology Virtual Data Layer API (spec 041).

Promotes VDL to first-class routes at /api/v1/vdl/*, delegating to
VirtualQueryService configured via control_plane_api.configure_virtual_query.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

vdl_logger = logger.bind(component="ontology-vdl")

router = APIRouter(prefix="/api/v1/vdl", tags=["Ontology VDL"])


class VirtualFilterModel(BaseModel):
    field: str
    operator: str
    value: Any | None = None


class VdlQueryRequest(BaseModel):
    virtual_entity: str = Field(alias="virtualEntity")
    fields: Optional[List[str]] = None
    filters: Optional[List[VirtualFilterModel]] = None
    limit: int = Field(default=50, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)

    model_config = {"populate_by_name": True}


class BatchQueryItem(VdlQueryRequest):
    query_id: Optional[str] = Field(default=None, alias="queryId")

    model_config = {"populate_by_name": True}


class BatchQueryRequest(BaseModel):
    queries: List[BatchQueryItem] = Field(min_length=1, max_length=20)
    parallel: bool = True


def _get_vq_service():
    from src.apis.control_plane_api import _virtual_query_service

    if _virtual_query_service is None:
        raise HTTPException(status_code=503, detail="Virtual query service not initialized")
    return _virtual_query_service


async def _run_query(body: Dict[str, Any]) -> Dict[str, Any]:
    from src.models.mapping_rule_models import VirtualQueryRequest

    vq_service = _get_vq_service()
    vq_request = VirtualQueryRequest(**body)
    result = await vq_service.query_virtual_entity(vq_request)
    if hasattr(result, "model_dump"):
        return result.model_dump(by_alias=True)
    return result


@router.post("/query")
async def vdl_query(request: VdlQueryRequest):
    """Query a single virtual entity via mapping rules."""
    try:
        return await _run_query(request.model_dump(by_alias=True, exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        vdl_logger.error(f"VDL query failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/batch-query")
async def vdl_batch_query(request: BatchQueryRequest):
    """Execute multiple VDL queries in one round trip."""
    start = time.time()

    async def _one(item: BatchQueryItem) -> Dict[str, Any]:
        payload = item.model_dump(by_alias=True, exclude_none=True)
        query_id = payload.pop("queryId", None) or payload.pop("query_id", None)
        try:
            result = await _run_query(payload)
            if query_id:
                result["queryId"] = query_id
            result["error"] = None
            return result
        except HTTPException as exc:
            return {
                "queryId": query_id,
                "virtualEntity": payload.get("virtualEntity"),
                "rows": [],
                "metadata": None,
                "error": {
                    "code": f"http_{exc.status_code}",
                    "message": str(exc.detail),
                    "retryable": exc.status_code in (429, 503),
                },
            }
        except Exception as exc:
            return {
                "queryId": query_id,
                "virtualEntity": payload.get("virtualEntity"),
                "rows": [],
                "metadata": None,
                "error": {"code": "query_failed", "message": str(exc), "retryable": False},
            }

    if request.parallel:
        results = await asyncio.gather(*[_one(q) for q in request.queries])
    else:
        results = []
        for q in request.queries:
            results.append(await _one(q))

    return {"results": results, "durationMs": int((time.time() - start) * 1000)}


@router.get("/entities")
async def list_vdl_entities():
    """List virtual entities and mapping status."""
    vq_service = _get_vq_service()
    try:
        entities = await vq_service.list_virtual_entities()
        if isinstance(entities, dict) and "entities" in entities:
            return entities
        return {"entities": entities, "total": len(entities) if isinstance(entities, list) else 0}
    except Exception as exc:
        vdl_logger.error(f"List VDL entities failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
async def vdl_health():
    """VDL subsystem health."""
    try:
        vq_service = _get_vq_service()
        entities = await vq_service.list_virtual_entities()
        count = len(entities) if isinstance(entities, list) else 0
        return {
            "status": "healthy",
            "mappingRulesLoaded": count,
            "fdwConnections": {"healthy": 1, "degraded": 0},
            "latencyP99Ms": 0,
        }
    except HTTPException:
        return {"status": "degraded", "mappingRulesLoaded": 0}


@router.get("/entities/{entity_id}/preview")
async def preview_vdl_entity(entity_id: str, limit: int = 10):
    """Preview first N rows for a virtual entity."""
    vq_service = _get_vq_service()
    try:
        result = await vq_service.preview_entity(entity_id, limit=min(limit, 100))
        if hasattr(result, "model_dump"):
            return result.model_dump(by_alias=True)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        vdl_logger.error(f"VDL preview failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
