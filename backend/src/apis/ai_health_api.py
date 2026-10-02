"""
AI Health Central API (AI-OPs plane, Phase 1)

Read + manual-trigger endpoints over the ``{cap}-{env}-health`` DynamoDB
table populated by ``AIHealthService``.

  GET  /api/v1/ai-health/latest?scope=all
  GET  /api/v1/ai-health/timeseries?scope=all&since=<iso>&limit=96
  POST /api/v1/ai-health/run?scope=all
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from src.services.ai_health_service import get_ai_health_service

router = APIRouter(prefix="/api/v1/ai-health", tags=["AI Health Central"])


_ALLOWED_SCOPES = {"all", "ai_ops", "data", "control", "reasoning", "workspace"}


def _validate_scope(scope: str) -> str:
    if scope not in _ALLOWED_SCOPES:
        raise HTTPException(status_code=400, detail=f"scope must be one of {sorted(_ALLOWED_SCOPES)}")
    return scope


@router.get("/latest", summary="Latest health snapshot for a scope")
async def latest(scope: str = Query("all")) -> Dict[str, Any]:
    scope = _validate_scope(scope)
    got = await get_ai_health_service().latest(scope)
    if not got:
        return {"scope": scope, "empty": True}
    return got


@router.get("/timeseries", summary="Recent health snapshots for a scope")
async def timeseries(
    scope: str = Query("all"),
    since: Optional[str] = Query(None, description="ISO 8601 timestamp lower bound"),
    limit: int = Query(96, ge=1, le=500),
) -> Dict[str, Any]:
    scope = _validate_scope(scope)
    since_dt: Optional[datetime] = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"invalid since ISO timestamp: {since}")
    items = await get_ai_health_service().timeseries(scope, since=since_dt, limit=limit)
    return {"scope": scope, "total": len(items), "items": items}


@router.post("/run", summary="Compute + persist a snapshot right now")
async def run_snapshot(scope: str = Query("all")) -> Dict[str, Any]:
    scope = _validate_scope(scope)
    snap = await get_ai_health_service().snapshot(scope)
    return snap
