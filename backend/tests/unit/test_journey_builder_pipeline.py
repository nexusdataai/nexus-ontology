"""
Unit tests for the Journey Builder backend pipeline.

Covers the three new helper functions in
``src/apis/copilot_journey_api.py``:

  - ``_topo_sort`` -- DAG ordering by edges with stable fallback and
                      cycle detection (422).
  - ``_apply_edges_to_params`` -- writes ``${steps.X.y}`` placeholders
                                  into target params.
  - ``_builder_to_journey_doc`` -- end-to-end transform producing a
                                   valid JourneyDoc with provenance,
                                   solution_id default, kind, etc.

Plus integration-style coverage for the rewritten endpoints using a
hand-rolled FastAPI app + httpx ASGITransport, with stubs for the
tool registry / connector_apis / journey_store / yaml_journey_runner.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

@dataclass
class _StubTool:
    name: str
    risk_level: str = "read_only"
    tool_kind: str = "read"
    connector_api: Optional[str] = None
    parameters: Dict[str, Any] = None


class _StubRegistry:
    def __init__(self, tools: List[_StubTool]):
        self._tools = list(tools)

    def list_tools(self) -> List[_StubTool]:
        return list(self._tools)


class _StubConnectorApis:
    def __init__(self, api_ids: List[str]):
        self._items = [type("Spec", (), {"api_id": x})() for x in api_ids]

    def list_all(self):
        return list(self._items)


class _StubJourneyStore:
    """In-memory create / get; matches the JourneyStoreService surface."""
    def __init__(self):
        self.rows: Dict[str, Dict[str, Any]] = {}

    async def create(self, journey: Dict[str, Any], user: str = "anonymous") -> Dict[str, Any]:
        jid = journey.get("journey_id") or journey.get("use_case_id") or f"j-{len(self.rows)}"
        record = {**journey, "journey_id": jid, "createdBy": user}
        self.rows[jid] = record
        return record

    async def get(self, journey_id: str):
        return self.rows.get(journey_id)


class _StubYamlJourneyRunner:
    """Captures the last run / resume call so tests can assert delegation."""
    def __init__(self):
        self.last_run: Optional[Dict[str, Any]] = None
        self.last_resume: Optional[Dict[str, Any]] = None

    async def run(self, *, journey, inputs=None, user="ai-engine",
                  run_id=None, auto_approve_steps=None):
        self.last_run = {
            "journey": journey.model_dump(mode="json") if hasattr(journey, "model_dump") else journey,
            "inputs": inputs or {},
            "user": user,
        }
        return {
            "run_id": "YJ-test",
            "status": "completed",
            "step_results": {},
            "completed_steps": [],
            "pending_step": None,
            "error": None,
        }

    async def resume(self, *, run_id: str, step_id: str, approved: bool, user: str = "x"):
        self.last_resume = {"run_id": run_id, "step_id": step_id, "approved": approved, "user": user}
        return {
            "run_id": run_id,
            "status": "completed" if approved else "failed",
            "step_results": {},
            "completed_steps": [step_id] if approved else [],
            "pending_step": None,
        }


# ---------------------------------------------------------------------------
# _topo_sort + _apply_edges_to_params + _builder_to_journey_doc
# ---------------------------------------------------------------------------

def test_topo_sort_preserves_order_when_no_edges():
    from src.apis.copilot_journey_api import _topo_sort
    nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    out = _topo_sort(nodes, [])
    assert [n["id"] for n in out] == ["a", "b", "c"]


def test_topo_sort_reorders_by_edges():
    from src.apis.copilot_journey_api import _topo_sort, BuilderEdge
    # Author placed "act" before "resolve"; the edge says act needs
    # resolve.results so topo-sort should swap them.
    nodes = [{"id": "act"}, {"id": "resolve"}]
    edges = [BuilderEdge(from_node="resolve", from_key="results", to_node="act", to_param="customer_id")]
    out = _topo_sort(nodes, edges)
    assert [n["id"] for n in out] == ["resolve", "act"]


def test_topo_sort_raises_422_on_cycle():
    from fastapi import HTTPException
    from src.apis.copilot_journey_api import _topo_sort, BuilderEdge
    nodes = [{"id": "a"}, {"id": "b"}]
    edges = [
        BuilderEdge(from_node="a", from_key="x", to_node="b", to_param="x"),
        BuilderEdge(from_node="b", from_key="y", to_node="a", to_param="y"),
    ]
    with pytest.raises(HTTPException) as exc:
        _topo_sort(nodes, edges)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "builder_cycle"


def test_topo_sort_raises_422_on_self_edge():
    from fastapi import HTTPException
    from src.apis.copilot_journey_api import _topo_sort, BuilderEdge
    nodes = [{"id": "a"}]
    edges = [BuilderEdge(from_node="a", from_key="x", to_node="a", to_param="y")]
    with pytest.raises(HTTPException) as exc:
        _topo_sort(nodes, edges)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "builder_self_edge"


def test_apply_edges_to_params_writes_substitution_placeholders():
    from src.apis.copilot_journey_api import _apply_edges_to_params, BuilderEdge
    nodes = [
        {"id": "src", "tool": "find_churning_customers", "params": {}},
        {"id": "dst", "tool": "apply_promo_discount", "params": {"discount_pct": 12.5}},
    ]
    edges = [
        BuilderEdge(from_node="src", from_key="results.0.customer_id",
                    to_node="dst", to_param="customer_id"),
    ]
    out = _apply_edges_to_params(nodes, edges)
    by_id = {n["id"]: n for n in out}
    assert by_id["dst"]["params"]["customer_id"] == "${steps.src.results.0.customer_id}"
    # Pre-existing param is preserved.
    assert by_id["dst"]["params"]["discount_pct"] == 12.5


def test_builder_to_journey_doc_emits_user_authored_doc_with_provenance():
    from src.apis.copilot_journey_api import BuilderSaveRequest, _builder_to_journey_doc, BuilderEdge
    req = BuilderSaveRequest(
        name="Retain Risky Customers",
        display_name="Retain Risky Customers",
        description="save play",
        steps=[
            {"id": "src", "name": "Find at-risk", "tool": "find_churning_customers", "params": {}},
            {"id": "dst", "name": "Apply promo", "tool": "apply_promo_discount", "params": {"discount_pct": 12.5}},
        ],
        edges=[BuilderEdge(from_node="src", from_key="results.0.customer_id",
                           to_node="dst", to_param="customer_id")],
    )
    doc = _builder_to_journey_doc(req)
    assert doc.kind == "user_authored"
    assert doc.provenance is not None
    assert doc.provenance.source == "journey-builder"
    assert doc.solution_id == "builder"
    assert doc.journey_id == "builder.retain_risky_customers"
    assert len(doc.stages) == 1
    assert doc.stages[0].stage_id == "main"
    steps = doc.stages[0].steps
    assert [s.step_id for s in steps] == ["src", "dst"]
    assert steps[0].order == 1 and steps[1].order == 2
    assert steps[1].params["customer_id"] == "${steps.src.results.0.customer_id}"


def test_builder_to_journey_doc_preserves_foreach():
    from src.apis.copilot_journey_api import BuilderSaveRequest, _builder_to_journey_doc
    req = BuilderSaveRequest(
        name="loopy",
        steps=[
            {"id": "src", "tool": "find_churning_customers", "params": {}, "name": "src"},
            {"id": "dst", "tool": "apply_promo_discount", "params": {"discount_pct": 5}, "foreach": "${steps.src.results}", "name": "dst"},
        ],
    )
    doc = _builder_to_journey_doc(req)
    # foreach lives under params["__foreach__"] in StepDoc.params (the
    # canonical YAML runner reads it from there).
    assert doc.stages[0].steps[1].params.get("__foreach__") == "${steps.src.results}"


# ---------------------------------------------------------------------------
# Multi-stage builder path
# ---------------------------------------------------------------------------


def test_builder_to_journey_doc_multi_stage_round_trip():
    """When req.stages is non-empty, each entry materialises one
    StageDoc with its own steps + connections."""
    from src.apis.copilot_journey_api import (
        BuilderConnection, BuilderSaveRequest, BuilderStage, _builder_to_journey_doc,
    )
    req = BuilderSaveRequest(
        name="multi stage",
        stages=[
            BuilderStage(
                stage_id="discover",
                name="Discover",
                order=1,
                steps=[
                    {"id": "find", "tool": "find_churning_customers",
                     "params": {}, "name": "find"},
                ],
            ),
            BuilderStage(
                stage_id="act",
                name="Act",
                order=2,
                steps=[
                    {"id": "csm", "tool": "assign_csm_outreach",
                     "params": {"account_id": "ACC-1", "subject": "Reach out"},
                     "name": "csm"},
                ],
                connections=[
                    BuilderConnection(
                        from_step="find", from_relationship="success",
                        to_step="csm", to_param="account_id",
                    ),
                ],
            ),
        ],
    )
    doc = _builder_to_journey_doc(req)
    assert [s.stage_id for s in doc.stages] == ["discover", "act"]
    assert [s.order for s in doc.stages] == [1, 2]
    assert [s.name for s in doc.stages] == ["Discover", "Act"]
    assert [s.step_id for s in doc.stages[0].steps] == ["find"]
    assert [s.step_id for s in doc.stages[1].steps] == ["csm"]
    # Connections are stage-local.
    assert doc.stages[0].connections == []
    assert len(doc.stages[1].connections) == 1
    assert doc.stages[1].connections[0].from_step == "find"
    assert doc.stages[1].connections[0].to_param == "account_id"


def test_builder_to_journey_doc_multi_stage_normalises_order():
    """Out-of-order ``order`` values get re-numbered to a deterministic
    1..N sequence so the runner always has a clean topological order."""
    from src.apis.copilot_journey_api import (
        BuilderSaveRequest, BuilderStage, _builder_to_journey_doc,
    )
    req = BuilderSaveRequest(
        name="reordered",
        stages=[
            BuilderStage(stage_id="c", name="C", order=99, steps=[]),
            BuilderStage(stage_id="a", name="A", order=10, steps=[]),
            BuilderStage(stage_id="b", name="B", order=50, steps=[]),
        ],
    )
    doc = _builder_to_journey_doc(req)
    assert [s.stage_id for s in doc.stages] == ["a", "b", "c"]
    assert [s.order for s in doc.stages] == [1, 2, 3]


def test_builder_to_journey_doc_falls_back_to_single_stage_when_stages_empty():
    """Legacy single-stage path keeps working byte-for-byte when
    req.stages is omitted."""
    from src.apis.copilot_journey_api import BuilderSaveRequest, _builder_to_journey_doc
    req = BuilderSaveRequest(
        name="legacy",
        steps=[{"id": "s1", "tool": "find_churning_customers",
                "params": {}, "name": "s1"}],
    )
    doc = _builder_to_journey_doc(req)
    assert len(doc.stages) == 1
    assert doc.stages[0].stage_id == "main"
    assert doc.stages[0].name == "Main"
    assert [s.step_id for s in doc.stages[0].steps] == ["s1"]


def test_builder_to_journey_doc_multi_stage_respects_execution_mode():
    """Sequential journeys still force per-stage connections=[]
    regardless of what the multi-stage payload carried."""
    from src.apis.copilot_journey_api import (
        BuilderConnection, BuilderSaveRequest, BuilderStage, _builder_to_journey_doc,
    )
    req = BuilderSaveRequest(
        name="seq multi",
        execution_mode="sequential",
        stages=[
            BuilderStage(stage_id="a", name="A", order=1, steps=[
                {"id": "s1", "tool": "find_churning_customers",
                 "params": {}, "name": "s1"},
            ]),
            BuilderStage(stage_id="b", name="B", order=2, steps=[
                {"id": "s2", "tool": "assign_csm_outreach",
                 "params": {"account_id": "X", "subject": "Y"}, "name": "s2"},
            ], connections=[
                # Sneaked-in connection: must be dropped by the
                # multi-stage path because execution_mode=sequential.
                BuilderConnection(from_step="s1", from_relationship="success",
                                  to_step="s2", to_param="account_id"),
            ]),
        ],
    )
    doc = _builder_to_journey_doc(req)
    assert doc.execution_mode == "sequential"
    for stage in doc.stages:
        assert stage.connections == []


# ---------------------------------------------------------------------------
# Endpoint integration tests through an in-process FastAPI app
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def builder_app():
    """Mount the copilot_journey_api router with all stubs wired."""
    from src.apis import copilot_journey_api

    registry = _StubRegistry([
        _StubTool(name="find_churning_customers", risk_level="read_only", tool_kind="read"),
        _StubTool(name="apply_promo_discount", risk_level="high_risk_write",
                  tool_kind="mutate", connector_api="oracle.promotion.create"),
    ])
    connector_apis = _StubConnectorApis(["oracle.promotion.create"])
    store = _StubJourneyStore()
    yaml_runner = _StubYamlJourneyRunner()
    # ``_copilot_engine`` must be non-None for /journey-builder/save's
    # _check guard NOT to fire (save doesn't call _check, but other
    # paths might in future). Use a bare MagicMock.
    copilot_journey_api.configure(
        engine=MagicMock(),
        journey_store=store,
        yaml_journey_runner=yaml_runner,
        tool_registry=registry,
        connector_apis=connector_apis,
    )

    app = FastAPI()
    app.include_router(copilot_journey_api.router)
    return app, store, yaml_runner


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t.local")


def _save_body() -> Dict[str, Any]:
    return {
        "name": "Test Journey",
        "display_name": "Test",
        "description": "smoke",
        "steps": [
            {"id": "src", "name": "Find", "tool": "find_churning_customers", "params": {}},
            {"id": "dst", "name": "Apply", "tool": "apply_promo_discount",
             "params": {"name": "x", "discount_pct": 5}},
        ],
        "edges": [
            {"from_node": "src", "from_key": "results.0.customer_id",
             "to_node": "dst", "to_param": "customer_id"},
        ],
    }


@pytest.mark.asyncio
async def test_validate_returns_strict_report_green_when_tools_registered(builder_app):
    app, _store, _runner = builder_app
    async with _client(app) as client:
        resp = await client.post("/journey-builder/validate", json=_save_body())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["valid"] is True
        assert body["errors"] == []
        # ``report`` is always populated for the strict result.
        assert "report" in body


@pytest.mark.asyncio
async def test_validate_flags_unknown_tool(builder_app):
    app, _store, _runner = builder_app
    bad = _save_body()
    bad["steps"][1]["tool"] = "does_not_exist"
    async with _client(app) as client:
        resp = await client.post("/journey-builder/validate", json=bad)
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        codes = {iss["code"] for iss in body["report"]["errors"]}
        assert "unknown_tool" in codes


@pytest.mark.asyncio
async def test_save_persists_journey_to_store(builder_app):
    app, store, _runner = builder_app
    async with _client(app) as client:
        resp = await client.post("/journey-builder/save", json=_save_body())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        jid = body["journey_id"]
        assert jid in store.rows
        # The persisted row has the substituted placeholder param.
        saved = store.rows[jid]
        steps = saved["stages"][0]["steps"]
        assert steps[1]["params"]["customer_id"] == "${steps.src.results.0.customer_id}"


@pytest.mark.asyncio
async def test_save_422_on_unknown_tool(builder_app):
    app, store, _runner = builder_app
    bad = _save_body()
    bad["steps"][1]["tool"] = "does_not_exist"
    async with _client(app) as client:
        resp = await client.post("/journey-builder/save", json=bad)
        assert resp.status_code == 422
        # No row persisted.
        assert store.rows == {}


@pytest.mark.asyncio
async def test_run_delegates_to_yaml_runner(builder_app):
    app, _store, runner = builder_app
    async with _client(app) as client:
        resp = await client.post("/journey-builder/run", json=_save_body())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["run_id"] == "YJ-test"
        assert body["via"] == "yaml_journey_runner"
        assert runner.last_run is not None
        # The runner was handed the resolved JourneyDoc, not the raw
        # builder payload.
        passed = runner.last_run["journey"]
        steps = passed["stages"][0]["steps"]
        assert steps[1]["params"]["customer_id"] == "${steps.src.results.0.customer_id}"


@pytest.mark.asyncio
async def test_approve_step_forwards_to_runner_resume(builder_app):
    app, _store, runner = builder_app
    async with _client(app) as client:
        resp = await client.post(
            "/journey-builder/run/YJ-abc/approve-step",
            json={"step_id": "dst", "approved": True, "user": "qa"},
        )
        assert resp.status_code == 200
        assert runner.last_resume == {"run_id": "YJ-abc", "step_id": "dst", "approved": True, "user": "qa"}


@pytest.mark.asyncio
async def test_tool_outputs_returns_hints_map(builder_app):
    app, _store, _runner = builder_app
    async with _client(app) as client:
        resp = await client.get("/journey-builder/tool-outputs")
        assert resp.status_code == 200
        body = resp.json()
        # find_churning_customers has an explicit catalogue entry.
        hints = body["hints"]["find_churning_customers"]
        keys = {h["key"] for h in hints}
        assert "results" in keys
        assert "results.0.customer_id" in keys


@pytest.mark.asyncio
async def test_run_returns_422_on_builder_cycle(builder_app):
    app, _store, _runner = builder_app
    body = _save_body()
    body["edges"].append({
        "from_node": "dst", "from_key": "promo_id",
        "to_node": "src", "to_param": "horizon_days",
    })
    async with _client(app) as client:
        resp = await client.post("/journey-builder/run", json=body)
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "builder_cycle"
