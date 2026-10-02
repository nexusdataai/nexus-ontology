"""
Pydantic models for the AI Automation Framework.

Authors describe automation Use Cases as YAML files under
``enterprise-knowledge/automation/<solution>/<use_case_id>.yaml``. The
indexer (``services/control_plane/automation_indexer.py``) validates each
file against these schemas before writing rows to pgvector and edges to
the Apache AGE graph store.

A Use Case is the unit of retrieval: when the user states a goal, the
CopilotEngine searches ``onto_use_case`` content type, picks the best
match by score, and renders the canonical Stage / Step / ToolBinding /
ConnectorAPI graph as the structured "playbook" the LLM must follow.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$")
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


# ---------------------------------------------------------------------------
# Phase 3 - Tool taxonomy
# ---------------------------------------------------------------------------

class ToolKind(str, Enum):
    """Cursor-for-data tool taxonomy (see plan section 28).

    - read    : Cursor analog `find`/`grep`. Pulls VDL rows. No side effects.
    - analyze : Cursor analog linter / type-checker. Pure compute over reads
                (scoring, clustering, ML inference, projections). No side
                effects.
    - decide  : LLM-only branching step. Cursor analog: agent's reasoning
                step. No side effects.
    - mutate  : Writes to a system of record (Oracle / SAP / SFDC) via a
                connector API. Cursor analog: edit + save.
    - notify  : Sends a message to an external channel (WhatsApp, email,
                Slack, alert) via a connector API.
    """
    READ = "read"
    ANALYZE = "analyze"
    DECIDE = "decide"
    MUTATE = "mutate"
    NOTIFY = "notify"


_NON_CONNECTOR_KINDS = {ToolKind.READ.value, ToolKind.ANALYZE.value, ToolKind.DECIDE.value}
_CONNECTOR_KINDS = {ToolKind.MUTATE.value, ToolKind.NOTIFY.value}

# Stage names that constrain which tool kinds may appear within them.
_STAGE_ACT_NAMES = {"act", "notify"}
_STAGE_RESOLVE_NAMES = {"resolve", "diagnose"}


def _infer_tool_kind(*, risk_level: Optional[str], connector_api: Optional[str]) -> str:
    """Heuristic default for ``tool_kind`` (plan section 28 backward-compat).

    Used when a tool's YAML / Tool dataclass / DDB row was authored before
    Phase 3. Conservative: a tool with a connector_api is assumed mutating;
    a read_only tool is assumed read; everything else falls through to
    analyze. The inference is logged as a warning by the indexer so authors
    are nudged to set ``tool_kind`` explicitly.
    """
    if connector_api:
        return ToolKind.MUTATE.value
    if (risk_level or "").lower() == "read_only":
        return ToolKind.READ.value
    return ToolKind.ANALYZE.value


class ToolRuntime(BaseModel):
    """How the runtime executes a tool. Exactly ONE of the three fields
    must be set.

    - source_code : Inline Python (typically used by DDB-authored tools
                    via the Tool Builder).
    - module_path : Dotted import path resolved at startup; e.g.
                    ``services.control_plane.tools.o2c_tools.place_credit_hold``.
                    Used by code-defined tools that ship their YAML
                    descriptor alongside the registration.
    - ddb_ref     : Tool stored in the DynamoDB Tool Builder; the YAML is
                    a metadata pointer. Resolved via DynamicToolLoader.
    """

    source_code: Optional[str] = None
    module_path: Optional[str] = None
    ddb_ref: Optional[str] = None

    @model_validator(mode="after")
    def _exactly_one(self) -> "ToolRuntime":
        provided = [v for v in (self.source_code, self.module_path, self.ddb_ref) if v]
        if len(provided) != 1:
            raise ValueError(
                "ToolRuntime must have exactly one of: source_code, module_path, ddb_ref"
            )
        return self


def _validate_id(value: str, kind: str) -> str:
    if not _ID_RE.match(value):
        raise ValueError(
            f"{kind} id '{value}' must be lowercase, start with a letter, "
            f"and contain only [a-z0-9_] (dot-segments allowed)"
        )
    return value


class ConnectorAPIDoc(BaseModel):
    """One connector API definition.

    Inline-declared inside a use case YAML when the API is unique to the
    use case. Globally-declared ones live in
    ``services/control_plane/connector_apis.py``; the indexer merges both
    and refuses to insert duplicates.
    """

    api_id: str = Field(..., description="Stable id, e.g. 'sfdc.account.credit_hold.set'")
    target_system: str = Field(..., description="oracle | sap | sfdc | external")
    operation: str = Field(..., description="HTTP verb + path, e.g. 'PATCH /api/v1/simulator/sfdc/accounts/{id}/credit-hold'")
    description: Optional[str] = None
    request_schema: Dict[str, Any] = Field(default_factory=dict)
    response_schema: Dict[str, Any] = Field(default_factory=dict)
    simulator_writeback: bool = True
    risk_level: str = Field(default="low_risk_write", description="read_only | low_risk_write | high_risk_write")

    @field_validator("api_id")
    @classmethod
    def _v_api_id(cls, v: str) -> str:
        return _validate_id(v, "ConnectorAPI")

    @field_validator("target_system")
    @classmethod
    def _v_target(cls, v: str) -> str:
        if v not in {"oracle", "sap", "sfdc", "external"}:
            raise ValueError(f"target_system must be one of oracle/sap/sfdc/external, got {v}")
        return v

    @field_validator("risk_level")
    @classmethod
    def _v_risk(cls, v: str) -> str:
        if v not in {"read_only", "low_risk_write", "high_risk_write"}:
            raise ValueError(f"risk_level must be read_only/low_risk_write/high_risk_write, got {v}")
        return v


class ToolBindingDoc(BaseModel):
    """How a step invokes a registered ReAct tool."""

    binding_id: Optional[str] = None
    tool: str = Field(..., description="Name of a tool registered with ToolRegistry")
    params: Dict[str, Any] = Field(default_factory=dict, description="Static or templated params; ${expr} markers are resolved at runtime")
    description: Optional[str] = None
    connector_api: Optional[str] = Field(default=None, description="api_id of a ConnectorAPIDoc this tool ultimately calls")

    @field_validator("tool")
    @classmethod
    def _v_tool(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError(f"tool name '{v}' must be lowercase a-z0-9_-")
        return v


class StepDoc(BaseModel):
    """One atomic action inside a stage."""

    step_id: str = Field(..., description="Slug, unique within stage")
    name: str
    description: Optional[str] = None
    order: int = 1
    requires_approval: bool = False
    tool: Optional[str] = Field(default=None, description="Shortcut: register a single ToolBinding inline")
    params: Dict[str, Any] = Field(default_factory=dict)
    connector_api: Optional[str] = None
    bindings: List[ToolBindingDoc] = Field(default_factory=list)
    success_criteria: Optional[str] = None

    @field_validator("step_id")
    @classmethod
    def _v_step(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError(f"step_id '{v}' must be lowercase a-z0-9_-")
        return v

    def effective_bindings(self) -> List[ToolBindingDoc]:
        """Return the bindings list, materialising the inline shortcut form."""
        if self.bindings:
            return self.bindings
        if self.tool:
            return [ToolBindingDoc(
                binding_id=f"{self.step_id}_main",
                tool=self.tool,
                params=self.params or {},
                connector_api=self.connector_api,
                description=self.description,
            )]
        return []


class ConnectionDoc(BaseModel):
    """A NiFi-style edge between two steps inside the same stage.

    Replaces the implicit ``${steps.X.y}`` substitution model: the
    producer step's named output ``from_relationship`` feeds the
    consumer's input port ``to_param``. ``from_path`` is an optional
    dotted / indexed accessor into the producer's relationship payload
    (e.g. ``results.0.customer_id``); when omitted, the entire
    relationship dict is passed as the param value.

    Validation invariants (enforced by JourneyDoc.validate_strict):
      - ``from_step`` and ``to_step`` exist in the same stage.
      - ``from_relationship`` matches one of the source tool's declared
        ``output_relationships``.
      - ``to_param`` is a key in the destination tool's
        ``parameters.properties`` JSON schema.
      - At most one ConnectionDoc per ``(to_step, to_param)`` pair
        when ``fan_in_strategy == 'single_producer'`` (the default).
        Other strategies allow multi-producer fan-in.

    Phase 2 (Data Queues) additions:
      - ``max_object_count`` / ``max_byte_size`` -- per-queue back-pressure
        thresholds (NiFi FlowFileQueue equivalent). When the queue
        depth or byte size exceeds the threshold, the producer's
        ``enqueue`` call blocks (or yields) until the consumer drains.
      - ``fan_in_strategy`` -- how multiple producers feeding the same
        (to_step, to_param) port are merged.
    """

    from_step: str
    from_relationship: str
    to_step: str
    to_param: str
    from_path: Optional[str] = Field(
        default=None,
        description="Dotted / indexed path into the relationship payload",
    )
    # Phase 2 -- per-queue back-pressure thresholds.
    max_object_count: Optional[int] = Field(
        default=None,
        description="Max items in the queue before the producer back-pressures",
    )
    max_byte_size: Optional[int] = Field(
        default=None,
        description="Max total bytes in the queue before the producer back-pressures",
    )
    # Phase 2 -- multi-producer merging strategy. ``single_producer``
    # (default) preserves Phase-1 single-input-port semantics. The
    # other modes relax it so two ConnectionDocs feeding the same
    # (to_step, to_param) merge in either FIFO or round-robin order.
    fan_in_strategy: Literal["single_producer", "merge_fifo", "merge_round_robin"] = Field(
        default="single_producer",
        description="How multiple producers feed the same input port",
    )
    # Phase 3 -- parallel consumer workers. When > 1, N asyncio tasks
    # drain this queue concurrently using the same consumer group.
    # Default 1 preserves serial dispatch.
    concurrent_consumers: int = Field(
        default=1, ge=1, le=64,
        description="Number of parallel worker tasks draining this queue",
    )
    # Phase 5 -- prioritizer + expiry.
    #   fifo (default) -- first in first out via Redis Streams / deque.
    #   lifo           -- newest item first.
    #   by_attribute   -- score taken from ``priority_path``; lower
    #                     numeric score dequeues first. Requires Sorted
    #                     Set backing (mutually exclusive with
    #                     concurrent_consumers > 1; validator rejects
    #                     the combo).
    prioritizer: Literal["fifo", "lifo", "by_attribute"] = Field(
        default="fifo",
        description="Queue ordering strategy",
    )
    priority_path: Optional[str] = Field(
        default=None,
        description="Dotted accessor into the payload for the priority score (required when prioritizer='by_attribute')",
    )
    # Items older than ``expiry_seconds`` are dropped (NOT delivered).
    # Default None means no expiry sweep.
    expiry_seconds: Optional[int] = Field(
        default=None, gt=0,
        description="Drop items older than this many seconds without delivery",
    )

    @field_validator("from_step", "to_step")
    @classmethod
    def _v_step_id(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError(f"step id '{v}' must be lowercase a-z0-9_-")
        return v

    @field_validator("from_relationship")
    @classmethod
    def _v_relationship(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError(f"relationship name '{v}' must be lowercase a-z0-9_-")
        return v


class StageDoc(BaseModel):
    """A phase inside a use case."""

    stage_id: str
    name: str
    description: Optional[str] = None
    order: int = 1
    steps: List[StepDoc] = Field(default_factory=list)
    # Phase 1 -- first-class dataflow edges between sibling steps.
    # See ConnectionDoc above. Empty list (default) keeps every
    # pre-Phase-1 stage valid; the runner falls back to ${steps.X.y}
    # substitution when this list is empty.
    connections: List[ConnectionDoc] = Field(default_factory=list)

    @field_validator("stage_id")
    @classmethod
    def _v_stage(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError(f"stage_id '{v}' must be lowercase a-z0-9_-")
        return v


class UseCaseDoc(BaseModel):
    """One automation Use Case.

    One YAML file under ``enterprise-knowledge/automation/<solution>/`` =
    one of these.
    """

    use_case_id: str
    title: str
    solution_id: str = Field(..., description="appId, e.g. 'order-to-cash'")
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    kpi_impact: List[str] = Field(default_factory=list)
    consumes_entities: List[str] = Field(default_factory=list)
    produces_entities: List[str] = Field(default_factory=list)
    stages: List[StageDoc] = Field(default_factory=list)
    connector_apis: List[ConnectorAPIDoc] = Field(default_factory=list)
    version: int = 1
    status: str = Field(default="draft", description="draft | active | deprecated")

    @field_validator("use_case_id")
    @classmethod
    def _v_uc(cls, v: str) -> str:
        return _validate_id(v, "UseCase")

    @field_validator("solution_id")
    @classmethod
    def _v_sol(cls, v: str) -> str:
        valid = {
            "order-to-cash", "demand-forecasting", "inventory-optimization",
            "procurement-analytics", "production-quality", "supply-chain-risk",
            "customer-360", "esg-sustainability",
            # CPQ solutions (sell-side Trade CPQ + buy-side Sourcing CPQ)
            "trade-cpq", "sourcing-cpq",
            # Journey Builder produced docs use the ``builder`` solution
            # marker so they round-trip through validate_strict without
            # masquerading as one of the curated solutions.
            "builder",
        }
        if v not in valid:
            raise ValueError(f"solution_id '{v}' must be one of {sorted(valid)}")
        return v

    @field_validator("status")
    @classmethod
    def _v_status(cls, v: str) -> str:
        if v not in {"draft", "active", "deprecated"}:
            raise ValueError(f"status must be draft/active/deprecated, got {v}")
        return v

    def all_tool_names(self) -> List[str]:
        """Collect every distinct tool name referenced by this use case."""
        out: List[str] = []
        for stage in self.stages:
            for step in stage.steps:
                for b in step.effective_bindings():
                    if b.tool not in out:
                        out.append(b.tool)
        return out

    def all_connector_api_ids(self) -> List[str]:
        out: List[str] = []
        for stage in self.stages:
            for step in stage.steps:
                for b in step.effective_bindings():
                    if b.connector_api and b.connector_api not in out:
                        out.append(b.connector_api)
        for api in self.connector_apis:
            if api.api_id not in out:
                out.append(api.api_id)
        return out


class IndexedUseCaseSummary(BaseModel):
    """Light row returned by the catalogue listing endpoint."""

    use_case_id: str
    title: str
    solution_id: str
    status: str
    stage_count: int = 0
    step_count: int = 0
    tool_count: int = 0
    connector_api_count: int = 0
    indexed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 2 - Tool Catalogue
# ---------------------------------------------------------------------------

class ToolDoc(BaseModel):
    """One ReAct tool, codified as YAML under
    ``enterprise-knowledge/tools/<group>/<tool_id>.yaml``.

    The YAML is metadata only - the executable Python lives in
    ``services/control_plane/tools/*.py`` (or in the DynamoDB Tool Builder
    for user-authored tools). ``tool_id`` MUST equal the ``Tool.name``
    registered in the live ToolRegistry.
    """

    tool_id: str = Field(..., description="Stable id; equals Tool.name in registry")
    display_name: str
    group: str = Field(..., description="o2c | virtual_query | rag | fdw | policy | simulator | etc.")
    description: str
    risk_level: str = Field(default="read_only")
    requires_approval: bool = False
    cacheable: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema, identical shape to Tool.parameters")
    connector_api: Optional[str] = None
    consumes_entities: List[str] = Field(default_factory=list)
    produces_entities: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    example_invocation: Optional[Dict[str, Any]] = None
    # Phase 3 (additive, optional - inferred from risk_level/connector_api
    # when omitted, see _infer_tool_kind).
    tool_kind: Optional[str] = Field(
        default=None,
        description="read | analyze | decide | mutate | notify (see ToolKind)",
    )
    header_comment: Optional[str] = Field(
        default=None,
        description="Cursor-style header comment block harvested from the YAML",
    )
    runtime: Optional[ToolRuntime] = None

    @field_validator("tool_id")
    @classmethod
    def _v_tool_id(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError(f"tool_id '{v}' must be lowercase a-z0-9_-")
        return v

    @field_validator("risk_level")
    @classmethod
    def _v_risk(cls, v: str) -> str:
        if v not in {"read_only", "low_risk_write", "high_risk_write"}:
            raise ValueError(f"risk_level must be read_only/low_risk_write/high_risk_write, got {v}")
        return v

    @field_validator("tool_kind")
    @classmethod
    def _v_kind(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            ToolKind(v)
        except ValueError:
            raise ValueError(
                f"tool_kind '{v}' must be one of "
                f"{[k.value for k in ToolKind]}"
            )
        return v

    @model_validator(mode="after")
    def _v_kind_connector_invariant(self) -> "ToolDoc":
        """A mutate/notify tool MUST have a connector_api; a
        read/analyze/decide tool MUST NOT (plan section 28).
        """
        kind = self.tool_kind or _infer_tool_kind(
            risk_level=self.risk_level, connector_api=self.connector_api,
        )
        if kind in _CONNECTOR_KINDS and not self.connector_api:
            raise ValueError(
                f"tool_kind '{kind}' requires connector_api to be set "
                f"(tool_id={self.tool_id})"
            )
        if kind in _NON_CONNECTOR_KINDS and self.connector_api:
            raise ValueError(
                f"tool_kind '{kind}' must NOT set connector_api "
                f"(tool_id={self.tool_id}, connector_api={self.connector_api})"
            )
        return self

    def effective_tool_kind(self) -> str:
        """Returns the explicit ``tool_kind`` or the heuristic inference."""
        return self.tool_kind or _infer_tool_kind(
            risk_level=self.risk_level, connector_api=self.connector_api,
        )


# ---------------------------------------------------------------------------
# Phase 2 - Unified Journey schema
# ---------------------------------------------------------------------------

class ProvenanceMeta(BaseModel):
    source: str = Field(default="yaml", description="yaml | copilot | plugin | user_authored")
    session_id: Optional[str] = None
    base_use_case_id: Optional[str] = None
    generated_at: Optional[str] = None
    user: Optional[str] = None


class ParamSpec(BaseModel):
    name: str
    type: str = "string"
    description: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None


class OutputSpec(BaseModel):
    name: str
    type: str = "object"
    description: Optional[str] = None
    entity: Optional[str] = None


class ValidationIssue(BaseModel):
    severity: str = "error"
    path: str = ""
    code: str
    message: str


class ValidationReport(BaseModel):
    ok: bool = True
    errors: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[ValidationIssue] = Field(default_factory=list)

    def add_error(self, path: str, code: str, message: str) -> None:
        self.errors.append(ValidationIssue(severity="error", path=path, code=code, message=message))
        self.ok = False

    def add_warning(self, path: str, code: str, message: str) -> None:
        self.warnings.append(ValidationIssue(severity="warning", path=path, code=code, message=message))


class JourneyDoc(UseCaseDoc):
    """Unified Journey schema (Phase 2).

    Extends ``UseCaseDoc`` with provenance and runtime input/output declarations.
    A curated playbook on disk validates against ``UseCaseDoc`` (kind=playbook,
    no provenance). A Copilot-generated or user-saved journey carries
    ``kind=copilot_generated`` or ``user_authored`` plus ``provenance``.

    Both ``use_case_id`` (legacy) and ``journey_id`` (new) are accepted on
    input. Saved Copilot journeys reference their parent playbook via
    ``provenance.base_use_case_id``.
    """

    journey_id: Optional[str] = None
    kind: str = Field(default="playbook", description="playbook | copilot_generated | user_authored")
    provenance: Optional[ProvenanceMeta] = None
    inputs: List[ParamSpec] = Field(default_factory=list)
    outputs: List[OutputSpec] = Field(default_factory=list)
    # Phase 1 -- registry bucket / namespace this journey belongs to.
    # Mirrors NiFi-Registry's bucket grouping. Defaults to "default" so
    # every pre-Phase-1 persisted JourneyDoc keeps validating. The
    # legacy migration script stamps each existing journey's bucket
    # from its ``solution_id``.
    bucket: str = Field(default="default", description="Registry bucket / namespace this journey belongs to")
    # Execution-mode discriminator (sequential vs dataflow).
    #   sequential -- steps run strictly in order, no inter-step data
    #     exchange. Runner skips ConnectionDoc routing entirely and
    #     omits the ``steps`` namespace from substitution context so a
    #     stray ``${steps.X.y}`` cannot resolve. Useful for
    #     knowledge-indexing / ETL playbooks where each step does its
    #     own side-effect work.
    #   dataflow -- steps may consume one another's outputs via
    #     ConnectionDocs + ${steps.X.y} substitution. Default to keep
    #     every existing playbook + persisted user journey valid.
    execution_mode: Literal["sequential", "dataflow"] = Field(
        default="dataflow",
        description=(
            "sequential: steps run strictly in order with no data exchange. "
            "dataflow: steps may consume one another's outputs via ConnectionDocs."
        ),
    )

    @field_validator("kind")
    @classmethod
    def _v_kind(cls, v: str) -> str:
        if v not in {"playbook", "copilot_generated", "user_authored"}:
            raise ValueError(f"kind must be playbook/copilot_generated/user_authored, got {v}")
        return v

    def get_journey_id(self) -> str:
        return self.journey_id or self.use_case_id

    def validate_strict(
        self,
        known_tools: Optional[set] = None,
        known_connector_apis: Optional[set] = None,
        tool_kinds: Optional[Dict[str, str]] = None,
        tool_relationships: Optional[Dict[str, List[str]]] = None,
        tool_param_schemas: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> ValidationReport:
        """Cross-reference checks against live registries.

        ``tool_kinds`` is an optional ``{tool_id: tool_kind}`` map. When
        supplied, the validator enforces the Phase-3 stage/kind alignment
        rules (see plan section 28):

        - Stages named ``act`` or ``notify`` MUST contain at least one step
          whose resolved tool is ``mutate`` or ``notify``.
        - Stages named ``resolve`` or ``diagnose`` MUST contain only steps
          whose resolved tools are ``read``, ``analyze`` or ``decide``.
        - Steps MUST NOT carry their own ``connector_api`` (forbidden at
          the step level; the linkage lives on the tool's ``ToolDoc``).
          Existing playbooks with leftover step-level ``connector_api``
          fields generate a warning until the strip pass lands.

        Phase 1 additions:

        ``tool_relationships`` is an optional ``{tool_id: [relationship_name, ...]}``
        map. When supplied, every ``ConnectionDoc.from_relationship``
        must be present on the source tool. Relationships declared on
        the producer tool that are not consumed by any ConnectionDoc
        AND are not the conventional ``failure`` channel raise a
        ``relationship_not_consumed`` warning.

        ``tool_param_schemas`` is an optional ``{tool_id: parameters_dict}``
        map. When supplied, every ``ConnectionDoc.to_param`` must be a
        key in the destination tool's ``parameters.properties``.

        ``ConnectionDoc`` single-producer-per-input-port is always
        enforced (no ``known_*`` map needed): a ``(to_step, to_param)``
        pair appearing on two ConnectionDocs in the same stage raises
        a ``duplicate_input_producer`` error.

        Returns a structured report - never raises - so the planner can
        feed validation errors back to the LLM for repair.
        """
        report = ValidationReport()
        known_tools = known_tools or set()
        known_connector_apis = known_connector_apis or set()
        tool_kinds = tool_kinds or {}
        tool_relationships = tool_relationships or {}
        tool_param_schemas = tool_param_schemas or {}
        inline_apis = {api.api_id for api in self.connector_apis}
        seen_step_ids: set = set()

        # Sequential-mode invariants -- enforced top-level so a journey
        # tagged ``sequential`` can never carry dataflow wiring.
        is_sequential = self.execution_mode == "sequential"
        _STEPS_PLACEHOLDER_RX = re.compile(r"\$\{\s*steps\.")
        if is_sequential:
            for stage_idx_seq, stage_seq in enumerate(self.stages):
                stage_path_seq = f"stages[{stage_idx_seq}]"
                if stage_seq.connections:
                    report.add_error(
                        stage_path_seq, "sequential_journey_has_connections",
                        f"Stage '{stage_seq.stage_id}' carries {len(stage_seq.connections)} "
                        "ConnectionDoc(s) but the journey is execution_mode=sequential. "
                        "Either remove the connections or switch to execution_mode=dataflow.",
                    )
                for step_idx_seq, step_seq in enumerate(stage_seq.steps):
                    step_path_seq = f"{stage_path_seq}.steps[{step_idx_seq}]"
                    for k, v in (step_seq.params or {}).items():
                        if isinstance(v, str) and _STEPS_PLACEHOLDER_RX.search(v):
                            report.add_error(
                                f"{step_path_seq}.params.{k}",
                                "sequential_journey_has_step_substitution",
                                f"Step '{step_seq.step_id}' param '{k}' references "
                                f"${{steps.X.y}} but execution_mode=sequential forbids "
                                "inter-step data exchange. Use a literal value, an "
                                "${{inputs.X}} reference, or switch to dataflow mode.",
                            )

        if not self.stages:
            report.add_warning("stages", "empty_stages", "Journey has no stages")

        for stage_idx, stage in enumerate(self.stages):
            stage_path = f"stages[{stage_idx}]"
            if not stage.steps:
                report.add_warning(stage_path, "empty_stage", f"Stage '{stage.stage_id}' has no steps")

            stage_kinds: List[str] = []  # collected for stage/kind alignment
            for step_idx, step in enumerate(stage.steps):
                step_path = f"{stage_path}.steps[{step_idx}]"
                if step.step_id in seen_step_ids:
                    report.add_error(step_path, "duplicate_step_id", f"Duplicate step_id '{step.step_id}'")
                seen_step_ids.add(step.step_id)

                # Phase 3: connector_api on a step is forbidden.
                if step.connector_api:
                    report.add_warning(
                        step_path, "step_connector_api_forbidden",
                        f"Step '{step.step_id}' carries connector_api='{step.connector_api}' - "
                        "connector wiring belongs on the tool's ToolDoc, not on the step. "
                        "This warning will become an error once the strip pass lands.",
                    )

                bindings = step.effective_bindings()
                if not bindings:
                    report.add_warning(step_path, "no_tool", f"Step '{step.step_id}' has no tool binding (LLM-only step)")
                    stage_kinds.append(ToolKind.DECIDE.value)
                    continue
                for b_idx, b in enumerate(bindings):
                    b_path = f"{step_path}.bindings[{b_idx}]"
                    if known_tools and b.tool not in known_tools:
                        report.add_error(b_path, "unknown_tool", f"Tool '{b.tool}' is not registered in ToolRegistry")
                    if b.connector_api:
                        # Same rule applies to inline bindings.
                        report.add_warning(
                            b_path, "binding_connector_api_forbidden",
                            f"Tool binding '{b.tool}' carries connector_api='{b.connector_api}' - "
                            "connector wiring belongs on the tool's ToolDoc, not on the binding.",
                        )
                        if known_connector_apis and b.connector_api not in known_connector_apis and b.connector_api not in inline_apis:
                            report.add_error(b_path, "unknown_connector_api",
                                             f"connector_api '{b.connector_api}' is not registered and not inline-declared")

                    # Track resolved tool_kind for stage/kind alignment.
                    kind = tool_kinds.get(b.tool)
                    if kind:
                        stage_kinds.append(kind)

            # Stage/kind alignment (only when we have kind info).
            if tool_kinds:
                lname = stage.stage_id.lower()
                if lname in _STAGE_ACT_NAMES and stage_kinds:
                    if not any(k in _CONNECTOR_KINDS for k in stage_kinds):
                        report.add_error(
                            stage_path, "act_stage_no_mutator",
                            f"Stage '{stage.stage_id}' is an act/notify stage but contains "
                            f"no step whose resolved tool is mutate/notify (kinds seen: {stage_kinds}).",
                        )
                if lname in _STAGE_RESOLVE_NAMES and stage_kinds:
                    illegal = [k for k in stage_kinds if k in _CONNECTOR_KINDS]
                    if illegal:
                        report.add_error(
                            stage_path, "resolve_stage_has_mutator",
                            f"Stage '{stage.stage_id}' is a resolve/diagnose stage but "
                            f"contains a step whose resolved tool is mutate/notify "
                            f"(illegal kinds: {illegal}).",
                        )

            # ---------------- Phase 1: ConnectionDoc checks ----------------
            # Build a per-stage map of step_id -> primary tool (used to
            # resolve relationship and param-name lookups against the
            # caller-supplied tool_relationships / tool_param_schemas maps).
            step_tool: Dict[str, str] = {}
            for step in stage.steps:
                bindings = step.effective_bindings()
                if bindings:
                    step_tool[step.step_id] = bindings[0].tool

            seen_input_ports: set = set()
            consumed_outputs: Dict[str, set] = {}  # producer_step_id -> {relationship_name}

            for c_idx, conn in enumerate(stage.connections):
                c_path = f"{stage_path}.connections[{c_idx}]"

                # Endpoints exist in the stage.
                if conn.from_step not in step_tool and conn.from_step not in [s.step_id for s in stage.steps]:
                    report.add_error(
                        c_path, "connection_unknown_source",
                        f"Connection from_step '{conn.from_step}' does not exist in stage '{stage.stage_id}'",
                    )
                    continue
                if conn.to_step not in step_tool and conn.to_step not in [s.step_id for s in stage.steps]:
                    report.add_error(
                        c_path, "connection_unknown_target",
                        f"Connection to_step '{conn.to_step}' does not exist in stage '{stage.stage_id}'",
                    )
                    continue

                # Self-loop guard.
                if conn.from_step == conn.to_step:
                    report.add_error(
                        c_path, "connection_self_loop",
                        f"Connection has the same from_step and to_step '{conn.from_step}'",
                    )
                    continue

                # Phase 5: prioritizer + parallel consumers are
                # mutually exclusive (Sorted Set backing has no
                # consumer-group semantics).
                if conn.prioritizer != "fifo" and conn.concurrent_consumers > 1:
                    report.add_error(
                        c_path, "prioritizer_concurrent_conflict",
                        f"prioritizer='{conn.prioritizer}' cannot be combined with "
                        f"concurrent_consumers={conn.concurrent_consumers}. Sorted-Set "
                        "backed queues are single-consumer.",
                    )
                # ``by_attribute`` requires a ``priority_path``.
                if conn.prioritizer == "by_attribute" and not conn.priority_path:
                    report.add_error(
                        c_path, "prioritizer_missing_path",
                        "prioritizer='by_attribute' requires priority_path to be set "
                        "(e.g. 'urgency' or 'sla_pct').",
                    )

                # Relationship exists on the source tool's declaration.
                # WARNING (not error) during the Phase 1 transition: the
                # legacy canvas may still emit hint-keyed source handles
                # ("results", "count") that don't match the declared
                # relationships. The runtime ConnectionDoc routing keeps
                # working (the runner falls back to substitution when
                # the relationship lookup misses) so the journey runs
                # either way. The warning surfaces the drift to authors.
                src_tool = step_tool.get(conn.from_step)
                if src_tool and tool_relationships:
                    declared = tool_relationships.get(src_tool)
                    if declared is not None and conn.from_relationship not in declared:
                        report.add_warning(
                            c_path, "connection_unknown_relationship",
                            f"Tool '{src_tool}' does not declare relationship '{conn.from_relationship}' "
                            f"(declared: {sorted(declared)})",
                        )

                # to_param exists in the destination tool's JSON schema.
                # Also a WARNING for the same reason -- dynamic kwargs
                # and dotted-param tools legitimately accept inputs not
                # listed in their JSON schema's ``properties``.
                dst_tool = step_tool.get(conn.to_step)
                if dst_tool and tool_param_schemas:
                    schema = tool_param_schemas.get(dst_tool) or {}
                    properties = (schema.get("properties") or {})
                    if properties and conn.to_param not in properties:
                        report.add_warning(
                            c_path, "connection_unknown_param",
                            f"Tool '{dst_tool}' does not declare param '{conn.to_param}' "
                            f"(declared: {sorted(properties.keys())})",
                        )

                # Single-producer-per-input-port unless the
                # ConnectionDoc opts into a fan-in merge strategy
                # (Phase 2 of the Data Queues plan).
                input_port = (conn.to_step, conn.to_param)
                if input_port in seen_input_ports:
                    if conn.fan_in_strategy == "single_producer":
                        report.add_error(
                            c_path, "duplicate_input_producer",
                            f"Multiple ConnectionDocs feed (to_step='{conn.to_step}', "
                            f"to_param='{conn.to_param}'). Either remove one or set "
                            "fan_in_strategy to 'merge_fifo' / 'merge_round_robin'.",
                        )
                    else:
                        # Multi-producer merge -- legitimate fan-in.
                        report.add_warning(
                            c_path, "multi_producer_fan_in",
                            f"Multiple producers feed (to_step='{conn.to_step}', "
                            f"to_param='{conn.to_param}') with fan_in_strategy="
                            f"'{conn.fan_in_strategy}'.",
                        )
                seen_input_ports.add(input_port)

                consumed_outputs.setdefault(conn.from_step, set()).add(conn.from_relationship)

            # Auto-terminate warning: relationships declared on a producer
            # but not consumed by any ConnectionDoc in this stage (and not
            # the conventional ``failure`` channel) generate a warning.
            if tool_relationships:
                for step_id, tool_name in step_tool.items():
                    declared = tool_relationships.get(tool_name) or []
                    consumed = consumed_outputs.get(step_id, set())
                    for rel in declared:
                        if rel in consumed:
                            continue
                        if rel == "failure":
                            continue
                        report.add_warning(
                            f"{stage_path}.step[{step_id}]",
                            "relationship_not_consumed",
                            f"Step '{step_id}' (tool '{tool_name}') declares relationship "
                            f"'{rel}' but no ConnectionDoc consumes it. Either wire it to a "
                            "downstream step or mark the relationship auto_terminate_default.",
                        )

        return report
