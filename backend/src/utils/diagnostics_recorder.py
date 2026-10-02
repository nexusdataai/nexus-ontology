"""
Diagnostics response-recording middleware (AI-OPs plane, Phase 1).

Intercepts responses on the diagnostic route families and persists a copy
into the ``{cap}-{env}-diagnostics`` DynamoDB table via
``DiagnosticsHistoryService``.

Registered from ``mcp_http_gateway.py`` startup with:

    from src.utils.diagnostics_recorder import register_diagnostics_recorder
    register_diagnostics_recorder(app)

Design:
- Path -> scope mapping is intentionally minimal: the top URL family after
  ``/api/v1/diagnostics/`` (or ``/api/v1/connector-apis/diagnostic``)
  determines the scope tag. Unknown paths are ignored.
- Only successful (2xx) JSON responses under a size cap (256KB) are
  recorded, to keep the diagnostics table lean.
- History-endpoint reads themselves are excluded to avoid recursion.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from fastapi import FastAPI
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp


_MAX_BODY_BYTES = 256 * 1024

# Ordered path->scope patterns. First match wins.
_SCOPE_PATTERNS = [
    # ReAct tools diagnostics (nested prefix, match before the generic one)
    (re.compile(r"^/api/v1/diagnostics/react-tools\b"), "react-tools"),
    # Automation diagnostics
    (re.compile(r"^/api/v1/diagnostics/automation\b"), "automation"),
    # Virtual data diagnostics
    (re.compile(r"^/api/v1/diagnostics/virtual-entities\b"), "virtual-data"),
    # Dashboard diagnostics
    (re.compile(r"^/api/v1/diagnostics/dashboards?\b"), "dashboard"),
    (re.compile(r"^/api/v1/diagnostics/entities/"), "dashboard"),
    (re.compile(r"^/api/v1/diagnostics/backends$"), "dashboard"),
    # Solution diagnostics (o2c, df, io, pa, pq, scr, c360, esg, cpq, simulators)
    (re.compile(r"^/api/v1/diagnostics/(o2c|df|io|pa|pq|scr|c360|esg|cpq|simulators)\b"),
     lambda m: m.group(1)),
    # Connector API diagnostics (health/smoke). Skip mutating invoke calls.
    (re.compile(r"^/api/v1/connector-apis/diagnostic\b"), "connector-apis"),
    (re.compile(r"^/api/v1/connector-apis/smoke-test\b"), "connector-apis-smoke"),
]

# Paths that must never be recorded (would recurse or add noise).
_EXCLUDES = [
    re.compile(r"^/api/v1/diagnostics/history\b"),
    re.compile(r"^/api/v1/ai-health\b"),
]


def _scope_for_path(path: str) -> Optional[str]:
    for pat in _EXCLUDES:
        if pat.match(path):
            return None
    for pat, scope in _SCOPE_PATTERNS:
        m = pat.match(path)
        if m:
            return scope(m) if callable(scope) else scope
    return None


class _DiagnosticsRecorderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)

        # Only POST/GET on JSON bodies for successful diagnostic runs.
        method = request.method.upper()
        if method not in ("GET", "POST"):
            return response

        scope = _scope_for_path(request.url.path)
        if scope is None:
            return response

        status = int(getattr(response, "status_code", 0) or 0)
        if not (200 <= status < 300):
            return response

        media = (response.headers.get("content-type") or "").lower()
        if "application/json" not in media:
            return response

        try:
            body_bytes = b""
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                body_bytes += chunk
                if len(body_bytes) > _MAX_BODY_BYTES:
                    break
        except Exception as e:
            logger.debug(f"diagnostics recorder body-read failed: {e}")
            return response

        # Re-emit unchanged.
        new_resp = Response(
            content=body_bytes,
            status_code=status,
            headers={k: v for k, v in response.headers.items() if k.lower() != "content-length"},
            media_type=response.media_type,
        )

        if len(body_bytes) > _MAX_BODY_BYTES:
            logger.debug(
                f"diagnostics recorder skipped scope={scope} path={request.url.path} "
                f"(body {len(body_bytes)} > cap {_MAX_BODY_BYTES})"
            )
            return new_resp

        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            return new_resp

        try:
            from src.services.diagnostics_history_service import (
                get_diagnostics_history_service,
            )
            svc = get_diagnostics_history_service()
            # summary = minimal top-level fields, keep the full payload as
            # ``result`` (already handled by service.record()).
            summary = {}
            if isinstance(payload, dict):
                for k in ("summary", "status", "healthy", "verdict", "verified", "counts"):
                    if k in payload and not isinstance(payload[k], (list, dict)):
                        summary[k] = payload[k]
            await svc.record(scope=scope, result=payload, summary=summary or None, succeeded=True)
        except Exception as e:
            logger.debug(f"diagnostics recorder persist failed: {e}")

        return new_resp


def register_diagnostics_recorder(app: FastAPI) -> None:
    """Attach the middleware to the FastAPI app."""
    app.add_middleware(_DiagnosticsRecorderMiddleware)
    logger.info("Diagnostics recorder middleware registered")
