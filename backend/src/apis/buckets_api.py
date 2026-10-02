"""Registry-bucket APIs (Phase 1 of ReAct-Tool-improvement).

Surfaces every bucket currently in use by the live ToolRegistry plus
optional bucket metadata sourced from a small in-memory catalogue. The
ToolRegistry is the canonical source of which tools belong to which
bucket; this API just aggregates and exposes it.

Endpoints:
  GET  /api/v1/control-plane/buckets                -> list buckets + counts
  GET  /api/v1/control-plane/buckets/{name}         -> single bucket detail
  GET  /api/v1/control-plane/buckets/{name}/tools   -> tool slice in bucket

Bucket *creation* / mutation is intentionally out of scope for Phase 1
(buckets are identity + namespacing only -- not access policy or
versioning, which are deferred to follow-on plans).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/v1/control-plane/buckets", tags=["Registry Buckets"])

# Filled by ``configure(...)`` at gateway boot time.
_tool_registry: Any = None

# Catalogue of human-readable bucket metadata. Buckets that exist in
# the live registry but are not catalogued surface with their slug as
# both name and description so the UI always has something to render.
_BUCKET_CATALOGUE: Dict[str, Dict[str, str]] = {
    "customer-360": {
        "title": "Customer 360",
        "description": "Churn, upsell, CLV, promotions, CSM outreach.",
    },
    "o2c": {
        "title": "Order-to-Cash",
        "description": "Quoting, three-way match, AR write-backs, dunning, expedite.",
    },
    "supply-chain": {
        "title": "Supply Chain",
        "description": "Inventory, demand forecast, procurement, quality, supplier risk.",
    },
    "esg": {
        "title": "ESG",
        "description": "Sustainability and compliance breach analyzers.",
    },
    "platform-rag": {
        "title": "Platform / RAG",
        "description": "Knowledge retrieval, policy compliance.",
    },
    "notify": {
        "title": "Notify",
        "description": "WhatsApp / email / Slack fan-out.",
    },
    "infra-query": {
        "title": "Infra / Query",
        "description": "FDW + virtual-data-layer reads.",
    },
    "dynamic": {
        "title": "User-authored (DDB)",
        "description": "Tools published via the Tool Builder (DynamoDB).",
    },
    "default": {
        "title": "Uncategorised",
        "description": "Tools that have not yet declared a bucket; surfaced for diagnostics.",
    },
}


def configure(*, tool_registry: Any) -> None:
    """Wire the live ToolRegistry handle. Called by mcp_http_gateway at boot."""
    global _tool_registry
    _tool_registry = tool_registry


def _bucket_meta(name: str) -> Dict[str, str]:
    """Return ``{title, description}`` for ``name``, falling back to the slug."""
    meta = _BUCKET_CATALOGUE.get(name)
    if meta:
        return dict(meta)
    return {"title": name, "description": ""}


def _bucket_summary(name: str, tools: List[Any]) -> Dict[str, Any]:
    meta = _bucket_meta(name)
    return {
        "name": name,
        "title": meta["title"],
        "description": meta["description"],
        "tool_count": len(tools),
        "tools_preview": [t.name for t in tools[:8]],
    }


@router.get("")
async def list_buckets():
    """List every bucket currently surfaced by the live registry.

    The catalogue defaults are merged in so the UI always sees the
    eight canonical buckets even when (e.g. during early boot) no
    tools have registered yet.
    """
    if _tool_registry is None:
        return {"buckets": [], "total": 0, "store": "unconfigured"}

    grouped: Dict[str, List[Any]] = {}
    try:
        for t in _tool_registry.list_tools():
            bucket = getattr(t, "bucket", "default") or "default"
            grouped.setdefault(bucket, []).append(t)
    except Exception as e:
        logger.warning(f"buckets list failed: {e}")
        return {"buckets": [], "total": 0, "error": str(e)}

    # Ensure every catalogued bucket appears, even when empty, so the
    # UI palette can render headings deterministically.
    for catalogued in _BUCKET_CATALOGUE.keys():
        grouped.setdefault(catalogued, [])

    summaries = [_bucket_summary(name, tools) for name, tools in grouped.items()]
    summaries.sort(key=lambda b: (b["name"] != "default", b["name"]))
    return {"buckets": summaries, "total": len(summaries)}


@router.get("/{name}")
async def get_bucket(name: str):
    """Return a single bucket plus the full list of its tools."""
    if _tool_registry is None:
        raise HTTPException(status_code=503, detail="ToolRegistry not configured")

    try:
        tools = [t for t in _tool_registry.list_tools()
                 if (getattr(t, "bucket", "default") or "default") == name]
    except Exception as e:
        logger.warning(f"buckets get failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if not tools and name not in _BUCKET_CATALOGUE:
        raise HTTPException(
            status_code=404,
            detail={"code": "bucket_not_found", "bucket": name},
        )

    meta = _bucket_meta(name)
    return {
        "name": name,
        "title": meta["title"],
        "description": meta["description"],
        "tool_count": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": getattr(t, "description", ""),
                "risk_level": getattr(getattr(t, "risk_level", None), "value", None) or "read_only",
                "tool_kind": getattr(t, "tool_kind", None),
                "tags": list(getattr(t, "tags", []) or []),
                "connector_api": getattr(t, "connector_api", None),
                "output_relationships": [
                    {
                        "name": getattr(r, "name", "success"),
                        "description": getattr(r, "description", ""),
                        "auto_terminate_default": getattr(r, "auto_terminate_default", False),
                    }
                    for r in getattr(t, "output_relationships", None) or []
                ],
            }
            for t in tools
        ],
    }


@router.get("/{name}/tools")
async def list_bucket_tools(name: str, search: Optional[str] = None):
    """Return only the tool name + description slice for a bucket.

    Lighter-weight than ``GET /{name}``; powers the Tool Palette
    grouping in the Journey Builder where only the names are needed.
    """
    detail = await get_bucket(name)
    tools = detail["tools"]
    if search:
        needle = search.lower()
        tools = [t for t in tools if needle in t["name"].lower() or needle in (t["description"] or "").lower()]
    return {
        "name": name,
        "tool_count": len(tools),
        "tools": [{"name": t["name"], "description": t["description"]} for t in tools],
    }
