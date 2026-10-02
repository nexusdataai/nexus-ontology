"""
Dynamic Tool Loader.

Compiles a user-authored Python source string (containing
``async def run(params, vdl, connectors, ctx, log)``) into a ``Tool``
that can be registered alongside the code-defined tools.

Responsibilities:

  - parse + compile source on first use, cache by ``(tool_id, version)``
  - on each invocation: build fresh helper instances, dispatch with a
    60 s ``asyncio.wait_for`` watchdog, capture exceptions
  - emit an Audit_Event tagged ``api_id=tool.{tool_id}`` so the existing
    Connector API Workbench audit panel includes user-tool runs
  - on update: invalidate the cache entry for the tool

Trust model: chosen execution path is "Raw Python in-process". This
loader does NOT sandbox; it relies on (a) authenticated builders only,
(b) a curated stdlib namespace in ``dynamic_tool_helpers.make_exec_globals``,
(c) the watchdog timeout for awaitable hangs.
"""

from __future__ import annotations

import asyncio
import time
import traceback
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from loguru import logger

from src.services.control_plane.dynamic_tool_helpers import (
    ConnectorsHelper,
    Ctx,
    ToolLogger,
    VdlHelper,
    make_exec_globals,
)
from src.services.control_plane.tool_registry import RiskLevel, Tool, ToolRegistry

dtl_logger = logger.bind(component="dynamic-tool-loader")

DEFAULT_TIMEOUT_S = 60


class DynamicToolLoader:
    """Compile + cache + dispatch user-authored tools."""

    def __init__(
        self,
        store: Any,
        virtual_query_service: Any = None,
        invoke_connector_fn: Optional[Callable[[str, Dict], Awaitable[Dict]]] = None,
        emit_audit_fn: Optional[Callable[..., Awaitable[Any]]] = None,
        timeout_s: int = DEFAULT_TIMEOUT_S,
    ) -> None:
        """
        store               - ToolStoreService (read-only here; writes happen via API).
        virtual_query_service - injected into VdlHelper.
        invoke_connector_fn   - async callable (api_id, payload) -> dict; usually
                                `connector_api_workbench_api._invoke`.
        emit_audit_fn         - async callable for Audit_Event emission;
                                usually `connector_runtime.emit_audit`.
        timeout_s             - per-invocation watchdog.
        """
        self._store = store
        self._vqs = virtual_query_service
        self._invoke = invoke_connector_fn
        self._emit_audit = emit_audit_fn
        self._timeout_s = timeout_s
        # cache key: (tool_id, version, source_sha256) -> compiled async run callable
        self._compiled: Dict[Tuple[str, int, str], Callable] = {}

    # ------------------------------------------------------------------
    # Compile + cache
    # ------------------------------------------------------------------

    def compile(self, source_code: str) -> Callable:
        """Compile a source string and return its top-level ``run`` coroutine.

        The exec'd module is fresh per compile - do not share state with
        prior compiles. ``make_exec_globals`` is called with stub helpers
        for the compile pass; real helper instances are bound at dispatch
        time (so each invocation gets fresh ctx/log).
        """
        compiled = compile(source_code, filename="<dynamic_tool>", mode="exec")
        # Stub helpers are fine for the import-time exec - tool authors
        # rarely call them at module top-level.
        stub_ctx = Ctx(user="compile-stub")
        ns = make_exec_globals(
            vdl=VdlHelper(self._vqs),
            connectors=ConnectorsHelper(self._invoke, stub_ctx),
            ctx=stub_ctx,
            log=ToolLogger(tool_name="compile-stub"),
        )
        # Single namespace exec: passing the same dict for globals + locals
        # ensures `import` statements at module level bind into the same
        # scope the `run` function closes over.
        exec(compiled, ns)
        run_fn = ns.get("run")
        if run_fn is None or not asyncio.iscoroutinefunction(run_fn):
            raise ValueError(
                "compiled source did not produce a top-level "
                "`async def run(...)` coroutine"
            )
        return run_fn

    def invalidate(self, tool_id: str) -> None:
        """Drop all cache entries for a given tool_id."""
        self._compiled = {
            k: v for k, v in self._compiled.items() if k[0] != tool_id
        }

    def invalidate_all(self) -> None:
        self._compiled.clear()

    # ------------------------------------------------------------------
    # Tool factory
    # ------------------------------------------------------------------

    def make_tool(self, meta: Dict[str, Any]) -> Tool:
        """Wrap a META row from DDB as a ``Tool`` registrable in ``ToolRegistry``."""
        tool_id = meta.get("tool_id") or ""
        name = meta.get("name") or tool_id
        risk = self._to_risk_enum(meta.get("risk_level", "read_only"))
        params = dict(meta.get("parameters") or {"type": "object", "properties": {}, "required": []})
        connector_api = meta.get("connector_api")
        tags = list(meta.get("tags") or [])
        if "dynamic" not in tags:
            tags.append("dynamic")
        version = int(meta.get("current_version", 1))
        source_sha = str(meta.get("source_sha256") or "")
        source_code = meta.get("source_code") or ""

        async def _execute(**kwargs: Any) -> Dict[str, Any]:
            return await self._dispatch(
                tool_id=tool_id,
                tool_name=name,
                version=version,
                source_code=source_code,
                source_sha=source_sha,
                params=kwargs,
                ctx_override=None,
            )

        return Tool(
            name=name,
            description=str(meta.get("description") or ""),
            parameters=params,
            risk_level=risk,
            execute=_execute,
            requires_approval=bool(meta.get("requires_approval", False)),
            cacheable=bool(meta.get("cacheable", False)),
            connector_api=connector_api,
            tags=tags,
            # Phase 1 -- DDB-authored tools land in the ``dynamic``
            # registry bucket. The DDB META row may override via a
            # ``bucket`` field; default keeps the existing rows valid.
            bucket=str(meta.get("bucket") or "dynamic"),
        )

    # ------------------------------------------------------------------
    # Dispatch (used by Tool.execute and by /test endpoint)
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        meta: Dict[str, Any],
        params: Dict[str, Any],
        *,
        ctx_override: Optional[Ctx] = None,
        return_logs: bool = False,
    ) -> Dict[str, Any]:
        """Public dispatch used by the /test endpoint and the journey runner."""
        out = await self._dispatch(
            tool_id=meta.get("tool_id") or "",
            tool_name=meta.get("name") or "",
            version=int(meta.get("current_version", 1)),
            source_code=meta.get("source_code") or "",
            source_sha=str(meta.get("source_sha256") or ""),
            params=params,
            ctx_override=ctx_override,
            return_logs=return_logs,
        )
        return out

    async def _dispatch(
        self,
        *,
        tool_id: str,
        tool_name: str,
        version: int,
        source_code: str,
        source_sha: str,
        params: Dict[str, Any],
        ctx_override: Optional[Ctx],
        return_logs: bool = False,
    ) -> Dict[str, Any]:
        cache_key = (tool_id, version, source_sha)
        run_fn = self._compiled.get(cache_key)
        if run_fn is None:
            try:
                run_fn = self.compile(source_code)
                self._compiled[cache_key] = run_fn
            except Exception as e:
                err = f"compile failed: {e}"
                dtl_logger.error("{} | {}", tool_id, err)
                return self._error(err, return_logs=return_logs)

        ctx = ctx_override or Ctx(
            user="diagnostic-runner",
            tool_id=tool_id,
            tool_name=tool_name,
        )
        log = ToolLogger(tool_name=tool_name or tool_id)
        vdl = VdlHelper(self._vqs)
        connectors = ConnectorsHelper(self._invoke, ctx)

        t0 = time.monotonic()
        try:
            result = await asyncio.wait_for(
                run_fn(params, vdl, connectors, ctx, log),
                timeout=self._timeout_s,
            )
        except asyncio.TimeoutError:
            err = f"tool exceeded {self._timeout_s}s watchdog"
            log.error(err)
            await self._safe_audit(
                ctx=ctx, verb=f"tool.{tool_name}", target=tool_id,
                api_id=f"tool.{tool_id}", payload={"error": err}, status="timeout",
            )
            self._forward_logs_to_run_context(log)
            return self._error(err, return_logs=return_logs, logs=log.lines())
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            tb = traceback.format_exc(limit=8)
            log.error(err, traceback=tb)
            await self._safe_audit(
                ctx=ctx, verb=f"tool.{tool_name}", target=tool_id,
                api_id=f"tool.{tool_id}", payload={"error": err}, status="exception",
            )
            self._forward_logs_to_run_context(log)
            return self._error(err, return_logs=return_logs, logs=log.lines())

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        await self._safe_audit(
            ctx=ctx, verb=f"tool.{tool_name}", target=tool_id,
            api_id=f"tool.{tool_id}",
            payload={"params": params, "duration_ms": elapsed_ms},
            status="ok",
        )

        # Forward the per-tool ``ToolLogger`` buffer to the active
        # RunContext (Copilot Saved studio) so each custom-code
        # ``log.info()`` line becomes a per-step log entry. No-op
        # outside of a Copilot saved-journey run.
        self._forward_logs_to_run_context(log)

        # Conform to the Tool.execute contract: caller expects a dict.
        # If a tool returns a non-dict, wrap it.
        if not isinstance(result, dict):
            result = {"result": result}
        result.setdefault("_meta", {})
        result["_meta"]["duration_ms"] = elapsed_ms
        result["_meta"]["invocation_id"] = ctx.invocation_id
        if return_logs:
            result["_meta"]["logs"] = log.lines()
        return result

    @staticmethod
    def _forward_logs_to_run_context(log: Any) -> None:
        """Push each ``ToolLogger`` line into the active RunContext
        (if any) so custom-code stdout shows up under the Copilot Saved
        studio's per-step view."""
        try:
            from src.services.control_plane.run_context import emit as _emit
            for line in (log.lines() or []):
                level = "INFO"
                msg = ""
                details = None
                if isinstance(line, dict):
                    level = (line.get("level") or "INFO").upper()
                    msg = line.get("message") or line.get("msg") or ""
                    details = {
                        k: v for k, v in line.items()
                        if k not in ("level", "message", "msg")
                    } or None
                else:
                    msg = str(line)
                _emit(level=level, message=msg, details=details, source="custom_code")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _to_risk_enum(v: Any) -> RiskLevel:
        try:
            return RiskLevel(str(v))
        except Exception:
            return RiskLevel.READ_ONLY

    def _error(
        self,
        msg: str,
        *,
        return_logs: bool = False,
        logs: Optional[list] = None,
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {"error": msg}
        if return_logs:
            out["_meta"] = {"logs": logs or []}
        return out

    async def _safe_audit(
        self,
        *,
        ctx: Ctx,
        verb: str,
        target: str,
        api_id: str,
        payload: Dict[str, Any],
        status: str,
    ) -> None:
        if self._emit_audit is None:
            return
        try:
            await self._emit_audit(
                actor=ctx.user, verb=verb, target=target,
                payload={**payload, "status": status,
                         "journey_id": ctx.journey_id,
                         "session_id": ctx.session_id,
                         "invocation_id": ctx.invocation_id},
                api_id=api_id,
            )
        except Exception as e:
            dtl_logger.debug("audit emission failed: {}", e)

    # ------------------------------------------------------------------
    # Bulk registration helper
    # ------------------------------------------------------------------

    async def register_all_active(self, registry: ToolRegistry) -> int:
        """Pull every active tool from the store and register it.

        Code-defined tools registered first (by ``register_*tools``) take
        precedence: if a code-defined tool already owns a name, the
        DDB-defined tool with that name is skipped (warning logged).
        """
        if self._store is None:
            return 0
        try:
            summaries = await self._store.list()
        except Exception as e:
            dtl_logger.warning("list tools for registration failed: {}", e)
            return 0

        existing_names = {t.name for t in registry.list_tools()}
        registered = 0
        for s in summaries:
            if s.name in existing_names:
                dtl_logger.warning(
                    "DDB tool '{}' shadowed by code-defined tool of same name; "
                    "skipping registration", s.name,
                )
                continue
            try:
                doc = await self._store.get(s.tool_id)
                if doc is None:
                    continue
                meta = doc.dict() if hasattr(doc, "dict") else doc
                tool = self.make_tool(meta)
                registry.register(tool)
                registered += 1
            except Exception as e:
                dtl_logger.warning("register {} failed: {}", s.tool_id, e)
        dtl_logger.info("DynamoDB tools registered: {}", registered)
        return registered
