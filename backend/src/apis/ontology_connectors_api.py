"""
Ontology unified Connector API (spec 041).

Facade at /api/v1/connectors/{connectorId}/invoke for AI Engine tool packages.
Delegates to the Connector API Workbench invoke path (simulator writeback).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from src.services.control_plane import connector_apis as _ca

conn_logger = logger.bind(component="ontology-connectors")

router = APIRouter(prefix="/api/v1/connectors", tags=["Ontology Connectors"])

CONNECTOR_ALIASES = {
    "salesforce": "sfdc",
    "crm": "sfdc",
    "oracle_erp": "oracle",
    "sap_s4hana": "sap",
}


class InvokeContext(BaseModel):
    execution_id: Optional[str] = Field(default=None, alias="executionId")
    step_id: Optional[str] = Field(default=None, alias="stepId")
    tool_id: Optional[str] = Field(default=None, alias="toolId")
    tenant_id: Optional[str] = Field(default=None, alias="tenantId")
    user_id: Optional[str] = Field(default=None, alias="userId")

    model_config = {"populate_by_name": True}


class ConnectorInvokeRequest(BaseModel):
    action: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[InvokeContext] = None
    idempotency_key: Optional[str] = Field(default=None, alias="idempotencyKey")

    model_config = {"populate_by_name": True}


async def _resolve_api_id(connector_id: str, action: str) -> str:
    if connector_id.count(".") >= 2:
        spec = await _ca.get_async(connector_id)
        if spec is not None:
            return connector_id

    system = CONNECTOR_ALIASES.get(connector_id, connector_id)
    candidates = [
        f"{system}.{action}",
        f"{system}.{action.replace('_', '.')}",
        action if action.count(".") >= 2 else None,
    ]
    for api_id in candidates:
        if not api_id:
            continue
        spec = await _ca.get_async(api_id)
        if spec is not None:
            return api_id

    for spec in await _ca.list_all_async():
        if spec.target_system == system and (
            spec.api_id.endswith(f".{action}") or action in spec.api_id
        ):
            return spec.api_id

    raise HTTPException(
        status_code=404,
        detail=f"no connector API for {connector_id}/{action}",
    )


@router.get("")
async def list_connectors():
    """List connectors grouped by target system."""
    by_system: Dict[str, Dict[str, Any]] = {}
    for spec in await _ca.list_all_async():
        entry = by_system.setdefault(
            spec.target_system,
            {
                "id": spec.target_system,
                "displayName": spec.target_system.upper(),
                "status": "configured",
                "actions": [],
                "riskClasses": {},
            },
        )
        action_name = spec.api_id.split(".", 1)[-1] if "." in spec.api_id else spec.operation
        if action_name not in entry["actions"]:
            entry["actions"].append(action_name)
        entry["riskClasses"][action_name] = spec.risk_level.replace("_risk_write", "").replace("_", "")
    return {"connectors": list(by_system.values())}


@router.get("/{connector_id}/actions")
async def list_connector_actions(connector_id: str):
    system = CONNECTOR_ALIASES.get(connector_id, connector_id)
    specs = await _ca.list_for_system_async(system)
    if not specs and connector_id.count(".") >= 2:
        one = await _ca.get_async(connector_id)
        specs = [one] if one else []
    if not specs:
        raise HTTPException(status_code=404, detail=f"connector not found: {connector_id}")
    actions = []
    for spec in specs:
        action_name = spec.api_id.split(".", 1)[-1] if "." in spec.api_id else spec.operation
        actions.append(
            {
                "action": action_name,
                "description": spec.description,
                "riskClass": spec.risk_level.replace("_risk_write", "").replace("_", ""),
                "requiresApproval": "high_risk" in spec.risk_level,
                "parameters": spec.request_schema or {"type": "object"},
            }
        )
    return {"connectorId": connector_id, "actions": actions}


@router.post("/{connector_id}/invoke")
async def invoke_connector(connector_id: str, body: ConnectorInvokeRequest):
    """Execute a connector action (primary runtime endpoint for AI Engine tools)."""
    from src.apis.connector_api_workbench_api import _invoke as wb_invoke

    api_id = await _resolve_api_id(connector_id, body.action)
    payload = dict(body.arguments or {})
    if body.context and body.context.user_id:
        payload.setdefault("actor", body.context.user_id)

    start_detail = await wb_invoke(api_id, payload)
    success = start_detail.get("verdict") in ("pass", "healthy", None) or start_detail.get("success", True)
    result = start_detail.get("result") or start_detail.get("response") or start_detail
    if isinstance(result, dict) and "result" in result and len(result) == 1:
        result = result["result"]

    if not success and start_detail.get("verdict") == "fail":
        err_msg = start_detail.get("detail") or start_detail.get("message") or "connector invoke failed"
        return {
            "success": False,
            "result": None,
            "error": {"code": "connector_error", "message": str(err_msg), "retryable": False},
            "durationMs": start_detail.get("duration_ms", 0),
        }

    return {
        "success": True,
        "result": result if isinstance(result, dict) else {"value": result},
        "durationMs": start_detail.get("duration_ms", 0),
    }
