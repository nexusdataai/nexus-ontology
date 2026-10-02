#!/usr/bin/env python3
"""
Phase 3 - YAML header-comment linter.

Walks ``enterprise-knowledge/automation/**/*.yaml`` and
``enterprise-knowledge/tools/**/*.yaml`` and verifies that every YAML
file begins with a Cursor-style header comment block (plan section 29).

A valid header band is:
  - The very first non-blank line is a ``#``-prefixed comment.
  - The block contains a banner row matching ``# =+`` (a row of '=').
  - The block contains a ``What this playbook does`` (automation) or
    ``What it does`` (tool) section heading.

CLI:
  python scripts/lint_yaml_headers.py                    # both dirs, strict
  python scripts/lint_yaml_headers.py --phase3-grace     # missing -> warning
  python scripts/lint_yaml_headers.py --tools-only       # tool YAMLs only
  python scripts/lint_yaml_headers.py --automation-only  # automation YAMLs only
  python scripts/lint_yaml_headers.py --json             # machine-readable

Exit codes:
  0 = no violations (or only warnings under --phase3-grace).
  1 = violations found.

The Phase-3 rollout grace period downgrades missing-header to warning so
this can land before the 32 YAMLs are rewritten with header bands.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_AUTOMATION_ROOT = _BACKEND_ROOT / "enterprise-knowledge" / "automation"
_TOOLS_ROOT = _BACKEND_ROOT / "enterprise-knowledge" / "tools"

_BANNER_RE = re.compile(r"^#\s*=+\s*$")
_AUTO_TOPIC_RE = re.compile(r"What this playbook does", re.IGNORECASE)
_TOOL_TOPIC_RE = re.compile(r"What it does", re.IGNORECASE)


@dataclass
class LintIssue:
    file: str
    code: str
    severity: str  # "error" | "warning"
    message: str


def _read_header_lines(path: Path) -> List[str]:
    """Return the contiguous run of comment lines at the top of the file."""
    out: List[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return out
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            out.append(stripped)
            continue
        if not stripped:
            if out:
                # Blank line inside a header band is allowed (visual gap).
                out.append("")
                continue
            # Leading blank lines before any comment - keep scanning.
            continue
        break
    return out


def _check_header(
    path: Path, kind: str, grace: bool
) -> List[LintIssue]:
    rel = str(path)
    header = _read_header_lines(path)
    issues: List[LintIssue] = []

    if not header:
        sev = "warning" if grace else "error"
        issues.append(LintIssue(
            file=rel,
            code="missing_header",
            severity=sev,
            message=(
                "File does not begin with a Cursor-style header comment band. "
                "See plan section 29 for the template."
            ),
        ))
        return issues

    has_banner = any(_BANNER_RE.match(line) for line in header)
    if not has_banner:
        sev = "warning" if grace else "error"
        issues.append(LintIssue(
            file=rel,
            code="missing_banner",
            severity=sev,
            message=(
                "Header has no '# ====' banner row. The decoration is required "
                "so the indexer can reliably identify the header band."
            ),
        ))

    topic_re = _AUTO_TOPIC_RE if kind == "automation" else _TOOL_TOPIC_RE
    expected_topic = "What this playbook does" if kind == "automation" else "What it does"
    has_topic = any(topic_re.search(line) for line in header)
    if not has_topic:
        sev = "warning" if grace else "error"
        issues.append(LintIssue(
            file=rel,
            code="missing_topic_heading",
            severity=sev,
            message=(
                f"Header has no '{expected_topic}' section heading. "
                "See plan section 29 for the template."
            ),
        ))

    return issues


def _walk(root: Path, kind: str, grace: bool) -> List[LintIssue]:
    issues: List[LintIssue] = []
    if not root.exists():
        return issues
    for fpath in sorted(root.rglob("*.yaml")):
        issues.extend(_check_header(fpath, kind, grace))
    return issues


def _bucket(issues: List[LintIssue]) -> Tuple[int, int]:
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    return errors, warnings


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint YAML header comments per plan section 29."
    )
    parser.add_argument(
        "--phase3-grace", action="store_true",
        help="Downgrade missing-header / missing-banner / missing-topic to warning.",
    )
    parser.add_argument(
        "--tools-only", action="store_true",
        help="Only lint enterprise-knowledge/tools/.",
    )
    parser.add_argument(
        "--automation-only", action="store_true",
        help="Only lint enterprise-knowledge/automation/.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit machine-readable JSON (used by automation_diag).",
    )
    parser.add_argument(
        "--automation-root", type=Path, default=_AUTOMATION_ROOT,
    )
    parser.add_argument(
        "--tools-root", type=Path, default=_TOOLS_ROOT,
    )
    args = parser.parse_args(argv)

    issues: List[LintIssue] = []
    if not args.tools_only:
        issues.extend(_walk(args.automation_root, "automation", args.phase3_grace))
    if not args.automation_only:
        issues.extend(_walk(args.tools_root, "tool", args.phase3_grace))

    errors, warnings = _bucket(issues)

    if args.json:
        payload = {
            "ok": errors == 0,
            "errors": errors,
            "warnings": warnings,
            "phase3_grace": args.phase3_grace,
            "issues": [i.__dict__ for i in issues],
        }
        print(json.dumps(payload, indent=2))
    else:
        for i in issues:
            print(f"{i.severity.upper():7s} {i.code:24s} {i.file}: {i.message}")
        print(f"\nlint_yaml_headers: errors={errors} warnings={warnings} "
              f"grace={args.phase3_grace}")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
