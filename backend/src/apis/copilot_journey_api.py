"""
Copilot Journey and Journey Builder API

Endpoints for AI-guided journey planning, execution with feedback,
and interactive journey building with validation and save.

The ``/journey-builder/*`` family rides on a single canonical pipeline:

  builder request -> _builder_to_journey_doc -> JourneyDoc -> { save | run | validate }

so the three operations share a single transform and use the same
backend services as Copilot-saved journeys (Foundry DDB persistence)
and the YAML Journey Runner (PG-backed execution + approval pause).
"""

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field, ValidationError

router = APIRouter(tags=["Copilot Journey"])

_copilot_engine = None
_journey_store = None
_yaml_journey_runner = None
_tool_registry = None
_connector_apis = None


def configure(engine, journey_store=None, yaml_journey_runner=None,
              tool_registry=None, connector_apis=None):
    """Wire the dependencies shared by the journey-builder family.

    ``yaml_journey_runner`` enables the canonical run path; when absent
    the legacy ephemeral-Copilot-session fallback continues to work.
    ``tool_registry`` + ``connector_apis`` are used by ``validate``
    and ``save`` to call ``JourneyDoc.validate_strict``.
    """
    global _copilot_engine, _journey_store, _yaml_journey_runner
    global _tool_registry, _connector_apis
    _copilot_engine = engine
    if journey_store is not None:
        _journey_store = journey_store
    if yaml_journey_runner is not None:
        _yaml_journey_runner = yaml_journey_runner
    if tool_registry is not None:
        _tool_registry = tool_registry
    if connector_apis is not None:
        _connector_apis = connector_apis


def _check():
    if not _copilot_engine:
        raise HTTPException(status_code=503, detail="Copilot engine not initialized")


class PlanRequest(BaseModel):
    goal: str
    use_case: str = ""
    max_steps: int = Field(default=10, ge=1, le=20)
    auto_execute: bool = False


class FeedbackRequest(BaseModel):
    action: str = "approve"
    feedback: str = ""
    changes: Optional[dict] = None


class SaveJourneyRequest(BaseModel):
    name: str = ""


class BuilderSuggestRequest(BaseModel):
    current_steps: list = Field(default_factory=list)
    goal: str = ""
    use_case: str = ""


class BuilderEdge(BaseModel):
    """One dataflow edge in the Journey Builder graph.

    Materialises into ``target.params[to_param] =
    "${steps.<from_node>.<from_key>}"`` so the existing param
    substitution helper resolves the chain at run time.
    """
    from_node: str
    from_key: str
    to_node: str
    to_param: str


class BuilderConnection(BaseModel):
    """Phase 1 -- explicit relationship-routed edge between two builder steps.

    Mirrors ``automation_models.ConnectionDoc`` over the wire. The
    canvas emits one of these per drag-drawn arrow (and per Reads-from
    dropdown pick). ``BuilderEdge`` continues to be accepted for
    backward compatibility with older UI builds; if both are present
    the connections take precedence.
    """

    from_step: str
    from_relationship: str
    to_step: str
    to_param: str
    from_path: Optional[str] = None


class BuilderStage(BaseModel):
    """Per-stage payload used by multi-stage Journey Builder canvases.

    When ``BuilderSaveRequest.stages`` is non-empty the API walks this
    list to materialise one ``StageDoc`` per entry. When ``stages`` is
    absent / empty the legacy single-stage shape is used (a single
    ``main`` stage containing the flat ``steps`` / ``edges`` /
    ``connections`` lists).
    """

    stage_id: str
    name: Optional[str] = None
    order: int = 1
    steps: list = Field(default_factory=list)
    edges: List[BuilderEdge] = Field(default_factory=list)
    connections: List[BuilderConnection] = Field(default_factory=list)


class BuilderSaveRequest(BaseModel):
    name: str
    display_name: str = ""
    description: str = ""
    trigger: str = "manual"
    steps: list = Field(default_factory=list)
    edges: List[BuilderEdge] = Field(default_factory=list)
    connections: List[BuilderConnection] = Field(default_factory=list)
    # Multi-stage shape -- when present, ``_builder_to_journey_doc``
    # materialises one StageDoc per entry. The flat ``steps`` /
    # ``edges`` / ``connections`` fields above are then ignored. When
    # ``stages`` is empty (the legacy single-stage canvas), the flat
    # fields produce a single ``main`` stage. Both shapes round-trip
    # cleanly so older UI builds keep working.
    stages: List[BuilderStage] = Field(default_factory=list)
    bucket: Optional[str] = None
    solution_id: Optional[str] = None
    # Execution-mode discriminator -- ``sequential`` skips ConnectionDoc
    # routing in the runner and rejects ``${steps.X.y}`` substitution.
    # Defaults to ``dataflow`` so the existing canvas keeps working.
    execution_mode: Optional[str] = "dataflow"
    inputs: Optional[Dict[str, Any]] = None


class BuilderValidateRequest(BaseModel):
    name: str = ""
    description: str = ""
    steps: list = Field(default_factory=list)
    edges: List[BuilderEdge] = Field(default_factory=list)
    connections: List[BuilderConnection] = Field(default_factory=list)
    stages: List[BuilderStage] = Field(default_factory=list)
    bucket: Optional[str] = None
    solution_id: Optional[str] = None
    execution_mode: Optional[str] = "dataflow"


# ---------------------------------------------------------------------------
# BuilderState -> JourneyDoc pipeline
# ---------------------------------------------------------------------------

_SLUG_RX = re.compile(r"[^a-z0-9_]+")


def _slug(value: str) -> str:
    """Lowercase ``[a-z0-9_]`` slug matching ``automation_models._ID_RE``.

    Hyphens are deliberately collapsed to underscores so the resulting
    string is a valid ``use_case_id`` segment. Empty inputs fall back
    to ``builder_<uuid>``; leading digits are prefixed with ``b_`` to
    satisfy the ``[a-z][a-z0-9_]*`` start-with-letter rule.
    """
    raw = (value or "").strip().lower()
    out = _SLUG_RX.sub("_", raw).strip("_")
    if not out:
        return f"builder_{uuid.uuid4().hex[:8]}"
    if not out[0].isalpha():
        out = f"b_{out}"
    return out


def _topo_sort(nodes: List[Dict[str, Any]], edges: List[BuilderEdge]) -> List[Dict[str, Any]]:
    """Topologically sort builder nodes by the edges' producer -> consumer
    dependencies. When the graph has no edges or only some nodes are
    referenced, the relative order of unconstrained nodes is preserved
    from the input list (stable). Raises HTTPException(422) on cycles.
    """
    if not nodes:
        return []
    id_to_node = {str(n.get("id") or ""): n for n in nodes if n.get("id")}
    incoming: Dict[str, int] = {nid: 0 for nid in id_to_node}
    deps: Dict[str, List[str]] = {nid: [] for nid in id_to_node}
    for e in edges or []:
        src, dst = e.from_node, e.to_node
        if src not in id_to_node or dst not in id_to_node:
            continue
        if src == dst:
            raise HTTPException(
                status_code=422,
                detail={"code": "builder_self_edge", "edge": e.model_dump()},
            )
        deps[src].append(dst)
        incoming[dst] += 1

    # Stable Kahn's algorithm: emit nodes in original order among those
    # whose remaining incoming-edge count is zero.
    original_order = [str(n.get("id")) for n in nodes if n.get("id") in id_to_node]
    ready = [nid for nid in original_order if incoming[nid] == 0]
    emitted: List[str] = []
    while ready:
        # Always pick the leftmost ready node (by original order) so
        # users see deterministic ordering matching how they laid the
        # graph out.
        nid = ready.pop(0)
        emitted.append(nid)
        for child in deps[nid]:
            incoming[child] -= 1
            if incoming[child] == 0:
                # Insert preserving original order among newly ready nodes.
                idx = original_order.index(child)
                inserted = False
                for i, existing in enumerate(ready):
                    if original_order.index(existing) > idx:
                        ready.insert(i, child)
                        inserted = True
                        break
                if not inserted:
                    ready.append(child)
    if len(emitted) != len(id_to_node):
        # Cycle: at least one node never reached zero incoming.
        leftover = [nid for nid in id_to_node if nid not in emitted]
        raise HTTPException(
            status_code=422,
            detail={
                "code": "builder_cycle",
                "message": "Journey builder graph has a cycle",
                "involved_nodes": leftover,
            },
        )
    return [id_to_node[nid] for nid in emitted]


def _apply_edges_to_params(
    nodes: List[Dict[str, Any]],
    edges: List[BuilderEdge],
) -> List[Dict[str, Any]]:
    """Return a new node list whose target params carry ``${steps.X.y}``
    placeholders for each incoming edge. The runtime substitution
    helper in ``_param_substitution.py`` resolves these at execute time.
    """
    by_id = {str(n.get("id") or ""): dict(n) for n in nodes if n.get("id")}
    for n in by_id.values():
        n["params"] = dict(n.get("params") or {})
    for e in edges or []:
        node = by_id.get(e.to_node)
        if node is None:
            continue
        placeholder = "${steps." + e.from_node + "." + e.from_key + "}"
        node["params"][e.to_param] = placeholder
    return [by_id[str(n.get("id"))] for n in nodes if n.get("id") in by_id]


def _build_stage_doc(
    *,
    stage_id: str,
    name: Optional[str],
    order: int,
    raw_steps: list,
    edges: List[BuilderEdge],
    connections: List[BuilderConnection],
    execution_mode: str,
):
    """Build one ``StageDoc`` from a single stage's slice of builder state.

    Used by both the legacy single-stage path and the new multi-stage
    path -- the shape produced per stage is identical so JourneyDoc
    invariants stay consistent.
    """
    from src.models.automation_models import (
        ConnectionDoc, StageDoc, StepDoc,
    )

    nodes_with_edges = _apply_edges_to_params(raw_steps, edges)
    ordered = _topo_sort(nodes_with_edges, edges)

    stage_steps: List[StepDoc] = []
    for i, n in enumerate(ordered):
        sid = str(n.get("id") or f"s{i + 1}")
        params = dict(n.get("params") or {})
        foreach_val = n.get("foreach") or params.pop("__foreach__", None)
        if foreach_val:
            params["__foreach__"] = foreach_val
        stage_steps.append(StepDoc(
            step_id=sid,
            name=str(n.get("name") or sid),
            order=i + 1,
            tool=n.get("tool"),
            params=params,
            requires_approval=bool(n.get("requires_approval", False)),
        ))

    stage_connections: List[ConnectionDoc] = [
        ConnectionDoc(
            from_step=c.from_step,
            from_relationship=c.from_relationship,
            to_step=c.to_step,
            to_param=c.to_param,
            from_path=c.from_path,
        )
        for c in (connections or [])
    ]

    return StageDoc(
        stage_id=stage_id,
        name=name or stage_id,
        order=order,
        steps=stage_steps,
        # Sequential journeys carry no connections regardless of what
        # the canvas state held -- validate_strict would reject them.
        connections=[] if execution_mode == "sequential" else stage_connections,
    )


def _builder_to_journey_doc(req: BuilderSaveRequest):
    """Single canonical transform: ``BuilderState`` -> ``JourneyDoc``.

    All builder writes (save / run / validate) funnel through this
    helper so the JourneyDoc shape is identical regardless of which
    operation invoked it. Returns the Pydantic model (caller dumps).

    Multi-stage shape (preferred when ``req.stages`` is non-empty):
      Each entry materialises one StageDoc. The flat ``req.steps`` /
      ``req.edges`` / ``req.connections`` fields are ignored in this
      mode. Stage order is normalised to the ``order`` attribute.

    Single-stage shape (legacy back-compat, when ``req.stages`` is
    empty):
      A single ``main`` stage is built from ``req.steps`` etc. Mirrors
      the original pre-multi-stage behaviour byte-for-byte so older UI
      builds keep working.
    """
    from src.models.automation_models import (
        JourneyDoc, ProvenanceMeta,
    )

    # Sanitise the execution_mode -- the wire is permissive (Optional[str])
    # so we coerce here before constructing the strict Pydantic model.
    raw_mode = (req.execution_mode or "dataflow").strip().lower()
    execution_mode = raw_mode if raw_mode in {"sequential", "dataflow"} else "dataflow"

    if req.stages:
        # Multi-stage path. Normalise order so duplicates / missing
        # values produce a deterministic 1..N sequence.
        sorted_stages = sorted(
            enumerate(req.stages),
            key=lambda pair: (pair[1].order if isinstance(pair[1].order, int) else pair[0] + 1, pair[0]),
        )
        stages_doc = []
        for new_idx, (_, s) in enumerate(sorted_stages):
            stages_doc.append(_build_stage_doc(
                stage_id=s.stage_id,
                name=s.name,
                order=new_idx + 1,
                raw_steps=s.steps,
                edges=s.edges,
                connections=s.connections,
                execution_mode=execution_mode,
            ))
    else:
        # Legacy single-stage path.
        stages_doc = [_build_stage_doc(
            stage_id="main",
            name="Main",
            order=1,
            raw_steps=req.steps,
            edges=req.edges,
            connections=req.connections,
            execution_mode=execution_mode,
        )]

    journey_id = f"builder.{_slug(req.name)}"
    return JourneyDoc(
        use_case_id=journey_id,
        journey_id=journey_id,
        title=req.display_name or req.name,
        solution_id=req.solution_id or "builder",
        bucket=req.bucket or "default",
        execution_mode=execution_mode,
        kind="user_authored",
        provenance=ProvenanceMeta(
            source="journey-builder",
            generated_at=datetime.now(timezone.utc).isoformat(),
        ),
        description=req.description,
        stages=stages_doc,
    )


def _collect_validation_inputs():
    """Materialise the (known_tools, known_apis, tool_kinds,
    tool_relationships, tool_param_schemas) tuple that
    ``JourneyDoc.validate_strict`` consumes. Falls back gracefully when
    a dependency was never wired in (offline tests etc.).
    """
    known_tools: set = set()
    tool_kinds: Dict[str, str] = {}
    tool_relationships: Dict[str, List[str]] = {}
    tool_param_schemas: Dict[str, Dict[str, Any]] = {}
    if _tool_registry is not None:
        try:
            for t in _tool_registry.list_tools():
                known_tools.add(t.name)
                kind = getattr(t, "tool_kind", None)
                if not kind:
                    if getattr(t, "connector_api", None):
                        kind = "mutate"
                    else:
                        rl = getattr(t, "risk_level", None)
                        rl_v = getattr(rl, "value", None) or str(rl or "")
                        kind = "read" if rl_v == "read_only" else "analyze"
                tool_kinds[t.name] = kind
                # Phase 1: relationship + param-schema metadata.
                rel_method = getattr(t, "relationship_names", None)
                if callable(rel_method):
                    try:
                        tool_relationships[t.name] = list(rel_method())
                    except Exception:
                        pass
                params = getattr(t, "parameters", None)
                if isinstance(params, dict):
                    tool_param_schemas[t.name] = params
        except Exception as e:
            logger.warning(f"validate_strict tool collection failed: {e}")

    known_apis: set = set()
    if _connector_apis is not None:
        try:
            known_apis = {s.api_id for s in _connector_apis.list_all()}
        except Exception as e:
            logger.warning(f"validate_strict connector_apis collection failed: {e}")

    return known_tools, known_apis, tool_kinds, tool_relationships, tool_param_schemas


# ============================================================================
# Copilot Journey Endpoints
# ============================================================================

@router.post("/copilot-journey")
async def create_copilot_journey(req: PlanRequest):
    _check()
    session = await _copilot_engine.create_session(req.goal, req.use_case)
    plan_result = await _copilot_engine.plan(session.session_id, req.use_case)

    if req.auto_execute:
        exec_result = await _copilot_engine.execute_plan(session.session_id)
        return {**plan_result, **exec_result, "auto_executed": True}

    return {**plan_result, "awaiting_approval": True}


@router.post("/copilot-journey/{session_id}/execute")
async def execute_copilot_journey(session_id: str):
    _check()
    result = await _copilot_engine.execute_plan(session_id)
    return result


@router.post("/copilot-journey/{session_id}/feedback")
async def copilot_feedback(session_id: str, req: FeedbackRequest):
    _check()
    if req.action == "approve":
        result = await _copilot_engine.execute_plan(session_id)
        return result
    elif req.action == "replan":
        result = await _copilot_engine.replan(session_id, req.feedback)
        return result
    elif req.action == "feedback":
        result = await _copilot_engine.replan(session_id, req.feedback)
        return result
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")


class StepApprovalRequest(BaseModel):
    step_id: str
    approved: bool = True


@router.post("/copilot-journey/{session_id}/approve-step")
async def approve_copilot_step(session_id: str, req: StepApprovalRequest):
    """Resolve a per-step approval gate (paused with status awaiting_step_approval)."""
    _check()
    result = _copilot_engine.approve_step(session_id, req.step_id, approved=req.approved)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    # Surface the bridge-minted job_id (when present) so the studio
    # can keep its polling pointed at the same JobExecution across
    # approve / resume cycles instead of re-discovering via /jobs.
    session = _copilot_engine.get_session(session_id) if _copilot_engine else None
    job_id = result.get("job_id") or (session.job_id if session else None)
    if result.get("status") == "approved":
        # Continue execution from the approved step.
        cont = await _copilot_engine.execute_plan(session_id)
        return {**result, **cont, "job_id": cont.get("job_id") or job_id}
    return {**result, "job_id": job_id}


@router.get("/copilot-journey/{session_id}")
async def get_copilot_session(session_id: str):
    _check()
    session = _copilot_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "goal": session.goal,
        "status": session.status,
        "plan": session.plan,
        "completed_steps": session.completed_steps,
        "rag_context": session.rag_context,
        "playbook_context": session.playbook_context,
        "pending_step": session.pending_step,
        "events": session.events[-20:],
        "created_at": session.created_at.isoformat(),
    }


@router.post("/copilot-journey/{session_id}/save")
async def save_copilot_as_journey(session_id: str, req: SaveJourneyRequest):
    _check()
    result = await _copilot_engine.save_as_journey(
        session_id, req.name, journey_store=_journey_store,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    if result.get("journey_id"):
        result["url"] = f"/workspace/automation?tab=journeys&id={result['journey_id']}"
    return result


@router.get("/copilot-journey/{session_id}/stream")
async def stream_copilot(session_id: str):
    _check()
    session = _copilot_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        last_idx = 0
        while True:
            if last_idx < len(session.events):
                for evt in session.events[last_idx:]:
                    yield f"data: {json.dumps(evt, default=str)}\n\n"
                last_idx = len(session.events)
            if session.status in ("completed", "error"):
                yield f"data: {json.dumps({'phase': 'done', 'status': session.status})}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ============================================================================
# Journey Builder Endpoints
# ============================================================================

@router.post("/journey-builder/suggest")
async def suggest_steps(req: BuilderSuggestRequest):
    _check()
    session = await _copilot_engine.create_session(req.goal or "Continue building journey", req.use_case)

    if req.current_steps:
        session.plan = req.current_steps
        session.completed_steps = [{"step_id": s.get("id", ""), "result_preview": "existing"} for s in req.current_steps]
        result = await _copilot_engine.replan(session.session_id, f"Suggest next steps after: {json.dumps([s.get('name', '') for s in req.current_steps])}")
        return {"suggestions": result.get("revised_plan", []), "session_id": session.session_id}

    result = await _copilot_engine.plan(session.session_id, req.use_case)
    return {"suggestions": result.get("plan", []), "session_id": session.session_id}


@router.post("/journey-builder/validate")
async def validate_journey(req: BuilderValidateRequest):
    """Server-side strict validation of the in-progress builder state.

    Builds a transient ``JourneyDoc`` from the builder request, runs
    ``JourneyDoc.validate_strict`` against the live ToolRegistry +
    connector_apis, and returns BOTH the structured report and the
    legacy ``{valid, errors, warnings}`` shape the existing UI banner
    consumes.

    The ``solution_id=builder`` doc deliberately does NOT pass
    ``tool_kinds`` into ``validate_strict`` so the Phase-3 stage/kind
    alignment rules (which expect ``act`` / ``notify`` stage names) do
    not fire on the builder's single ``main`` stage.
    """
    # Cycle / self-edge detection lives in _topo_sort -- catch the
    # HTTPException and surface it as a builder validation error rather
    # than a 422 response so the UI banner stays consistent.
    try:
        save_like = BuilderSaveRequest(
            name=req.name or "preview",
            display_name=req.name or "preview",
            description=req.description,
            steps=req.steps,
            edges=req.edges,
            connections=req.connections,
            stages=req.stages,
            bucket=req.bucket,
            execution_mode=req.execution_mode,
            solution_id=req.solution_id,
        )
        doc = _builder_to_journey_doc(save_like)
    except HTTPException as he:
        detail = he.detail if isinstance(he.detail, dict) else {"code": "builder_invalid", "message": str(he.detail)}
        return {
            "valid": False,
            "errors": [detail.get("message") or detail.get("code", "invalid graph")],
            "warnings": [],
            "report": {"errors": [detail], "warnings": []},
        }
    except ValidationError as e:
        # ConnectionDoc / StageDoc / JourneyDoc Pydantic validation
        # surfaced before validate_strict could run -- shape it like a
        # validation failure so the UI banner renders cleanly instead
        # of a generic 500.
        msgs = [f"{'.'.join(str(p) for p in err.get('loc', []))}: {err.get('msg','')}" for err in e.errors()]
        return {
            "valid": False,
            "errors": msgs,
            "warnings": [],
            "report": {
                "errors": [
                    {"severity": "error", "code": err.get("type", "validation"),
                     "path": ".".join(str(p) for p in err.get("loc", [])),
                     "message": err.get("msg", "")}
                    for err in e.errors()
                ],
                "warnings": [],
            },
        }

    known_tools, known_apis, _kinds, tool_rels, tool_params = _collect_validation_inputs()
    report = doc.validate_strict(
        known_tools=known_tools or None,
        known_connector_apis=known_apis or None,
        tool_kinds=None,  # builder graphs use a single "main" stage; do not enforce stage/kind alignment.
        tool_relationships=tool_rels or None,
        tool_param_schemas=tool_params or None,
    )

    return {
        "valid": not report.errors,
        "errors": [iss.message for iss in report.errors],
        "warnings": [iss.message for iss in report.warnings],
        "report": report.model_dump(),
    }


@router.post("/journey-builder/save")
async def save_journey(req: BuilderSaveRequest):
    """Persist a JourneyDoc-shaped row in Foundry workspace DDB.

    Pipeline: BuilderState -> JourneyDoc -> validate_strict (errors abort
    with 422) -> journey_store.create. Returns ``{success, journey_id,
    url, yaml, validation_report}``. The legacy ``journey_definition``
    field is preserved for callers that still expect it.
    """
    try:
        doc = _builder_to_journey_doc(req)
    except ValidationError as e:
        # ConnectionDoc / StageDoc / JourneyDoc Pydantic validation
        # surfaced before validate_strict could run. Convert into a
        # structured 422 with the same shape the UI's banner consumes.
        raise HTTPException(
            status_code=422,
            detail={
                "code": "builder_doc_construction_failed",
                "message": "Builder payload did not pass model validation",
                "errors": [
                    {"severity": "error", "path": ".".join(str(p) for p in err.get("loc", [])),
                     "code": err.get("type", "validation"), "message": err.get("msg", "")}
                    for err in e.errors()
                ],
                "warnings": [],
            },
        )

    # Strict validation before persisting; surfacing errors here keeps
    # the DDB free of journeys that reference non-registered tools.
    known_tools, known_apis, _kinds, tool_rels, tool_params = _collect_validation_inputs()
    report = doc.validate_strict(
        known_tools=known_tools or None,
        known_connector_apis=known_apis or None,
        tool_kinds=None,
        tool_relationships=tool_rels or None,
        tool_param_schemas=tool_params or None,
    )
    if report.errors:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "builder_validation_failed",
                "message": "Strict validation rejected the journey",
                "errors": [iss.model_dump() for iss in report.errors],
                "warnings": [iss.model_dump() for iss in report.warnings],
            },
        )

    if _journey_store is None:
        # No DDB wired -- return the YAML to the caller without
        # persistence so dev / unit tests still see the canonical doc.
        doc_dict = doc.model_dump(mode="json")
        return {
            "success": False,
            "journey_id": None,
            "journey_name": _slug(req.name),
            "yaml": yaml.dump(doc_dict, default_flow_style=False, sort_keys=False),
            "validation_report": report.model_dump(),
            "warning": "journey_store not configured; doc returned but not persisted",
        }

    doc_dict = doc.model_dump(mode="json")
    try:
        persisted = await _journey_store.create(doc_dict, user="journey-builder")
    except Exception as e:
        logger.warning(f"journey_store.create failed: {e}")
        raise HTTPException(status_code=500, detail={"code": "save_failed", "message": str(e)})

    journey_id = persisted.get("journey_id") or doc_dict.get("journey_id")
    return {
        "success": True,
        "journey_id": journey_id,
        "journey_name": _slug(req.name),
        "yaml": yaml.dump(doc_dict, default_flow_style=False, sort_keys=False),
        "journey_definition": doc_dict,
        "url": f"/workspace/automation?tab=journeys&id={journey_id}",
        "validation_report": report.model_dump(),
    }


# ============================================================================
# Saved Journey CRUD + run
# ============================================================================


class RunJourneyRequest(BaseModel):
    inputs: Optional[dict] = None


@router.get("/journeys")
async def list_saved_journeys(
    search: str = "",
    kind: Optional[str] = None,
    solution_id: Optional[str] = None,
):
    """List Copilot-saved + user-authored journeys from Foundry workspace DDB."""
    if _journey_store is None:
        return {"journeys": [], "total": 0, "store": "unconfigured"}
    try:
        journeys = await _journey_store.list_all(
            search=search, kind=kind, solution_id=solution_id,
        )
    except Exception as e:
        logger.warning(f"Saved-journeys list failed: {e}")
        return {"journeys": [], "total": 0, "error": str(e)}
    summaries = [
        {
            "journey_id": j.get("journey_id"),
            "title": j.get("title") or j.get("display_name"),
            "kind": j.get("kind"),
            "solution_id": j.get("solution_id"),
            "tags": j.get("tags", []),
            "createdAt": j.get("createdAt"),
            "updatedAt": j.get("updatedAt"),
            "createdBy": j.get("createdBy"),
            "step_count": sum(len(st.get("steps", [])) for st in j.get("stages", [])),
        }
        for j in journeys
    ]
    return {"journeys": summaries, "total": len(summaries)}


@router.get("/journeys/{journey_id}")
async def get_saved_journey(journey_id: str):
    if _journey_store is None:
        raise HTTPException(status_code=503, detail="Journey store not configured")
    journey = await _journey_store.get(journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail=f"Journey not found: {journey_id}")
    yaml_str = yaml.dump(journey, default_flow_style=False, sort_keys=False)
    return {"journey": journey, "yaml": yaml_str}


@router.delete("/journeys/{journey_id}")
async def delete_saved_journey(journey_id: str):
    if _journey_store is None:
        raise HTTPException(status_code=503, detail="Journey store not configured")
    ok = await _journey_store.delete(journey_id)
    return {"success": ok, "journey_id": journey_id}


@router.post("/journeys/{journey_id}/run")
async def run_saved_journey(journey_id: str, req: RunJourneyRequest):
    """Run a saved journey: build a fresh Copilot session from the stored
    JourneyDoc, flatten its stages into the engine plan format, and
    execute. Returns the same envelope as ``/copilot-journey/{id}/execute``.
    """
    _check()
    if _journey_store is None:
        raise HTTPException(status_code=503, detail="Journey store not configured")
    journey = await _journey_store.get(journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail=f"Journey not found: {journey_id}")

    title = journey.get("title") or journey.get("display_name") or journey_id
    session = await _copilot_engine.create_session(f"Run saved journey: {title}")

    plan_steps = []
    idx = 0
    for stage in journey.get("stages", []):
        for step in stage.get("steps", []):
            idx += 1
            params = dict(step.get("params") or {})
            foreach = params.pop("__foreach__", None) or step.get("foreach")
            entry = {
                "id": step.get("step_id") or step.get("id") or f"s{idx}",
                "name": step.get("name") or f"Step {idx}",
                "tool": step.get("tool"),
                "params": params,
                "rationale": step.get("description") or step.get("rationale"),
                "requires_approval": bool(step.get("requires_approval")),
                "use_case_id": journey.get("use_case_id"),
                "stage_id": stage.get("stage_id"),
                "step_id": step.get("step_id"),
            }
            if foreach:
                entry["foreach"] = foreach
            plan_steps.append(entry)

    session.plan = plan_steps
    session.status = "planned"
    session.playbook_context = {
        "use_case": {
            "use_case_id": journey.get("use_case_id"),
            "title": title,
            "solution_id": journey.get("solution_id"),
            "kind": journey.get("kind"),
        },
        "source": "saved_journey",
        "journey_id": journey_id,
    }
    if (req.inputs or None) is not None:
        session.step_results["inputs"] = req.inputs

    # Persist and execute through the same path the Copilot UI uses, so
    # the awaiting_step_approval pause behaves identically and the user
    # can resume via the same /approve-step endpoint.
    _copilot_engine._persist_session(session)
    result = await _copilot_engine.execute_plan(session.session_id)
    # ``result`` already carries ``job_id`` for saved-journey runs (the
    # engine mints it via the JourneyExecutorBridge on first dispatch).
    # Reload from the session in case execute_plan minted it on a
    # branch that didn't include it in the inline response.
    job_id = result.get("job_id") or session.job_id
    return {
        **result,
        "journey_id": journey_id,
        "session_id": session.session_id,
        "job_id": job_id,
    }


@router.post("/journey-builder/run")
async def run_journey(req: BuilderSaveRequest):
    """Dispatch the in-progress builder graph through the YAML Journey
    Runner (the same pipeline the Reasoning > Tools Registry execute
    drawer uses).

    Returns the canonical ``RunEnvelope`` shape:
    ``{run_id, status, step_results, completed_steps, pending_step,
    error}`` so the UI can branch identically on
    ``completed`` / ``awaiting_step_approval`` / ``failed`` without
    knowing whether the journey came from the builder or from a saved
    Copilot run.

    Falls back to the legacy ephemeral-Copilot-session execution when
    the YAML runner has not been wired in (dev / unit tests).
    """
    if _yaml_journey_runner is None:
        _check()
        session = await _copilot_engine.create_session(
            f"Run journey: {req.name}", ""
        )
        session.plan = req.steps
        result = await _copilot_engine.execute_plan(session.session_id)
        return {**result, "journey_name": req.name, "via": "legacy_copilot"}

    try:
        doc = _builder_to_journey_doc(req)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail={"code": "builder_invalid", "message": str(e)})

    envelope = await _yaml_journey_runner.run(
        journey=doc,
        inputs=req.inputs or {},
        user="journey-builder",
    )
    envelope = dict(envelope)
    envelope["journey_name"] = req.name
    envelope["via"] = "yaml_journey_runner"
    return envelope


class BuilderApproveStepRequest(BaseModel):
    """Approve / reject the current pending step in a builder run."""
    step_id: str
    approved: bool = True
    user: Optional[str] = None


@router.get("/journey-builder/tool-outputs")
async def builder_tool_outputs():
    """Return per-tool output-key hints the Journey Builder canvas
    surfaces on each tool node's right-side output ports.

    Hints are documentation-only (the runtime substitution engine is
    dynamic and does not enforce types). See
    :pymod:`src.services.control_plane.tool_output_hints` for the
    catalogue and heuristic defaults.
    """
    from src.services.control_plane.tool_output_hints import build_hints_map
    return {"hints": build_hints_map(_tool_registry)}


@router.get("/journey-builder/tool-relationships")
async def builder_tool_relationships():
    """Return each tool's declared output relationships.

    Phase 1: replaces the per-tool output-key hint catalogue as the
    canonical source of which channels a tool exposes for downstream
    consumption. The UI binds one source handle per relationship.

    Shape: ``{ relationships: { tool_name: [ {name, description, auto_terminate_default}, ... ] } }``.
    Tools registered before Phase 1 surface a single ``success``
    relationship via the default field on :class:`Tool`.
    """
    if _tool_registry is None:
        return {"relationships": {}}

    out: Dict[str, List[Dict[str, Any]]] = {}
    try:
        tools = _tool_registry.list_tools()
    except Exception as e:
        logger.warning(f"tool-relationships list failed: {e}")
        return {"relationships": {}}

    for t in tools:
        rels = getattr(t, "output_relationships", None) or []
        out[t.name] = [
            {
                "name": getattr(r, "name", "success"),
                "description": getattr(r, "description", ""),
                "auto_terminate_default": getattr(r, "auto_terminate_default", False),
            }
            for r in rels
        ]
    return {"relationships": out}


@router.post("/journey-builder/run/{run_id}/approve-step")
async def approve_builder_step(run_id: str, req: BuilderApproveStepRequest):
    """Thin alias of POST /api/v1/yaml-journeys/{run_id}/approve-step.

    Keeps the journey-builder UI on a single namespace and returns the
    same envelope so the resume path is symmetric with /journey-builder/run.
    """
    if _yaml_journey_runner is None:
        raise HTTPException(status_code=503, detail="YAML journey runner not initialized")
    return await _yaml_journey_runner.resume(
        run_id=run_id,
        step_id=req.step_id,
        approved=req.approved,
        user=req.user or "journey-builder",
    )
