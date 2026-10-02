"""Diagnostics endpoints for the Data Queues subsystem.

Read-only inspection of every queue belonging to a running journey plus
a purge affordance for operators / tests. Powered by the same
DataQueueManager used by the runner so the snapshot always reflects
live state.

Endpoints:
  GET  /api/v1/control-plane/runs/{run_id}/queues
  DELETE /api/v1/control-plane/runs/{run_id}/queues
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/v1/control-plane/runs", tags=["Data Queues"])

_queue_manager: Any = None


def configure(*, queue_manager: Any) -> None:
    """Wire the live DataQueueManager handle. Called from mcp_http_gateway."""
    global _queue_manager
    _queue_manager = queue_manager


@router.get("/{run_id}/queues")
async def get_run_queues(run_id: str) -> Dict[str, Any]:
    """Return per-queue depth + pending counts for ``run_id``.

    Shape: ``{run_id, queues: {queue_key: {depth, pending, ...}}}``.
    """
    if _queue_manager is None:
        raise HTTPException(status_code=503, detail="DataQueueManager not configured")
    try:
        snap = await _queue_manager.snapshot(run_id)
    except Exception as e:
        logger.warning(f"data-queue snapshot failed for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"run_id": run_id, "queues": snap}


@router.delete("/{run_id}/queues")
async def purge_run_queues(run_id: str) -> Dict[str, Any]:
    """Purge every queue owned by ``run_id``. Returns the purged count
    for the diagnostics view."""
    if _queue_manager is None:
        raise HTTPException(status_code=503, detail="DataQueueManager not configured")
    try:
        before = await _queue_manager.snapshot(run_id)
        await _queue_manager.reset_run(run_id)
    except Exception as e:
        logger.warning(f"data-queue purge failed for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"run_id": run_id, "purged_queues": len(before)}
