"""
RAG Service for the AI Control Plane.

Orchestrates:
  1. Semantic vector search over indexed schema/policy metadata
  2. Context construction from retrieved documents
  3. LLM chat completion with augmented context
  4. Source attribution in the response

This is the Enterprise RAG Layer from the architecture doc — it provides
the LLM with real schema definitions, field metadata, and business rules
so it can reason about the data plane without hallucinating.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from .embedding_service import EmbeddingService
from .vector_store import VectorStore
from .llm_client import LLMClient
from .graph_store import GraphStore
from .cache import get_cached, set_cached

cp_logger = logger.bind(component="control-plane")

ENTERPRISE_ONTO_TYPES = (
    "onto_schema",
    "onto_policy",
    "onto_workflow",
    "onto_integration",
)

SYSTEM_PROMPT = """You are an AI assistant for an enterprise data platform with a Virtual Data Layer spanning multiple systems of record.

PLATFORM ARCHITECTURE:
- **Virtual Data Layer**: ~45+ unified schema entities across 6 systems (Salesforce CRM, SAP S/4HANA, Oracle ERP, Google Drive, Social Listening, File Uploads)
- **Mapping Rules**: Connect virtual entities to actual data sources (FDW foreign tables or in-memory simulators)
- **Supply Chain Domain**: Beverage supply chain aligned to SCOR model (Plan, Source, Make, Deliver, Return, Enable) with GS1 identifiers (GTIN, GLN, SSCC)

Your retrieved context contains multiple knowledge types:
- **Schema**: Virtual entity definitions with field types, constraints, SCOR process, GS1 standards, and mapping status (mapped/virtual/unmapped)
- **Policies**: Business rules — inventory management, procurement, quality, supply chain risk, pricing/discount, sustainability, data freshness, order fulfillment, credit, close window, RBAC
- **Workflows**: SCOR-aligned process definitions — demand forecasting, inventory rebalancing, order-to-cash monitoring, supplier risk scoring, production scheduling, quality deviation, ESG reporting
- **Integrations**: Cross-system sync mappings — SF-Oracle sync, SF-SAP demand sync, SAP-Oracle finance sync, SAP inventory feed, unstructured extraction, social listening feed

When answering:
- Identify the source of truth system (Salesforce vs SAP vs Oracle) for each data point
- Note the data status: mapped (live queryable), virtual (integration-only), or mapped via rule (simulator)
- Reference the SCOR process when applicable (Plan/Source/Make/Deliver/Return/Enable)
- Mention applicable policies, approval rules, and thresholds with specific values
- Describe workflow steps and their trigger conditions
- Note cross-system dependencies, sync rules, and integration mappings
- Reference specific field names, GS1 identifiers, policy IDs, and workflow names from the context
- If the context contains field constraints, ALWAYS include them in your answer
- If the context doesn't contain the answer, say so honestly

Do NOT just list table names. Provide business-meaningful answers that include
constraints, dependencies, ownership, SCOR alignment, and approval requirements."""


class RAGService:
    """Enterprise RAG: vector retrieval + LLM reasoning over schema metadata."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        llm_client: LLMClient,
        graph_store: Optional[GraphStore] = None,
    ):
        self._embeddings = embedding_service
        self._vector = vector_store
        self._llm = llm_client
        self._graph = graph_store

    async def ask(
        self,
        question: str,
        content_type: Optional[str] = None,
        context_limit: int = 15,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        rag_key = f"{question.strip().lower()}|{content_type}|{context_limit}"
        cached = await get_cached("rag", rag_key)
        if cached:
            return cached

        query_embedding = self._embeddings.embed_text(question)

        context_docs = await self._vector.search(
            query_embedding=query_embedding,
            content_type=content_type,
            limit=context_limit,
            min_similarity=0.25,
        )

        context_text = self._build_context(context_docs)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"## Retrieved Schema Context\n\n{context_text}\n\n## Question\n\n{question}",
            },
        ]

        llm_result = self._llm.chat(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.1,
        )

        sources = [
            {
                "source_id": doc["source_id"],
                "content_type": doc["content_type"],
                "similarity": round(float(doc["similarity"]), 4),
            }
            for doc in context_docs[:5]
        ]

        result = {
            "answer": llm_result["content"],
            "sources": sources,
            "context_docs_used": len(context_docs),
            "usage": llm_result.get("usage", {}),
        }
        await set_cached("rag", rag_key, result, ttl_s=600)
        return result

    async def hybrid_search(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 15,
        graph_hops: int = 2,
    ) -> Dict[str, Any]:
        """
        Hybrid retrieval: vector similarity search + graph dependency expansion.

        1. Vector search for top-K semantic matches
        2. Extract onto_ids from results
        3. Graph expansion to find related policies, workflows, integrations
        4. Fetch graph-expanded documents from vector store by source_id
        5. Merge, deduplicate, and build structured retrieval bundle
        """
        import time as _time

        hs_key = f"{query.strip().lower()}|{content_type}|{limit}|{graph_hops}"
        cached = await get_cached("rag_hs", hs_key)
        if cached:
            return cached

        t0 = _time.monotonic()
        query_embedding = self._embeddings.embed_text(query)
        embed_ms = round((_time.monotonic() - t0) * 1000)

        t1 = _time.monotonic()
        vector_results = await self._vector.search(
            query_embedding=query_embedding,
            content_type=content_type,
            limit=limit,
            min_similarity=0.20,
            content_types=None if content_type else list(ENTERPRISE_ONTO_TYPES),
        )
        vector_ms = round((_time.monotonic() - t1) * 1000)

        vector_phase = {
            "step": "Vector Search",
            "description": f"Embedded query ({embed_ms}ms), searched {limit} nearest neighbors (min similarity 0.20)",
            "duration_ms": vector_ms + embed_ms,
            "results_count": len(vector_results),
            "top_hits": [
                {"source_id": r.get("source_id", ""), "content_type": r.get("content_type", ""),
                 "similarity": round(float(r.get("similarity", 0)), 3)}
                for r in vector_results[:8]
            ],
        }

        graph_results = []
        graph_phase: Dict[str, Any] = {
            "step": "Graph Expansion",
            "description": "No graph expansion performed",
            "duration_ms": 0,
            "results_count": 0,
            "edges_traversed": [],
        }

        if self._graph and vector_results:
            onto_ids = [
                r.get("metadata", {}).get("onto_id") or r.get("source_id", "")
                for r in vector_results
            ]
            onto_ids = [oid for oid in onto_ids if oid]

            if onto_ids:
                t2 = _time.monotonic()
                try:
                    neighbors = await self._graph.expand_neighbors(onto_ids[:10], hops=graph_hops)
                    if neighbors:
                        seen_vector = {r.get("source_id", "") for r in vector_results}
                        neighbor_ids = [n["onto_id"] for n in neighbors if n["onto_id"] not in seen_vector]

                        edges_traversed = [
                            {"from": n.get("source_id", ""), "to": n["onto_id"],
                             "relation": n.get("relation_type", ""), "hop": n.get("hop_distance", 1)}
                            for n in neighbors if n["onto_id"] not in seen_vector
                        ]

                        for nid in neighbor_ids[:15]:
                            try:
                                ndocs = await self._vector_lookup_by_source_id(nid)
                                for nd in ndocs:
                                    nd["_graph_expanded"] = True
                                    nd["_relation_type"] = next(
                                        (n.get("relation_type", "") for n in neighbors if n["onto_id"] == nid), ""
                                    )
                                    graph_results.append(nd)
                            except Exception:
                                pass

                        graph_ms = round((_time.monotonic() - t2) * 1000)
                        graph_phase = {
                            "step": "Graph Expansion",
                            "description": f"Expanded {len(onto_ids[:10])} seed nodes by {graph_hops} hops in Apache AGE",
                            "duration_ms": graph_ms,
                            "results_count": len(graph_results),
                            "neighbors_found": len(neighbors),
                            "edges_traversed": edges_traversed[:20],
                        }
                except Exception as e:
                    cp_logger.warning(f"Graph expansion failed: {e}")
                    graph_phase["description"] = f"Graph expansion failed: {e}"

        seen = set()
        merged = []
        for doc in vector_results + graph_results:
            sid = doc.get("source_id", "")
            if sid not in seen:
                seen.add(sid)
                merged.append(doc)

        merged.sort(key=lambda d: float(d.get("similarity", 0)), reverse=True)
        merged = merged[:limit]

        by_category: Dict[str, List] = {}
        for doc in merged:
            meta = doc.get("metadata", {})
            cat = meta.get("category", doc.get("content_type", "unknown"))
            by_category.setdefault(cat, []).append({
                "source_id": doc.get("source_id", ""),
                "content_type": doc.get("content_type", ""),
                "content": doc.get("content", ""),
                "similarity": round(float(doc.get("similarity", 0)), 4),
                "metadata": meta,
                "graph_expanded": doc.get("_graph_expanded", False),
                "relation_type": doc.get("_relation_type", ""),
            })

        hs_result = {
            "results": merged,
            "total": len(merged),
            "vector_hits": len(vector_results),
            "graph_hits": len(graph_results),
            "by_category": by_category,
            "pipeline_phases": [vector_phase, graph_phase],
        }
        await set_cached("rag_hs", hs_key, hs_result, ttl_s=600)
        return hs_result

    async def _vector_lookup_by_source_id(self, source_id: str) -> List[Dict[str, Any]]:
        """Look up a document in the vector store by its source_id (exact match via SQL)."""
        from sqlalchemy import text
        import asyncio
        import json

        engine = self._vector._conn.engine
        if engine is None:
            return []

        def _query():
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT content_type, source_id, content, metadata FROM control_plane_embeddings WHERE source_id = :sid LIMIT 1"),
                    {"sid": source_id},
                )
                rows = []
                for row in result.fetchall():
                    meta = row[3] if isinstance(row[3], dict) else json.loads(row[3]) if row[3] else {}
                    rows.append({
                        "content_type": row[0],
                        "source_id": row[1],
                        "content": row[2],
                        "metadata": meta,
                        "similarity": 0.5,
                    })
                return rows

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _query)

    @staticmethod
    def _build_context(docs: List[Dict[str, Any]]) -> str:
        if not docs:
            return "(No matching schema context found in the knowledge base.)"

        sections = []
        for i, doc in enumerate(docs, 1):
            sim = round(float(doc["similarity"]), 3)
            sections.append(
                f"### Source {i} [{doc['content_type']}] (relevance: {sim})\n"
                f"{doc['content']}"
            )
        return "\n\n".join(sections)
