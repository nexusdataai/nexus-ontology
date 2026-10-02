"""
Onto API — REST endpoints for the Semantic RAG knowledge graph.

Provides hybrid search, index statistics, bundle management, and
graph neighborhood queries for the RAG Playground UI.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from loguru import logger

cp_logger = logger.bind(component="onto-api")

router = APIRouter(prefix="/onto", tags=["Onto - Semantic RAG"])

_rag_service = None
_vector_store = None
_graph_store = None
_embedding_service = None


_ensure_init_fn = None


def init_onto_api(rag_service, vector_store, graph_store, embedding_service):
    global _rag_service, _vector_store, _graph_store, _embedding_service
    _rag_service = rag_service
    _vector_store = vector_store
    _graph_store = graph_store
    _embedding_service = embedding_service


def set_init_fn(fn):
    global _ensure_init_fn
    _ensure_init_fn = fn


async def _ensure_ready():
    if _rag_service is None and _ensure_init_fn:
        await _ensure_init_fn()


class HybridSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language query")
    content_type: Optional[str] = Field(None, description="Filter: onto_schema, onto_policy, onto_workflow, onto_integration")
    limit: int = Field(15, ge=1, le=50)
    graph_hops: int = Field(2, ge=0, le=4, description="Graph traversal depth")


class HybridSearchResponse(BaseModel):
    total: int
    vector_hits: int
    graph_hits: int
    by_category: Dict[str, Any]
    results: List[Dict[str, Any]]


@router.post("/search", response_model=HybridSearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    """Hybrid semantic search: vector similarity + graph dependency expansion."""
    await _ensure_ready()
    if not _rag_service:
        return HybridSearchResponse(total=0, vector_hits=0, graph_hits=0, by_category={}, results=[])

    try:
        result = await _rag_service.hybrid_search(
            query=request.query,
            content_type=request.content_type,
            limit=request.limit,
            graph_hops=request.graph_hops,
        )
    except Exception as e:
        cp_logger.warning(f"Hybrid search failed: {e}")
        return HybridSearchResponse(total=0, vector_hits=0, graph_hits=0, by_category={}, results=[])

    return HybridSearchResponse(
        total=result.get("total", 0),
        vector_hits=result.get("vector_hits", 0),
        graph_hits=result.get("graph_hits", 0),
        by_category=result.get("by_category", {}),
        results=[
            {
                "source_id": r.get("source_id", ""),
                "content_type": r.get("content_type", ""),
                "content": r.get("content", "")[:1000],
                "similarity": round(float(r.get("similarity", 0)), 4),
                "metadata": r.get("metadata", {}),
                "graph_expanded": r.get("_graph_expanded", False),
            }
            for r in result.get("results", [])
        ],
    )


@router.get("/stats")
async def get_stats():
    """Get index statistics: document counts by content type."""
    await _ensure_ready()
    if not _vector_store:
        return {"total_embeddings": 0, "onto_documents": 0, "by_content_type": {}, "legacy_embeddings": 0,
                "status": "not_initialized"}

    try:
        total = await _vector_store.count()

        onto_types = ["onto_schema", "onto_policy", "onto_workflow", "onto_integration", "onto_graph_index"]
        by_type = {}
        for ct in onto_types:
            by_type[ct] = await _vector_store.count(content_type=ct)

        legacy_count = total - sum(by_type.values())

        last_indexed_at = await _vector_store.max_updated_at()

        return {
            "total_embeddings": total,
            "onto_documents": sum(v for k, v in by_type.items() if k != "onto_graph_index"),
            "by_content_type": by_type,
            "legacy_embeddings": max(legacy_count, 0),
            "last_indexed_at": last_indexed_at,
        }
    except Exception as e:
        cp_logger.warning(f"Stats query failed (table may not exist yet): {e}")
        return {"total_embeddings": 0, "onto_documents": 0, "by_content_type": {},
                "legacy_embeddings": 0, "status": "table_not_created",
                "hint": "Run the Semantic RAG pipeline to create the knowledge index"}


@router.get("/documents")
async def list_documents(
    content_type: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None, description="Text filter on source_id or content"),
):
    """List indexed documents with pagination and optional text filter."""
    await _ensure_ready()
    if not _vector_store:
        return {"documents": [], "total": 0, "offset": offset, "limit": limit}

    try:
        rows, total = await _vector_store.list(
            content_type=content_type,
            offset=offset,
            limit=limit,
            search_text=q,
        )
        documents = []
        for r in rows:
            meta = r.get("metadata", {})
            if isinstance(meta, str):
                import json as _json
                try:
                    meta = _json.loads(meta)
                except Exception:
                    meta = {}
            documents.append({
                "source_id": r.get("source_id", ""),
                "content_type": r.get("content_type", ""),
                "content": r.get("content", ""),
                "metadata": meta,
                "updated_at": str(r["updated_at"]) if r.get("updated_at") else None,
            })
        return {"documents": documents, "total": total, "offset": offset, "limit": limit}
    except Exception as e:
        cp_logger.warning(f"List documents failed: {e}")
        return {"documents": [], "total": 0, "offset": offset, "limit": limit}


@router.get("/documents/{source_id:path}")
async def get_document(source_id: str):
    """Get a single document by source_id."""
    await _ensure_ready()
    if not _vector_store:
        raise HTTPException(status_code=503, detail="Vector store not initialized")

    try:
        row = await _vector_store.get_by_source_id(source_id)
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        meta = row.get("metadata", {})
        if isinstance(meta, str):
            import json as _json
            try:
                meta = _json.loads(meta)
            except Exception:
                meta = {}
        return {
            "source_id": row.get("source_id", ""),
            "content_type": row.get("content_type", ""),
            "content": row.get("content", ""),
            "metadata": meta,
            "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        cp_logger.warning(f"Get document failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")


@router.get("/graph/{onto_id}")
async def get_graph_neighborhood(onto_id: str, hops: int = Query(2, ge=1, le=4)):
    """Get the graph neighborhood for a document (nodes + edges)."""
    await _ensure_ready()
    if not _graph_store:
        return {"center": onto_id, "hops": hops, "nodes": [], "edges": [], "neighbor_count": 0}

    try:
        neighbors = await _graph_store.expand_neighbors([onto_id], hops=hops)
        all_ids = [onto_id] + [n["onto_id"] for n in neighbors]
        full_subgraph = await _graph_store.get_subgraph(all_ids)

        return {
            "center": onto_id,
            "hops": hops,
            "nodes": full_subgraph.get("nodes", []),
            "edges": full_subgraph.get("edges", []),
            "neighbor_count": len(neighbors),
        }
    except Exception as e:
        cp_logger.warning(f"Graph query failed: {e}")
        return {"center": onto_id, "hops": hops, "nodes": [], "edges": [], "neighbor_count": 0}


@router.get("/bundles")
async def list_bundles():
    """List .onto bundles stored in S3."""
    await _ensure_ready()
    try:
        import boto3
        from src.config.config_provider import get_config
        config = get_config()
        s3 = boto3.client('s3', region_name=config.aws_region)
        bucket = config.s3_recordings_bucket

        response = s3.list_objects_v2(Bucket=bucket, Prefix="onto-bundles/", Delimiter="/")
        prefixes = response.get("CommonPrefixes", [])

        bundles = []
        for p in prefixes:
            prefix = p["Prefix"]
            job_id = prefix.split("/")[1] if "/" in prefix else prefix
            bundles.append({
                "job_id": job_id,
                "bundle_key": f"{prefix}bundle.onto",
                "report_key": f"{prefix}validation-report.json",
            })

        return {"bundles": bundles, "bucket": bucket}

    except Exception as e:
        return {"bundles": [], "error": str(e)}
