"""Copilot → AI Engine decoupling tests (v1.0.0)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.ai_engine_client import AiEngineClient, AiEngineClientError
from src.services.control_plane.copilot_engine import CopilotEngine, CopilotSession


@pytest.fixture
def mock_ai_client() -> MagicMock:
    client = MagicMock(spec=AiEngineClient)
    client.configured = True
    client.submit_execution = AsyncMock(
        return_value={
            "execution_id": "exec-abc",
            "status": "RUNNING",
            "journey_id": "order-to-cash-monitor",
            "tenant_id": "tenant-1",
            "links": {"self": "/api/v1/executions/exec-abc"},
        }
    )
    return client


@pytest.fixture
def engine_with_ai(mock_ai_client: MagicMock) -> CopilotEngine:
    eng = CopilotEngine(ai_engine_client=mock_ai_client)
    return eng


@pytest.mark.asyncio
async def test_saved_journey_delegates_to_ai_engine(engine_with_ai: CopilotEngine, mock_ai_client: MagicMock) -> None:
    session = CopilotSession("sess-1", "Run O2C")
    session.plan = [{"id": "s1", "tool": "query_virtual_entity", "params": {}}]
    session.playbook_context = {
        "source": "saved_journey",
        "journey_id": "order-to-cash-monitor",
    }
    engine_with_ai._sessions[session.session_id] = session

    result = await engine_with_ai.execute_plan(session.session_id)

    assert result["via"] == "ai_engine"
    assert result["execution_id"] == "exec-abc"
    assert result["journey_id"] == "order-to-cash-monitor"
    mock_ai_client.submit_execution.assert_awaited_once()
    call_kwargs = mock_ai_client.submit_execution.await_args.kwargs
    assert call_kwargs["journey_id"] == "order-to-cash-monitor"
    assert call_kwargs["labels"]["source"] == "saved_journey"


@pytest.mark.asyncio
async def test_ad_hoc_execute_plan_blocked_when_ai_engine_enabled(engine_with_ai: CopilotEngine, mock_ai_client: MagicMock) -> None:
    session = CopilotSession("sess-2", "Ad hoc goal")
    session.plan = [{"id": "s1", "tool": "search_enterprise_knowledge", "params": {}}]
    engine_with_ai._sessions[session.session_id] = session

    result = await engine_with_ai.execute_plan(session.session_id)

    assert result["error"] == "in_process_execution_disabled"
    mock_ai_client.submit_execution.assert_not_awaited()


@pytest.mark.asyncio
async def test_in_process_execution_when_ai_engine_disabled() -> None:
    """Without AI Engine client, execute_plan enters the tool loop (no immediate block)."""
    eng = CopilotEngine(ai_engine_client=None)
    session = CopilotSession("sess-3", "Local run")
    session.plan = []
    eng._sessions[session.session_id] = session

    result = await eng.execute_plan(session.session_id)

    assert result.get("error") != "in_process_execution_disabled"
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_ai_engine_submit_failure_surfaces_error(engine_with_ai: CopilotEngine, mock_ai_client: MagicMock) -> None:
    mock_ai_client.submit_execution = AsyncMock(
        side_effect=AiEngineClientError("HTTP 404", status_code=404)
    )
    session = CopilotSession("sess-4", "Run saved")
    session.playbook_context = {"source": "saved_journey", "journey_id": "missing-journey"}
    engine_with_ai._sessions[session.session_id] = session

    result = await engine_with_ai.execute_plan(session.session_id)

    assert result["error"] == "ai_engine_submit_failed"
    assert "404" in result["message"]
