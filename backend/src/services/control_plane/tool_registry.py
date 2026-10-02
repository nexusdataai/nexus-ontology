"""
Tool Registry for the AI Control Plane.

Manages available tools that the ReAct agent can invoke.  Each tool has:
  - An OpenAI function-calling definition (name, description, parameters JSON schema)
  - A risk level (read_only, low_risk_write, high_risk_write)
  - An async execute() callable
  - One or more named output relationships (NiFi-style routing channels)

The LLM never calls raw APIs.  It selects a tool, the registry validates
and dispatches, and the result is fed back into the agent loop.

Phase 1 of the ReAct-Tool-improvement plan introduces named output
relationships so a single tool can fan its output out to multiple named
channels, and journeys can wire each channel into a specific downstream
input by ConnectionDoc instead of by ``${steps.X.y}`` substitution.
"""

import inspect
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from loguru import logger
from .cache import get_cached, set_cached

cp_logger = logger.bind(component="control-plane")


# ---------------------------------------------------------------------------
# Phase 2 -- per-tool log surface (registry-injected)
# ---------------------------------------------------------------------------


class ToolLogger:
    """Per-tool log surface that routes through the active RunContext.

    Injected by ``ToolRegistry.execute_with_relationships`` when the
    target tool's ``execute`` callable declares a ``log`` keyword
    parameter. Tools that DON'T declare ``log`` remain wholly
    untouched -- this is opt-in.

    No-op outside of a Copilot saved-journey run (the RunContext
    ``emit`` function silently drops when no context is active), so
    sprinkling ``log.info(...)`` calls into a code-defined tool is
    safe regardless of how the tool is invoked.
    """

    def __init__(self, tool_name: str):
        self._tool = tool_name

    def _emit(self, level: str, msg: str, **kw: Any) -> None:
        try:
            from .run_context import emit as _emit
            details = {"tool": self._tool, **kw} if kw else {"tool": self._tool}
            _emit(level=level, message=msg, details=details, source="tool")
        except Exception:
            pass

    def debug(self, msg: str, **kw: Any) -> None: self._emit("DEBUG", msg, **kw)
    def info(self, msg: str, **kw: Any) -> None: self._emit("INFO", msg, **kw)
    def warning(self, msg: str, **kw: Any) -> None: self._emit("WARNING", msg, **kw)
    def error(self, msg: str, **kw: Any) -> None: self._emit("ERROR", msg, **kw)


class RiskLevel(str, Enum):
    READ_ONLY = "read_only"
    LOW_RISK_WRITE = "low_risk_write"
    HIGH_RISK_WRITE = "high_risk_write"


# ---------------------------------------------------------------------------
# Phase 1 -- named output relationships
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Relationship:
    """A named output channel a tool may emit on.

    Mirrors NiFi's ``Relationship`` concept: every tool declares one or
    more relationships at registration time; at runtime each
    ``execute(...)`` call emits zero or more :class:`RelationshipResult`
    instances, each tagged with the relationship it travelled.

    ``auto_terminate_default=True`` means it is acceptable for a journey
    to leave this relationship unconsumed by any ConnectionDoc; the
    runner does not log a warning in that case. Typical use: a "failure"
    relationship that's only interesting when something goes wrong.
    """

    name: str
    description: str = ""
    auto_terminate_default: bool = False


# Conventional default relationship name used when a tool does not
# explicitly declare an output relationship set. Mirrors the "success"
# relationship most NiFi processors emit on.
DEFAULT_RELATIONSHIP = Relationship(name="success", description="Default channel for single-output tools")


@dataclass
class RelationshipResult:
    """One payload emitted on a named relationship.

    ``data`` keeps the existing tool-return shape (a plain
    ``Dict[str, Any]``); the only new thing is ``relationship`` to label
    which channel it travelled. Tools that previously returned a plain
    dict are auto-wrapped into ``[RelationshipResult("success", dict)]``
    by :meth:`ToolRegistry.execute_with_relationships`.
    """

    relationship: str
    data: Dict[str, Any]


# Type alias for what a tool's ``execute`` callable may return.
# - Plain dict (legacy)                   -> auto-wrapped on the conventional relationship.
# - Single RelationshipResult             -> wrapped into a one-element list.
# - List[RelationshipResult]              -> passed through.
ToolReturn = Union[Dict[str, Any], RelationshipResult, List[RelationshipResult]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    risk_level: RiskLevel
    execute: Callable[..., Coroutine[Any, Any, ToolReturn]]
    requires_approval: bool = False
    cacheable: bool = False
    # api_id of a ConnectorAPISpec from
    # services.control_plane.connector_apis - lets the indexer wire
    # (TOOL)-[:CALLS_API]->(CONNECTOR_API) edges and the diagnostic
    # verify every write tool has a backing connector API.
    connector_api: Optional[str] = None
    # tags surfaced through to_openai_tools metadata for solution-scoped
    # filtering (e.g. ["o2c", "ar"]).
    tags: List[str] = field(default_factory=list)
    # Phase 3 - Cursor-for-data taxonomy: read | analyze | decide | mutate | notify.
    # Optional; when None the heuristic in effective_tool_kind() infers
    # it from risk_level + connector_api so existing registrations keep
    # working unchanged.
    tool_kind: Optional[str] = None
    # Phase 1 -- named output relationships. Defaults to a single
    # "success" channel so unmigrated tools keep working unchanged.
    output_relationships: List[Relationship] = field(
        default_factory=lambda: [DEFAULT_RELATIONSHIP],
    )
    # Phase 1 -- registry bucket / namespace. Mirrors NiFi-Registry's
    # bucket grouping. Defaults to "default" so unmigrated tools keep
    # registering without churn.
    bucket: str = "default"
    # Phase 3 (Data Queues) -- streaming tool flag. When True, ``execute``
    # is expected to return an ``AsyncIterator[RelationshipResult]``;
    # each yielded item is XADDed to its outbound queue as it arrives
    # so downstream consumers can process incrementally. When False
    # (default), ``execute`` returns a single value or list and is
    # awaited to completion before any enqueue happens.
    streaming: bool = False

    def effective_tool_kind(self) -> str:
        """Returns the explicit ``tool_kind`` or the heuristic inference.

        Heuristic (matches automation_models._infer_tool_kind so YAML
        and code-defined tools agree on the default):
          - connector_api set            -> "mutate"
          - risk_level == read_only      -> "read"
          - otherwise                    -> "analyze"
        """
        if self.tool_kind:
            return self.tool_kind
        if self.connector_api:
            return "mutate"
        if self.risk_level == RiskLevel.READ_ONLY:
            return "read"
        return "analyze"

    def relationship_names(self) -> List[str]:
        """Return the names of every declared output relationship."""
        return [r.name for r in self.output_relationships]

    def primary_relationship(self) -> Relationship:
        """The first declared relationship -- the default channel for
        single-output tools and the back-compat target for callers of
        :meth:`ToolRegistry.execute` (which still returns a plain dict).
        """
        return self.output_relationships[0] if self.output_relationships else DEFAULT_RELATIONSHIP


class ToolRegistry:
    """Central registry of tools available to the agent."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        # Phase-2 cache: maps tool.name -> bool indicating whether its
        # ``execute`` callable accepts a ``log`` keyword. Populated
        # lazily on first inspection; ``register`` invalidates the
        # entry if a tool is replaced.
        self._accepts_log_cache: Dict[str, bool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        # Invalidate the log-acceptance cache so a re-registered tool
        # (with a possibly different signature) is re-inspected.
        self._accepts_log_cache.pop(tool.name, None)
        cp_logger.debug(f"Tool registered: {tool.name} (risk={tool.risk_level.value})")

    def _tool_accepts_log(self, tool: "Tool") -> bool:
        """True iff ``tool.execute`` declares a ``log`` keyword
        parameter (either named or via ``**kwargs``). Cached per
        tool name so the signature is inspected at most once per
        process. Defensive against lambdas / partials / builtins
        with unintrospectable signatures -- returns False in those
        cases so injection is skipped silently."""
        cached = self._accepts_log_cache.get(tool.name)
        if cached is not None:
            return cached
        accepts = False
        try:
            target = tool.execute
            if hasattr(target, "__wrapped__"):
                target = target.__wrapped__
            sig = inspect.signature(target)
            # IMPORTANT: only inject ``log`` when the signature
            # explicitly names it as a parameter. We deliberately do
            # NOT auto-inject for ``**kwargs`` forwarders -- those are
            # the most common pattern in register_*_tools today
            # (``lambda **kw: _impl(**kw)``), and forwarding ``log``
            # blind into an inner ``_impl`` that doesn't accept it
            # would raise TypeError. Tools opt in by declaring ``log``
            # explicitly on both the registered callable AND the inner
            # impl (see Section 17.5 seed migrations).
            for p in sig.parameters.values():
                if p.name == "log":
                    accepts = True
                    break
        except (TypeError, ValueError):
            accepts = False
        self._accepts_log_cache[tool.name] = accepts
        return accepts

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def to_openai_tools(self, max_risk: Optional[RiskLevel] = None) -> List[Dict[str, Any]]:
        """Convert registered tools to OpenAI function-calling format.

        If max_risk is specified, only include tools at or below that risk level.
        """
        risk_order = [RiskLevel.READ_ONLY, RiskLevel.LOW_RISK_WRITE, RiskLevel.HIGH_RISK_WRITE]
        max_idx = risk_order.index(max_risk) if max_risk else len(risk_order) - 1

        defs = []
        for tool in self._tools.values():
            if risk_order.index(tool.risk_level) <= max_idx:
                defs.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                })
        return defs

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    #
    # Three entry points, sharing one normalisation pipeline:
    #
    #   execute(name, args)                       -> Dict[str, Any]
    #     Back-compat shim. Returns the data dict from the tool's
    #     PRIMARY (first-declared) relationship, or ``{"error": ...}``
    #     when the tool failed or is unknown. Every legacy caller that
    #     reads ``result["some_key"]`` keeps working unchanged.
    #
    #   execute_with_relationships(name, args)    -> List[RelationshipResult]
    #     Phase 1 relationship-aware path. Tools may return a plain
    #     dict, a RelationshipResult, or a list; the registry normalises
    #     to a list. Multi-channel fan-out (e.g. matched / no_match) is
    #     visible here but collapses to "primary only" in execute().
    #
    #   execute_single(name, args, expected=...)  -> Dict[str, Any]
    #     Convenience for migrated call sites that want one specific
    #     relationship by name. Raises KeyError if the tool did not
    #     emit on ``expected``.

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        results = await self.execute_with_relationships(name, arguments)
        # When execute_with_relationships failed to find the tool or the
        # tool raised, it surfaces a single RelationshipResult on the
        # conventional ``failure`` channel; preserve the legacy
        # ``{"error": ...}`` envelope by returning its data verbatim so
        # downstream callers see the same shape they always have.
        if not results:
            return {}
        primary = results[0]
        return primary.data

    async def execute_with_relationships(
        self, name: str, arguments: Dict[str, Any],
    ) -> List[RelationshipResult]:
        """Execute the tool and normalise its return into a list of
        :class:`RelationshipResult` instances.

        Errors and missing-tool conditions are surfaced as a single
        result on a conventional ``failure`` channel carrying
        ``{"error": "..."}`` so callers can still pattern-match on the
        error key without special-casing exception types.
        """
        tool = self._tools.get(name)
        if not tool:
            return [RelationshipResult(relationship="failure", data={"error": f"Tool '{name}' not found"})]

        cache_key: Optional[str] = None
        if tool.cacheable:
            cache_key = f"{name}|{json.dumps(arguments, sort_keys=True, default=str)}"
            cached = await get_cached("tool", cache_key)
            if cached is not None:
                cp_logger.debug(f"Tool cache hit: {name}")
                # Cached value is the plain-dict shape produced by the
                # legacy execute(...) path. Re-wrap into the primary
                # relationship so the new entry point stays consistent.
                return [RelationshipResult(relationship=tool.primary_relationship().name, data=cached)]

        # Phase-2: if the tool's ``execute`` callable declares a
        # ``log`` keyword, inject a ToolLogger bound to the active
        # RunContext so any ``log.info(...)`` calls inside the tool
        # surface in the Copilot Saved studio's per-step view.
        # Tools that don't declare ``log`` are unaffected.
        injected_args = arguments
        try:
            if "log" not in arguments and self._tool_accepts_log(tool):
                injected_args = {**arguments, "log": ToolLogger(tool_name=name)}
        except Exception:
            pass

        try:
            raw = await tool.execute(**injected_args)
        except Exception as e:
            cp_logger.error(f"Tool '{name}' execution failed: {e}")
            return [RelationshipResult(relationship="failure", data={"error": str(e)})]

        # Phase 3 -- streaming tools may return an AsyncIterator that
        # yields RelationshipResults one at a time. Drain into a list
        # so downstream consumers see the same list shape they do for
        # non-streaming tools. (The XADD-per-yield streaming dispatch
        # ships in a later phase; this scaffolding makes
        # ``Tool.streaming=True`` tools usable today.)
        if hasattr(raw, "__aiter__"):
            results = await self._drain_async_iter(tool, raw)
        else:
            results = self._normalise_to_results(tool, raw)

        if cache_key is not None and results and "error" not in results[0].data:
            # Cache only the primary-channel payload so the cache shape
            # stays compatible with the legacy execute(...) return.
            await set_cached("tool", cache_key, results[0].data, ttl_s=120)

        return results

    async def execute_single(
        self, name: str, arguments: Dict[str, Any], *, expected: str = "success",
    ) -> Dict[str, Any]:
        """Execute the tool and return the data of the ``expected`` relationship.

        Convenience for call sites (stage processors, copilot engine
        fallback) that previously expected ``execute(...)`` to return a
        plain dict and want the explicit-relationship semantics without
        looping over results themselves.

        Raises ``KeyError`` if the tool emitted nothing on ``expected``;
        treats the "failure" channel as a normal return and surfaces it
        when the caller asks for it explicitly.
        """
        results = await self.execute_with_relationships(name, arguments)
        for r in results:
            if r.relationship == expected:
                return r.data
        raise KeyError(
            f"Tool '{name}' emitted no result on relationship '{expected}' "
            f"(channels seen: {[r.relationship for r in results]})"
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_to_results(tool: "Tool", raw: ToolReturn) -> List[RelationshipResult]:
        """Convert a raw tool return into a list of RelationshipResults.

        - ``List[RelationshipResult]`` -> pass through, after asserting
          every relationship is declared on the tool.
        - ``RelationshipResult``       -> wrap in a list (after same assertion).
        - ``Dict``                     -> wrap as a single result on the
          tool's primary relationship. For unmigrated tools this is the
          conventional ``success`` channel.

        A tool that declares multiple relationships but returns a plain
        dict is a coding defect; it is auto-wrapped on the primary
        relationship plus a log warning so the diagnostic catches it.

        Phase 3 (Data Queues) streaming tools that return an
        ``AsyncIterator[RelationshipResult]`` are NOT normalised here
        -- the registry detects them on the public ``execute_with_relationships``
        path and routes through a streaming consumer instead. This
        helper only sees materialised returns.
        """
        declared = set(tool.relationship_names())

        if isinstance(raw, RelationshipResult):
            ToolRegistry._assert_declared(tool, [raw], declared)
            return [raw]

        if isinstance(raw, list):
            if not all(isinstance(r, RelationshipResult) for r in raw):
                cp_logger.warning(
                    f"Tool '{tool.name}' returned a list with non-RelationshipResult items; "
                    "wrapping the whole list under the primary relationship."
                )
                return [RelationshipResult(relationship=tool.primary_relationship().name,
                                           data={"items": raw})]
            ToolRegistry._assert_declared(tool, raw, declared)
            return list(raw)

        if isinstance(raw, dict):
            if len(declared) > 1:
                cp_logger.warning(
                    f"Tool '{tool.name}' declares {sorted(declared)} relationships but returned "
                    "a plain dict; wrapping on the primary relationship. "
                    "Update the tool to return RelationshipResult / List[RelationshipResult]."
                )
            return [RelationshipResult(relationship=tool.primary_relationship().name, data=raw)]

        # Anything else (None, scalars, ...): coerce to a dict-shaped value.
        return [RelationshipResult(
            relationship=tool.primary_relationship().name,
            data={"value": raw},
        )]

    @staticmethod
    async def _drain_async_iter(tool: "Tool", aiter: Any) -> List[RelationshipResult]:
        """Phase 3: drain an ``AsyncIterator[RelationshipResult]`` into a
        list. Items emitted by a streaming tool's async generator are
        collected eagerly here so the existing list-shaped consumer
        path keeps working unchanged. A future phase will move the
        XADD-per-yielded-item dispatch into this drain loop directly.
        """
        results: List[RelationshipResult] = []
        declared = set(tool.relationship_names())
        async for item in aiter:
            if isinstance(item, RelationshipResult):
                results.append(item)
            elif isinstance(item, dict):
                # Auto-wrap dict yields on the primary relationship so
                # streaming tools that just yield dicts keep working.
                results.append(RelationshipResult(
                    relationship=tool.primary_relationship().name, data=item,
                ))
            else:
                results.append(RelationshipResult(
                    relationship=tool.primary_relationship().name, data={"value": item},
                ))
        ToolRegistry._assert_declared(tool, results, declared)
        return results

    @staticmethod
    def _assert_declared(
        tool: "Tool", results: List[RelationshipResult], declared: set,
    ) -> None:
        for r in results:
            if r.relationship not in declared and r.relationship != "failure":
                cp_logger.warning(
                    f"Tool '{tool.name}' emitted relationship '{r.relationship}' which is "
                    f"not declared in output_relationships (declared: {sorted(declared)}). "
                    "The runner will accept it but consumers cannot bind to it."
                )
