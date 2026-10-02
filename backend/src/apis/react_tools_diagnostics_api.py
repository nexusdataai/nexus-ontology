"""
ReAct Tools Diagnostics API.

Five endpoints powering the ReAct Tools tab in the Diagnostics page.
The heavy lifting lives in
``services/control_plane/react_tools_diagnostics.py``; this module is a
thin FastAPI surface that resolves the live ToolRegistry, connector_apis
registry, and AutomationIndexer references and forwards.

Routes:

  GET  /api/v1/diagnostics/react-tools/registry
  GET  /api/v1/diagnostics/react-tools/contracts
  GET  /api/v1/diagnostics/react-tools/connector-apis
  POST /api/v1/diagnostics/react-tools/run
       body: {only_read_only?: bool, tool_ids?: string[]}
  POST /api/v1/diagnostics/react-tools/{tool}/execute
       body: {params: {...}}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException
from loguru import logger
from pydantic import BaseModel

from src.services.control_plane import react_tools_diagnostics as rtd

router = APIRouter(prefix="/api/v1/diagnostics/react-tools", tags=["Diagnostics"])

_tool_registry: Any = None
_connector_apis: Any = None
_automation_indexer: Any = None


def configure(
    tool_registry: Any,
    connector_apis: Any = None,
    automation_indexer: Any = None,
) -> None:
    global _tool_registry, _connector_apis, _automation_indexer
    _tool_registry = tool_registry
    if connector_apis is not None:
        _connector_apis = connector_apis
    if automation_indexer is not None:
        _automation_indexer = automation_indexer


def _require_registry() -> Any:
    if _tool_registry is None:
        raise HTTPException(status_code=503, detail="Tool registry not configured")
    return _tool_registry


@router.get("/registry")
async def registry():
    """Live ToolRegistry snapshot enriched with use-case usage counts and
    YAML-coverage flags from the AutomationIndexer.
    """
    registry = _require_registry()
    use_case_dry: Optional[Dict[str, Any]] = None
    if _automation_indexer is not None:
        try:
            use_case_dry = await _automation_indexer.dry_run()
        except Exception as e:
            logger.warning(f"automation_indexer.dry_run failed: {e}")
    try:
        return rtd.registry_health(
            registry,
            automation_indexer=_automation_indexer,
            use_case_dry_run=use_case_dry,
        )
    except Exception as e:
        logger.error(f"registry_health failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contracts")
async def contracts():
    """Validate every Tool's parameters JSON Schema and connector_api binding."""
    registry = _require_registry()
    try:
        return rtd.validate_contracts(registry, _connector_apis)
    except Exception as e:
        logger.error(f"validate_contracts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connector-apis")
async def connector_apis():
    """Validate every connector_api spec, count tool callers, surface orphans."""
    registry = _require_registry()
    try:
        return await rtd.validate_connector_apis(_connector_apis, registry=registry)
    except Exception as e:
        logger.error(f"validate_connector_apis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RunRequest(BaseModel):
    only_read_only: bool = False
    tool_ids: Optional[List[str]] = None


@router.post("/run")
async def run_all(body: RunRequest = Body(default_factory=RunRequest)):
    """Smoke-run every tool with its canary params; record per-tool result.

    ``only_read_only=true`` skips low/high-risk-write tools - useful on
    shared environments where simulator pollution is undesired.
    """
    registry = _require_registry()
    try:
        return await rtd.run_canaries(
            registry,
            only_read_only=body.only_read_only,
            tool_ids=body.tool_ids,
        )
    except Exception as e:
        logger.error(f"run_canaries failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExecuteRequest(BaseModel):
    params: Dict[str, Any] = {}


@router.post("/{tool_name}/execute")
async def execute_one(tool_name: str, body: ExecuteRequest = Body(default_factory=ExecuteRequest)):
    """Interactive Try-it: invoke ``tool_name`` with caller-supplied params."""
    registry = _require_registry()
    try:
        return await rtd.execute_tool(registry, tool_name, body.params)
    except Exception as e:
        logger.error(f"execute_tool({tool_name}) failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
