"""
Data Source Mode admin API.

Two routes that drive the per-source ``simulator | real`` switch via the
``DataSourceModeService`` singleton:

  GET /api/v1/data-source-mode
       -> { "modes": {"sfdc":"simulator","oracle":"real",...},
            "default": "simulator",
            "available_sources": ["sfdc","oracle","sap","external"],
            "summary": {"simulator": 3, "real": 1} }

  PUT /api/v1/data-source-mode/{source}
       body: {"mode": "simulator" | "real"}
       -> { "source": "...", "mode": "...", "previous_mode": "..." }

Setting a source mode triggers any registered listener (e.g. the
simulator-load callback) and updates the SSM key
``data_source_mode/{source}`` so subsequent reads (and other replicas)
see the new value.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

ds_logger = logger.bind(component="data-source-mode-api")

router = APIRouter(prefix="/api/v1/data-source-mode", tags=["Data Source Mode"])

_mode_service: Any = None


def configure(mode_service: Any) -> None:
    global _mode_service
    _mode_service = mode_service


def _require_service() -> Any:
    if _mode_service is None:
        raise HTTPException(status_code=503, detail="Data source mode service not configured")
    return _mode_service


class SetModeRequest(BaseModel):
    mode: str = Field(..., description="'simulator' or 'real'")


@router.get("")
async def list_modes():
    svc = _require_service()
    modes = svc.all_modes()
    summary = {"simulator": 0, "real": 0}
    for v in modes.values():
        summary[v] = summary.get(v, 0) + 1
    return {
        "modes": modes,
        "default": svc.DEFAULT_MODE,
        "available_sources": list(svc.SOURCES),
        "summary": summary,
    }


@router.put("/{source}")
async def set_mode(source: str, body: SetModeRequest):
    svc = _require_service()
    if source not in svc.SOURCES:
        raise HTTPException(
            status_code=400,
            detail={"error": f"unknown source '{source}'", "allowed": list(svc.SOURCES)},
        )
    if body.mode not in ("simulator", "real"):
        raise HTTPException(
            status_code=400,
            detail={"error": f"mode must be 'simulator' or 'real', got '{body.mode}'"},
        )
    previous = svc.effective_mode(source)
    try:
        new_mode = await svc.set_mode(source, body.mode)
    except Exception as e:
        ds_logger.warning(f"set_mode({source}, {body.mode}) failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"source": source, "mode": new_mode, "previous_mode": previous}
