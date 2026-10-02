"""
In-process integration test for the YAML Journey runner REST API.

Stands up a minimal FastAPI app wired with:
  - yaml_journey_api router (run / approve-step / get / list)
  - a stub ToolRegistry with two tools (one read, one mutate-with-approval)
  - an in-memory session store (drop-in for CopilotSessionStore)

Drives the full lifecycle:
  POST /run with inline YAML body -> pause on the approval step ->
  POST /{id}/approve-step -> complete -> GET /{id} -> GET / .

Also covers the negative paths: invalid YAML and unknown-tool validation
failure return 422 with the structured detail.
"""

from __future__ import annotations

import os
import sys
import textwrap
from typing import Any, Dict, List, Optional

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Stubs (mirror the tools_builder_api integration style)
# ---------------------------------------------------------------------------


class _StubTool:
    def __init__(self, name: str, *, risk_level: str = "read_only",
                 tool_kind: str = "read", connector_api: Optional[str] = None,
                 result: Optional[Dict[str, Any]] = None) -> None:
        self.name = name
        self.risk_level = risk_level
        self.tool_kind = tool_kind
        self.connector_api = connector_api
        self._result = result if result is not None else {"ok": True, "tool": name}
        self.calls: List[Dict[str, Any]] = []

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(kwargs)
        return dict(self._result)


class _StubRegistry:
    def __init__(self, tools: List[_StubTool]):
        self._tools = {t.name: t for t in tools}

    def list_tools(self) -> List[_StubTool]:
        return list(self._tools.values())

    def get(self, name: str) -> Optional[_StubTool]:
        return self._tools.get(name)

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        t = self._tools.get(name)
        if t is None:
            return {"error": f"Tool '{name}' not found"}
        try:
            return await t.execute(**arguments)
        except Exception as e:
            return {"error": str(e)}


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
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def yj_app():
    """FastAPI app with the yaml_journey_api wired to a stub runner."""
    from src.apis import yaml_journey_api
    from src.services.control_plane.yaml_journey_runner import YamlJourneyRunner

    registry = _StubRegistry([
        _StubTool("query_inventory", result={"count": 3, "rows": [{"sku": "A"}, {"sku": "B"}]}),
        _StubTool(
            "place_credit_hold",
            risk_level="high_risk_write",
            tool_kind="mutate",
            connector_api="sfdc.account.credit_hold.set",
            result={"action": "credit_hold_placed", "account_id": "A-1"},
        ),
    ])
    store = _MemStore()
    runner = YamlJourneyRunner(tool_registry=registry, session_store=store)
    yaml_journey_api.configure(runner)

    app = FastAPI()
    app.include_router(yaml_journey_api.router)
    return app, registry, store


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t.local")


_YAML_HAPPY = textwrap.dedent("""
    use_case_id: it.happy
    journey_id: it.happy
    title: Integration Happy
    solution_id: order-to-cash
    description: integration test happy path
    stages:
      - stage_id: resolve
        name: Resolve
        order: 1
        steps:
          - step_id: list
            name: List
            order: 1
            tool: query_inventory
            params: { limit: 10 }
      - stage_id: act
        name: Act
        order: 2
        steps:
          - step_id: place_hold
            name: Place credit hold
            order: 1
            tool: place_credit_hold
            requires_approval: true
            params:
              account_id: A-1
              first_sku: "${steps.list.rows.0.sku}"
""").strip()


_YAML_BAD = "not: valid: yaml: at all: :"


_JOURNEY_UNKNOWN_TOOL = {
    "use_case_id": "it.unknown",
    "journey_id": "it.unknown",
    "title": "Unknown tool",
    "solution_id": "order-to-cash",
    "description": "validation negative",
    "stages": [{
        "stage_id": "resolve", "name": "R", "order": 1,
        "steps": [{"step_id": "step1", "name": "S1", "order": 1, "tool": "does_not_exist"}],
    }],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_pauses_on_approval_step_then_resumes_to_completion(yj_app):
    app, registry, store = yj_app
    async with _client(app) as client:
        # 1. POST /run with inline YAML; expect pause on place_hold.
        resp = await client.post("/api/v1/yaml-journeys/run",
                                 json={"yaml": _YAML_HAPPY, "inputs": {}})
        assert resp.status_code == 200, resp.text
        env = resp.json()
        assert env["status"] == "awaiting_step_approval"
        assert env["pending_step"]["step_id"] == "place_hold"
        assert env["pending_step"]["tool"] == "place_credit_hold"
        run_id = env["run_id"]

        # query_inventory ran; place_credit_hold did NOT.
        assert registry.get("query_inventory").calls == [{"limit": 10}]
        assert registry.get("place_credit_hold").calls == []

        # 2. GET /{run_id} mirrors the persisted state.
        resp = await client.get(f"/api/v1/yaml-journeys/{run_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "awaiting_step_approval"
        assert body["completed_steps"] == ["list"]

        # 3. Approve the step -> completes.
        resp = await client.post(
            f"/api/v1/yaml-journeys/{run_id}/approve-step",
            json={"step_id": "place_hold", "approved": True},
        )
        assert resp.status_code == 200, resp.text
        env = resp.json()
        assert env["status"] == "completed"
        assert env["pending_step"] is None
        assert env["completed_steps"] == ["list", "place_hold"]

        # place_credit_hold received the substituted account_id + first_sku
        # (preserved type because the placeholder was a whole-string expr).
        call = registry.get("place_credit_hold").calls[0]
        assert call == {"account_id": "A-1", "first_sku": "A"}

        # 4. GET / shows the run in the list.
        resp = await client.get("/api/v1/yaml-journeys")
        assert resp.status_code == 200
        runs = resp.json()["runs"]
        assert any(r["run_id"] == run_id and r["status"] == "completed" for r in runs)


@pytest.mark.asyncio
async def test_run_with_invalid_yaml_returns_422(yj_app):
    app, _registry, _store = yj_app
    async with _client(app) as client:
        resp = await client.post("/api/v1/yaml-journeys/run", json={"yaml": _YAML_BAD})
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["code"] in ("yaml_parse_error", "yaml_root_not_object")


@pytest.mark.asyncio
async def test_run_with_unknown_tool_returns_422_with_validation_report(yj_app):
    app, _registry, store = yj_app
    async with _client(app) as client:
        resp = await client.post("/api/v1/yaml-journeys/run",
                                 json={"journey": _JOURNEY_UNKNOWN_TOOL})
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["status"] == "failed"
        codes = {iss["code"] for iss in detail["validation_report"]["errors"]}
        assert "unknown_tool" in codes
        # No session persisted on validation failure.
        assert store.data == {}


@pytest.mark.asyncio
async def test_get_nonexistent_run_returns_404(yj_app):
    app, _registry, _store = yj_app
    async with _client(app) as client:
        resp = await client.get("/api/v1/yaml-journeys/does-not-exist")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "run_not_found"
