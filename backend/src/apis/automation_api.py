"""
Automation Knowledge Base admin API.

Endpoints:
  GET    /api/v1/automation/use-cases             -> light index (vector-derived summaries)
  GET    /api/v1/automation/use-cases/{uc_id}     -> full doc
  POST   /api/v1/automation/reindex               -> re-walk playbooks and re-embed
  GET    /api/v1/automation/connector-apis        -> connector API registry listing
  GET    /api/v1/automation/registry              -> raw AUTOMATION# rows (Phase 3.2)
  POST   /api/v1/automation/registry              -> create/update a playbook YAML
  DELETE /api/v1/automation/registry/{uc_id}      -> delete a playbook YAML
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Path
from loguru import logger
from pydantic import BaseModel

from src.services.control_plane import connector_apis as _ca
from src.services.control_plane.automation_registry_service import (
    get_automation_registry,
)

router = APIRouter(prefix="/api/v1/automation", tags=["Automation"])

_indexer: Any = None


def configure(indexer: Any) -> None:
    global _indexer
    _indexer = indexer


def _svc():
    if not _indexer:
        raise HTTPException(status_code=503, detail="Automation indexer not available")
    return _indexer


@router.get("/use-cases")
async def list_use_cases():
    summaries = await _svc().list_use_cases()
    return {"items": [s.dict() for s in summaries]}


@router.get("/use-cases/{use_case_id}")
async def get_use_case(use_case_id: str):
    doc = await _svc().get_use_case(use_case_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Use case not found: {use_case_id}")
    return doc.dict()


@router.post("/reindex")
async def reindex():
    try:
        stats = await _svc().index_all()
        return stats
    except Exception as e:
        logger.error(f"Automation reindex failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connector-apis")
async def list_connector_apis(target_system: Optional[str] = None):
    if target_system:
        items = await _ca.list_for_system_async(target_system)
    else:
        items = await _ca.list_all_async()
    return {"items": [_ca.to_dict(s) for s in items]}


# ---------------------------------------------------------------------------
# Automation Registry CRUD (Phase 3.2, data-organization spec)
# ---------------------------------------------------------------------------


class AutomationRegistryUpsert(BaseModel):
    use_case_id: str
    solution: str
    yaml_text: str
    source_file: str = ""


def _sanitize(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in item.items() if k not in {"PK", "SK", "GSI1PK", "GSI1SK"}}


@router.get("/registry")
async def list_registry(solution: Optional[str] = None):
    items = await get_automation_registry().list(solution)
    return {"total": len(items), "items": [_sanitize(i) for i in items]}


@router.get("/registry/{use_case_id}")
async def get_registry_entry(use_case_id: str = Path(...)):
    got = await get_automation_registry().get(use_case_id)
    if not got:
        raise HTTPException(status_code=404, detail=f"automation not found: {use_case_id}")
    return _sanitize(got)


@router.post("/registry", status_code=201)
async def upsert_registry_entry(body: AutomationRegistryUpsert):
    saved = await get_automation_registry().upsert(
        body.use_case_id,
        solution=body.solution,
        yaml_text=body.yaml_text,
        source_file=body.source_file,
    )
    return _sanitize(saved)


@router.put("/registry/{use_case_id}")
async def update_registry_entry(
    use_case_id: str = Path(...),
    body: AutomationRegistryUpsert = Body(...),
):
    if body.use_case_id != use_case_id:
        raise HTTPException(
            status_code=400,
            detail="path use_case_id and body use_case_id must match",
        )
    return await upsert_registry_entry(body)


@router.delete("/registry/{use_case_id}", status_code=204)
async def delete_registry_entry(use_case_id: str = Path(...)):
    await get_automation_registry().delete(use_case_id)
    return None
