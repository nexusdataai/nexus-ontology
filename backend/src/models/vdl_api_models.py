"""
Virtual Data API models (Data Plane, Phase 2).

A VDL API acts on a virtual entity (defined in the VDL catalog) via one or
more Connector API implementations. Chain semantics:

  UI/Copilot -> VdlApiSpec.resolve(verb, args)
             -> [ImplBinding{connector_api_id, arg_mapping}] execution
             -> ConnectorApiRegistryService.get(connector_api_id)
             -> ConnectorRuntime dispatch (FDW SQL or third-party REST)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


VdlVerb = str  # 'read' | 'write' | 'upsert' | 'delete' | 'aggregate'


class ImplBinding(BaseModel):
    """One implementation of a VDL API: which Connector API to call and how
    to map VDL API arguments into the connector call payload."""

    connector_api_id: str = Field(..., description="Target CONNAPI# api_id")
    arg_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="{'connector_arg_name': 'vdl_arg_ref'} - vdl_arg_ref uses "
                    "dotted paths (e.g. 'customer.id' or a literal '$now').",
    )
    when: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional predicate; the binding fires only when the "
                    "supplied VDL args match. Absent => always applies.",
    )


class DirectSqlBinding(BaseModel):
    """Optional read-through fast-path via VirtualQueryService.

    When a ``read`` verb can be satisfied by a single SQL query against the
    mapped source, callers can define this instead of (or alongside) a
    Connector API impl.
    """

    virtual_entity: str
    filters: Optional[Dict[str, Any]] = None
    projection: Optional[List[str]] = None
    limit: Optional[int] = None


class VdlApiSpec(BaseModel):
    api_id: str
    verb: VdlVerb
    virtual_entity: str
    parameters_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema")
    impl: List[ImplBinding] = Field(default_factory=list)
    direct_sql: Optional[DirectSqlBinding] = None
    risk_level: str = "read_only"
    description: str = ""
    tags: List[str] = Field(default_factory=list)


class ExecutionStep(BaseModel):
    connector_api_id: str
    args: Dict[str, Any]


class ExecutionPlan(BaseModel):
    api_id: str
    verb: VdlVerb
    virtual_entity: str
    steps: List[ExecutionStep] = Field(default_factory=list)
    direct_sql: Optional[DirectSqlBinding] = None


class InvokeResult(BaseModel):
    api_id: str
    ok: bool
    plan: ExecutionPlan
    step_results: List[Dict[str, Any]] = Field(default_factory=list)
    duration_ms: int
    error: Optional[str] = None
