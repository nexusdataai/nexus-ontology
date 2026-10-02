"""
Unit tests for :pymod:`src.services.control_plane.yaml_journey_runner`.

The runner is exercised against a hand-rolled in-memory ToolRegistry +
session store. No DB, no FastAPI, no real CopilotSessionStore needed -
the store contract is just ``save / load / list_recent``.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.models.automation_models import JourneyDoc
from src.services.control_plane.tool_registry import RelationshipResult
from src.services.control_plane.yaml_journey_runner import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PAUSED,
    YamlJourneyRunner,
)


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubTool:
    def __init__(self, name: str, risk_level: str = "read_only",
                 tool_kind: str = "read", connector_api: Optional[str] = None,
                 result: Optional[Dict[str, Any]] = None,
                 raises: Optional[Exception] = None,
                 # Phase 1 -- per-relationship results for fan-out tests.
                 relationship_results: Optional[List[RelationshipResult]] = None,
                 output_relationships: Optional[List[str]] = None):
        self.name = name
        self.risk_level = risk_level
        self.tool_kind = tool_kind
        self.connector_api = connector_api
        self.parameters = {"type": "object", "properties": {}, "required": []}
        self._result = result if result is not None else {"ok": True, "tool": name}
        self._raises = raises
        self._relationship_results = relationship_results
        self._declared_relationships = output_relationships or ["success"]
        self.calls: List[Dict[str, Any]] = []

    def relationship_names(self) -> List[str]:
        return list(self._declared_relationships)

    async def execute(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._raises:
            raise self._raises
        if self._relationship_results is not None:
            return list(self._relationship_results)
        return dict(self._result)


class _StubRegistry:
    def __init__(self, tools: List[_StubTool]):
        self._tools = {t.name: t for t in tools}

    def list_tools(self) -> List[_StubTool]:
        return list(self._tools.values())

    def get(self, name: str) -> Optional[_StubTool]:
        return self._tools.get(name)

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"Tool '{name}' not found"}
        try:
            return await tool.execute(**arguments)
        except Exception as e:
            return {"error": str(e)}

    async def execute_with_relationships(
        self, name: str, arguments: Dict[str, Any],
    ) -> List[RelationshipResult]:
        tool = self._tools.get(name)
        if tool is None:
            return [RelationshipResult(relationship="failure",
                                       data={"error": f"Tool '{name}' not found"})]
        try:
            raw = await tool.execute(**arguments)
        except Exception as e:
            return [RelationshipResult(relationship="failure", data={"error": str(e)})]

        if isinstance(raw, list):
            return [r if isinstance(r, RelationshipResult)
                    else RelationshipResult(relationship="success", data=r)
                    for r in raw]
        if isinstance(raw, RelationshipResult):
            return [raw]
        if isinstance(raw, dict):
            primary = tool._declared_relationships[0] if tool._declared_relationships else "success"
            return [RelationshipResult(relationship=primary, data=raw)]
        return [RelationshipResult(relationship="success", data={"value": raw})]


class _MemStore:
    def __init__(self) -> None:
        self.data: Dict[str, Dict[str, Any]] = {}

    def save(self, k: str, v: Dict[str, Any]) -> None:
        self.data[k] = dict(v)

    def load(self, k: str) -> Optional[Dict[str, Any]]:
        return self.data.get(k)

    def delete(self, k: str) -> None:
        self.data.pop(k, None)

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self.data.values())[-limit:]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _journey(stages: List[Dict[str, Any]], *, journey_id: str = "test.j1") -> JourneyDoc:
    return JourneyDoc.model_validate({
        "use_case_id": journey_id,
        "journey_id": journey_id,
        "title": "Test Journey",
        "solution_id": "order-to-cash",
        "description": "unit test",
        "stages": stages,
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_threads_results_between_steps():
    """step1 result is referenced by step2 via ${steps.step1.X}."""
    registry = _StubRegistry([
        _StubTool("query_inventory", result={"count": 42, "rows": [{"sku": "A"}]}),
        _StubTool("log_count", result={"logged": True}),
    ])
    runner = YamlJourneyRunner(tool_registry=registry, session_store=_MemStore())

    journey = _journey([{
        "stage_id": "resolve", "name": "Resolve", "order": 1,
        "steps": [
            {"step_id": "step1", "name": "S1", "order": 1, "tool": "query_inventory"},
            {"step_id": "step2", "name": "S2", "order": 2, "tool": "log_count",
             "params": {"count": "${steps.step1.count}", "first_sku": "{{ steps.step1.rows.0.sku }}"}},
        ],
    }])

    env = await runner.run(journey=journey, inputs={})
    assert env["status"] == STATUS_COMPLETED
    assert env["completed_steps"] == ["step1", "step2"]
    # step2 received the resolved values, with integer preserved (whole-string placeholder).
    call = registry.get("log_count").calls[0]
    assert call == {"count": 42, "first_sku": "A"}


@pytest.mark.asyncio
async def test_approval_pause_returns_envelope_and_persists_session():
    """A high-risk step with requires_approval=true pauses with the envelope."""
    registry = _StubRegistry([
        _StubTool("place_credit_hold", risk_level="high_risk_write",
                  tool_kind="mutate", connector_api="sfdc.account.credit_hold.set"),
    ])
    store = _MemStore()
    runner = YamlJourneyRunner(tool_registry=registry, session_store=store)

    journey = _journey([{
        "stage_id": "act", "name": "Act", "order": 1,
        "steps": [
            {"step_id": "approve_me", "name": "Approve me", "order": 1,
             "tool": "place_credit_hold", "requires_approval": True,
             "params": {"account_id": "A-1"}},
        ],
    }])

    env = await runner.run(journey=journey)
    assert env["status"] == STATUS_PAUSED
    assert env["pending_step"]["step_id"] == "approve_me"
    assert env["pending_step"]["tool"] == "place_credit_hold"
    assert env["completed_steps"] == []
    # The tool must NOT have been invoked yet.
    assert registry.get("place_credit_hold").calls == []
    # Persisted under the right run_id.
    saved = store.load(env["run_id"])
    assert saved is not None
    assert saved["status"] == STATUS_PAUSED


@pytest.mark.asyncio
async def test_resume_completes_after_approval():
    """After approve-step, the runner resumes and reaches completion."""
    registry = _StubRegistry([
        _StubTool("place_credit_hold", risk_level="high_risk_write",
                  tool_kind="mutate", connector_api="sfdc.account.credit_hold.set"),
    ])
    runner = YamlJourneyRunner(tool_registry=registry, session_store=_MemStore())

    journey = _journey([{
        "stage_id": "act", "name": "Act", "order": 1,
        "steps": [
            {"step_id": "approve_me", "name": "Approve me", "order": 1,
             "tool": "place_credit_hold", "requires_approval": True,
             "params": {"account_id": "A-1"}},
        ],
    }])

    paused = await runner.run(journey=journey)
    run_id = paused["run_id"]
    resumed = await runner.resume(run_id=run_id, step_id="approve_me", approved=True)
    assert resumed["status"] == STATUS_COMPLETED
    assert resumed["completed_steps"] == ["approve_me"]
    assert resumed["pending_step"] is None
    assert registry.get("place_credit_hold").calls == [{"account_id": "A-1"}]


@pytest.mark.asyncio
async def test_validation_failure_blocks_run():
    """Unregistered tool name returns errored envelope and never starts a session."""
    registry = _StubRegistry([])
    store = _MemStore()
    runner = YamlJourneyRunner(tool_registry=registry, session_store=store)

    journey = _journey([{
        "stage_id": "resolve", "name": "R", "order": 1,
        "steps": [{"step_id": "step1", "name": "S1", "order": 1, "tool": "does_not_exist"}],
    }])

    env = await runner.run(journey=journey)
    assert env["status"] == STATUS_FAILED
    assert env["run_id"] is None
    assert "validation_report" in env
    codes = {iss["code"] for iss in env["validation_report"]["errors"]}
    assert "unknown_tool" in codes
    assert store.data == {}  # no session persisted


@pytest.mark.asyncio
async def test_tool_error_aborts_and_records_partial():
    """A tool returning {"error": ...} fails the run and records the partial result."""
    registry = _StubRegistry([
        _StubTool("flaky_tool", result={"error": "boom", "partial_field": "x"}),
    ])
    runner = YamlJourneyRunner(tool_registry=registry, session_store=_MemStore())

    journey = _journey([{
        "stage_id": "resolve", "name": "R", "order": 1,
        "steps": [{"step_id": "step1", "name": "S1", "order": 1, "tool": "flaky_tool"}],
    }])

    env = await runner.run(journey=journey)
    assert env["status"] == STATUS_FAILED
    assert env["completed_steps"] == []
    assert "boom" in (env["error"] or "")
    assert env["step_results"]["step1"]["error"] == "boom"


@pytest.mark.asyncio
async def test_substitution_namespaces_steps_inputs_context_both_syntaxes():
    """Both {{ }} and ${ } work; inputs / steps / context all resolve."""
    captured: Dict[str, Any] = {}

    class _CaptureTool(_StubTool):
        async def execute(self, **kwargs: Any) -> Dict[str, Any]:
            captured.update(kwargs)
            return {"ok": True, "echo": kwargs}

    registry = _StubRegistry([
        _StubTool("seed", result={"value": "hello", "list": [1, 2, 3]}),
        _CaptureTool("capture"),
    ])
    runner = YamlJourneyRunner(tool_registry=registry, session_store=_MemStore())

    journey = _journey([{
        "stage_id": "resolve", "name": "R", "order": 1,
        "steps": [
            {"step_id": "seed", "name": "Seed", "order": 1, "tool": "seed"},
            {"step_id": "capture", "name": "Capture", "order": 2, "tool": "capture", "params": {
                "from_step_brace":  "{{ steps.seed.value }}",
                "from_step_dollar": "${steps.seed.value}",
                "from_stage_alias": "${stage.resolve.seed.value}",
                "from_input":       "{{ inputs.who }}",
                "from_context":     "${context.run_id}",
                "raw_list":         "${steps.seed.list}",
                "interpolated":     "run-${context.run_id} (${inputs.who})",
            }},
        ],
    }])

    env = await runner.run(journey=journey, inputs={"who": "alice"})
    assert env["status"] == STATUS_COMPLETED
    assert captured["from_step_brace"] == "hello"
    assert captured["from_step_dollar"] == "hello"
    assert captured["from_stage_alias"] == "hello"
    assert captured["from_input"] == "alice"
    assert captured["from_context"].startswith("YJ-")
    assert captured["raw_list"] == [1, 2, 3]
    assert "alice" in captured["interpolated"]


@pytest.mark.asyncio
async def test_get_and_list_recent_filter_by_kind():
    registry = _StubRegistry([_StubTool("noop", result={"ok": True})])
    runner = YamlJourneyRunner(tool_registry=registry, session_store=_MemStore())

    journey = _journey([{
        "stage_id": "resolve", "name": "R", "order": 1,
        "steps": [{"step_id": "step1", "name": "S1", "order": 1, "tool": "noop"}],
    }])
    env = await runner.run(journey=journey)
    run_id = env["run_id"]

    session = runner.get(run_id)
    assert session is not None
    assert session.run_id == run_id
    assert session.kind == "yaml_journey"

    listed = runner.list_recent()
    assert any(r["run_id"] == run_id for r in listed)


# ---------------------------------------------------------------------------
# Phase 1 -- ConnectionDoc routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connection_doc_routes_relationship_into_consumer_param():
    """Producer emits ``matched`` on its sole relationship; consumer
    receives the routed value via ConnectionDoc.from_path.
    """
    producer = _StubTool(
        "find_things",
        output_relationships=["matched", "no_match"],
        relationship_results=[
            RelationshipResult(relationship="matched", data={"results": [{"customer_id": "ACC-1001"}]}),
            RelationshipResult(relationship="no_match", data={"reason": "empty"}),
        ],
    )
    consumer = _StubTool("consume_thing", output_relationships=["success"])
    consumer.parameters = {
        "type": "object",
        "properties": {"customer_id": {"type": "string"}},
        "required": ["customer_id"],
    }
    registry = _StubRegistry([producer, consumer])
    runner = YamlJourneyRunner(tool_registry=registry, session_store=_MemStore())

    journey = _journey([{
        "stage_id": "resolve", "name": "R", "order": 1,
        "steps": [
            {"step_id": "s1", "name": "S1", "order": 1, "tool": "find_things"},
            {"step_id": "s2", "name": "S2", "order": 2, "tool": "consume_thing"},
        ],
        "connections": [
            {
                "from_step": "s1", "from_relationship": "matched",
                "from_path": "results.0.customer_id",
                "to_step": "s2", "to_param": "customer_id",
            },
        ],
    }])

    env = await runner.run(journey=journey)
    assert env["status"] == STATUS_COMPLETED, env
    assert env["completed_steps"] == ["s1", "s2"]
    # The consumer received the routed value.
    assert registry.get("consume_thing").calls == [{"customer_id": "ACC-1001"}]


@pytest.mark.asyncio
async def test_connection_doc_overrides_literal_param():
    """A literal ``customer_id`` in step.params is overridden by an
    incoming ConnectionDoc -- mirrors NiFi semantics where a wire wins
    over a hand-typed value.
    """
    producer = _StubTool("p", result={"customer_id": "FROM-WIRE"})
    consumer = _StubTool("c")
    consumer.parameters = {"type": "object", "properties": {"customer_id": {"type": "string"}}}
    registry = _StubRegistry([producer, consumer])
    runner = YamlJourneyRunner(tool_registry=registry, session_store=_MemStore())

    journey = _journey([{
        "stage_id": "resolve", "name": "R", "order": 1,
        "steps": [
            {"step_id": "s1", "name": "S1", "order": 1, "tool": "p"},
            {"step_id": "s2", "name": "S2", "order": 2, "tool": "c",
             "params": {"customer_id": "LITERAL"}},
        ],
        "connections": [
            {"from_step": "s1", "from_relationship": "success",
             "from_path": "customer_id",
             "to_step": "s2", "to_param": "customer_id"},
        ],
    }])

    env = await runner.run(journey=journey)
    assert env["status"] == STATUS_COMPLETED, env
    assert registry.get("c").calls[0]["customer_id"] == "FROM-WIRE"


@pytest.mark.asyncio
async def test_connection_doc_missing_path_falls_back_to_literal():
    """If from_path resolves to None, the consumer keeps whatever literal
    was in step.params (no override). This is the safety net that lets
    half-wired journeys still run end-to-end without crashing on a
    missing-segment KeyError.
    """
    producer = _StubTool("p", result={"only_this": "x"})
    consumer = _StubTool("c")
    consumer.parameters = {"type": "object", "properties": {"customer_id": {"type": "string"}}}
    registry = _StubRegistry([producer, consumer])
    runner = YamlJourneyRunner(tool_registry=registry, session_store=_MemStore())

    journey = _journey([{
        "stage_id": "resolve", "name": "R", "order": 1,
        "steps": [
            {"step_id": "s1", "name": "S1", "order": 1, "tool": "p"},
            {"step_id": "s2", "name": "S2", "order": 2, "tool": "c",
             "params": {"customer_id": "LITERAL_DEFAULT"}},
        ],
        "connections": [
            {"from_step": "s1", "from_relationship": "success",
             "from_path": "this.path.does.not.exist",
             "to_step": "s2", "to_param": "customer_id"},
        ],
    }])

    env = await runner.run(journey=journey)
    assert env["status"] == STATUS_COMPLETED, env
    # No override happened; literal preserved.
    assert registry.get("c").calls[0]["customer_id"] == "LITERAL_DEFAULT"


# ---------------------------------------------------------------------------
# Execution mode -- sequential vs dataflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sequential_mode_skips_connection_routing():
    """A journey tagged sequential must not invoke _apply_connections,
    even when stage.connections is somehow present. The runner walks
    steps strictly by order; the producer's relationship_outputs are
    NOT injected into the consumer's params.
    """
    producer = _StubTool("seed", result={"customer_id": "WIRED"})
    captured: Dict[str, Any] = {}

    class _CaptureTool(_StubTool):
        async def execute(self, **kwargs):  # type: ignore[override]
            self.calls.append(kwargs)
            captured.update(kwargs)
            return {"received": True}

    registry = _StubRegistry([producer, _CaptureTool("downstream")])
    runner = YamlJourneyRunner(tool_registry=registry, session_store=_MemStore())

    # Hand-craft a journey-dict that bypasses validate_strict (which
    # would otherwise reject a sequential journey carrying a
    # ConnectionDoc). We construct the JourneyDoc directly so the
    # runner sees a sequential journey whose stage has a leftover
    # ConnectionDoc -- proving the runner's branch is what protects
    # us, not just the validator.
    from src.models.automation_models import (
        ConnectionDoc, JourneyDoc, StageDoc, StepDoc,
    )
    journey = JourneyDoc(
        use_case_id="seq.skip",
        journey_id="seq.skip",
        title="Sequential skip test",
        solution_id="builder",
        execution_mode="sequential",
        stages=[StageDoc(
            stage_id="main", name="Main", order=1,
            steps=[
                StepDoc(step_id="seed", name="Seed", order=1, tool="seed"),
                StepDoc(step_id="downstream", name="Down", order=2,
                        tool="downstream", params={"customer_id": "LITERAL"}),
            ],
            connections=[ConnectionDoc(
                from_step="seed", from_relationship="success",
                from_path="customer_id",
                to_step="downstream", to_param="customer_id",
            )],
        )],
    )

    # The runner's _validate would reject this, so we step around it
    # by calling _run_loop directly with a pre-seeded session.
    from src.services.control_plane.yaml_journey_runner import RunSession
    session = RunSession(
        run_id="YJ-seq-test", journey=journey.model_dump(mode="json"),
    )
    runner._save(session)  # so the in-memory store can find it
    env = await runner._run_loop(session)
    assert env["status"] == STATUS_COMPLETED, env
    # Sequential mode preserved the LITERAL -- ConnectionDoc routing
    # never fired and the substitution context had no ``steps`` key.
    assert captured["customer_id"] == "LITERAL"


@pytest.mark.asyncio
async def test_dataflow_mode_still_routes_via_connection_doc():
    """Regression guard: dataflow mode (default) keeps Phase-1 routing."""
    producer = _StubTool("seed", result={"customer_id": "WIRED"})
    captured: Dict[str, Any] = {}

    class _CaptureTool(_StubTool):
        async def execute(self, **kwargs):  # type: ignore[override]
            self.calls.append(kwargs)
            captured.update(kwargs)
            return {"received": True}

    registry = _StubRegistry([producer, _CaptureTool("downstream")])
    runner = YamlJourneyRunner(tool_registry=registry, session_store=_MemStore())

    journey = _journey([{
        "stage_id": "main", "name": "Main", "order": 1,
        "steps": [
            {"step_id": "seed", "name": "Seed", "order": 1, "tool": "seed"},
            {"step_id": "downstream", "name": "Down", "order": 2,
             "tool": "downstream", "params": {"customer_id": "LITERAL"}},
        ],
        "connections": [{
            "from_step": "seed", "from_relationship": "success",
            "from_path": "customer_id",
            "to_step": "downstream", "to_param": "customer_id",
        }],
    }])
    # Default execution_mode is dataflow.
    env = await runner.run(journey=journey)
    assert env["status"] == STATUS_COMPLETED, env
    assert captured["customer_id"] == "WIRED"


@pytest.mark.asyncio
async def test_relationship_outputs_persisted_per_step_and_channel():
    """RunSession.relationship_outputs is keyed by (step_id, relationship)."""
    producer = _StubTool(
        "fanout",
        output_relationships=["matched", "no_match"],
        relationship_results=[
            RelationshipResult(relationship="matched", data={"id": "A"}),
            RelationshipResult(relationship="no_match", data={"reason": "x"}),
        ],
    )
    registry = _StubRegistry([producer])
    store = _MemStore()
    runner = YamlJourneyRunner(tool_registry=registry, session_store=store)

    journey = _journey([{
        "stage_id": "resolve", "name": "R", "order": 1,
        "steps": [{"step_id": "s1", "name": "S1", "order": 1, "tool": "fanout"}],
    }])

    env = await runner.run(journey=journey)
    assert env["status"] == STATUS_COMPLETED, env

    saved = store.load(env["run_id"])
    assert saved is not None
    rel_outputs = saved.get("relationship_outputs") or {}
    assert rel_outputs.get("s1", {}).get("matched") == {"id": "A"}
    assert rel_outputs.get("s1", {}).get("no_match") == {"reason": "x"}
    # Back-compat: step_results still surfaces the PRIMARY-channel payload only.
    assert saved.get("step_results", {}).get("s1") == {"id": "A"}
