"""
Virtual Data Diagnostics REST API.

Surface for the new "Virtual Data" tab inside the existing
``/operations/diagnostics`` page.

Routes:
  GET  /api/v1/diagnostics/virtual-entities                 -> light index
  POST /api/v1/diagnostics/virtual-entities/{entity}/run    -> diagnose one
  POST /api/v1/diagnostics/virtual-entities/run-all         -> diagnose many
       (SSE if ``Accept: text/event-stream``)
"""

from __future__ import annotations

import json
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from src.models.virtual_data_diagnostics_models import (
    RunAllRequest,
    RunOneRequest,
    ScanResult,
    VirtualEntityDiagnostic,
    VirtualEntityIndexEntry,
)

router = APIRouter(prefix="/api/v1/diagnostics/virtual-entities",
                   tags=["Virtual Data Diagnostics"])

_service: Any = None


def configure(service: Any) -> None:
    global _service
    _service = service


def _svc():
    if not _service:
        raise HTTPException(status_code=503,
                            detail="Virtual data diagnostics service not available")
    return _service


@router.get("",
            response_model=List[VirtualEntityIndexEntry],
            response_model_by_alias=True)
async def list_virtual_entities():
    """Light index of every mapped virtual entity. Does NOT run the probe."""
    try:
        return await _svc().list_index()
    except Exception as e:
        logger.error(f"list_virtual_entities failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{entity}/run",
             response_model=VirtualEntityDiagnostic,
             response_model_by_alias=True)
async def run_one(entity: str, body: Optional[RunOneRequest] = None):
    """Run the full probe for a single virtual entity."""
    body = body or RunOneRequest()
    try:
        return await _svc().diagnose_entity(entity, limit=body.limit)
    except Exception as e:
        logger.error(f"run_one virtual-entity {entity} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-all")
async def run_all(request: Request, body: Optional[RunAllRequest] = None):
    """
    Run the probe for many virtual entities.

    Sends a streaming response (one ``VirtualEntityDiagnostic`` per event)
    if ``Accept: text/event-stream``; otherwise returns a single
    ``ScanResult`` JSON.
    """
    body = body or RunAllRequest()
    accepts = (request.headers.get("accept") or "").lower()
    if "text/event-stream" in accepts:
        return StreamingResponse(
            _stream_run_all(body),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    try:
        result: ScanResult = await _svc().diagnose_all(
            entities=body.entities,
            limit=body.limit,
            concurrency=body.concurrency,
        )
        return result.dict(by_alias=True)
    except Exception as e:
        logger.error(f"run_all virtual-entities failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _stream_run_all(body: RunAllRequest):
    """SSE generator: emits one event per entity + a summary event."""
    healthy = degraded = unhealthy = 0
    total = 0
    try:
        async for d in _svc().diagnose_all_streaming(
            entities=body.entities,
            limit=body.limit,
            concurrency=body.concurrency,
        ):
            total += 1
            overall_val = getattr(d.overall, "value", d.overall)
            if overall_val == "healthy":
                healthy += 1
            elif overall_val == "degraded":
                degraded += 1
            elif overall_val == "unhealthy":
                unhealthy += 1
            payload = json.dumps(
                {"type": "entity", "data": d.dict(by_alias=True)},
                default=str,
            )
            yield f"data: {payload}\n\n"

        summary = json.dumps({
            "type": "summary",
            "data": {
                "total": total,
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
            },
        })
        yield f"data: {summary}\n\n"
    except Exception as e:
        logger.error(f"_stream_run_all (virtual-entities) failed: {e}")
        err = json.dumps({"type": "error", "data": {"message": str(e)}})
        yield f"data: {err}\n\n"
