"""
Dump the live ToolRegistry into per-tool YAML files under
``enterprise-knowledge/tools/<group>/<tool_id>.yaml``.

This is a one-shot bootstrap. After running it, humans hand-edit the
descriptions, tags, consumes_entities / produces_entities, and example
invocations. Subsequent re-runs are idempotent and skip files that
already exist (use ``--overwrite`` to force).

Usage:

    # Pull from a live backend HTTP endpoint (recommended; avoids the
    # brittle offline re-register path and gets every tool the runtime
    # actually exposes).
    python3 scripts/migrations/dump_tool_catalog.py \\
        --from-url http://localhost:8000/api/v1/control-plane/tools

    # Pull from a backend pod via kubectl exec:
    python3 scripts/migrations/dump_tool_catalog.py \\
        --from-pod nexus-ai-dev-backend-XXXXX --namespace nexus-ai-dev

    # Or re-register tools in-process (legacy; may miss families that
    # require runtime services like sqlalchemy/RAG).
    python3 scripts/migrations/dump_tool_catalog.py

The Python side of the registry stays the source of truth for execution;
the YAML is metadata that powers the knowledge graph + Copilot's
semantic tool discovery.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _tools_root() -> Path:
    return _backend_root() / "enterprise-knowledge" / "tools"


def _infer_group(tool_name: str, tags: list) -> str:
    if tags:
        return str(tags[0])
    if tool_name.startswith("query_"):
        return "virtual_query"
    if "rag" in tool_name or "search_enterprise" in tool_name:
        return "rag"
    if "fdw" in tool_name:
        return "fdw"
    if any(k in tool_name for k in ("hold", "credit", "dunning", "invoice", "case", "outcome", "discount", "expedite")):
        return "o2c"
    return "misc"


def _infer_group_for_dict(name: str, tags: list) -> str:
    return _infer_group(name, tags)


def _build_doc(tool: Any) -> Dict[str, Any]:
    """Construct a ToolDoc-shaped dict from a live Tool registration."""
    name = tool.name
    risk = tool.risk_level.value if hasattr(tool.risk_level, "value") else str(tool.risk_level)
    group = _infer_group(name, list(getattr(tool, "tags", []) or []))
    return {
        "tool_id": name,
        "display_name": name.replace("_", " ").title(),
        "group": group,
        "description": tool.description.strip() if tool.description else "",
        "risk_level": risk,
        "requires_approval": bool(getattr(tool, "requires_approval", False)),
        "cacheable": bool(getattr(tool, "cacheable", False)),
        "parameters": tool.parameters or {"type": "object", "properties": {}},
        "connector_api": getattr(tool, "connector_api", None),
        "consumes_entities": [],
        "produces_entities": [],
        "tags": list(getattr(tool, "tags", []) or []),
        "example_invocation": None,
    }


def _build_doc_from_dict(tool: Dict[str, Any]) -> Dict[str, Any]:
    """Construct a ToolDoc-shaped dict from /api/v1/control-plane/tools JSON."""
    name = tool.get("name") or tool.get("tool_id") or ""
    tags = list(tool.get("tags") or [])
    return {
        "tool_id": name,
        "display_name": tool.get("display_name") or name.replace("_", " ").title(),
        "group": _infer_group(name, tags),
        "description": (tool.get("description") or "").strip(),
        "risk_level": tool.get("risk_level") or "read_only",
        "requires_approval": bool(tool.get("requires_approval", False)),
        "cacheable": bool(tool.get("cacheable", False)),
        "parameters": tool.get("parameters") or {"type": "object", "properties": {}},
        "connector_api": tool.get("connector_api"),
        "consumes_entities": tool.get("consumes_entities") or [],
        "produces_entities": tool.get("produces_entities") or [],
        "tags": tags,
        "example_invocation": tool.get("example_invocation"),
    }


def _fetch_tools_from_url(url: str) -> List[Dict[str, Any]]:
    import urllib.request
    with urllib.request.urlopen(url, timeout=30) as r:
        body = r.read().decode("utf-8")
    import json as _json
    data = _json.loads(body)
    return data.get("tools") or []


def _fetch_tools_from_pod(pod: str, namespace: str) -> List[Dict[str, Any]]:
    import subprocess, json as _json
    out = subprocess.check_output([
        "kubectl", "-n", namespace, "exec", pod, "--",
        "curl", "-s", "http://localhost:8000/api/v1/control-plane/tools",
    ], timeout=30).decode("utf-8")
    return _json.loads(out).get("tools") or []


async def _load_registry():
    """Boot the same wiring the gateway uses so every tool is registered."""
    sys.path.insert(0, str(_backend_root()))
    os.environ.setdefault("DISABLE_BACKGROUND_INDEXERS", "1")

    from src.services.control_plane.tool_registry import ToolRegistry
    registry = ToolRegistry()

    # Best-effort registration mirroring control_plane_api._ensure_init.
    # Failure to register any one family is logged and ignored.
    try:
        from src.services.control_plane.tools.fdw_tools import register_fdw_tools
        register_fdw_tools(registry, fdw_query_service=None)
    except Exception as e:
        print(f"  warn: fdw_tools register skipped: {e}", file=sys.stderr)
    try:
        from src.services.control_plane.tools.rag_tools import register_rag_tools
        register_rag_tools(registry, rag_service=None)
    except Exception as e:
        print(f"  warn: rag_tools register skipped: {e}", file=sys.stderr)
    try:
        from src.services.control_plane.tools.virtual_query_tools import register_virtual_query_tools
        register_virtual_query_tools(registry, virtual_query_service=None)
    except Exception as e:
        print(f"  warn: virtual_query_tools register skipped: {e}", file=sys.stderr)
    try:
        from src.services.control_plane.tools.o2c_tools import register_o2c_tools
        register_o2c_tools(registry, virtual_query_service=None)
    except Exception as e:
        print(f"  warn: o2c_tools register skipped: {e}", file=sys.stderr)
    try:
        from src.services.control_plane.tools.supply_chain_tools import register_supply_chain_tools
        register_supply_chain_tools(registry, virtual_query_service=None)
    except Exception as e:
        print(f"  warn: supply_chain_tools register skipped: {e}", file=sys.stderr)
    try:
        from src.services.control_plane.tools.demand_forecast_tools import register_demand_forecast_tools
        register_demand_forecast_tools(registry, virtual_query_service=None)
    except Exception as e:
        print(f"  warn: demand_forecast_tools register skipped: {e}", file=sys.stderr)
    try:
        from src.services.control_plane.tools.policy_compliance_tool import register_policy_compliance_tool
        register_policy_compliance_tool(registry)
    except Exception as e:
        print(f"  warn: policy_compliance_tool register skipped: {e}", file=sys.stderr)

    return registry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing YAML files")
    parser.add_argument("--group", default=None, help="Only dump tools whose inferred group matches")
    parser.add_argument("--from-url", default=None,
                        help="Pull live tool list from a /api/v1/control-plane/tools URL")
    parser.add_argument("--from-pod", default=None,
                        help="Pull live tool list from a backend pod via kubectl exec")
    parser.add_argument("--namespace", default="nexus-ai-dev",
                        help="Kubernetes namespace for --from-pod (default nexus-ai-dev)")
    parser.add_argument("--out", default=None,
                        help="Override output dir (default: enterprise-knowledge/tools)")
    args = parser.parse_args()

    docs: List[Dict[str, Any]]
    if args.from_url:
        live = _fetch_tools_from_url(args.from_url)
        docs = [_build_doc_from_dict(t) for t in live]
        print(f"Pulled {len(docs)} tools from {args.from_url}")
    elif args.from_pod:
        live = _fetch_tools_from_pod(args.from_pod, args.namespace)
        docs = [_build_doc_from_dict(t) for t in live]
        print(f"Pulled {len(docs)} tools from pod {args.from_pod}")
    else:
        loop = asyncio.new_event_loop()
        try:
            registry = loop.run_until_complete(_load_registry())
        finally:
            loop.close()
        tools = registry.list_tools()
        if not tools:
            print("No tools registered - try --from-url or --from-pod.", file=sys.stderr)
            return 2
        docs = [_build_doc(t) for t in tools]

    out_root = Path(args.out) if args.out else _tools_root()
    out_root.mkdir(parents=True, exist_ok=True)
    backend_root = _backend_root()

    written = 0
    skipped = 0
    for doc in docs:
        if args.group and doc["group"] != args.group:
            continue
        group_dir = out_root / doc["group"]
        group_dir.mkdir(parents=True, exist_ok=True)
        target = group_dir / f"{doc['tool_id']}.yaml"
        if target.exists() and not args.overwrite:
            skipped += 1
            continue
        with target.open("w", encoding="utf-8") as f:
            yaml.dump(doc, f, sort_keys=False, default_flow_style=False)
        written += 1
        try:
            rel = target.relative_to(backend_root)
        except ValueError:
            rel = target
        print(f"  wrote {rel}")

    print()
    print(f"Tools dumped: {written} new / {skipped} skipped (existing) / {len(docs)} total")
    print(f"Catalogue root: {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
