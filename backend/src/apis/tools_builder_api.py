"""
Tool Builder REST API.

Routes:

  GET    /api/v1/tools                            list with filters
  POST   /api/v1/tools                            create
  GET    /api/v1/tools/{id}                       full doc + current source
  PUT    /api/v1/tools/{id}                       update (writes new VERSION)
  DELETE /api/v1/tools/{id}                       soft delete
  GET    /api/v1/tools/{id}/versions              list versions
  GET    /api/v1/tools/{id}/versions/{n}          version snapshot
  POST   /api/v1/tools/{id}/restore/{n}           promote a version back to current
  POST   /api/v1/tools/{id}/test                  run with sample params
  POST   /api/v1/tools/import                     bulk import
  GET    /api/v1/tools/export                     bulk export

Every successful mutation:
  1. Updates DDB through ToolStoreService.
  2. Re-registers / unregisters the tool in the live ToolRegistry via
     DynamicToolLoader (so /chat sees the change immediately on this pod).
  3. Publishes a tool-cache-invalidate event for sibling pods.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Path, Query
from loguru import logger

from src.models.tool_builder_models import (
    ToolCreate,
    ToolDoc,
    ToolImportBundle,
    ToolImportResult,
    ToolSummary,
    ToolTestRequest,
    ToolTestResponse,
    ToolUpdate,
    ToolVersion,
)
from src.services.control_plane.dynamic_tool_helpers import Ctx
from src.services.control_plane.dynamic_tool_loader import DynamicToolLoader

router = APIRouter(prefix="/api/v1/tools", tags=["Tool Builder"])
tb_logger = logger.bind(component="tools-builder-api")

_store: Any = None
_loader: Optional[DynamicToolLoader] = None
_registry: Any = None


def configure(
    store: Any,
    loader: Optional[DynamicToolLoader] = None,
    registry: Any = None,
) -> None:
    """Wire the store + loader + registry once at startup."""
    global _store, _loader, _registry
    _store = store
    _loader = loader
    _registry = registry


def _require_store():
    if _store is None:
        raise HTTPException(status_code=503, detail="Tool store not configured")
    return _store


def _re_register_in_registry(meta: dict) -> None:
    """Replace (or add) the tool in the live ``ToolRegistry`` on this pod."""
    if _registry is None or _loader is None:
        return
    try:
        # Drop cached compile if any.
        _loader.invalidate(meta.get("tool_id") or "")
        # If a code-defined tool already owns this name, skip.
        from src.services.control_plane.tool_registry import Tool
        existing = _registry.get(meta.get("name") or "")
        if existing and getattr(existing, "execute", None) and getattr(existing, "name", None) == meta.get("name"):
            # Re-register (overwrites) - simplest path; loader produces the new Tool.
            pass
        new_tool = _loader.make_tool(meta)
        _registry.register(new_tool)
    except Exception as e:
        tb_logger.debug("registry re-register failed: {}", e)


def _unregister_in_registry(name: Optional[str], tool_id: Optional[str]) -> None:
    if _registry is None or not name:
        return
    try:
        # No public unregister; reach into the dict directly.
        if hasattr(_registry, "_tools"):
            _registry._tools.pop(name, None)
        if _loader and tool_id:
            _loader.invalidate(tool_id)
    except Exception as e:
        tb_logger.debug("registry unregister failed: {}", e)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=List[ToolSummary])
async def list_tools(
    search: str = Query(default=""),
    tag: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
):
    store = _require_store()
    tags = [tag] if tag else None
    return await store.list(search=search, tags=tags, risk_level=risk_level)


@router.post("", response_model=ToolDoc, status_code=201)
async def create_tool(body: ToolCreate = Body(...)):
    store = _require_store()
    try:
        doc = await store.create(body, user="builder")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    _re_register_in_registry(doc.dict())
    return doc


@router.get("/export")
async def export_tools(ids: Optional[str] = Query(default=None)):
    """Comma-separated tool_ids; omit for full export."""
    store = _require_store()
    tool_ids = [s.strip() for s in (ids or "").split(",") if s.strip()] or None
    return await store.export_bundle(tool_ids)


@router.post("/import", response_model=ToolImportResult)
async def import_tools(bundle: ToolImportBundle = Body(...)):
    store = _require_store()
    result = await store.import_bundle(bundle, user="builder-import")
    # Post-import: re-register every imported/updated tool so the live
    # registry reflects the import without restarting the pod.
    if _loader and _registry:
        try:
            await _loader.register_all_active(_registry)
        except Exception as e:
            tb_logger.debug("post-import registry refresh failed: {}", e)
    return result


@router.get("/{tool_id}", response_model=ToolDoc)
async def get_tool(tool_id: str = Path(...)):
    store = _require_store()
    doc = await store.get(tool_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"tool not found: {tool_id}")
    return doc


@router.put("/{tool_id}", response_model=ToolDoc)
async def update_tool(tool_id: str = Path(...), body: ToolUpdate = Body(...)):
    store = _require_store()
    try:
        doc = await store.update(tool_id, body, user="builder")
    except Exception as e:
        raise HTTPException(status_code=409 if "concurrent" in str(e) else 400, detail=str(e))
    _re_register_in_registry(doc.dict())
    return doc


@router.delete("/{tool_id}")
async def delete_tool(tool_id: str = Path(...)):
    store = _require_store()
    doc = await store.get(tool_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"tool not found: {tool_id}")
    ok = await store.delete(tool_id, user="builder")
    if ok:
        _unregister_in_registry(doc.name, tool_id)
    return {"deleted": ok, "tool_id": tool_id}


@router.get("/{tool_id}/versions", response_model=List[ToolVersion])
async def list_versions(tool_id: str = Path(...)):
    store = _require_store()
    return await store.list_versions(tool_id)


@router.get("/{tool_id}/versions/{version}", response_model=ToolDoc)
async def get_version(tool_id: str = Path(...), version: int = Path(...)):
    store = _require_store()
    doc = await store.get(tool_id, version=version)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"version not found: {tool_id}/{version}")
    return doc


@router.post("/{tool_id}/restore/{version}", response_model=ToolDoc)
async def restore_version(tool_id: str = Path(...), version: int = Path(...)):
    store = _require_store()
    try:
        doc = await store.restore_version(tool_id, version, user="builder")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    _re_register_in_registry(doc.dict())
    return doc


@router.post("/{tool_id}/test", response_model=ToolTestResponse)
async def test_tool(tool_id: str = Path(...), body: ToolTestRequest = Body(default_factory=ToolTestRequest)):
    store = _require_store()
    if _loader is None:
        raise HTTPException(status_code=503, detail="dynamic tool loader not configured")
    doc = await store.get(tool_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"tool not found: {tool_id}")
    meta = doc.dict()
    ctx = Ctx(user="diagnostic-runner", tool_id=tool_id, tool_name=doc.name)
    t0 = time.monotonic()
    try:
        result = await _loader.dispatch(meta, body.params, ctx_override=ctx, return_logs=True)
    except Exception as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return ToolTestResponse(status="fail", duration_ms=elapsed_ms, error=str(e))
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    if isinstance(result, dict) and "error" in result and "result" not in result:
        return ToolTestResponse(
            status="fail",
            duration_ms=elapsed_ms,
            error=str(result.get("error")),
            logs=(result.get("_meta") or {}).get("logs") or [],
        )
    logs = []
    if isinstance(result, dict):
        meta_block = result.get("_meta") or {}
        logs = list(meta_block.get("logs") or [])
        # Don't return _meta.logs twice - it's already in the response.
        if "_meta" in result:
            result = {k: v for k, v in result.items() if k != "_meta"}
    return ToolTestResponse(
        status="pass",
        duration_ms=elapsed_ms,
        result=result,
        logs=logs,
    )
