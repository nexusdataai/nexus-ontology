"""
Knowledge Pipeline API (Control plane, Phase 3.4).

  GET  /api/v1/knowledge-pipelines
  GET  /api/v1/knowledge-pipelines/{id}
  GET  /api/v1/knowledge-pipelines/{id}/runs
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Path, Query

from src.services.control_plane.knowledge_pipeline_service import (
    get_knowledge_pipeline_service,
)

router = APIRouter(prefix="/api/v1/knowledge-pipelines", tags=["Knowledge Pipelines"])


def _sanitize(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in item.items() if k not in {"PK", "SK", "GSI1PK", "GSI1SK"}}


@router.get("")
async def list_pipelines() -> Dict[str, Any]:
    items = await get_knowledge_pipeline_service().list()
    return {"total": len(items), "items": [_sanitize(i) for i in items]}


@router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: str = Path(...)) -> Dict[str, Any]:
    got = await get_knowledge_pipeline_service().get(pipeline_id)
    if not got:
        raise HTTPException(status_code=404, detail=f"pipeline not found: {pipeline_id}")
    return _sanitize(got)


@router.get("/{pipeline_id}/runs")
async def list_runs(
    pipeline_id: str = Path(...),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    items = await get_knowledge_pipeline_service().list_runs(pipeline_id, limit=limit)
    return {"pipelineId": pipeline_id, "total": len(items), "items": [_sanitize(i) for i in items]}
