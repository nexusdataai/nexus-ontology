"""
Data Flow Graph models for Pipeline Studio.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DataFlowViewport(BaseModel):
    x: float = 0
    y: float = 0
    zoom: float = 1


class DataFlowNodeUi(BaseModel):
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    label: Optional[str] = None
    proposed: bool = False

    class Config:
        populate_by_name = True


class DataFlowNode(BaseModel):
    id: str
    type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    ui: DataFlowNodeUi = Field(default_factory=DataFlowNodeUi)
    auto_inserted: bool = Field(default=False, alias="autoInserted")

    class Config:
        populate_by_name = True


class DataFlowEdge(BaseModel):
    id: str
    source: str
    target: str
    source_handle: Optional[str] = Field(default=None, alias="sourceHandle")
    target_handle: Optional[str] = Field(default=None, alias="targetHandle")
    relationship: Optional[str] = Field(default="success")

    class Config:
        populate_by_name = True


class DataFlowGraph(BaseModel):
    version: int = 1
    draft_version: int = Field(default=1, alias="draftVersion")
    nodes: List[DataFlowNode] = Field(default_factory=list)
    edges: List[DataFlowEdge] = Field(default_factory=list)
    viewport: DataFlowViewport = Field(default_factory=DataFlowViewport)

    class Config:
        populate_by_name = True


class DataFlowValidateIssue(BaseModel):
    severity: Literal["error", "warning"] = "error"
    code: str
    message: str
    node_id: Optional[str] = Field(default=None, alias="nodeId")

    class Config:
        populate_by_name = True


class DataFlowValidateResponse(BaseModel):
    valid: bool
    issues: List[DataFlowValidateIssue] = Field(default_factory=list)
    warnings: List[DataFlowValidateIssue] = Field(default_factory=list)


class DataFlowCompileResponse(BaseModel):
    valid: bool
    issues: List[DataFlowValidateIssue] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled_steps: List[str] = Field(default_factory=list, alias="enabledSteps")
    runtime_steps: List[Dict[str, str]] = Field(default_factory=list, alias="runtimeSteps")
    metadata_patch: Dict[str, Any] = Field(default_factory=dict, alias="metadataPatch")
    graph_with_injections: Optional[DataFlowGraph] = Field(default=None, alias="graphWithInjections")

    class Config:
        populate_by_name = True


class DataFlowCatalogResponse(BaseModel):
    node_types: List[Dict[str, Any]] = Field(default_factory=list, alias="nodeTypes")
    runtime_steps_by_source: Dict[str, List[Dict[str, str]]] = Field(
        default_factory=dict, alias="runtimeStepsBySource"
    )
    runtime_step_order: List[str] = Field(default_factory=list, alias="runtimeStepOrder")

    class Config:
        populate_by_name = True


class DataFlowSaveRequest(BaseModel):
    graph: DataFlowGraph
    deploy: bool = False
    name: Optional[str] = None


class DataFlowCreatePipelineRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    graph: DataFlowGraph
    deploy: bool = False


class DataFlowPlanRequest(BaseModel):
    graph: DataFlowGraph
    prompt: str
    journey_id: Optional[str] = Field(default=None, alias="journeyId")


class ProposedPatchOp(BaseModel):
    op: Literal["add_node", "remove_node", "update_node", "add_edge", "remove_edge", "update_params"]
    node: Optional[DataFlowNode] = None
    edge: Optional[DataFlowEdge] = None
    node_id: Optional[str] = Field(default=None, alias="nodeId")
    params: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None


class DataFlowPlanResponse(BaseModel):
    patches: List[ProposedPatchOp] = Field(default_factory=list)
    explanation: str = ""
    impact: Dict[str, Any] = Field(default_factory=dict)


class DataFlowApplyPatchesRequest(BaseModel):
    graph: DataFlowGraph
    patches: List[ProposedPatchOp] = Field(default_factory=list)


class DataFlowExecutionGraphPreview(BaseModel):
    """Phase 3: compiled ExecutionGraph-shaped payload for AI Engine."""
    journey_id: Optional[str] = Field(default=None, alias="journeyId")
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    runtime: Literal["ontology", "ai_engine"] = "ontology"

    class Config:
        populate_by_name = True