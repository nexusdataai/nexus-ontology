"""
RAG Tool for the AI Control Plane.

Exposes semantic search over indexed schema/policy knowledge as an
agent-callable tool.  The agent uses this to look up table definitions,
field meanings, and business rules before taking action.
"""

from typing import Any, Dict, List, Optional

from ..embedding_service import EmbeddingService
from ..vector_store import VectorStore
from ..tool_registry import Tool, RiskLevel
from ..rag_service import RAGService


async def _rag_search(
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    query: str,
    content_type: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    emb = embedding_service.embed_text(query)
    results = await vector_store.search(
        query_embedding=emb,
        content_type=content_type,
        limit=limit,
        min_similarity=0.25,
    )
    return {
        "results": [
            {
                "source_id": r["source_id"],
                "content_type": r["content_type"],
                "content": r["content"][:500],
                "similarity": round(float(r["similarity"]), 4),
            }
            for r in results
        ],
        "total": len(results),
    }


async def _hybrid_rag_search(
    rag_service: RAGService,
    query: str,
    content_type: Optional[str] = None,
    limit: int = 15,
) -> Dict[str, Any]:
    result = await rag_service.hybrid_search(
        query=query, content_type=content_type, limit=limit,
    )

    bundle: Dict[str, Any] = {
        "schemas": [],
        "policies": [],
        "workflows": [],
        "integrations": [],
    }
    graph_traversals: List[Dict[str, str]] = []

    for r in result.get("results", []):
        ct = r.get("content_type", "")
        is_graph = bool(r.get("_graph_expanded"))
        rel_type = r.get("_relation_type", "") if is_graph else ""

        entry = {
            "source_id": r.get("source_id", ""),
            "content": r.get("content", "")[:800],
            "similarity": round(float(r.get("similarity", 0)), 4),
            "via_graph": is_graph,
            "relation_type": rel_type,
        }

        if ct == "onto_schema":
            bundle["schemas"].append(entry)
        elif ct == "onto_policy":
            bundle["policies"].append(entry)
        elif ct == "onto_workflow":
            bundle["workflows"].append(entry)
        elif ct == "onto_integration":
            bundle["integrations"].append(entry)
        else:
            bundle["schemas"].append(entry)

        if is_graph:
            graph_traversals.append({"source_id": entry["source_id"], "relation_type": rel_type})

    graph_hits = result.get("graph_hits", 0)
    rel_counts: Dict[str, int] = {}
    for gt in graph_traversals:
        rt = gt.get("relation_type", "UNKNOWN")
        rel_counts[rt] = rel_counts.get(rt, 0) + 1
    traversal_summary = ", ".join(f"{k}({v})" for k, v in sorted(rel_counts.items())) if rel_counts else "none"

    vec_schemas = sum(1 for s in bundle["schemas"] if not s.get("via_graph"))
    graph_schemas = sum(1 for s in bundle["schemas"] if s.get("via_graph"))
    vec_policies = sum(1 for s in bundle["policies"] if not s.get("via_graph"))
    graph_policies = sum(1 for s in bundle["policies"] if s.get("via_graph"))

    return {
        "retrieval_bundle": bundle,
        "total": result.get("total", 0),
        "vector_hits": result.get("vector_hits", 0),
        "graph_hits": graph_hits,
        "graph_traversals": graph_traversals,
        "graph_traversal_summary": traversal_summary,
        "pipeline_phases": result.get("pipeline_phases", []),
        "summary": (
            f"Found {len(bundle['schemas'])} schemas ({graph_schemas} via graph), "
            f"{len(bundle['policies'])} policies ({graph_policies} via graph), "
            f"{len(bundle['workflows'])} workflows, "
            f"{len(bundle['integrations'])} integrations | "
            f"Graph: {graph_hits} docs via {traversal_summary}"
        ),
    }


def register_rag_tools(
    registry,
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    rag_service: Optional[RAGService] = None,
):
    """Register RAG search tools with the tool registry."""

    registry.register(Tool(
        name="search_schema_knowledge",
        description=(
            "Semantic search over indexed FDW schema metadata, TMF specs, and policies. "
            "Use this to find which tables/columns relate to a concept (e.g. 'billing', "
            "'customer address', 'product pricing') without knowing exact table names."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of what you're looking for",
                },
                "content_type": {
                    "type": "string",
                    "enum": ["fdw_table", "fdw_server", "tmf_spec"],
                    "description": "Optional filter by content type",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
        risk_level=RiskLevel.READ_ONLY,
        execute=lambda **kw: _rag_search(embedding_service, vector_store, **kw),
        cacheable=True,
    ))

    if rag_service:
        registry.register(Tool(
            name="search_enterprise_knowledge",
            description=(
                "Hybrid semantic search over the enterprise knowledge graph. "
                "Combines vector similarity with graph dependency traversal to find "
                "schemas, policies, workflows, and integration mappings related to a concept. "
                "Use this for questions about business rules, approval thresholds, "
                "cross-system dependencies, and field ownership."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language question about enterprise data, policies, or workflows",
                    },
                    "content_type": {
                        "type": "string",
                        "enum": ["onto_schema", "onto_policy", "onto_workflow", "onto_integration"],
                        "description": "Optional filter by knowledge category",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 15)",
                        "default": 15,
                    },
                },
                "required": ["query"],
            },
            risk_level=RiskLevel.READ_ONLY,
            execute=lambda **kw: _hybrid_rag_search(rag_service, **kw),
            cacheable=True,
        ))

    # Phase 1 -- platform-rag bucket for the RAG search surface.
    for tool_name in ("search_schema_knowledge", "search_enterprise_knowledge"):
        tool = registry.get(tool_name)
        if tool is not None:
            tool.bucket = "platform-rag"
