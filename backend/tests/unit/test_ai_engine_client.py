"""Unit tests for AiEngineClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.services.ai_engine_client import AiEngineClient, AiEngineClientError


def _mock_response(status_code: int, json_body: dict | list | None = None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text or (str(json_body) if json_body is not None else "")
    resp.json = MagicMock(return_value=json_body or {})
    return resp


@pytest.mark.asyncio
async def test_submit_execution_success() -> None:
    http = AsyncMock()
    http.post = AsyncMock(
        return_value=_mock_response(
            202,
            {
                "execution_id": "e-123",
                "status": "RUNNING",
                "journey_id": "order-to-cash-monitor",
                "tenant_id": "t-1",
                "links": {"self": "/api/v1/executions/e-123"},
            },
        )
    )
    client = AiEngineClient(
        url="http://ai-engine.test",
        enabled=True,
        http_client=http,
    )

    result = await client.submit_execution(
        journey_id="order-to-cash-monitor",
        labels={"triggered_by": "copilot"},
    )

    assert result["execution_id"] == "e-123"
    assert result["status"] == "RUNNING"
    http.post.assert_awaited_once()
    call_kwargs = http.post.await_args.kwargs
    assert call_kwargs["json"]["journey_id"] == "order-to-cash-monitor"
    assert call_kwargs["json"]["labels"]["triggered_by"] == "copilot"
    assert http.post.await_args.args[0] == "http://ai-engine.test/api/v1/executions/"


@pytest.mark.asyncio
async def test_submit_execution_disabled_raises() -> None:
    client = AiEngineClient(url="", enabled=False)
    with pytest.raises(AiEngineClientError, match="not configured"):
        await client.submit_execution(journey_id="demo")


@pytest.mark.asyncio
async def test_submit_execution_http_error_raises() -> None:
    http = AsyncMock()
    http.post = AsyncMock(return_value=_mock_response(404, text="journey not found"))
    client = AiEngineClient(url="http://ai-engine.test", enabled=True, http_client=http)

    with pytest.raises(AiEngineClientError, match="HTTP 404") as exc_info:
        await client.submit_execution(journey_id="missing-journey")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_submit_execution_transport_error_raises() -> None:
    http = AsyncMock()
    http.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    client = AiEngineClient(url="http://ai-engine.test", enabled=True, http_client=http)

    with pytest.raises(AiEngineClientError, match="unreachable"):
        await client.submit_execution(journey_id="demo")


@pytest.mark.asyncio
async def test_list_executions_success() -> None:
    http = AsyncMock()
    http.get = AsyncMock(
        return_value=_mock_response(
            200,
            [{"execution_id": "e-1", "journey_id": "j1", "status": "RUNNING"}],
        )
    )
    client = AiEngineClient(url="http://ai-engine.test", enabled=True, http_client=http)

    rows = await client.list_executions(status="RUNNING")
    assert len(rows) == 1
    assert rows[0]["execution_id"] == "e-1"
    http.get.assert_awaited_once()
    assert http.get.await_args.kwargs["params"] == {"status": "RUNNING"}


def test_configured_requires_url_and_enabled() -> None:
    assert AiEngineClient(url="http://x", enabled=True).configured is True
    assert AiEngineClient(url="", enabled=True).configured is False
    assert AiEngineClient(url="http://x", enabled=False).configured is False
