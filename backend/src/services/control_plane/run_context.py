"""
RunContext -- a ``contextvars.ContextVar``-based carrier for
``(journey_id, job_id, step_id)`` so deep sub-call sites (virtual
queries, connector APIs, custom code) can emit per-step log entries
through the ``JourneyExecutorBridge`` without widening every
internal function signature.

Set in ``CopilotEngine._call_tool`` just before tool dispatch; reset
afterwards. When unset (e.g. ad-hoc Copilot chat, regular Journeys
runtime, unit tests) every ``emit(...)`` call is a no-op so this is
safe to call unconditionally from instrumented services.
"""

from __future__ import annotations

import logging
import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


_REDACT_KEY_RX = re.compile(
    r"(token|secret|password|api[_-]?key|auth(?:orization)?|bearer|cookie)",
    re.IGNORECASE,
)
_REDACT_MARKER = "***"


def redact(value: Any, _depth: int = 0) -> Any:
    """Walk a dict / list and replace values whose key matches a
    secret-ish regex with ``***``. Strings / scalars at the top level
    pass through unchanged."""
    if _depth > 6:
        return value
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            if isinstance(k, str) and _REDACT_KEY_RX.search(k):
                out[k] = _REDACT_MARKER
            else:
                out[k] = redact(v, _depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(v, _depth + 1) for v in value]
    return value


@dataclass
class RunContext:
    """Active Copilot-run scope for emitting per-step logs."""

    journey_id: str
    job_id: str
    step_id: str
    bridge: Any = None  # JourneyExecutorBridge -- kept as Any to avoid import cycle
    # Extra metadata that emit() may stash on the log entry. Unused
    # for now but lets us thread tool_name / connector_api / etc.
    meta: Dict[str, Any] = field(default_factory=dict)


_current_run: ContextVar[Optional[RunContext]] = ContextVar(
    "copilot_run_context", default=None,
)


def get_current() -> Optional[RunContext]:
    return _current_run.get()


def set_current(ctx: Optional[RunContext]):
    """Set the active context and return the token so callers can
    ``reset(token)`` after the scope ends."""
    return _current_run.set(ctx)


def reset(token) -> None:
    try:
        _current_run.reset(token)
    except Exception:
        # Token from a different context -- best effort.
        pass


def emit(
    level: str = "INFO",
    message: str = "",
    details: Optional[Dict[str, Any]] = None,
    source: str = "tool",
) -> None:
    """Append a log entry under the active step. No-op when there is
    no active ``RunContext`` (ad-hoc chat / regular Journeys / tests).

    ``details`` is redacted before being persisted.
    """
    ctx = _current_run.get()
    if ctx is None or ctx.bridge is None:
        return
    safe_details = redact(details) if details else None
    try:
        ctx.bridge.write_step_log(
            journey_id=ctx.journey_id,
            job_id=ctx.job_id,
            step_id=ctx.step_id,
            level=(level or "INFO").upper(),
            message=message or "",
            details=safe_details,
            source=source,
        )
    except Exception as e:
        logger.debug("run_context.emit suppressed: %s", e)
