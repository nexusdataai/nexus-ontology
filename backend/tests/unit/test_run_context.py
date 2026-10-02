"""Unit tests for ``run_context`` -- the ContextVar carrier that lets
deep sub-call sites (virtual queries, connector APIs, custom code)
emit per-step log entries through the JourneyExecutorBridge without
widening every internal function signature."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.services.control_plane import run_context as rc


def test_emit_is_noop_without_active_context() -> None:
    """No active RunContext (the case for regular Journeys, ad-hoc
    Copilot chat, unit tests of unrelated services) -> emit() must
    NOT raise and must NOT touch the bridge."""
    bridge = MagicMock()
    # Defensive: nothing should be set after import.
    assert rc.get_current() is None
    rc.emit(level="INFO", message="should be dropped")
    bridge.write_step_log.assert_not_called()


def test_emit_routes_to_bridge_when_context_is_set() -> None:
    bridge = MagicMock()
    token = rc.set_current(rc.RunContext(
        journey_id="J", job_id="JOB-001-x", step_id="s1", bridge=bridge,
    ))
    try:
        rc.emit(level="DEBUG", message="hello",
                details={"sql": "select 1"}, source="virtual_query")
    finally:
        rc.reset(token)
    bridge.write_step_log.assert_called_once()
    kwargs = bridge.write_step_log.call_args.kwargs
    assert kwargs["journey_id"] == "J"
    assert kwargs["job_id"] == "JOB-001-x"
    assert kwargs["step_id"] == "s1"
    assert kwargs["level"] == "DEBUG"
    assert kwargs["message"] == "hello"
    assert kwargs["source"] == "virtual_query"
    # details must have been redact()-walked.
    assert kwargs["details"] == {"sql": "select 1"}


def test_emit_redacts_secret_keys_in_details() -> None:
    bridge = MagicMock()
    token = rc.set_current(rc.RunContext(
        journey_id="J", job_id="JOB-001", step_id="s1", bridge=bridge,
    ))
    try:
        rc.emit(level="INFO", message="connector",
                details={
                    "api_id": "stripe.charges.create",
                    "Authorization": "Bearer sk_live_abc",
                    "payload": {"password": "hunter2", "amount": 100},
                    "secret_key": "abc",
                },
                source="connector_api")
    finally:
        rc.reset(token)
    sent = bridge.write_step_log.call_args.kwargs["details"]
    assert sent["api_id"] == "stripe.charges.create"
    assert sent["Authorization"] == "***"
    assert sent["secret_key"] == "***"
    assert sent["payload"]["password"] == "***"
    assert sent["payload"]["amount"] == 100  # non-secret survives


def test_reset_restores_previous_context() -> None:
    bridge1, bridge2 = MagicMock(), MagicMock()
    t1 = rc.set_current(rc.RunContext("J", "JOB-1", "s1", bridge=bridge1))
    t2 = rc.set_current(rc.RunContext("J", "JOB-1", "s2", bridge=bridge2))
    try:
        rc.emit(message="inner")
        assert bridge2.write_step_log.call_count == 1
        assert bridge1.write_step_log.call_count == 0
        rc.reset(t2)
        rc.emit(message="outer")
        assert bridge1.write_step_log.call_count == 1
    finally:
        try:
            rc.reset(t1)
        except Exception:
            pass


def test_emit_swallows_bridge_exception() -> None:
    bridge = MagicMock()
    bridge.write_step_log.side_effect = RuntimeError("ddb sad")
    token = rc.set_current(rc.RunContext("J", "X", "s1", bridge=bridge))
    try:
        rc.emit(message="should not raise")  # must not bubble up
    finally:
        rc.reset(token)


def test_redact_handles_lists_and_deep_nesting() -> None:
    out = rc.redact({
        "items": [
            {"name": "ok", "token": "xyz"},
            {"name": "ok2", "password": "p"},
        ],
        "outer": {"inner": {"api_key": "k", "id": 1}},
    })
    assert out["items"][0]["token"] == "***"
    assert out["items"][1]["password"] == "***"
    assert out["outer"]["inner"]["api_key"] == "***"
    assert out["outer"]["inner"]["id"] == 1
