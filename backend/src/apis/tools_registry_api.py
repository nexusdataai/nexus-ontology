"""
Tools Registry API (Reasoning plane, Phase 3.3, data-organization spec)

Read-only + resync endpoints over ``TOOLREG#`` rows in foundry-workspace.

  GET  /api/v1/tools-registry                     -> list
  GET  /api/v1/tools-registry/{tool_id}          -> one
  POST /api/v1/tools-registry/resync             -> re-project from in-memory
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Path, Query
from loguru import logger

from src.services.control_plane.tools_registry_service import (
    get_tools_registry_service,
)

router = APIRouter(prefix="/api/v1/tools-registry", tags=["Tools Registry"])

_tool_registry_ref: Any = None


def configure(tool_registry: Any) -> None:
    global _tool_registry_ref
    _tool_registry_ref = tool_registry


def _sanitize(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in item.items() if k not in {"PK", "SK", "GSI1PK", "GSI1SK"}}


@router.get("")
async def list_tools(group: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    items = await get_tools_registry_service().list(group)
    return {"total": len(items), "items": [_sanitize(i) for i in items]}


@router.get("/{tool_id}")
async def get_tool(tool_id: str = Path(...)) -> Dict[str, Any]:
    got = await get_tools_registry_service().get(tool_id)
    if not got:
        raise HTTPException(status_code=404, detail=f"tool not found: {tool_id}")
    return _sanitize(got)


@router.post("/resync")
async def resync() -> Dict[str, Any]:
    if _tool_registry_ref is None:
        raise HTTPException(status_code=503, detail="tool registry not wired")
    written = await get_tools_registry_service().sync_from_in_memory(_tool_registry_ref)
    return {"synced": written}
