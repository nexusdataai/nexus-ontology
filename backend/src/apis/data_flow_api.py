"""
Pipeline Studio — Data Flow graph APIs.
"""

from __future__ import annotations

import copy
import os
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

from src.models.data_flow_models import (
    DataFlowApplyPatchesRequest,
    DataFlowCatalogResponse,
    DataFlowCompileResponse,
    DataFlowCreatePipelineRequest,
    DataFlowExecutionGraphPreview,
    DataFlowGraph,
    DataFlowPlanRequest,
    DataFlowPlanResponse,
    DataFlowSaveRequest,
    DataFlowValidateResponse,
)
from src.constants.etl_step_catalog import STUB_NODE_TYPES
from src.services.data_flow_service import flow_stub_types
from src.services.flow_runtime.dag_runner import graph_has_flow_processor_nodes
from src.services.flow_runtime.nexus_flow_journey import run_nexus_flow_linear
from src.models.journey_model import JourneyActionRequest
from src.services import data_flow_service

router = APIRouter(prefix="/api/v1/data-flow", tags=["data-flow"])

_journey_service: Any = None
_mapping_rule_checker: Optional[Callable[[str], bool]] = None
_mapping_rule_service: Any = None


def configure(
    journey_service: Any = None,
    mapping_rule_checker: Optional[Callable[[str], bool]] = None,
    mapping_rule_service: Any = None,
) -> None:
    global _journey_service, _mapping_rule_checker, _mapping_rule_service
    _journey_service = journey_service
    _mapping_rule_checker = mapping_rule_checker
    _mapping_rule_service = mapping_rule_service
    if mapping_rule_checker is None and mapping_rule_service is not None:
        repo = getattr(mapping_rule_service, "_repo", None)

        def _sync_rule_exists(rule_id: str) -> bool:
            if not rule_id or repo is None:
                return True
            try:
                return bool(repo.get_mapping_rule(rule_id))
            except Exception:
                return True

        _mapping_rule_checker = _sync_rule_exists


def _rule_exists(rule_id: str) -> bool:
    if not rule_id or not _mapping_rule_checker:
        return True
    return bool(_mapping_rule_checker(rule_id))


@router.get("/catalog", response_model=DataFlowCatalogResponse)
async def get_catalog():
    raw = data_flow_service.get_catalog()
    return DataFlowCatalogResponse.model_validate(raw)


@router.post("/validate", response_model=DataFlowValidateResponse)
async def validate_data_flow(graph: DataFlowGraph):
    return data_flow_service.validate_graph(graph, mapping_rule_exists=_rule_exists)


@router.post("/compile", response_model=DataFlowCompileResponse)
async def compile_data_flow(graph: DataFlowGraph):
    return data_flow_service.compile_graph(graph, mapping_rule_exists=_rule_exists)


@router.post("/plan", response_model=DataFlowPlanResponse)
async def plan_data_flow(request: DataFlowPlanRequest):
    return data_flow_service.plan_from_prompt(request.graph, request.prompt)


@router.post("/apply-patches", response_model=DataFlowGraph)
async def apply_patches(request: DataFlowApplyPatchesRequest):
    return data_flow_service.apply_patches(request.graph, request.patches)


@router.post("/sources/google-drive/test")
async def test_google_drive_source():
    """Connection test for Flow Studio Google Drive source nodes."""
    from src.services.gdrive_connector_service import get_gdrive_connector_service

    svc = get_gdrive_connector_service()
    return await svc.test_connection()


@router.post("/flow/preview-run")
async def preview_flow_run(graph: DataFlowGraph):
    from src.services.flow_runtime.execution_policy import require_flow_runtime_execution

    require_flow_runtime_execution()
    if not graph_has_flow_processor_nodes(graph):
        raise HTTPException(status_code=422, detail="Graph has no nexus.* flow processors")
    return run_nexus_flow_linear(graph)


def _refuse_stub_deploy(graph: DataFlowGraph, deploy: bool) -> None:
    if not deploy:
        return
    stub_types = STUB_NODE_TYPES | flow_stub_types()
    stubs = [n.type for n in graph.nodes if n.type in stub_types]
    if stubs:
        raise HTTPException(
            status_code=422,
            detail={"error": "Cannot deploy stub steps", "stubs": stubs},
        )


@router.post("/pipelines")
async def create_pipeline_from_graph(body: DataFlowCreatePipelineRequest) -> Dict[str, Any]:
    if _journey_service is None:
        raise HTTPException(status_code=503, detail="Journey service not available")
    _refuse_stub_deploy(body.graph, body.deploy)
    validation = data_flow_service.validate_graph(body.graph, mapping_rule_exists=_rule_exists)
    compiled = data_flow_service.compile_graph(body.graph, mapping_rule_exists=_rule_exists)
    if body.deploy and not compiled.valid:
        raise HTTPException(
            status_code=422,
            detail={"error": "Invalid graph", "issues": [i.model_dump(by_alias=True) for i in compiled.issues]},
        )
    if not body.deploy and not compiled.valid:
        graph = body.graph
        patch = {
            "config": data_flow_service.compile_graph(body.graph, inject_missing=False, mapping_rule_exists=_rule_exists).config
            if body.graph.nodes
            else {},
            "studioLayout": "v1",
            "validationSnapshot": validation.model_dump(by_alias=True),
        }
    else:
        if not compiled.valid:
            raise HTTPException(
                status_code=422,
                detail={"error": "Invalid graph", "issues": [i.model_dump(by_alias=True) for i in compiled.issues]},
            )
        graph = compiled.graph_with_injections or body.graph
        patch = dict(compiled.metadata_patch)
        patch["validationSnapshot"] = validation.model_dump(by_alias=True)
    patch["dataFlowGraph"] = graph.model_dump(by_alias=True)
    if body.deploy:
        patch["productionGraphSnapshot"] = copy.deepcopy(patch["dataFlowGraph"])
        patch["productionConfig"] = copy.deepcopy(patch.get("config", {}))

    flow_mode = graph_has_flow_processor_nodes(graph)
    stage_id = "nexus_flow" if flow_mode else "etl_pipeline"
    stage_label = f"Nexus Flow — {body.name}" if flow_mode else f"ETL Pipeline — {body.name}"
    create_req = JourneyActionRequest(
        action="create",
        name=body.name,
        description=stage_label,
        odaComponentType="data-pipeline",
        journey_data={
            "name": body.name,
            "description": stage_label,
            "odaComponentType": "data-pipeline",
            "metadata": patch,
            "stages": [
                {
                    "stageId": stage_id,
                    "name": stage_label,
                    "order": 0,
                    "steps": [],
                }
            ],
        },
    )
    created = await _journey_service.execute_action(create_req)
    if created.status != "success":
        raise HTTPException(status_code=500, detail=created.message or "Failed to create pipeline")
    journey_id = created.journey_id or (created.data or {}).get("journeyId")
    return {
        "success": True,
        "journeyId": journey_id,
        "compiled": compiled.model_dump(by_alias=True),
        "deployed": body.deploy,
    }


@router.post("/execution-graph", response_model=DataFlowExecutionGraphPreview)
async def preview_execution_graph(graph: DataFlowGraph, journey_id: Optional[str] = None):
    try:
        payload = data_flow_service.compile_to_execution_graph(graph, journey_id=journey_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return DataFlowExecutionGraphPreview.model_validate(payload)


@router.get("/journeys/{journey_id}")
async def get_journey_data_flow(journey_id: str) -> Dict[str, Any]:
    if _journey_service is None:
        raise HTTPException(status_code=503, detail="Journey service not available")
    req = JourneyActionRequest(action="read", journey_id=journey_id)
    result = await _journey_service.execute_action(req)
    if result.status == "error" or not result.data:
        raise HTTPException(status_code=404, detail="Journey not found")
    data = result.data
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else data
    if not isinstance(meta, dict):
        meta = data
    graph = meta.get("dataFlowGraph")
    prod = meta.get("productionGraphSnapshot")
    return {
        "journeyId": journey_id,
        "graph": graph,
        "productionGraphSnapshot": prod,
        "config": meta.get("config"),
        "studioLayout": meta.get("studioLayout"),
        "draftVersion": (graph or {}).get("draftVersion") if isinstance(graph, dict) else None,
    }


@router.put("/journeys/{journey_id}")
async def save_journey_data_flow(journey_id: str, body: DataFlowSaveRequest) -> Dict[str, Any]:
    if _journey_service is None:
        raise HTTPException(status_code=503, detail="Journey service not available")

    _refuse_stub_deploy(body.graph, body.deploy)
    validation = data_flow_service.validate_graph(body.graph, mapping_rule_exists=_rule_exists)
    compiled = data_flow_service.compile_graph(body.graph, mapping_rule_exists=_rule_exists)
    if body.deploy and not compiled.valid:
        raise HTTPException(
            status_code=422,
            detail={"error": "Invalid graph", "issues": [i.model_dump(by_alias=True) for i in compiled.issues]},
        )

    req = JourneyActionRequest(action="read", journey_id=journey_id)
    read_result = await _journey_service.execute_action(req)
    if read_result.status == "error":
        raise HTTPException(status_code=404, detail="Journey not found")

    existing = read_result.data or {}
    meta = existing.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    if not body.deploy and not compiled.valid:
        graph = body.graph
        patch = {
            "dataFlowGraph": graph.model_dump(by_alias=True),
            "studioLayout": meta.get("studioLayout", "v1"),
            "validationSnapshot": validation.model_dump(by_alias=True),
        }
        loose = data_flow_service.compile_graph(body.graph, inject_missing=False, mapping_rule_exists=_rule_exists)
        if loose.config:
            patch["config"] = loose.config
    else:
        if not compiled.valid:
            raise HTTPException(
                status_code=422,
                detail={"error": "Invalid graph", "issues": [i.model_dump(by_alias=True) for i in compiled.issues]},
            )
        graph = compiled.graph_with_injections or body.graph
        patch = dict(compiled.metadata_patch)
        patch["dataFlowGraph"] = graph.model_dump(by_alias=True)
        patch["validationSnapshot"] = validation.model_dump(by_alias=True)

    if body.deploy:
        patch["productionGraphSnapshot"] = copy.deepcopy(patch["dataFlowGraph"])
        patch["productionConfig"] = copy.deepcopy(patch.get("config", {}))

    journey_data: Dict[str, Any] = {"metadata": {**meta, **patch}}
    if body.name:
        journey_data["name"] = body.name
    elif existing.get("name"):
        journey_data["name"] = existing["name"]

    update_req = JourneyActionRequest(
        action="update",
        journey_id=journey_id,
        journey_data=journey_data,
    )
    upd = await _journey_service.execute_action(update_req)
    if upd.status != "success":
        raise HTTPException(status_code=500, detail=upd.message or "Failed to save")

    runtime_mode = os.environ.get("PIPELINE_RUNTIME", "ontology").strip().lower()
    execution_id = None
    if runtime_mode in ("ai_engine", "dual") and body.deploy:
        try:
            from src.services.ai_engine_client import AiEngineClient, AiEngineClientError

            client = AiEngineClient()
            if client.configured:
                exec_graph = data_flow_service.compile_to_execution_graph(graph, journey_id=journey_id)
                resp = await client.submit_execution(
                    journey_id=journey_id,
                    stage_id="etl_pipeline",
                    variables={"dataFlowExecutionGraph": exec_graph},
                    labels={"kind": "data-pipeline", "deploy": "true"},
                )
                execution_id = resp.get("execution_id") or resp.get("executionId")
        except AiEngineClientError as exc:
            logger.warning(f"AI Engine deploy submit skipped: {exc}")
            if runtime_mode == "ai_engine":
                raise HTTPException(status_code=502, detail=str(exc))

    return {
        "success": True,
        "compiled": compiled.model_dump(by_alias=True),
        "deployed": body.deploy,
        "executionId": execution_id,
        "pipelineRuntime": runtime_mode,
    }