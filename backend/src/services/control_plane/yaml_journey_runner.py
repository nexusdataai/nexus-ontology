"""
YAML Journey Runner.

Generic top-level executor for a parsed :class:`JourneyDoc`. Walks
``stages`` (sorted by ``order``) and inside each stage walks ``steps``
(sorted by ``order``); for each step it dispatches the resolved tool
through the live :class:`ToolRegistry`, which already covers both
code-defined tools and DynamoDB-authored dynamic tools.

The runner deliberately mirrors the envelope shape that the AI Copilot
uses (``awaiting_step_approval`` -> resume) so the UI can consume both
paths with one component. Sessions are persisted through
:class:`CopilotSessionStore` (PG-backed when available, in-memory
otherwise) keyed by a generated ``run_id`` and stamped with
``kind='yaml_journey'`` so diagnostics can distinguish them from
Copilot-generated runs.

Single public entrypoint per phase:

  * :meth:`run`     -- validate, create session, execute until a pause
                       or terminal state.
  * :meth:`resume`  -- mark a step approved (or rejected) and continue.
  * :meth:`get`     -- fetch persisted session for inspection.

The runner is dependency-injected with ``tool_registry``,
``policy_engine`` (currently used only to surface BLOCK reasons in the
``pending_step.policy_decision`` payload), ``session_store`` and an
optional ``connector_apis`` module so ``JourneyDoc.validate_strict``
can cross-reference api ids.

Substitution semantics are documented on
:pymod:`src.services.control_plane._param_substitution`.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.models.automation_models import (
    JourneyDoc,
    StageDoc,
    StepDoc,
    ToolBindingDoc,
    ValidationReport,
)
from src.services.control_plane._param_substitution import substitute
from src.services.control_plane.data_queue import (
    DataQueueManager, make_data_queue_manager,
)

yj_logger = logger.bind(component="yaml-journey-runner")

# Status values surfaced to callers; mirrored from copilot_engine.
STATUS_RUNNING = "running"
STATUS_PAUSED = "awaiting_step_approval"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunSession:
    """The full state of one YAML-journey run.

    Persisted as a JSONB blob in ``copilot_sessions`` (or in-memory in
    dev). The runner round-trips this dataclass through
    :meth:`to_dict` / :meth:`from_dict` on every save / load so that
    nested ``JourneyDoc`` rehydration stays explicit.

    ``step_results`` keeps the legacy primary-relationship-only view
    (``{step_id: dict}``) used by every existing consumer (Copilot UI,
    diagnostics, save-as-journey). ``relationship_outputs`` is the
    Phase 1 add: per-step, per-relationship map of payloads, used to
    resolve ``ConnectionDoc`` routing inside the same run.
    """

    run_id: str
    journey: Dict[str, Any]
    inputs: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relationship_outputs: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    completed_step_ids: List[str] = field(default_factory=list)
    approved_steps: List[str] = field(default_factory=list)
    rejected_steps: List[str] = field(default_factory=list)
    pending_step: Optional[Dict[str, Any]] = None
    status: str = STATUS_RUNNING
    error: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    kind: str = "yaml_journey"
    user: str = "ai-engine"
    auto_approve_steps: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["updated_at"] = _now_iso()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunSession":
        # Drop unknown keys so we keep forward-compat with new columns.
        known = {f for f in cls.__dataclass_fields__.keys()}
        clean = {k: v for k, v in (data or {}).items() if k in known}
        return cls(**clean)

    def add_event(self, phase: str, **payload: Any) -> None:
        self.events.append({"phase": phase, "ts": _now_iso(), **payload})


class YamlJourneyRunner:
    """Executes one ``JourneyDoc`` end-to-end with pause/resume support."""

    def __init__(
        self,
        *,
        tool_registry: Any,
        session_store: Any,
        policy_engine: Any = None,
        connector_apis: Any = None,
        data_queue_manager: Optional[DataQueueManager] = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._session_store = session_store
        self._policy_engine = policy_engine
        self._connector_apis = connector_apis
        # Phase 1 of the Data Queues plan: the runner routes producer
        # outputs / consumer inputs through a DataQueueManager. Default
        # backend is InMemory which is semantically identical to today's
        # ``relationship_outputs`` dict.
        self._data_queue: DataQueueManager = data_queue_manager or make_data_queue_manager()

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    async def run(
        self,
        *,
        journey: JourneyDoc,
        inputs: Optional[Dict[str, Any]] = None,
        user: str = "ai-engine",
        run_id: Optional[str] = None,
        auto_approve_steps: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate ``journey``, persist a fresh session, execute until pause / terminal."""
        report = self._validate(journey)
        if report.errors:
            return {
                "run_id": None,
                "status": STATUS_FAILED,
                "step_results": {},
                "completed_steps": [],
                "pending_step": None,
                "error": "journey failed validation",
                "validation_report": report.model_dump(),
            }

        run_id = run_id or f"YJ-{uuid.uuid4().hex[:12]}"
        session = RunSession(
            run_id=run_id,
            journey=journey.model_dump(mode="json"),
            inputs=inputs or {},
            user=user,
            auto_approve_steps=list(auto_approve_steps or []),
            approved_steps=list(auto_approve_steps or []),
        )
        session.add_event(
            "started",
            journey_id=journey.get_journey_id(),
            stages=len(journey.stages),
        )
        self._save(session)

        return await self._run_loop(session, validation_report=report)

    async def resume(
        self,
        *,
        run_id: str,
        step_id: str,
        approved: bool,
        user: str = "ai-engine",
    ) -> Dict[str, Any]:
        """Approve (or reject) the pending step and continue execution."""
        session = self._load(run_id)
        if session is None:
            return {
                "run_id": run_id,
                "status": STATUS_FAILED,
                "step_results": {},
                "completed_steps": [],
                "pending_step": None,
                "error": "run not found",
            }
        if session.status not in (STATUS_PAUSED, STATUS_RUNNING):
            return self._envelope(session)

        if approved:
            if step_id not in session.approved_steps:
                session.approved_steps.append(step_id)
            session.add_event("step_approved", step_id=step_id, user=user)
        else:
            if step_id not in session.rejected_steps:
                session.rejected_steps.append(step_id)
            session.add_event("step_rejected", step_id=step_id, user=user)
            session.status = STATUS_FAILED
            session.error = f"step '{step_id}' rejected by {user}"
            session.pending_step = None
            self._save(session)
            return self._envelope(session)

        session.pending_step = None
        session.status = STATUS_RUNNING
        self._save(session)
        return await self._run_loop(session)

    def get(self, run_id: str) -> Optional[RunSession]:
        """Return the persisted session for inspection (or ``None``)."""
        return self._load(run_id)

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent YAML-journey runs, filtering ``copilot_sessions`` by ``kind``."""
        try:
            rows = self._session_store.list_recent(limit=limit * 2)
        except Exception as e:
            yj_logger.warning(f"session_store.list_recent failed: {e}")
            return []
        out: List[Dict[str, Any]] = []
        for row in rows:
            if row.get("kind") != "yaml_journey":
                continue
            out.append({
                "run_id": row.get("run_id"),
                "status": row.get("status"),
                "user": row.get("user"),
                "journey_id": (row.get("journey") or {}).get("journey_id")
                              or (row.get("journey") or {}).get("use_case_id"),
                "completed_steps": row.get("completed_step_ids") or [],
                "pending_step": row.get("pending_step"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at") or row.get("_updated_at"),
                "error": row.get("error"),
            })
            if len(out) >= limit:
                break
        return out

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate(self, journey: JourneyDoc) -> ValidationReport:
        """Cross-reference the journey against live registries."""
        known_tools: set = set()
        tool_kinds: Dict[str, str] = {}
        tool_relationships: Dict[str, List[str]] = {}
        tool_param_schemas: Dict[str, Dict[str, Any]] = {}
        try:
            for t in self._tool_registry.list_tools():
                known_tools.add(t.name)
                kind = getattr(t, "tool_kind", None)
                if not kind:
                    # Heuristic mirror of Tool.effective_tool_kind for tools
                    # registered before the explicit field landed.
                    if getattr(t, "connector_api", None):
                        kind = "mutate"
                    else:
                        risk = getattr(t, "risk_level", None)
                        risk_v = getattr(risk, "value", None) or str(risk or "")
                        kind = "read" if risk_v == "read_only" else "analyze"
                tool_kinds[t.name] = kind
                # Phase 1: surface relationship + param-schema info so
                # validate_strict can check ConnectionDocs.
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
            yj_logger.warning(f"registry.list_tools failed: {e}")

        known_apis: set = set()
        if self._connector_apis is not None:
            try:
                known_apis = {s.api_id for s in self._connector_apis.list_all()}
            except Exception as e:
                yj_logger.warning(f"connector_apis.list_all failed: {e}")

        report = journey.validate_strict(
            known_tools=known_tools or None,
            known_connector_apis=known_apis or None,
            tool_kinds=tool_kinds or None,
            tool_relationships=tool_relationships or None,
            tool_param_schemas=tool_param_schemas or None,
        )

        # validate_strict's unknown_tool check is skipped when known_tools
        # is empty (it treats an empty set as "no info"). Catch the
        # genuinely-empty-registry case ourselves by walking every binding
        # against the live set; dedup against errors already recorded.
        already = {iss.path for iss in report.errors if iss.code == "unknown_tool"}
        for stage_idx, stage in enumerate(journey.stages):
            for step_idx, step in enumerate(stage.steps):
                for b_idx, b in enumerate(step.effective_bindings()):
                    if b.tool in known_tools:
                        continue
                    path = f"stages[{stage_idx}].steps[{step_idx}].bindings[{b_idx}]"
                    if path in already:
                        continue
                    report.add_error(
                        path, "unknown_tool",
                        f"Tool '{b.tool}' is not registered in ToolRegistry",
                    )
        return report

    async def _run_loop(
        self,
        session: RunSession,
        *,
        validation_report: Optional[ValidationReport] = None,
    ) -> Dict[str, Any]:
        """Walk stages -> steps, dispatching tools until pause / completion."""
        try:
            journey = JourneyDoc.model_validate(session.journey)
        except Exception as e:
            session.status = STATUS_FAILED
            session.error = f"journey rehydrate failed: {e}"
            self._save(session)
            return self._envelope(session, validation_report=validation_report)

        for stage in sorted(journey.stages, key=lambda s: s.order):
            terminal = await self._run_stage(session, stage)
            if terminal:
                return self._envelope(session, validation_report=validation_report)

        session.status = STATUS_COMPLETED
        session.pending_step = None
        session.add_event("completed", step_count=len(session.completed_step_ids))
        self._save(session)
        # Phase 1 (Data Queues): release queue state for this run so
        # the InMemory backend doesn't accumulate per-run dicts.
        try:
            await self._data_queue.reset_run(session.run_id)
        except Exception as e:
            yj_logger.warning(f"data-queue reset failed for run {session.run_id}: {e}")
        return self._envelope(session, validation_report=validation_report)

    async def _run_stage(self, session: RunSession, stage: StageDoc) -> bool:
        """Execute every step in ``stage``. Returns ``True`` on a terminal pause/fail."""
        for step in sorted(stage.steps, key=lambda s: s.order):
            if step.step_id in session.completed_step_ids:
                continue
            if step.step_id in session.rejected_steps:
                session.status = STATUS_FAILED
                session.error = f"step '{step.step_id}' previously rejected"
                self._save(session)
                return True

            binding = self._resolve_binding(step)
            if binding is None:
                # LLM-only "decide" step: nothing to dispatch.
                session.step_results[step.step_id] = {"kind": "decide", "skipped": True}
                session.completed_step_ids.append(step.step_id)
                session.add_event("step_skipped", step_id=step.step_id, reason="no_tool_binding")
                self._save(session)
                continue

            if step.requires_approval and step.step_id not in session.approved_steps:
                session.pending_step = {
                    "step_id": step.step_id,
                    "stage_id": stage.stage_id,
                    "tool": binding.tool,
                    "params_preview": self._preview(self._merge_params(step, binding)),
                }
                session.status = STATUS_PAUSED
                session.add_event(
                    "awaiting_step_approval",
                    step_id=step.step_id,
                    tool=binding.tool,
                )
                self._save(session)
                return True

            terminal = await self._dispatch_step(
                session, stage=stage, step=step, binding=binding,
            )
            if terminal:
                return True
        return False

    async def _dispatch_step(
        self,
        session: RunSession,
        *,
        stage: StageDoc,
        step: StepDoc,
        binding: ToolBindingDoc,
    ) -> bool:
        """Resolve params, call the tool, capture or fail.

        Param resolution order (Phase 1):
          1. Start from the merged ``step.params`` + ``binding.params``.
          2. For every :class:`ConnectionDoc` in ``stage.connections``
             whose ``to_step == step.step_id``, look up the producer's
             relationship output in ``session.relationship_outputs``,
             resolve ``from_path`` against it, and overwrite the
             corresponding ``to_param``. (Single-producer-per-port is
             enforced by validate_strict.)
          3. Run the legacy substitution pass (``${steps.X.y}``) over
             whatever remains, against ``session.step_results``. This
             is the back-compat fallback for journeys authored before
             Phase 1.

        Returns ``True`` if a terminal state was reached (failure) so
        the caller stops iterating.
        """
        # Sequential mode: skip ConnectionDoc routing AND omit the
        # ``steps`` namespace from the substitution context so any
        # ``${steps.X.y}`` placeholder (which validate_strict already
        # rejects at save time) cannot resolve at runtime either.
        execution_mode = (session.journey.get("execution_mode") or "dataflow")
        is_sequential = execution_mode == "sequential"

        if is_sequential:
            ctx = {
                "inputs": session.inputs,
                "params": session.inputs,
                "journey": session.inputs,
                "context": {"run_id": session.run_id, "user": session.user},
            }
        else:
            ctx = {
                "steps": session.step_results,
                "inputs": session.inputs,
                "params": session.inputs,
                "journey": session.inputs,
                "context": {"run_id": session.run_id, "user": session.user},
            }
        try:
            params = self._merge_params(step, binding)
            if not is_sequential:
                # ConnectionDoc routing -- dataflow primary path.
                await self._apply_connections(params, session=session, stage=stage, step=step)
            # Substitution: dataflow uses the full ctx; sequential uses
            # the steps-free ctx so legacy placeholders cannot resolve.
            params = substitute(params, ctx=ctx)
        except Exception as e:
            session.status = STATUS_FAILED
            session.error = f"param resolution failed for step '{step.step_id}': {e}"
            self._save(session)
            return True

        session.add_event("step_started", step_id=step.step_id, tool=binding.tool)

        try:
            results = await self._tool_registry.execute_with_relationships(binding.tool, params)
        except Exception as e:
            return self._handle_step_failure(
                session, step, binding, error=f"tool raised: {e}",
            )

        # If the registry surfaced a "failure" relationship as the only
        # output (missing tool / coroutine raised), treat it as a fail.
        if results and len(results) == 1 and results[0].relationship == "failure":
            err = results[0].data.get("error") if isinstance(results[0].data, dict) else None
            return self._handle_step_failure(
                session, step, binding,
                error=str(err) if err else "tool failed", partial=results[0].data,
            )

        # Preserve back-compat for ``step_results`` (primary channel only).
        if results:
            primary_data = results[0].data
            if isinstance(primary_data, dict) and "error" in primary_data:
                return self._handle_step_failure(
                    session, step, binding,
                    error=str(primary_data["error"]), partial=primary_data,
                )
            session.step_results[step.step_id] = primary_data if isinstance(primary_data, dict) else {"value": primary_data}

        # Record per-relationship outputs so downstream ConnectionDocs
        # can route by name.
        per_rel: Dict[str, Dict[str, Any]] = {}
        for r in results:
            data = r.data if isinstance(r.data, dict) else {"value": r.data}
            per_rel[r.relationship] = data
        session.relationship_outputs[step.step_id] = per_rel

        # Phase 1 (Data Queues): enqueue the producer's payloads onto
        # every outbound queue declared by ConnectionDocs in this
        # stage. The InMemory backend mirrors the dict snapshot above
        # so the consumer-side _apply_connections fallback path keeps
        # working identically to today. Failure-channel emissions are
        # NOT enqueued (they're surfaced as step failures upstream).
        try:
            await self._enqueue_outbound(session, stage=stage, step=step, per_rel=per_rel)
        except Exception as e:
            # Queue enqueue failure must not derail the journey -- the
            # dict snapshot above still satisfies consumers via the
            # fallback in _apply_connections.
            yj_logger.warning(
                f"data-queue enqueue failed for step '{step.step_id}': {e}",
            )

        session.completed_step_ids.append(step.step_id)
        session.add_event(
            "step_completed",
            step_id=step.step_id,
            tool=binding.tool,
            relationships=[r.relationship for r in results],
            result_preview=self._preview(session.step_results.get(step.step_id) or {}),
        )
        self._save(session)
        return False

    # ------------------------------------------------------------------

    async def _enqueue_outbound(
        self,
        session: RunSession,
        *,
        stage: StageDoc,
        step: StepDoc,
        per_rel: Dict[str, Dict[str, Any]],
    ) -> None:
        """Push each emitted relationship payload onto its outbound queue.

        Phase 1: best-effort. The dict snapshot in
        ``session.relationship_outputs`` is the authoritative source
        for consumers; the queue is an additive parallel channel that
        future phases will rely on for back-pressure / streaming /
        durability.
        """
        for conn in stage.connections:
            if conn.from_step != step.step_id:
                continue
            payload = per_rel.get(conn.from_relationship)
            if payload is None:
                continue
            await self._data_queue.enqueue(
                run_id=session.run_id, conn=conn, payload=payload,
            )

    async def _apply_connections(
        self,
        params: Dict[str, Any],
        *,
        session: RunSession,
        stage: StageDoc,
        step: StepDoc,
    ) -> None:
        """Overwrite ``params`` keys driven by ConnectionDocs.

        For every ConnectionDoc whose ``to_step`` is the current step,
        prefer the data-queue (Phase 1) and fall back to the
        per-relationship dict snapshot. Connections targeting a
        producer that has not yet emitted leave the param untouched so
        the legacy substitution / literal fallback can still resolve it.

        The queue is async; the dict fallback is sync. We try the queue
        first with a zero-timeout dequeue (non-blocking); when empty we
        consult the snapshot. This means InMemory backend never blocks
        in Phase 1 -- it behaves identically to the snapshot path.
        """
        for conn in stage.connections:
            if conn.to_step != step.step_id:
                continue

            # Phase 1: try the queue first (non-blocking).
            payload: Any = None
            try:
                item = await self._data_queue.dequeue(
                    run_id=session.run_id, conn=conn, consumer=step.step_id, block_ms=0,
                )
                if item is not None:
                    payload = item.payload
                    # Phase 1 ack-eagerly so the InMemory backend's
                    # ``pending`` slot frees up. Phase 4 will switch
                    # to ack-on-step-commit for crash recovery.
                    await self._data_queue.ack(
                        run_id=session.run_id, conn=conn,
                        consumer=step.step_id, item_id=item.item_id,
                    )
            except Exception as e:
                yj_logger.warning(
                    f"data-queue dequeue failed for step '{step.step_id}' "
                    f"<- {conn.from_step}.{conn.from_relationship}: {e}",
                )

            # Snapshot fallback for legacy sessions / queue misses.
            if payload is None:
                rel_map = session.relationship_outputs.get(conn.from_step)
                if rel_map is None:
                    continue
                payload = rel_map.get(conn.from_relationship)
                if payload is None:
                    continue

            value = self._resolve_path(payload, conn.from_path) if conn.from_path else payload
            # ``_resolve_path`` returns None when a segment is missing.
            # Treat that as "no value to inject" so the consumer keeps
            # whatever literal sits in step.params for that key.
            if value is None:
                continue
            params[conn.to_param] = value

    @staticmethod
    def _resolve_path(payload: Any, path: str) -> Any:
        """Resolve a dotted / indexed accessor against a JSON-shaped payload.

        Supports keys (``results.foo.bar``) and integer indices
        (``results.0.customer_id``). Returns ``None`` if any segment
        is unresolvable rather than raising, so a missing intermediate
        key cascades into a "literal fallback" rather than a hard fail.
        """
        if path in (None, ""):
            return payload
        node: Any = payload
        for segment in path.split("."):
            if node is None:
                return None
            if isinstance(node, list):
                try:
                    idx = int(segment)
                except ValueError:
                    return None
                if 0 <= idx < len(node):
                    node = node[idx]
                else:
                    return None
            elif isinstance(node, dict):
                node = node.get(segment)
            else:
                return None
        return node

    def _handle_step_failure(
        self,
        session: RunSession,
        step: StepDoc,
        binding: ToolBindingDoc,
        *,
        error: str,
        partial: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Treat a step error per the (currently single-mode) on_error policy.

        StepDoc has no ``on_error`` field today, so the behaviour is the
        plan's default: ``fail`` -- record error + set terminal status.
        """
        session.step_results[step.step_id] = {
            "tool": binding.tool, "error": error, "partial": partial,
        }
        session.status = STATUS_FAILED
        session.error = f"step '{step.step_id}' ({binding.tool}): {error}"
        session.add_event("step_failed", step_id=step.step_id, tool=binding.tool, error=error)
        self._save(session)
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_binding(step: StepDoc) -> Optional[ToolBindingDoc]:
        bindings = step.effective_bindings()
        return bindings[0] if bindings else None

    @staticmethod
    def _merge_params(step: StepDoc, binding: ToolBindingDoc) -> Dict[str, Any]:
        """Merge step.params with binding.params, binding wins on conflict."""
        merged: Dict[str, Any] = dict(step.params or {})
        merged.update(binding.params or {})
        return merged

    @staticmethod
    def _preview(payload: Any) -> Any:
        """Cheap preview for envelopes and event logs."""
        if isinstance(payload, dict):
            keys = list(payload.keys())[:8]
            return {k: YamlJourneyRunner._preview(payload[k]) for k in keys}
        if isinstance(payload, list):
            return f"<list len={len(payload)}>"
        if isinstance(payload, str) and len(payload) > 200:
            return payload[:197] + "..."
        return payload

    def _envelope(
        self,
        session: RunSession,
        *,
        validation_report: Optional[ValidationReport] = None,
    ) -> Dict[str, Any]:
        """Shape the public response. Mirrors copilot_engine.execute_plan."""
        env: Dict[str, Any] = {
            "run_id": session.run_id,
            "status": session.status,
            "step_results": session.step_results,
            "completed_steps": list(session.completed_step_ids),
            "pending_step": session.pending_step,
            "error": session.error,
            "kind": session.kind,
            "user": session.user,
            "updated_at": session.updated_at,
        }
        if validation_report is not None and (validation_report.warnings or validation_report.errors):
            env["validation_report"] = validation_report.model_dump()
        return env

    # ------------------------------------------------------------------
    # Store adapters (the store API is sync but tolerates concurrent use)
    # ------------------------------------------------------------------

    def _save(self, session: RunSession) -> None:
        try:
            self._session_store.save(session.run_id, session.to_dict())
        except Exception as e:
            yj_logger.warning(f"session_store.save failed for {session.run_id}: {e}")

    def _load(self, run_id: str) -> Optional[RunSession]:
        try:
            data = self._session_store.load(run_id)
        except Exception as e:
            yj_logger.warning(f"session_store.load failed for {run_id}: {e}")
            return None
        if not data:
            return None
        try:
            return RunSession.from_dict(data)
        except Exception as e:
            yj_logger.warning(f"RunSession.from_dict failed for {run_id}: {e}")
            return None
