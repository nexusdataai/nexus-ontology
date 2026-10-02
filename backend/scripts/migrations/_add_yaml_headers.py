#!/usr/bin/env python3
"""
One-shot helper that prepends a Cursor-style header band to every YAML
under ``enterprise-knowledge/tools/`` and ``enterprise-knowledge/automation/``
that does NOT already start with one.

Idempotent. Files that already begin with a banner row (``# =+``) are
left alone.

Usage:
    python3 scripts/migrations/_add_yaml_headers.py
    python3 scripts/migrations/_add_yaml_headers.py --tools-only
    python3 scripts/migrations/_add_yaml_headers.py --automation-only
    python3 scripts/migrations/_add_yaml_headers.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_AUTO_ROOT = _BACKEND_ROOT / "enterprise-knowledge" / "automation"
_TOOLS_ROOT = _BACKEND_ROOT / "enterprise-knowledge" / "tools"
_BANNER_RE = re.compile(r"^#\s*=+\s*$")


def _has_header(text: str) -> bool:
    """Return True if the file already begins with a banner row."""
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped:
            continue
        if not stripped.startswith("#"):
            return False
        if _BANNER_RE.match(stripped):
            return True
        # First non-blank is a comment but not a banner: keep scanning a
        # short distance for a banner before bailing.
        return any(_BANNER_RE.match(l.lstrip()) for l in text.splitlines()[:10])
    return False


def _wrap(text: str, width: int = 72) -> str:
    out = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            out.append("")
            continue
        line = ""
        for word in paragraph.split():
            if line and len(line) + 1 + len(word) > width:
                out.append(line)
                line = word
            else:
                line = (line + " " + word).strip()
        if line:
            out.append(line)
    return "\n".join(out)


def _tool_header(doc: Dict[str, Any]) -> str:
    tool_id = doc.get("tool_id", "<unknown>")
    kind = doc.get("tool_kind") or _infer_kind(doc)
    description = (doc.get("description") or "").strip()
    connector = doc.get("connector_api")
    consumes = doc.get("consumes_entities") or []
    produces = doc.get("produces_entities") or []

    cursor_analog = {
        "read":    "ripgrep -- pull rows that match a filter.",
        "analyze": "linter / type-checker -- score rows without writing.",
        "decide":  "agent reasoning step -- pick a branch from prior outputs.",
        "mutate":  "sed -- write a real change to the system of record.",
        "notify":  "post-build script -- push a notification to a channel.",
    }.get(kind, "tool that participates in an automation playbook.")

    inputs = []
    params = doc.get("parameters") or {}
    if isinstance(params, dict):
        for name in (params.get("properties") or {}):
            inputs.append(name)
    inputs_line = ", ".join(inputs) if inputs else "(none)"

    lines = [
        "# ============================================================================",
        f"# Tool: {tool_id}",
        f"# Kind: {kind}",
    ]
    if connector:
        lines.append(f"# Connector API: {connector}")
    lines.append("# ----------------------------------------------------------------------------")
    lines.append(f"# Cursor analog: {cursor_analog}")
    lines.append("#")
    lines.append("# What it does:")
    if description:
        for line in _wrap(description, 70).split("\n"):
            lines.append(f"#   {line}")
    else:
        lines.append("#   (description deferred -- see registry registration for runtime)")
    lines.append("#")
    lines.append(f"# Inputs:    {inputs_line}")
    lines.append(f"# Reads:     {', '.join(consumes) if consumes else 'none'}")
    lines.append(f"# Writes:    {', '.join(produces) if produces else 'none'}")
    lines.append("# ============================================================================")
    return "\n".join(lines) + "\n"


def _infer_kind(doc: Dict[str, Any]) -> str:
    if doc.get("connector_api"):
        # default heuristic from automation_models._infer_tool_kind
        return "mutate"
    if (doc.get("risk_level") or "").lower() == "read_only":
        return "read"
    return "analyze"


def _automation_header(doc: Dict[str, Any]) -> str:
    use_case_id = doc.get("use_case_id", "<unknown>")
    title = doc.get("title", use_case_id)
    solution = doc.get("solution_id", "<unknown>")
    description = (doc.get("description") or "").strip()
    kpis = doc.get("kpi_impact") or []
    tags = doc.get("tags") or []

    stages = doc.get("stages") or []
    stage_summary = []
    for s in stages:
        steps = s.get("steps") or []
        if steps:
            verbs = ", ".join(st.get("name", st.get("step_id", "")) for st in steps[:3])
            stage_summary.append(f"({s.get('stage_id', '?')}) {verbs}{'...' if len(steps) > 3 else ''}")
        else:
            stage_summary.append(f"({s.get('stage_id', '?')}) -- empty --")

    lines = [
        "# ============================================================================",
        f"# Automation: {title}",
        f"# Solution:   {solution}",
        f"# Use case:   {use_case_id}",
        "# ----------------------------------------------------------------------------",
        "# What this playbook does:",
    ]
    if description:
        for line in _wrap(description, 72).split("\n"):
            lines.append(f"#   {line}")
    else:
        lines.append("#   (description deferred -- generated from stage list below)")
    if stage_summary:
        lines.append("#")
        lines.append("# Stages:")
        for s in stage_summary:
            lines.append(f"#   - {s}")
    lines.append("#")
    if kpis:
        lines.append(f"# KPIs:       {', '.join(kpis)}")
    if tags:
        lines.append(f"# Tags:       {', '.join(tags)}")
    lines.append("# ============================================================================")
    return "\n".join(lines) + "\n"


def _process_file(path: Path, kind: str, dry_run: bool) -> str:
    text = path.read_text(encoding="utf-8")
    if _has_header(text):
        return "skip"
    try:
        doc = yaml.safe_load(text) or {}
    except Exception as e:
        return f"error: {e}"

    if not isinstance(doc, dict):
        return "skip-not-mapping"

    header = _tool_header(doc) if kind == "tool" else _automation_header(doc)
    new_text = header + text if text.endswith("\n") else header + text + "\n"
    if dry_run:
        return "would-write"
    path.write_text(new_text, encoding="utf-8")
    return "wrote"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tools-only", action="store_true")
    p.add_argument("--automation-only", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    targets = []
    if not args.tools_only:
        targets.append(("automation", _AUTO_ROOT))
    if not args.automation_only:
        targets.append(("tool", _TOOLS_ROOT))

    totals = {"wrote": 0, "skip": 0, "error": 0, "would-write": 0, "skip-not-mapping": 0}
    for kind, root in targets:
        if not root.exists():
            continue
        for fpath in sorted(root.rglob("*.yaml")):
            res = _process_file(fpath, kind, args.dry_run)
            bucket = res if res in totals else "error"
            if bucket == "error":
                print(f"  {res}: {fpath}", file=sys.stderr)
            totals[bucket] = totals.get(bucket, 0) + 1
            if res in {"wrote", "would-write"}:
                rel = fpath.relative_to(_BACKEND_ROOT)
                print(f"  {res:12s} {rel}")

    print()
    print(f"Header backfill: wrote={totals['wrote']} skip={totals['skip']} "
          f"would-write={totals['would-write']} error={totals['error']} "
          f"skip-not-mapping={totals['skip-not-mapping']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
