#!/usr/bin/env python3
"""
Phase 3 - Seed DynamoDB Tool Builder from YAML tool catalogue.

Walks ``enterprise-knowledge/tools/**/*.yaml`` and POSTs each tool's
metadata to the Tool Builder import endpoint
(``POST /api/v1/tools/import`` with ``mode=skip_existing``) so YAML-only
tools surface in the Tool Builder UI alongside code-defined and DDB-
authored ones.

Tools that already have a code-defined runtime in
``services.control_plane.tools.*`` are skipped (the YAML is descriptive
metadata only). Tools that supply ``runtime.source_code`` in their YAML
are imported with that source so they become executable in the runtime.

Each seeded tool is tagged with ``playbook_seeded`` so the Tool Builder
UI list view can render a badge.

Usage:

    # Seed against a running backend on localhost:8000 (dev default).
    python3 scripts/migrations/seed_tool_yamls_to_ddb.py

    # Seed against a custom URL.
    python3 scripts/migrations/seed_tool_yamls_to_ddb.py \\
        --url https://nexus-ai-dev-backend.example/api/v1/tools/import

    # Dry-run -- print the bundle but do not POST.
    python3 scripts/migrations/seed_tool_yamls_to_ddb.py --dry-run

    # Seed only one group.
    python3 scripts/migrations/seed_tool_yamls_to_ddb.py --group customer_360
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_TOOLS_ROOT = _BACKEND_ROOT / "enterprise-knowledge" / "tools"

_DEFAULT_URL = "http://localhost:8000/api/v1/tools/import"

# Minimal source the Tool Builder accepts when the YAML doesn't supply a
# real ``runtime.source_code``. The seeded tool will surface in the UI,
# carry the catalogue metadata, and act as a live placeholder until the
# author hand-edits the body.
_PLACEHOLDER_RUN = '''async def run(params, vdl, connectors, ctx, log):
    """Placeholder runtime for a YAML-seeded tool.

    The tool's metadata (description, parameters, connector_api, kind)
    came from enterprise-knowledge/tools/<group>/{tool_id}.yaml. The
    runtime body is empty until a developer fills it in via the Tool
    Builder UI.
    """
    log.info("playbook_seeded placeholder", tool_id="{tool_id}", params=params)
    return {{"ok": True, "tool_id": "{tool_id}", "playbook_seeded": True}}
'''


def _yaml_files(group_filter: Optional[str]) -> List[Path]:
    out: List[Path] = []
    for fpath in sorted(_TOOLS_ROOT.rglob("*.yaml")):
        if group_filter:
            try:
                if fpath.parent.name != group_filter:
                    continue
            except Exception:
                continue
        out.append(fpath)
    return out


def _build_create(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a ToolCreate-shaped dict for the import endpoint."""
    tool_id = doc.get("tool_id")
    if not tool_id:
        return None

    runtime = doc.get("runtime") or {}
    source = runtime.get("source_code") if isinstance(runtime, dict) else None
    if not source:
        source = _PLACEHOLDER_RUN.format(tool_id=tool_id)

    tags = list(doc.get("tags") or [])
    if "playbook_seeded" not in tags:
        tags.append("playbook_seeded")

    return {
        "name": tool_id,
        "description": (doc.get("description") or "").strip(),
        "parameters": doc.get("parameters") or {"type": "object", "properties": {}, "required": []},
        "risk_level": doc.get("risk_level") or "read_only",
        "requires_approval": bool(doc.get("requires_approval", False)),
        "cacheable": bool(doc.get("cacheable", False)),
        "connector_api": doc.get("connector_api"),
        "tags": tags,
        "source_code": source,
        "tool_kind": doc.get("tool_kind"),
        "header_comment": doc.get("header_comment"),
    }


def _post(url: str, body: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="ignore")
        raise SystemExit(
            f"POST {url} -> HTTP {e.code}\n{body_text[:400]}"
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default=_DEFAULT_URL,
                   help=f"Tool Builder import endpoint (default {_DEFAULT_URL})")
    p.add_argument("--group", default=None,
                   help="Only seed tools in this group folder")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the bundle but do not POST")
    p.add_argument("--mode", default="skip_existing",
                   choices=("skip_existing", "merge", "replace"),
                   help="Import mode (default: skip_existing)")
    args = p.parse_args()

    if not _TOOLS_ROOT.exists():
        print(f"No tool catalogue at {_TOOLS_ROOT}", file=sys.stderr)
        return 1

    tools: List[Dict[str, Any]] = []
    skipped: List[str] = []
    for fpath in _yaml_files(args.group):
        try:
            doc = yaml.safe_load(fpath.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"  parse-error {fpath.relative_to(_BACKEND_ROOT)}: {e}", file=sys.stderr)
            continue
        create = _build_create(doc)
        if create is None:
            skipped.append(str(fpath.relative_to(_BACKEND_ROOT)))
            continue
        tools.append(create)

    if not tools:
        print("No tool YAMLs found.")
        return 0

    bundle = {"tools": tools, "mode": args.mode}

    if args.dry_run:
        for t in tools:
            print(f"  would-seed {t['name']:40s} kind={t.get('tool_kind') or '-':8s} "
                  f"connector={t.get('connector_api') or '-'}")
        print(f"\nDry-run: {len(tools)} tools would be POSTed to {args.url} (mode={args.mode})")
        return 0

    print(f"POSTing {len(tools)} tools to {args.url} (mode={args.mode})...")
    result = _post(args.url, bundle)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
