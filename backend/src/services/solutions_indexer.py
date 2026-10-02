"""
Solutions indexer (Workspace, Phase 5)

Embeds each ``SOLUTIONYAML#`` row into pgvector under the
``onto_solution`` content type so NLP search from the App Catalogue
works.

Best-effort: pgvector/embedding failures are logged, not raised.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from src.services.solutions_yaml_service import get_solutions_yaml_service


_CONTENT_TYPE = "onto_solution"


def _solution_to_document(row: Dict[str, Any]) -> str:
    """Flatten a solution YAML row into a single text blob for embedding."""
    parts: List[str] = []
    parts.append(str(row.get("title") or row.get("solutionId") or ""))
    parts.append(str(row.get("description") or ""))
    for key in ("category", "priority", "timeToValue"):
        v = row.get(key)
        if v:
            parts.append(f"{key}: {v}")
    for list_key in ("verticals", "personas", "entities", "kpis", "automations", "analytics", "nlq_examples"):
        vals = row.get(list_key) or []
        if isinstance(vals, list) and vals:
            parts.append(f"{list_key}: {', '.join(str(v) for v in vals)}")
    return "\n".join(p for p in parts if p)


class SolutionsIndexer:
    def __init__(self, embedding_service: Any, vector_store: Any) -> None:
        self._embed = embedding_service
        self._vector = vector_store

    async def index_all(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {"indexed": 0, "errors": []}
        try:
            rows = await get_solutions_yaml_service().list()
        except Exception as e:
            logger.warning(f"SolutionsIndexer list failed: {e}")
            return {"indexed": 0, "errors": [str(e)]}

        for row in rows:
            try:
                doc_text = _solution_to_document(row)
                if not doc_text:
                    continue
                embedding = self._embed.embed_text(doc_text)
                source_id = str(row.get("solutionId") or row.get("PK", "").split("#", 1)[-1])
                metadata = {
                    "title": row.get("title"),
                    "category": row.get("category"),
                    "verticals": row.get("verticals") or [],
                    "personas": row.get("personas") or [],
                    "priority": row.get("priority"),
                    "timeToValue": row.get("timeToValue"),
                }
                await self._vector.upsert(
                    content_type=_CONTENT_TYPE,
                    source_id=source_id,
                    content=doc_text,
                    embedding=embedding,
                    metadata=metadata,
                )
                stats["indexed"] += 1
            except Exception as e:
                logger.warning(f"SolutionsIndexer failed for {row.get('solutionId')}: {e}")
                stats["errors"].append(str(e))
        if stats["indexed"]:
            logger.info(f"SolutionsIndexer indexed {stats['indexed']} solutions into pgvector")
        return stats

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            embedding = self._embed.embed_text(query)
        except Exception as e:
            logger.warning(f"SolutionsIndexer.search embed failed: {e}")
            return []
        try:
            hits = await self._vector.search(
                query_embedding=embedding,
                content_type=_CONTENT_TYPE,
                limit=limit,
                min_similarity=0.2,
            )
            return hits
        except Exception as e:
            logger.warning(f"SolutionsIndexer.search failed: {e}")
            return []
