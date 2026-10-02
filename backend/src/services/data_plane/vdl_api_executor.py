"""
VDL API executor (Data Plane, Phase 2)

Drives an ``ExecutionPlan`` produced by ``VdlApiRegistryService.resolve()``
through the Connector API workbench (for write verbs) or the existing
``VirtualQueryService`` (for read-through with ``direct_sql``).

Not a heavy orchestrator - a linear runner is enough for Phase 2. Complex
compositions (fan-out + join) can be layered on later without touching
existing consumers.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from src.models.vdl_api_models import ExecutionPlan, InvokeResult


_app_ref: Any = None


def configure(app: Any) -> None:
    """Wire the FastAPI app instance so we can dispatch via ASGI to
    ``/api/v1/connector-apis/{api_id}/invoke`` without a network hop."""
    global _app_ref
    _app_ref = app


async def execute(plan: ExecutionPlan) -> InvokeResult:
    """Run every step of the plan sequentially and aggregate results."""
    started = time.monotonic()
    step_results: List[Dict[str, Any]] = []
    ok = True
    error: Optional[str] = None

    # Read fast-path: direct_sql -> VirtualQueryService (single hop).
    if plan.verb == "read" and plan.direct_sql is not None:
        try:
            from src.services.virtual_query_service import get_virtual_query_service  # type: ignore
            svc = get_virtual_query_service()
            rows = await svc.query_virtual_entity(
                plan.direct_sql.virtual_entity,
                filters=plan.direct_sql.filters or {},
                projection=plan.direct_sql.projection,
                limit=plan.direct_sql.limit,
            )
            step_results.append({"source": "direct_sql", "rows": rows})
        except Exception as e:
            ok = False
            error = f"direct_sql failed: {e}"
            step_results.append({"source": "direct_sql", "error": str(e)})

    if plan.steps:
        if _app_ref is None:
            ok = False
            error = (error + "; " if error else "") + "executor app not configured"
        else:
            transport = httpx.ASGITransport(app=_app_ref)
            try:
                async with httpx.AsyncClient(transport=transport, base_url="http://vdl.local") as client:
                    for step in plan.steps:
                        try:
                            resp = await client.post(
                                f"/api/v1/connector-apis/{step.connector_api_id}/invoke",
                                json={"payload": step.args},
                                timeout=30.0,
                            )
                            step_results.append({
                                "connector_api_id": step.connector_api_id,
                                "status": resp.status_code,
                                "body": _try_json(resp),
                            })
                            if resp.status_code >= 400:
                                ok = False
                                error = (error + "; " if error else "") + (
                                    f"{step.connector_api_id} -> HTTP {resp.status_code}"
                                )
                        except Exception as e:
                            ok = False
                            error = (error + "; " if error else "") + f"{step.connector_api_id}: {e}"
                            step_results.append({
                                "connector_api_id": step.connector_api_id,
                                "error": str(e),
                            })
            except Exception as e:
                logger.warning(f"VDL API executor transport failed: {e}")
                ok = False
                error = (error + "; " if error else "") + f"transport: {e}"

    elapsed_ms = int((time.monotonic() - started) * 1000)
    return InvokeResult(
        api_id=plan.api_id,
        ok=ok and error is None,
        plan=plan,
        step_results=step_results,
        duration_ms=elapsed_ms,
        error=error,
    )


def _try_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return resp.text
