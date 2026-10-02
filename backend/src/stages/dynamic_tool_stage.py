"""
Dynamic Tool Stage.

Lets a journey reference a registered ReAct tool (code-defined OR
DDB-defined) as a journey step. Step config shape:

    {
      "id": "...",
      "tool_id":  "tool-record-payment-v2"   # tool_id OR tool_name
      "tool_name": "record_payment",         # convenience alias
      "params": { ... },                     # raw JSON params, supports
                                             # tiny placeholders:
                                             #   {{ steps.<id>.<key> }}
                                             #   {{ journey.<key> }}
                                             #   {{ params.<key> }}
      "on_error": "fail" | "continue"        # default fail
    }

The runner looks up the tool in the live ``ToolRegistry`` and dispatches
through ``registry.execute(name, resolved_params)``.

Substitution is intentionally minimal - if a journey author needs richer
templating later, swap to Jinja2 inside this file only.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from src.services.control_plane._param_substitution import (
    substitute as _substitute_shared,
)

from .base_stage import BaseStage


def _substitute(value: Any, *, ctx: Dict[str, Any]) -> Any:
    """Backward-compatible wrapper around the shared param substitution.

    Old callers passed ``ctx={"steps":..., "journey":..., "params":...}``;
    the shared helper accepts the same shape verbatim (``journey`` and
    ``params`` are aliases of ``inputs``).
    """
    return _substitute_shared(value, ctx=ctx)


class DynamicToolStage(BaseStage):
    """A stage whose every step dispatches to a registered tool."""

    def __init__(
        self,
        journey_id: str = "ad-hoc",
        stage_id: str = "dynamic_tool",
        job_id: str = "ad-hoc",
        region_name: Optional[str] = None,
        role_arn: Optional[str] = None,
    ) -> None:
        """
        Lightweight init. The base class sets up AWS clients which we
        don't strictly need for tool dispatch; we still call super() so
        any future framework hooks fire, but tolerate failures so the
        stage is constructible in tests / pure async contexts.
        """
        try:
            super().__init__(
                journey_id=journey_id,
                stage_id=stage_id,
                job_id=job_id,
                region_name=region_name,
                role_arn=role_arn,
            )
        except Exception:
            # Minimal fallback: set the attributes BaseStage methods
            # rely on without the AWS-dependent infra.
            self.journey_id = journey_id
            self.stage_id = stage_id
            self.job_id = job_id
            self.logs = []
            self.metrics = {}
            self.artifacts = {}
            import logging as _logging
            self.logger = _logging.getLogger(f"stage.{stage_id}")

    @property
    def stage_name(self) -> str:
        return "Dynamic Tool"

    @property
    def stage_description(self) -> str:
        return "Stage whose steps invoke registered ReAct tools."

    @property
    def steps(self) -> List[Dict[str, Any]]:
        # Steps are user-defined per-journey, so we expose an empty
        # default. The journey runner reads the actual step list from
        # ``step_data`` provided by the journey doc.
        return []

    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper around the async dispatch."""
        return asyncio.get_event_loop().run_until_complete(
            self._execute_step_async(step_id, step_data)
        )

    async def _execute_step_async(
        self, step_id: str, step_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        registry = self._resolve_registry()
        if registry is None:
            self.log_error("ToolRegistry not available", step_id=step_id)
            return {"status": "failed", "step_id": step_id, "error": "registry_unavailable"}

        tool_id = step_data.get("tool_id")
        tool_name = step_data.get("tool_name") or self._tool_name_for_id(registry, tool_id)
        if not tool_name:
            return {"status": "failed", "step_id": step_id, "error": "missing tool_id/tool_name"}

        tool = registry.get(tool_name)
        if tool is None:
            return {"status": "failed", "step_id": step_id, "error": f"tool not registered: {tool_name}"}

        # Resolve {{ }} placeholders in the params dict.
        ctx = {
            "steps": step_data.get("__steps_so_far") or {},
            "journey": step_data.get("__journey") or {},
            "params": step_data.get("__journey_params") or {},
        }
        params = _substitute(step_data.get("params") or {}, ctx=ctx)
        self.log_info(f"dispatching tool {tool_name}", step_id=step_id)

        try:
            result = await registry.execute(tool_name, params)
        except Exception as e:
            self.log_error(f"tool {tool_name} raised: {e}", step_id=step_id)
            on_error = step_data.get("on_error", "fail")
            if on_error == "continue":
                return {"status": "completed", "step_id": step_id, "tool": tool_name, "error": str(e)}
            return {"status": "failed", "step_id": step_id, "tool": tool_name, "error": str(e)}

        if isinstance(result, dict) and "error" in result:
            on_error = step_data.get("on_error", "fail")
            if on_error == "continue":
                return {"status": "completed", "step_id": step_id, "tool": tool_name, "result": result}
            return {"status": "failed", "step_id": step_id, "tool": tool_name, "error": str(result.get("error")), "result": result}

        return {
            "status": "completed",
            "step_id": step_id,
            "tool": tool_name,
            "result": result if isinstance(result, dict) else {"value": result},
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_registry() -> Optional[Any]:
        """Pull the live ToolRegistry off the agent_executor on demand."""
        try:
            from src.apis import control_plane_api as _cp
            ae = getattr(_cp, "_agent_executor", None)
            return ae._tools if ae is not None and hasattr(ae, "_tools") else None
        except Exception:
            return None

    @staticmethod
    def _tool_name_for_id(registry: Any, tool_id: Optional[str]) -> Optional[str]:
        """If only tool_id is given, look up the tool by its id attribute."""
        if not tool_id:
            return None
        try:
            for t in registry.list_tools():
                if getattr(t, "name", None) == tool_id:
                    return t.name
            # Fall back: scan the global tool store metadata for an id->name lookup.
            from src.apis import control_plane_api as _cp
            store = getattr(_cp, "_tool_store", None)
            if store is None:
                return None
            try:
                # this code runs sync inside execute_step; we drop into the loop below.
                loop = asyncio.get_event_loop()
                summaries = loop.run_until_complete(store.list())
            except Exception:
                return None
            for s in summaries:
                if s.tool_id == tool_id:
                    return s.name
        except Exception:
            return None
        return None
