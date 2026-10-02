"""
Dashboard Diagnostics REST API.

Surface for the new Dashboards tab inside the existing /operations/diagnostics
page. Exposes:

  GET  /api/v1/diagnostics/dashboards                  -> light index
  POST /api/v1/diagnostics/dashboards/{uid}/run        -> diagnose one
  POST /api/v1/diagnostics/dashboards/run-all          -> diagnose many
  GET  /api/v1/diagnostics/entities/{entity}           -> per-entity sample
  GET  /api/v1/diagnostics/backends                    -> simulator/Mimir/Athena
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from src.models.dashboard_diagnostics_models import (
    BackendsDiagnostic, DashboardDiagnostic, DashboardIndexEntry,
    EntityDiagnostic, RunAllRequest, RunOneRequest, ScanResult,
)

router = APIRouter(prefix="/api/v1/diagnostics", tags=["Dashboard Diagnostics"])

_service: Any = None


def configure(service: Any) -> None:
    global _service
    _service = service


def _svc():
    if not _service:
        raise HTTPException(status_code=503, detail="Dashboard diagnostics service not available")
    return _service


@router.get("/dashboards", response_model=List[DashboardIndexEntry], response_model_by_alias=True)
async def list_dashboards():
    """Light index of all dashboards. Does NOT run the diagnostic."""
    try:
        return await _svc().list_index()
    except Exception as e:
        logger.error(f"list_dashboards failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/dashboards/{uid}/run",
    response_model=DashboardDiagnostic,
    response_model_by_alias=True,
)
async def run_dashboard(uid: str, body: Optional[RunOneRequest] = None):
    """Run the diagnostic for one dashboard synchronously."""
    body = body or RunOneRequest()
    try:
        return await _svc().diagnose_dashboard(uid, limit_per_panel=body.limit_per_panel)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Dashboard not found: {uid}")
    except Exception as e:
        logger.error(f"run_dashboard {uid} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dashboards/run-all")
async def run_all_dashboards(request: Request, body: Optional[RunAllRequest] = None):
    """
    Run the diagnostic for many dashboards.

    If the client sends ``Accept: text/event-stream`` the response streams
    one ``DashboardDiagnostic`` per event as each dashboard finishes.
    Otherwise the endpoint blocks until every dashboard is done and
    returns a single ``ScanResult`` JSON.
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
            dashboard_uids=body.dashboard_uids,
            limit_per_panel=body.limit_per_panel,
            concurrency=body.concurrency,
        )
        return result.dict(by_alias=True)
    except Exception as e:
        logger.error(f"run_all_dashboards failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _stream_run_all(body: RunAllRequest):
    """SSE generator for diagnose_all_streaming."""
    healthy = degraded = unhealthy = 0
    total = 0
    try:
        async for d in _svc().diagnose_all_streaming(
            dashboard_uids=body.dashboard_uids,
            limit_per_panel=body.limit_per_panel,
            concurrency=body.concurrency,
        ):
            total += 1
            status_val = getattr(d.status, "value", d.status)
            if status_val == "healthy":
                healthy += 1
            elif status_val == "degraded":
                degraded += 1
            elif status_val == "unhealthy":
                unhealthy += 1
            payload = json.dumps({"type": "dashboard", "data": d.dict(by_alias=True)}, default=str)
            yield f"data: {payload}\n\n"
        summary = json.dumps({
            "type": "summary",
            "data": {"total": total, "healthy": healthy, "degraded": degraded, "unhealthy": unhealthy},
        })
        yield f"data: {summary}\n\n"
    except Exception as e:
        logger.error(f"_stream_run_all failed: {e}")
        err = json.dumps({"type": "error", "data": {"message": str(e)}})
        yield f"data: {err}\n\n"


@router.get(
    "/entities/{entity}",
    response_model=EntityDiagnostic,
    response_model_by_alias=True,
)
async def entity_check(entity: str, limit: int = 5):
    """Lower-level: mapping rule + reachability + sample query for one entity."""
    try:
        return await _svc().diagnose_entity(entity, limit=limit)
    except Exception as e:
        logger.error(f"entity_check {entity} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/backends",
    response_model=BackendsDiagnostic,
    response_model_by_alias=True,
)
async def backends_check():
    """Snapshot of every VDL backend (simulator schemas, Mimir, Athena)."""
    try:
        return await _svc().diagnose_backends()
    except Exception as e:
        logger.error(f"backends_check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation")
async def automation_check():
    """
    Walk every indexed automation Use Case and report:
    - missing_tools: tools referenced by a step but not registered
    - missing_apis: connector_api ids referenced but not in the registry
    - read_only_use_cases: use cases whose every step is read-only
    - by_solution: counts per solution_id

    The diagnostic UI's Dashboards tab already polls /backends and
    /dashboards. The Automation panel polls this endpoint to render the
    same status pill / drill-down pattern.
    """
    try:
        # Lazy imports so the module loads even when these services are
        # not yet wired (e.g. in unit tests).
        from src.apis import automation_api as _auto_api
        from src.services.control_plane import connector_apis as _ca

        if not getattr(_auto_api, "_indexer", None):
            return {"status": "skipped", "reason": "automation indexer not wired"}

        indexer = _auto_api._indexer
        summaries = await indexer.list_use_cases()

        # Pull the live tool registry through the running CopilotEngine.
        try:
            from src.apis.control_plane_api import _agent_executor
            tool_names = set()
            if _agent_executor and getattr(_agent_executor, "_tools", None):
                tool_names = {t.name for t in _agent_executor._tools.list_tools()}
        except Exception:
            tool_names = set()
        api_ids = {s.api_id for s in _ca.list_all()}

        missing_tools: List[Dict[str, Any]] = []
        missing_apis: List[Dict[str, Any]] = []
        read_only_use_cases: List[str] = []
        by_solution: Dict[str, Dict[str, int]] = {}
        total_steps = 0
        total_bindings = 0

        for s in summaries:
            doc = await indexer.get_use_case(s.use_case_id)
            if doc is None:
                continue
            slot = by_solution.setdefault(doc.solution_id, {"use_cases": 0, "steps": 0, "bindings": 0})
            slot["use_cases"] += 1
            for stage in doc.stages:
                slot["steps"] += len(stage.steps)
                total_steps += len(stage.steps)
                for step in stage.steps:
                    bindings = step.effective_bindings()
                    slot["bindings"] += len(bindings)
                    total_bindings += len(bindings)
                    for b in bindings:
                        if tool_names and b.tool not in tool_names:
                            missing_tools.append({"use_case": doc.use_case_id, "stage": stage.stage_id,
                                                   "step": step.step_id, "tool": b.tool})
                        if b.connector_api and api_ids and b.connector_api not in api_ids:
                            missing_apis.append({"use_case": doc.use_case_id, "stage": stage.stage_id,
                                                  "step": step.step_id, "api": b.connector_api})
            has_writes = any(b.connector_api for st in doc.stages for sp in st.steps
                              for b in sp.effective_bindings())
            if not has_writes:
                read_only_use_cases.append(doc.use_case_id)

        if missing_tools or missing_apis:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "total_use_cases": len(summaries),
            "total_steps": total_steps,
            "total_bindings": total_bindings,
            "missing_tools": missing_tools,
            "missing_apis": missing_apis,
            "read_only_use_cases": read_only_use_cases,
            "by_solution": by_solution,
            "tool_registry_size": len(tool_names),
            "connector_api_registry_size": len(api_ids),
        }
    except Exception as e:
        logger.error(f"automation_check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

