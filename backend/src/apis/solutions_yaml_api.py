"""
AI Solutions catalog API (Workspace, Phase 5).

Uses a dedicated ``/api/v1/solution-catalog`` prefix to avoid a routing
collision with the older ``/api/v1/solutions/{solution_id}`` wildcard
served by ``solution_api.py`` (SOLUTION# rows for view mapping). This
router owns the SOLUTIONYAML# rows + NLP search over pgvector.

  GET  /api/v1/solution-catalog
  GET  /api/v1/solution-catalog/{id}
  POST /api/v1/solution-catalog
  DELETE /api/v1/solution-catalog/{id}
  POST /api/v1/solution-catalog/search        - NLP search via pgvector
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Path
from pydantic import BaseModel

from src.services.solutions_yaml_service import get_solutions_yaml_service

router = APIRouter(prefix="/api/v1/solution-catalog", tags=["AI Solutions Catalog"])

_indexer_ref: Any = None


def configure(indexer: Any) -> None:
    """Wire the SolutionsIndexer instance so /search can dispatch."""
    global _indexer_ref
    _indexer_ref = indexer


class SolutionsUpsert(BaseModel):
    solutionId: str
    title: str
    description: str = ""
    priority: Optional[str] = None
    category: Optional[str] = None
    timeToValue: Optional[str] = None
    verticals: List[str] = []
    personas: List[str] = []
    entities: List[str] = []
    kpis: List[str] = []
    automations: List[str] = []
    analytics: List[str] = []
    nlq_examples: List[str] = []
    journeyId: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    sourceYaml: Optional[str] = None


class SolutionsSearchRequest(BaseModel):
    query: str
    limit: int = 5


def _sanitize(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in item.items() if k not in {"PK", "SK", "GSI1PK", "GSI1SK"}}


@router.get("")
async def list_catalog() -> Dict[str, Any]:
    items = await get_solutions_yaml_service().list()
    return {"total": len(items), "items": [_sanitize(i) for i in items]}


@router.post("/search")
async def search_catalog(body: SolutionsSearchRequest = Body(...)) -> Dict[str, Any]:
    if _indexer_ref is None:
        raise HTTPException(status_code=503, detail="solutions indexer not wired")
    hits = await _indexer_ref.search(body.query, limit=body.limit)
    return {"query": body.query, "total": len(hits), "items": hits}


@router.get("/{solution_id}")
async def get_catalog_entry(solution_id: str = Path(...)) -> Dict[str, Any]:
    got = await get_solutions_yaml_service().get(solution_id)
    if not got:
        raise HTTPException(status_code=404, detail=f"solution not found: {solution_id}")
    return _sanitize(got)


@router.post("", status_code=201)
async def upsert_catalog_entry(body: SolutionsUpsert) -> Dict[str, Any]:
    saved = await get_solutions_yaml_service().upsert(
        body.solutionId,
        body.model_dump(),
    )
    return _sanitize(saved)


@router.delete("/{solution_id}", status_code=204)
async def delete_catalog_entry(solution_id: str = Path(...)) -> None:
    await get_solutions_yaml_service().delete(solution_id)
    return None
