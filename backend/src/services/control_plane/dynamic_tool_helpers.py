"""
Helpers exposed to user-authored ReAct tools.

Every dynamic tool's ``async def run(params, vdl, connectors, ctx, log)``
receives instances of the four classes here. The shape of these objects
IS the public API for tool authors - keep additions small and well-named.

  vdl        - Virtual Data Layer query helper (VirtualQueryService wrapper)
  connectors - Connector API caller (Workbench /invoke wrapper)
  ctx        - per-invocation context (user, journey_id, session_id, ts)
  log        - buffered logger (returned in /test response so the builder UI shows)
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

ht_logger = logger.bind(component="dynamic-tool-helpers")


# ---------------------------------------------------------------------------
# vdl
# ---------------------------------------------------------------------------

class VdlHelper:
    """Read-only handle on the Virtual Data Layer.

    Methods are coroutine-friendly (always awaitable) so user code can
    write ``rows = await vdl.query(...)`` even when the underlying VQS is
    sync. None of these mutate the simulator - that goes through
    ``connectors``.
    """

    def __init__(self, virtual_query_service: Any) -> None:
        self._vqs = virtual_query_service

    async def query(
        self,
        entity: str,
        *,
        filters: Optional[List[Dict[str, Any]]] = None,
        fields: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query a virtual entity. ``filters`` is a list of ``{field, operator, value}``."""
        if self._vqs is None:
            raise RuntimeError("vdl: virtual query service not configured")
        from src.models.mapping_rule_models import (
            VirtualFilter,
            VirtualQueryRequest,
        )
        req = VirtualQueryRequest(
            virtual_entity=entity,
            fields=fields,
            filters=[VirtualFilter(**f) for f in (filters or [])] or None,
            limit=int(limit),
        )
        resp = await self._vqs.query_virtual_entity(req)
        return list(getattr(resp, "rows", None) or [])

    async def list_entities(self) -> List[str]:
        if self._vqs is None:
            return []
        try:
            entities = await self._vqs.list_virtual_entities()
        except Exception as e:
            ht_logger.debug("vdl.list_entities failed: {}", e)
            return []
        out: List[str] = []
        for e in entities or []:
            if isinstance(e, dict):
                name = e.get("virtual_entity") or e.get("virtualEntity") or e.get("name")
                if name:
                    out.append(str(name))
            else:
                out.append(str(e))
        return out

    async def get_entity_schema(self, entity: str) -> Dict[str, Any]:
        if self._vqs is None or not hasattr(self._vqs, "get_virtual_entity_schema"):
            return {}
        try:
            schema = await self._vqs.get_virtual_entity_schema(entity)
            return schema if isinstance(schema, dict) else {}
        except Exception as e:
            ht_logger.debug("vdl.get_entity_schema failed: {}", e)
            return {}


# ---------------------------------------------------------------------------
# connectors
# ---------------------------------------------------------------------------

class ConnectorsHelper:
    """Connector API caller. Routes through the Workbench ``_invoke`` so
    every call is verified (before/after diff) and audited (emit_audit).
    """

    def __init__(self, invoke_fn: Any, ctx: "Ctx") -> None:
        self._invoke = invoke_fn
        self._ctx = ctx

    async def call(self, api_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self._invoke is None:
            raise RuntimeError("connectors: workbench invoke not configured")
        body = dict(payload or {})
        # Stamp the calling user as actor so audit rows are filterable
        # by who/what initiated the write.
        body.setdefault("actor", self._ctx.user)

        # Bridge per-call log: emit a ``connector_request`` line under
        # the active step so the Copilot Studio drill-down shows what
        # API was called with which top-level keys (values redacted).
        # No-op when no RunContext is active.
        try:
            from src.services.control_plane.run_context import emit as _emit
            _emit(
                level="INFO",
                message=f"Connector API call -> {api_id}",
                details={
                    "api_id": api_id,
                    "payload_keys": sorted(list(body.keys())),
                    "payload": body,
                },
                source="connector_api",
            )
        except Exception:
            pass

        import time as _time
        _t0 = _time.monotonic()
        try:
            result = await self._invoke(api_id, body)
            try:
                from src.services.control_plane.run_context import emit as _emit
                _emit(
                    level="INFO",
                    message=(
                        f"Connector API {api_id} returned in "
                        f"{round((_time.monotonic() - _t0) * 1000)}ms"
                    ),
                    details={
                        "api_id": api_id,
                        "response_keys": (
                            sorted(list(result.keys()))
                            if isinstance(result, dict) else None
                        ),
                        "duration_ms": round((_time.monotonic() - _t0) * 1000),
                    },
                    source="connector_api",
                )
            except Exception:
                pass
            return result
        except Exception as e:
            try:
                from src.services.control_plane.run_context import emit as _emit
                _emit(
                    level="ERROR",
                    message=f"Connector API {api_id} failed: {e}",
                    details={
                        "api_id": api_id,
                        "duration_ms": round((_time.monotonic() - _t0) * 1000),
                    },
                    source="connector_api",
                )
            except Exception:
                pass
            raise


# ---------------------------------------------------------------------------
# ctx
# ---------------------------------------------------------------------------

class Ctx:
    """Per-invocation context handed to user code."""

    __slots__ = ("user", "journey_id", "session_id", "invocation_id", "started_at", "tool_id", "tool_name")

    def __init__(
        self,
        *,
        user: str = "anonymous",
        journey_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> None:
        self.user = user
        self.journey_id = journey_id
        self.session_id = session_id
        self.invocation_id = str(uuid.uuid4())
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.tool_id = tool_id
        self.tool_name = tool_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user": self.user,
            "journey_id": self.journey_id,
            "session_id": self.session_id,
            "invocation_id": self.invocation_id,
            "started_at": self.started_at,
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
        }


# ---------------------------------------------------------------------------
# log
# ---------------------------------------------------------------------------

class ToolLogger:
    """Buffered logger - lines are kept in-memory so the ``/test`` endpoint
    can return them to the builder UI. Also forwards each line to loguru
    bound to the tool name.
    """

    MAX_LINES = 500

    def __init__(self, tool_name: str) -> None:
        self._tool_name = tool_name
        self._buffer: List[Dict[str, Any]] = []
        self._sink = logger.bind(tool=tool_name, component="dynamic-tool")

    def _emit(self, level: str, msg: str, **kwargs: Any) -> None:
        line = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "msg": str(msg),
            "kw": kwargs,
        }
        if len(self._buffer) < self.MAX_LINES:
            self._buffer.append(line)
        try:
            getattr(self._sink, level)("{} | {}", msg, kwargs or "")
        except Exception:
            pass

    def info(self, msg: str, **kwargs: Any) -> None:
        self._emit("info", msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._emit("warning", msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._emit("error", msg, **kwargs)

    # Alias - tool authors often type `log.warn`.
    warn = warning

    def lines(self) -> List[Dict[str, Any]]:
        return list(self._buffer)


# ---------------------------------------------------------------------------
# Allowed builtins for dynamic exec
# ---------------------------------------------------------------------------
#
# The exec namespace is NOT a sandbox (chosen path A: trust authenticated
# builders). We still curate a stdlib subset so a typo doesn't accidentally
# import the wrong thing or shadow a helper name.

ALLOWED_MODULES: Dict[str, Any] = {}


def _build_allowed_modules() -> Dict[str, Any]:
    if ALLOWED_MODULES:
        return ALLOWED_MODULES
    import json as _json
    import datetime as _datetime
    import uuid as _uuid
    import re as _re
    import math as _math
    import decimal as _decimal
    import itertools as _itertools
    import functools as _functools
    import statistics as _statistics
    ALLOWED_MODULES.update({
        "json": _json,
        "datetime": _datetime,
        "uuid": _uuid,
        "re": _re,
        "math": _math,
        "decimal": _decimal,
        "itertools": _itertools,
        "functools": _functools,
        "statistics": _statistics,
        "time": time,
    })
    return ALLOWED_MODULES


def make_exec_globals(
    *,
    vdl: VdlHelper,
    connectors: ConnectorsHelper,
    ctx: Ctx,
    log: ToolLogger,
) -> Dict[str, Any]:
    """Build the globals dict passed to exec() for a tool source string."""
    return {
        "__builtins__": __builtins__,
        # injected helpers - the four args of `async def run(...)` get
        # the same handles via positional injection at call time, but
        # tool authors can also reference these names at module scope.
        "vdl": vdl,
        "connectors": connectors,
        "ctx": ctx,
        "log": log,
        # curated stdlib subset
        **_build_allowed_modules(),
    }
