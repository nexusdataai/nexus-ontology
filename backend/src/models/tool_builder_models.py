"""
Tool Builder Pydantic models.

Validation contract for user-authored ReAct tools persisted to DynamoDB.
Source code is parsed at the API boundary so an invalid tool never
reaches the registry, the loader, or the journey runner.
"""

from __future__ import annotations

import ast
import hashlib
import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class RiskLevel(str, Enum):
    READ_ONLY = "read_only"
    LOW_RISK_WRITE = "low_risk_write"
    HIGH_RISK_WRITE = "high_risk_write"


class ToolStatus(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"


# Phase 3 - Cursor-for-data tool taxonomy. Mirror of
# ``automation_models.ToolKind`` so DDB-authored tools share the same
# vocabulary as YAML-authored ones.
class ToolKind(str, Enum):
    READ = "read"
    ANALYZE = "analyze"
    DECIDE = "decide"
    MUTATE = "mutate"
    NOTIFY = "notify"


_NON_CONNECTOR_KINDS = {ToolKind.READ.value, ToolKind.ANALYZE.value, ToolKind.DECIDE.value}
_CONNECTOR_KINDS = {ToolKind.MUTATE.value, ToolKind.NOTIFY.value}


# Source code limits (DynamoDB items cap at 400 KB; keep headroom).
SOURCE_CODE_MAX_BYTES = 350 * 1024

# Names we will not allow as tool.name because they collide with code-defined
# tools or with reserved Python keywords.
_TOOL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,79}$")
_FORBIDDEN_NAMES = {
    "discover_tables", "discover_columns", "query_table",
    "search_schema_knowledge", "search_enterprise_knowledge",
    "query_virtual_entity", "list_virtual_entities", "get_entity_schema",
}


def _validate_source_code(source: str) -> str:
    """
    Three checks:
      - size <= SOURCE_CODE_MAX_BYTES
      - parses as Python (ast.parse won't raise SyntaxError)
      - contains an ``async def run(params, vdl, connectors, ctx, log)`` at module level
    """
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source_code must be a non-empty string")
    if len(source.encode("utf-8")) > SOURCE_CODE_MAX_BYTES:
        raise ValueError(
            f"source_code exceeds {SOURCE_CODE_MAX_BYTES} bytes; "
            "split into multiple tools or move large data to a connector API"
        )
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ValueError(f"source_code does not parse: {e}")

    has_run = False
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run":
            has_run = True
            arg_names = [a.arg for a in node.args.args]
            required = ["params", "vdl", "connectors", "ctx", "log"]
            missing = [a for a in required if a not in arg_names]
            if missing:
                raise ValueError(
                    f"async def run is missing required args: {missing}; "
                    f"signature must be (params, vdl, connectors, ctx, log)"
                )
            break
    if not has_run:
        raise ValueError(
            "source_code must define a top-level `async def run(params, vdl, connectors, ctx, log)`"
        )
    return source


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _validate_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanity-check the JSON Schema for tool parameters."""
    if not isinstance(params, dict):
        raise ValueError("parameters must be a JSON Schema object")
    if params.get("type") != "object":
        raise ValueError("parameters.type must be 'object'")
    properties = params.get("properties", {})
    if not isinstance(properties, dict):
        raise ValueError("parameters.properties must be a dict")
    required = params.get("required", []) or []
    if not isinstance(required, list):
        raise ValueError("parameters.required must be a list")
    for r in required:
        if r not in properties:
            raise ValueError(f"required key '{r}' not declared in properties")
    return params


def _check_kind_connector_invariant(tool_kind: Optional[str], connector_api: Optional[str]) -> None:
    """Phase 3 invariant: a mutate/notify tool MUST have a connector_api;
    a read/analyze/decide tool MUST NOT. Raises ValueError on violation.

    Called from ``ToolCreate`` / ``ToolUpdate`` validators so a Tool
    Builder UI POST can never create a kind-mismatched tool.
    """
    if tool_kind is None:
        return
    if tool_kind not in {k.value for k in ToolKind}:
        raise ValueError(
            f"tool_kind '{tool_kind}' must be one of {[k.value for k in ToolKind]}"
        )
    if tool_kind in _CONNECTOR_KINDS and not connector_api:
        raise ValueError(
            f"tool_kind '{tool_kind}' requires connector_api to be set"
        )
    if tool_kind in _NON_CONNECTOR_KINDS and connector_api:
        raise ValueError(
            f"tool_kind '{tool_kind}' must NOT set connector_api "
            f"(got connector_api='{connector_api}')"
        )


# ---------------------------------------------------------------------------
# Public models
# ---------------------------------------------------------------------------

class ToolCreate(BaseModel):
    """Body for POST /api/v1/tools."""
    name: str = Field(..., description="Python identifier; unique tool name.")
    description: str = Field("", max_length=2000)
    parameters: Dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []},
    )
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    requires_approval: bool = False
    cacheable: bool = False
    connector_api: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source_code: str = Field(..., description="Python source containing async def run(...).")
    # Phase 3 - additive, optional fields. ``tool_kind`` is inferred from
    # risk_level + connector_api when omitted (see _infer_tool_kind below).
    tool_kind: Optional[str] = None
    header_comment: Optional[str] = None

    @validator("name")
    def _name_ok(cls, v: str) -> str:
        if not _TOOL_NAME_PATTERN.match(v):
            raise ValueError(
                "name must match [a-z][a-z0-9_]{1,79} - lowercase, no spaces"
            )
        if v in _FORBIDDEN_NAMES:
            raise ValueError(f"name '{v}' collides with a code-defined tool")
        return v

    @validator("parameters")
    def _params_ok(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        return _validate_parameters(v)

    @validator("source_code")
    def _source_ok(cls, v: str) -> str:
        return _validate_source_code(v)

    @validator("tags", each_item=True)
    def _tag_ok(cls, v: str) -> str:
        v = (v or "").strip()
        if not v or len(v) > 60:
            raise ValueError("tag must be 1..60 chars")
        return v

    @validator("tool_kind", always=True)
    def _kind_invariant(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        _check_kind_connector_invariant(v, values.get("connector_api"))
        return v


class ToolUpdate(BaseModel):
    """Body for PUT /api/v1/tools/{id}.

    All fields are optional; ``if_unchanged_updated_at`` enables optimistic
    locking so two concurrent saves don't silently clobber each other.
    """
    description: Optional[str] = Field(None, max_length=2000)
    parameters: Optional[Dict[str, Any]] = None
    risk_level: Optional[RiskLevel] = None
    requires_approval: Optional[bool] = None
    cacheable: Optional[bool] = None
    connector_api: Optional[str] = None
    tags: Optional[List[str]] = None
    source_code: Optional[str] = None
    changelog: Optional[str] = Field(None, max_length=500)
    if_unchanged_updated_at: Optional[str] = None
    # Phase 3 - additive, optional fields.
    tool_kind: Optional[str] = None
    header_comment: Optional[str] = None

    @validator("parameters")
    def _params_ok(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        return _validate_parameters(v)

    @validator("source_code")
    def _source_ok(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_source_code(v)

    @validator("tool_kind", always=True)
    def _kind_invariant(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        # Only enforce when the caller is providing tool_kind in this PUT
        # body. A caller updating other fields doesn't need to re-state
        # tool_kind, and we don't have the prior connector_api to compare
        # against here.
        if v is None:
            return v
        _check_kind_connector_invariant(v, values.get("connector_api"))
        return v


class ToolSummary(BaseModel):
    """Lightweight row for list endpoints."""
    tool_id: str
    name: str
    description: str = ""
    risk_level: RiskLevel
    requires_approval: bool = False
    cacheable: bool = False
    connector_api: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    current_version: int = 1
    status: ToolStatus = ToolStatus.ACTIVE
    createdBy: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    # Phase 3 - additive, optional fields. Surfaced in the Tool Builder
    # UI list view so authors can filter by kind / spot tools missing
    # the header comment block.
    tool_kind: Optional[str] = None
    header_comment: Optional[str] = None


class ToolDoc(ToolSummary):
    """Full document including source code."""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    source_code: str = ""
    source_sha256: Optional[str] = None
    changelog: Optional[str] = None


class ToolVersion(BaseModel):
    """A historical version snapshot."""
    tool_id: str
    version: int
    source_code: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    source_sha256: Optional[str] = None
    changelog: Optional[str] = None
    createdBy: Optional[str] = None
    createdAt: Optional[str] = None


class ToolTestRequest(BaseModel):
    """Body for POST /api/v1/tools/{id}/test.

    Runs the current source against live VDL + connectors with synthetic
    ctx (user='diagnostic-runner', no journey_id, fresh invocation_id).
    """
    params: Dict[str, Any] = Field(default_factory=dict)


class ToolTestResponse(BaseModel):
    status: str  # "pass" | "fail"
    duration_ms: int
    result: Any = None
    error: Optional[str] = None
    logs: List[Dict[str, Any]] = Field(default_factory=list)


class ToolImportBundle(BaseModel):
    """Body for POST /api/v1/tools/import."""
    tools: List[ToolCreate]
    mode: str = Field("merge", pattern="^(merge|replace|skip_existing)$")


class ToolImportResult(BaseModel):
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[Dict[str, str]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal hash helper exposed for the service layer
# ---------------------------------------------------------------------------

def source_hash(source_code: str) -> str:
    return _sha256(source_code)
