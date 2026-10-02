"""
Nexus AI Engine HTTP client.

Submits journey executions to the AI Engine distributed runtime via
``POST /api/v1/executions/`` (spec 060).

Configuration via env / SSM:

- ``AI_ENGINE_URL``                 : base URL (e.g. ``http://nexus-ai-engine-api:8000``)
- ``AI_ENGINE_ENABLED``             : ``true`` / ``false`` — client short-circuit (default ``false``)
- ``AI_ENGINE_EXECUTION_ENABLED``   : alias read by Copilot decoupling (falls back to ``AI_ENGINE_ENABLED``)
- ``AI_ENGINE_TIMEOUT_S``           : request timeout in seconds (default ``30``)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx
from loguru import logger

ai_engine_logger = logger.bind(component="ai_engine")


class AiEngineClientError(Exception):
    """Raised when the AI Engine API returns a non-success response or is unreachable."""

    def __init__(self, message: str, *, status_code: int | None = None, body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class AiEngineClient:
    """
    Async HTTP client for the Nexus AI Engine executions API.

    When disabled (no URL or ``AI_ENGINE_*_ENABLED=false``), methods raise
    ``AiEngineClientError`` with a clear message so callers can fall back to
    in-process Copilot execution during rollout.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        enabled: Optional[bool] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.url = (url or os.environ.get("AI_ENGINE_URL", "")).rstrip("/")
        if enabled is None:
            flag = os.environ.get("AI_ENGINE_EXECUTION_ENABLED")
            if flag is None:
                flag = os.environ.get("AI_ENGINE_ENABLED", "false")
            enabled = str(flag).strip().lower() in ("1", "true", "yes", "on")
        self.enabled = bool(enabled and self.url)
        self._client = http_client
        self._timeout = float(timeout if timeout is not None else os.environ.get("AI_ENGINE_TIMEOUT_S", "30"))
        self._owned_client = http_client is None

    @property
    def configured(self) -> bool:
        return self.enabled

    def _client_or_new(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def aclose(self) -> None:
        if self._owned_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise AiEngineClientError(
                "AI Engine client is not configured (set AI_ENGINE_URL and AI_ENGINE_ENABLED=true)"
            )

    async def submit_execution(
        self,
        *,
        journey_id: str,
        journey_version: Optional[int] = None,
        tenant_id: Optional[str] = None,
        mode: str = "full",
        stage_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        labels: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Submit a journey execution.

        Returns the AI Engine 202 response body:
        ``{ execution_id, status, journey_id, tenant_id, links }``.
        """
        self._require_enabled()

        body: Dict[str, Any] = {
            "journey_id": journey_id,
            "mode": mode,
            "variables": variables or {},
            "labels": labels or {},
            "dry_run": dry_run,
        }
        if journey_version is not None:
            body["journey_version"] = journey_version
        if tenant_id is not None:
            body["tenant_id"] = tenant_id
        if stage_id is not None:
            body["stage_id"] = stage_id

        url = f"{self.url}/api/v1/executions/"
        try:
            cli = self._client_or_new()
            resp = await cli.post(url, json=body, headers={"Accept": "application/json"})
        except httpx.HTTPError as exc:
            ai_engine_logger.error("AI Engine submit_execution transport error: {}", exc)
            raise AiEngineClientError(f"AI Engine unreachable: {exc}") from exc

        if resp.status_code not in (200, 202):
            text = resp.text[:500]
            ai_engine_logger.error(
                "AI Engine submit_execution failed: status={} body={}",
                resp.status_code,
                text,
            )
            raise AiEngineClientError(
                f"AI Engine submit_execution failed: HTTP {resp.status_code}",
                status_code=resp.status_code,
                body=text,
            )

        payload = resp.json()
        ai_engine_logger.info(
            "Submitted execution journey_id={} execution_id={} status={}",
            journey_id,
            payload.get("execution_id"),
            payload.get("status"),
        )
        return payload

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Fetch execution state by ID."""
        self._require_enabled()
        url = f"{self.url}/api/v1/executions/{execution_id}"
        try:
            cli = self._client_or_new()
            resp = await cli.get(url, headers={"Accept": "application/json"})
        except httpx.HTTPError as exc:
            raise AiEngineClientError(f"AI Engine unreachable: {exc}") from exc
        if resp.status_code != 200:
            raise AiEngineClientError(
                f"AI Engine get_execution failed: HTTP {resp.status_code}",
                status_code=resp.status_code,
                body=resp.text[:500],
            )
        return resp.json()

    async def list_executions(
        self,
        *,
        journey_id: Optional[str] = None,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """List executions with optional filters."""
        self._require_enabled()
        params: Dict[str, str] = {}
        if journey_id:
            params["journey_id"] = journey_id
        if status:
            params["status"] = status
        if tenant_id:
            params["tenant_id"] = tenant_id
        url = f"{self.url}/api/v1/executions/"
        try:
            cli = self._client_or_new()
            resp = await cli.get(url, params=params, headers={"Accept": "application/json"})
        except httpx.HTTPError as exc:
            raise AiEngineClientError(f"AI Engine unreachable: {exc}") from exc
        if resp.status_code != 200:
            raise AiEngineClientError(
                f"AI Engine list_executions failed: HTTP {resp.status_code}",
                status_code=resp.status_code,
                body=resp.text[:500],
            )
        data = resp.json()
        return data if isinstance(data, list) else []


_default_client: Optional[AiEngineClient] = None


def get_default_ai_engine_client() -> AiEngineClient:
    global _default_client
    if _default_client is None:
        _default_client = AiEngineClient()
    return _default_client
