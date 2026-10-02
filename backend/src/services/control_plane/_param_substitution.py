"""
Shared placeholder-substitution helper for journey / step parameter
resolution.

Two equivalent placeholder syntaxes are supported so authors can use
either Jinja-style or Bash-style:

    {{ steps.<step_id>.<key>... }}
    ${ steps.<step_id>.<key>... }

Root namespaces:

  * ``steps.<step_id>.<key>``  -- result of a prior step in the same
                                  journey (the canonical thread).
  * ``stage.<stage_id>.<step_id>.<key>``
                              -- alias of ``steps.<step_id>.<key>``; the
                                 stage prefix lets authors scope by stage.
  * ``inputs.<key>`` / ``params.<key>``
                              -- top-level journey inputs the caller
                                 passed in. ``params`` is an alias retained
                                 for backward compatibility with the
                                 previous DynamicToolStage namespace.
  * ``journey.<key>``         -- legacy alias of ``inputs``.
  * ``context.<key>``         -- per-run metadata: ``run_id``, ``user``.

When a placeholder is the whole string (e.g. ``"${steps.a.list}"``), the
resolved Python value is returned as-is so list/dict references stay
typed. Otherwise the resolved value is stringified into the surrounding
template.

This module is intentionally tiny and dependency-free: it ships with
``re`` only and is imported by both
:pymod:`src.stages.dynamic_tool_stage` (single-step path) and
:pymod:`src.services.control_plane.yaml_journey_runner` (multi-step
path) so both routes substitute identically.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_BRACE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")
_DOLLAR = re.compile(r"\$\{\s*([a-zA-Z0-9_.]+)\s*\}")


def _resolve_path(path: str, *, ctx: Dict[str, Any]) -> Any:
    """Walk a dotted ``head.rest`` path against the substitution context.

    ``ctx`` is the dict assembled by the runner; expected keys are
    ``steps``, ``inputs``, ``params``, ``journey``, ``context``. Unknown
    head names resolve to ``None`` so the caller can fall back to the
    literal placeholder text.

    ``stage.<stage_id>.<step_id>.<key>`` is rewritten to
    ``steps.<step_id>.<key>`` before walking - the stage prefix is a pure
    author convenience.
    """
    parts = path.split(".")
    if not parts:
        return None
    head = parts[0]

    # ``stage.<stage_id>.<step_id>.<key>...`` --> ``steps.<step_id>.<key>...``
    if head == "stage" and len(parts) >= 3:
        parts = ["steps", parts[2], *parts[3:]]
        head = parts[0]

    rest = parts[1:]

    # Resolve the head against the context. The same dotted path works
    # whether the caller passed ``inputs`` (canonical) or one of its
    # legacy aliases ``params`` / ``journey`` as a distinct top-level
    # key. We try the literal head first (preserves the older
    # DynamicToolStage call shape), then fall back to ``inputs`` for the
    # alias names.
    cur: Any = ctx.get(head)
    if cur is None and head in ("params", "journey"):
        cur = ctx.get("inputs")
    if cur is None:
        return None

    for k in rest:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, list):
            try:
                cur = cur[int(k)]
            except Exception:
                return None
        else:
            return None
    return cur


def _expand_placeholders(value: str, *, ctx: Dict[str, Any]) -> Any:
    """Resolve every ``{{...}}`` / ``${...}`` placeholder inside one string.

    If the whole string is a single placeholder, the resolved Python
    value is returned so list / dict references survive (do not get
    stringified).
    """
    stripped = value.strip()

    # Whole-string single placeholder: preserve resolved type.
    m_full = _BRACE.fullmatch(stripped) or _DOLLAR.fullmatch(stripped)
    if m_full:
        return _resolve_path(m_full.group(1), ctx=ctx)

    def _repl(m: "re.Match[str]") -> str:
        v = _resolve_path(m.group(1), ctx=ctx)
        return "" if v is None else str(v)

    out = _BRACE.sub(_repl, value)
    out = _DOLLAR.sub(_repl, out)
    return out


def substitute(value: Any, *, ctx: Dict[str, Any]) -> Any:
    """Recursively replace placeholders inside any value.

    ``value`` may be a string, list, or dict (or any leaf type left
    alone). Returns a new value of the same shape with placeholders
    resolved against ``ctx``.

    ``ctx`` should contain ``steps``, ``inputs``, ``context`` (and
    optionally ``params`` / ``journey`` aliases). Missing keys are
    handled - placeholders against absent roots resolve to ``None``.
    """
    if isinstance(value, str):
        return _expand_placeholders(value, ctx=ctx)
    if isinstance(value, list):
        return [substitute(v, ctx=ctx) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, ctx=ctx) for k, v in value.items()}
    return value


def make_ctx(
    *,
    steps: Optional[Dict[str, Any]] = None,
    inputs: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Tiny convenience for callers that want to skip the dict literal."""
    return {
        "steps": steps or {},
        "inputs": inputs or {},
        "context": context or {},
    }
