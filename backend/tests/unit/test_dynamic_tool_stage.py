"""
Unit tests for ``stages/dynamic_tool_stage.py``.

Tests the placeholder-substitution helper and the step dispatch path
against a fake registry.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.stages.dynamic_tool_stage import DynamicToolStage, _substitute


def test_substitute_full_string_preserves_type():
    out = _substitute("{{ params.count }}", ctx={
        "steps": {}, "journey": {}, "params": {"count": 42},
    })
    assert out == 42  # not the string "42"


def test_substitute_inline_placeholder_strs_default():
    out = _substitute("hello {{ params.who }}", ctx={
        "steps": {}, "journey": {}, "params": {"who": "team"},
    })
    assert out == "hello team"


def test_substitute_unknown_path_yields_empty_string():
    out = _substitute("hello {{ foo.bar }}", ctx={
        "steps": {}, "journey": {}, "params": {},
    })
    assert out == "hello "


def test_substitute_recurses_into_dicts_and_lists():
    out = _substitute(
        {
            "id": "{{ params.id }}",
            "list": ["{{ steps.s1.value }}", "static"],
        },
        ctx={
            "steps": {"s1": {"value": "v"}},
            "journey": {},
            "params": {"id": "X"},
        },
    )
    assert out == {"id": "X", "list": ["v", "static"]}


# ---------------------------------------------------------------------------
# execute_step
# ---------------------------------------------------------------------------

class FakeTool:
    def __init__(self, name: str, fn: Any) -> None:
        self.name = name
        self.fn = fn


class FakeRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, FakeTool] = {}

    def register(self, tool: FakeTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str):
        return self._tools.get(name)

    def list_tools(self) -> List[FakeTool]:
        return list(self._tools.values())

    async def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"tool {name} not found"}
        return await tool.fn(args)


@pytest.mark.asyncio
async def test_execute_step_resolves_params_and_dispatches(monkeypatch):
    captured: List[Dict[str, Any]] = []

    async def echo(args):
        captured.append(args)
        return {"echoed": args}

    reg = FakeRegistry()
    reg.register(FakeTool("greeter", echo))

    # Patch the static resolver to return our fake registry.
    monkeypatch.setattr(DynamicToolStage, "_resolve_registry", staticmethod(lambda: reg))

    stage = DynamicToolStage()
    out = await stage._execute_step_async(
        "step-1",
        {
            "tool_name": "greeter",
            "params": {"who": "{{ params.who }}", "id": "{{ steps.s0.id }}"},
            "__steps_so_far": {"s0": {"id": "ID-1"}},
            "__journey_params": {"who": "team"},
        },
    )
    assert out["status"] == "completed"
    assert out["tool"] == "greeter"
    assert captured == [{"who": "team", "id": "ID-1"}]


@pytest.mark.asyncio
async def test_execute_step_missing_tool_returns_failure(monkeypatch):
    reg = FakeRegistry()
    monkeypatch.setattr(DynamicToolStage, "_resolve_registry", staticmethod(lambda: reg))

    stage = DynamicToolStage()
    out = await stage._execute_step_async("step-x", {"tool_name": "missing"})
    assert out["status"] == "failed"
    assert "not registered" in out["error"]


@pytest.mark.asyncio
async def test_execute_step_on_error_continue(monkeypatch):
    async def boom(_args):
        return {"error": "explodes"}

    reg = FakeRegistry()
    reg.register(FakeTool("boom_tool", boom))
    monkeypatch.setattr(DynamicToolStage, "_resolve_registry", staticmethod(lambda: reg))

    stage = DynamicToolStage()
    out = await stage._execute_step_async(
        "step-y",
        {"tool_name": "boom_tool", "on_error": "continue"},
    )
    assert out["status"] == "completed"
    assert out["result"]["error"] == "explodes"


@pytest.mark.asyncio
async def test_execute_step_on_error_default_fails(monkeypatch):
    async def boom(_args):
        return {"error": "explodes"}

    reg = FakeRegistry()
    reg.register(FakeTool("boom_tool", boom))
    monkeypatch.setattr(DynamicToolStage, "_resolve_registry", staticmethod(lambda: reg))

    stage = DynamicToolStage()
    out = await stage._execute_step_async("step-z", {"tool_name": "boom_tool"})
    assert out["status"] == "failed"
