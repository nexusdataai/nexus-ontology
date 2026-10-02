"""
Onto Data API — REST endpoints for managing Semantic RAG knowledge files in S3.

Provides upload, list, delete, download, and seed operations for
policies, workflows, and integration mappings.
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import Response
from typing import Any, Dict, Optional
from loguru import logger

cp_logger = logger.bind(component="onto-data-api")

router = APIRouter(prefix="/onto-data", tags=["Onto Data - Knowledge Files"])

_service = None


def init_onto_data_api(service):
    global _service
    _service = service


def _get_service():
    if _service is None:
        from src.services.onto_data_service import OntoDataService
        return OntoDataService()
    return _service


@router.get("/files")
async def list_files(category: Optional[str] = Query(None, description="Filter: policies, workflows, integrations")):
    """List knowledge files in S3."""
    svc = _get_service()
    try:
        files = svc.list_files(category)
        return {"files": files, "total": len(files)}
    except Exception as e:
        cp_logger.error(f"List files failed: {e}")
        return {"files": [], "total": 0, "error": str(e)}


@router.post("/files")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(..., description="Category: policies, workflows, integrations"),
):
    """Upload a knowledge file to S3."""
    svc = _get_service()

    if category not in ["policies", "workflows", "integrations"]:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    try:
        result = svc.upload_file(category, file.filename, content, file.content_type or "application/octet-stream")
        return {"success": True, "message": f"Uploaded {file.filename} to {category}", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{key:path}")
async def delete_file(key: str):
    """Delete a knowledge file from S3."""
    svc = _get_service()
    success = svc.delete_file(key)
    if success:
        return {"success": True, "message": f"Deleted {key}"}
    raise HTTPException(status_code=500, detail="Delete failed")


@router.get("/files/{key:path}")
async def download_file(key: str):
    """Download a knowledge file from S3."""
    svc = _get_service()
    content = svc.download_file(key)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    filename = key.split("/")[-1]
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    ct_map = {"md": "text/markdown", "json": "application/json", "yaml": "text/yaml",
              "yml": "text/yaml", "txt": "text/plain", "pdf": "application/pdf"}
    content_type = ct_map.get(ext, "application/octet-stream")

    return Response(content=content, media_type=content_type,
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.post("/seed")
async def seed_defaults():
    """Upload baked-in enterprise-knowledge files into DynamoDB.

    Equivalent to ``foundry/bootstrap?only=policies,workflows,integrations``;
    retained for back-compat with the old S3-seed API surface.
    """
    svc = _get_service()
    try:
        counts = svc.seed_defaults()
        total = sum(counts.values())
        return {"success": True, "message": f"Seeded {total} files", "counts": counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_info():
    """Get info about the knowledge data store."""
    svc = _get_service()
    try:
        return svc.get_info()
    except Exception as e:
        return {"error": str(e), "total_files": 0}


# ---------------------------------------------------------------------------
# Foundry bootstrap — single endpoint that seeds canonical entities +
# policies + workflows + integrations from baked-in enterprise-knowledge
# files into DynamoDB. Called by
# nexus-deployer/backup-restore/scripts/bootstrap_foundry_from_files.py.
# ---------------------------------------------------------------------------

_FOUNDRY_CATEGORIES = {"canonical", "policies", "workflows", "integrations"}


@router.post("/foundry/bootstrap")
async def bootstrap_foundry(
    only: Optional[str] = Query(
        None,
        description=(
            "Comma-separated subset of categories to seed: "
            "canonical, policies, workflows, integrations. "
            "Defaults to all four."
        ),
    ),
    force: bool = Query(False, description="Overwrite existing DDB rows (default: skip)"),
    dry_run: bool = Query(False, description="Plan only; do not write to DDB"),
):
    """Seed the Supply Chain Foundry DDB content from the baked-in
    ``enterprise-knowledge/`` files inside the backend pod.

    Idempotent. Reports per-category counts:
    ``{ canonical: {created, skipped_existing, errors, total}, files: {...} }``.
    """
    requested = set(only.split(",")) if only else set(_FOUNDRY_CATEGORIES)
    requested = {c.strip() for c in requested if c.strip()}
    unknown = requested - _FOUNDRY_CATEGORIES
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown categories: {sorted(unknown)}")

    response: Dict[str, Any] = {"force": force, "dry_run": dry_run, "requested": sorted(requested)}

    # --- Canonical entities (VDLENTITY# rows) ---
    if "canonical" in requested:
        try:
            from src.services.vdl_catalog_service import get_catalog
            catalog = get_catalog()
            response["canonical"] = catalog.seed_from_file(force=force, dry_run=dry_run)
            # Refresh the in-memory cache so the next request reflects the writes.
            if not dry_run and (response["canonical"].get("created") or 0) > 0:
                catalog.refresh()
        except Exception as e:
            cp_logger.error(f"bootstrap canonical failed: {e}")
            response["canonical"] = {"error": str(e), "created": 0, "skipped_existing": 0, "errors": 1, "total": 0}

    # --- Policies / Workflows / Integrations (file rows) ---
    file_categories = {"policies", "workflows", "integrations"} & requested
    if file_categories:
        svc = _get_service()
        file_result = {"created": 0, "skipped_existing": 0, "errors": 0, "by_category": {}}
        for cat in sorted(file_categories):
            cat_stats = _seed_file_category(svc, cat, force=force, dry_run=dry_run)
            file_result["by_category"][cat] = cat_stats
            file_result["created"] += cat_stats.get("created", 0)
            file_result["skipped_existing"] += cat_stats.get("skipped_existing", 0)
            file_result["errors"] += cat_stats.get("errors", 0)
        response["files"] = file_result

    return response


def _seed_file_category(svc, category: str, force: bool, dry_run: bool) -> Dict[str, Any]:
    """Walk the enterprise-knowledge category directory and upload each
    file via ``OntoDataService.upload_file`` (which routes to DDB)."""
    import os
    from src.services.onto_data_service import ENTERPRISE_KNOWLEDGE_DIR, SAMPLE_DATA_DIR, _filename_to_slug, _content_type_for_extension

    stats = {"created": 0, "skipped_existing": 0, "errors": 0, "total": 0, "details": []}

    candidate_dirs = []
    for base in (ENTERPRISE_KNOWLEDGE_DIR, SAMPLE_DATA_DIR):
        cat_dir = os.path.join(base, category)
        if os.path.isdir(cat_dir):
            candidate_dirs.append(cat_dir)
    if not candidate_dirs:
        return stats

    seen_slugs: set = set()
    existing_slugs: set = set()
    try:
        existing_slugs = {_filename_to_slug(f["filename"]) for f in svc.list_files(category)}
    except Exception:
        existing_slugs = set()

    for cat_dir in candidate_dirs:
        for filename in sorted(os.listdir(cat_dir)):
            filepath = os.path.join(cat_dir, filename)
            if not os.path.isfile(filepath):
                continue
            slug = _filename_to_slug(filename)
            if slug in seen_slugs:
                continue  # enterprise-knowledge wins over sample-data on duplicate slugs
            seen_slugs.add(slug)
            stats["total"] += 1

            if slug in existing_slugs and not force:
                stats["skipped_existing"] += 1
                continue
            if dry_run:
                stats["details"].append({"slug": slug, "action": "would_create"})
                stats["created"] += 1
                continue

            try:
                with open(filepath, "rb") as fh:
                    content = fh.read()
                ext = os.path.splitext(filename)[1].lower()
                ct = _content_type_for_extension(ext)
                svc.upload_file(category, filename, content, ct)
                stats["created"] += 1
            except Exception as e:
                cp_logger.warning(f"bootstrap {category}: failed to upload {filename}: {e}")
                stats["errors"] += 1

    return stats
