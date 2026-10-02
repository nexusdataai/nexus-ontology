"""
Diagnostics History API (AI-OPs plane, Phase 1)

Read-only endpoints for retrieving persisted diagnostic runs. Rows are
written automatically by ``diagnostics_recorder`` middleware after each
call to any ``/api/v1/diagnostics/*`` route, plus the connector API
diagnostics under ``/api/v1/connector-apis/diagnostic``.

  GET /api/v1/diagnostics/history?scope=o2c&limit=50
      -> [{scope, run_id, recordedAt, succeeded, summary, result}]
  GET /api/v1/diagnostics/history/scopes
      -> {scopes: [...]}
  GET /api/v1/diagnostics/history/{scope}/{run_id}
      -> full record
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from src.services.diagnostics_history_service import get_diagnostics_history_service

router = APIRouter(prefix="/api/v1/diagnostics/history", tags=["Diagnostics History"])


@router.get("", summary="List diagnostic runs for a scope")
async def list_runs(
    scope: str = Query(..., description="Diagnostic family, e.g. 'o2c', 'simulators', 'react-tools'"),
    limit: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    svc = get_diagnostics_history_service()
    items: List[Dict[str, Any]] = await svc.list(scope, limit=limit)
    return {"scope": scope, "total": len(items), "items": items}


@router.get("/scopes", summary="List distinct diagnostic scopes seen so far")
async def list_scopes() -> Dict[str, Any]:
    svc = get_diagnostics_history_service()
    scopes = await svc.scopes()
    return {"scopes": scopes}


@router.get("/{scope}/{run_id}", summary="Fetch one diagnostic run by id")
async def get_run(scope: str, run_id: str) -> Dict[str, Any]:
    svc = get_diagnostics_history_service()
    got: Optional[Dict[str, Any]] = await svc.get(scope, run_id)
    if not got:
        raise HTTPException(status_code=404, detail=f"run not found: {scope}/{run_id}")
    return got
