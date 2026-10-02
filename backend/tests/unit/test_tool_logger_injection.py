"""Tests for the Phase-2 ``ToolLogger`` primitive + the
``ToolRegistry.execute_with_relationships`` signature-inspecting
injection.

What we lock in:

1. ``ToolRegistry._tool_accepts_log`` returns True iff the
   ``Tool.execute`` callable declares an explicit ``log`` parameter
   (VAR_KEYWORD-only signatures are explicitly NOT enough -- that
   would forward ``log`` into unmigrated inner impls and raise).
2. When the tool accepts ``log``, the registry injects a
   ``ToolLogger`` bound to the active RunContext on each call.
3. ``ToolLogger.info(...)`` routes through ``run_context.emit`` with
   source="tool".
4. Tools that do NOT declare ``log`` keep working unchanged (no
   silent injection).
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from src.services.control_plane.tool_registry import (
    Tool, ToolRegistry, ToolLogger, RiskLevel, Relationship,
)
from src.services.control_plane import run_context as rc


def _make_tool_with_log() -> Tool:
    async def _impl(name: str, log=None):
        if log:
            log.info(f"hello {name}")
        return {"echo": name}
    return Tool(
        name="echo_with_log",
        description="",
        parameters={"type": "object", "properties": {"name": {"type": "string"}}},
        execute=lambda log=None, **kw: _impl(log=log, **kw),
        risk_level=RiskLevel.READ_ONLY,
        output_relationships=[Relationship(name="success")],
    )


def _make_tool_without_log() -> Tool:
    async def _impl(name: str):
        return {"echo": name}
    return Tool(
        name="echo_no_log",
        description="",
        parameters={"type": "object", "properties": {"name": {"type": "string"}}},
        execute=lambda **kw: _impl(**kw),
        risk_level=RiskLevel.READ_ONLY,
        output_relationships=[Relationship(name="success")],
    )


def test_accepts_log_detects_explicit_log_param() -> None:
    reg = ToolRegistry()
    tool = _make_tool_with_log()
    reg.register(tool)
    assert reg._tool_accepts_log(tool) is True
    # Second call hits the cache; same result.
    assert reg._tool_accepts_log(tool) is True


def test_accepts_log_rejects_kwargs_only_signature() -> None:
    """**kw forwarder is NOT enough -- explicit ``log`` required."""
    reg = ToolRegistry()
    tool = _make_tool_without_log()
    reg.register(tool)
    assert reg._tool_accepts_log(tool) is False


def test_registry_injects_toollogger_when_supported() -> None:
    """When the tool declares ``log``, execute_with_relationships
    injects a ToolLogger bound to the active RunContext."""
    bridge = MagicMock()
    token = rc.set_current(rc.RunContext(
        journey_id="J", job_id="JOB-001-X", step_id="s1", bridge=bridge,
    ))
    try:
        reg = ToolRegistry()
        reg.register(_make_tool_with_log())
        results = asyncio.run(reg.execute_with_relationships(
            "echo_with_log", {"name": "alice"},
        ))
        # Tool returned successfully.
        assert results[0].data == {"echo": "alice"}
        # The injected log fired one INFO line.
        bridge.write_step_log.assert_called()
        sent = bridge.write_step_log.call_args.kwargs
        assert sent["level"] == "INFO"
        assert "hello alice" in sent["message"]
        assert sent["source"] == "tool"
        # details carries the tool name.
        assert sent["details"]["tool"] == "echo_with_log"
    finally:
        rc.reset(token)


def test_registry_does_not_inject_for_unmigrated_tool() -> None:
    """A tool whose signature has only **kw must NOT receive ``log``,
    otherwise the inner impl would TypeError on the unexpected kwarg.
    """
    bridge = MagicMock()
    token = rc.set_current(rc.RunContext(
        journey_id="J", job_id="JOB-001-X", step_id="s1", bridge=bridge,
    ))
    try:
        reg = ToolRegistry()
        reg.register(_make_tool_without_log())
        results = asyncio.run(reg.execute_with_relationships(
            "echo_no_log", {"name": "bob"},
        ))
        # Tool returned successfully -- proving ``log`` was NOT
        # injected (otherwise the inner _impl(name: str) would have
        # raised on the unexpected keyword).
        assert results[0].data == {"echo": "bob"}
        # And no log line was emitted.
        bridge.write_step_log.assert_not_called()
    finally:
        rc.reset(token)


def test_toollogger_emits_with_source_tool_and_tool_name() -> None:
    bridge = MagicMock()
    token = rc.set_current(rc.RunContext(
        journey_id="J", job_id="JOB-001-X", step_id="s1", bridge=bridge,
    ))
    try:
        tl = ToolLogger(tool_name="find_churning_customers")
        tl.warning("rate-limited by Salesforce", retries=3)
    finally:
        rc.reset(token)
    sent = bridge.write_step_log.call_args.kwargs
    assert sent["source"] == "tool"
    assert sent["level"] == "WARNING"
    assert "rate-limited" in sent["message"]
    assert sent["details"]["tool"] == "find_churning_customers"
    assert sent["details"]["retries"] == 3


def test_toollogger_noop_outside_run_context() -> None:
    """Outside a Copilot saved-journey run (no RunContext active),
    ToolLogger emits become silent no-ops -- safe to sprinkle in any
    tool's body."""
    tl = ToolLogger(tool_name="anything")
    # Must not raise. There's no bridge to assert on; the assertion
    # is the absence of an exception.
    tl.info("this goes nowhere")
    tl.error("nor this")
