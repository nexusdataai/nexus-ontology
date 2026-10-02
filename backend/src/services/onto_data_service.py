"""
Onto Data Service

DynamoDB-backed storage for Semantic RAG knowledge documents (policies,
workflows, integration mappings) — part of the Supply Chain Foundry
consolidation (Stage 2).

Items are stored as ``POLICY#{slug}``, ``WORKFLOWDEF#{slug}`` and
``INTEGRATIONDEF#{slug}`` rows in the ``foundry-workspace`` table; the
original file content rides under ``contentText`` (UTF-8 string) with
structured metadata alongside.

The public API surface (``list_files``, ``upload_file``, ``delete_file``,
``download_file``, ``download_category_to_temp``, ``seed_defaults``,
``get_info``) is preserved verbatim from the previous S3-backed
implementation so that ``/api/v1/control-plane/onto-data/*`` API
consumers (UI Policy Builder, Workflows, Integration Rules tabs) and the
Knowledge Processor extractors continue to work unchanged.
"""

import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

onto_logger = logger.bind(component="onto-data")

VALID_CATEGORIES = ["policies", "workflows", "integrations"]

CATEGORY_EXTENSIONS = {
    "policies": [".md", ".txt", ".pdf"],
    "workflows": [".yaml", ".yml", ".json"],
    "integrations": [".json", ".yaml", ".yml"],
}

# Default filename extensions used when the slug-only key has no
# embedded extension. Mirrors the historical extension-by-category
# convention so that the Knowledge Processor extractors (which dispatch
# by extension via glob patterns) keep matching content.
DEFAULT_EXTENSION = {
    "policies": ".md",
    "workflows": ".yaml",
    "integrations": ".yaml",
}

SAMPLE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "stages", "semantic-rag", "sample-data"
)

ENTERPRISE_KNOWLEDGE_DIR = os.path.join(
    os.environ.get("APP_ROOT", "/app"), "enterprise-knowledge"
)


def _filename_to_slug(filename: str) -> str:
    """Strip the extension off a filename to produce a DDB slug.

    ``credit-policy.md`` -> ``credit-policy``. Extensionless names are
    returned as-is.
    """
    base = os.path.basename(filename)
    root, _ext = os.path.splitext(base)
    return root or base


def _key_to_category_slug(key: str) -> Optional[tuple]:
    """Parse an API key like ``policies/credit-policy.md`` -> ``("policies", "credit-policy")``.

    Returns ``None`` if the key doesn't conform.
    """
    parts = key.split("/", 1)
    if len(parts) != 2:
        return None
    category, filename = parts
    if category not in VALID_CATEGORIES:
        return None
    return category, _filename_to_slug(filename)


def _content_type_for_extension(ext: str) -> str:
    ext = ext.lower()
    if ext == ".json":
        return "application/json"
    if ext in (".yaml", ".yml"):
        return "text/yaml"
    if ext == ".md":
        return "text/markdown"
    if ext == ".pdf":
        return "application/pdf"
    if ext == ".txt":
        return "text/plain"
    return "application/octet-stream"


class OntoDataService:
    """DDB-backed manager for Semantic RAG knowledge files.

    Constructor signature is preserved for backward compatibility — the
    legacy ``bucket``/``prefix``/``region`` arguments are accepted but
    ignored (S3 is no longer the backing store).
    """

    # Maps API category names to repository method suffixes.
    _CRUD_BY_CATEGORY = {
        "policies": ("put_policy", "get_policy", "list_policies", "delete_policy"),
        "workflows": ("put_workflow_def", "get_workflow_def", "list_workflow_defs", "delete_workflow_def"),
        "integrations": ("put_integration_def", "get_integration_def", "list_integration_defs", "delete_integration_def"),
    }

    def __init__(self, bucket: str = "", prefix: str = "onto-data", region: str = "us-east-1"):
        # Legacy arguments preserved for backward compatibility; they are
        # surfaced via get_info() so operators reading the API response can
        # see which DDB table backs the service.
        self._legacy_bucket = bucket
        self._legacy_prefix = prefix
        self._region = region
        self._repo = None

    def _get_repo(self):
        if self._repo is None:
            try:
                from src.repositories.foundry_workspace_repository import (
                    FoundryWorkspaceRepository,
                )
                self._repo = FoundryWorkspaceRepository()
            except Exception as e:
                onto_logger.error(f"OntoDataService: foundry-workspace not available: {e}")
                self._repo = None
        return self._repo

    # ------------------------------------------------------------------
    # Public API (S3-era contract preserved for /onto-data/* consumers)
    # ------------------------------------------------------------------

    def list_files(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        repo = self._get_repo()
        if repo is None:
            return []

        categories = [category] if category and category in VALID_CATEGORIES else VALID_CATEGORIES
        files: List[Dict[str, Any]] = []
        for cat in categories:
            _put, _get, list_fn_name, _del = self._CRUD_BY_CATEGORY[cat]
            try:
                rows = getattr(repo, list_fn_name)()
            except Exception as e:
                onto_logger.warning(f"OntoDataService: list {cat} failed: {e}")
                continue
            for row in rows:
                filename = row.get("filename") or self._default_filename(cat, row.get("slug") or "")
                key = f"{cat}/{filename}"
                files.append({
                    "key": key,
                    "filename": filename,
                    "category": cat,
                    "size": int(row.get("sizeBytes") or len((row.get("contentText") or "").encode("utf-8"))),
                    "last_modified": row.get("updatedAt") or row.get("createdAt") or "",
                })
        return files

    def upload_file(
        self,
        category: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {category}. Must be one of {VALID_CATEGORIES}")

        repo = self._get_repo()
        if repo is None:
            raise RuntimeError("foundry-workspace DDB not available")

        slug = _filename_to_slug(filename)
        text = self._decode_content(content)
        now = datetime.now(timezone.utc).isoformat()

        attrs = {
            "slug": slug,
            "filename": filename,
            "category": category,
            "contentType": content_type,
            "contentText": text,
            "sizeBytes": len(content),
            "sourceFile": filename,
            "updatedAt": now,
        }
        # Preserve createdAt across overwrites.
        put_fn_name, get_fn_name, _list, _del = self._CRUD_BY_CATEGORY[category]
        existing = getattr(repo, get_fn_name)(slug)
        attrs["createdAt"] = (existing or {}).get("createdAt") or now

        getattr(repo, put_fn_name)(slug, attrs)
        key = f"{category}/{filename}"
        onto_logger.info(f"OntoDataService: stored {key} ({len(content)} bytes)")
        return {"key": key, "bucket": self._backing_table_name(), "size": len(content)}

    def delete_file(self, key: str) -> bool:
        repo = self._get_repo()
        if repo is None:
            return False

        parsed = _key_to_category_slug(key)
        if parsed is None:
            onto_logger.warning(f"OntoDataService: unparseable delete key {key!r}")
            return False
        category, slug = parsed

        _put, _get, _list, del_fn_name = self._CRUD_BY_CATEGORY[category]
        try:
            getattr(repo, del_fn_name)(slug)
            onto_logger.info(f"OntoDataService: deleted {key}")
            return True
        except Exception as e:
            onto_logger.error(f"OntoDataService: delete failed for {key}: {e}")
            return False

    def download_file(self, key: str) -> Optional[bytes]:
        repo = self._get_repo()
        if repo is None:
            return None
        parsed = _key_to_category_slug(key)
        if parsed is None:
            return None
        category, slug = parsed

        _put, get_fn_name, _list, _del = self._CRUD_BY_CATEGORY[category]
        try:
            row = getattr(repo, get_fn_name)(slug)
        except Exception as e:
            onto_logger.error(f"OntoDataService: download failed for {key}: {e}")
            return None
        if not row:
            return None
        text = row.get("contentText") or ""
        return text.encode("utf-8")

    def download_category_to_temp(self, category: str) -> str:
        """Materialize all files in a category to a temp directory so
        extractors that expect a local filesystem path keep working
        without modification.
        """
        files = self.list_files(category)
        temp_dir = tempfile.mkdtemp(prefix=f"onto_{category}_")

        for f in files:
            content = self.download_file(f["key"])
            if content is None:
                continue
            filepath = os.path.join(temp_dir, f["filename"])
            with open(filepath, "wb") as fh:
                fh.write(content)

        onto_logger.info(f"Materialized {len(files)} {category} files to {temp_dir}")
        return temp_dir

    def bootstrap_if_empty(self) -> Dict[str, int]:
        """Idempotent startup hook - seeds from disk only if the target
        category is empty in DDB.

        Introduced in Phase 3 (data-organization spec) so fresh
        environments come up with the enterprise-knowledge content already
        materialized into DDB without needing an operator to run
        ``foundry/bootstrap`` by hand.
        """
        repo = self._get_repo()
        if repo is None:
            return {cat: 0 for cat in VALID_CATEGORIES}

        counts: Dict[str, int] = {cat: 0 for cat in VALID_CATEGORIES}
        for cat in VALID_CATEGORIES:
            _put, _get, list_fn, _del = self._CRUD_BY_CATEGORY[cat]
            try:
                existing = getattr(repo, list_fn)()
            except Exception as e:
                onto_logger.warning(f"OntoDataService.bootstrap_if_empty list({cat}) failed: {e}")
                existing = []
            if existing:
                continue
            # Empty - seed only this category.
            cat_dir = os.path.join(ENTERPRISE_KNOWLEDGE_DIR, cat)
            if not os.path.isdir(cat_dir):
                continue
            for filename in sorted(os.listdir(cat_dir)):
                filepath = os.path.join(cat_dir, filename)
                if not os.path.isfile(filepath):
                    continue
                try:
                    with open(filepath, "rb") as fh:
                        content = fh.read()
                    ext = os.path.splitext(filename)[1].lower()
                    ct = _content_type_for_extension(ext)
                    self.upload_file(cat, filename, content, ct)
                    counts[cat] += 1
                except Exception as e:
                    onto_logger.error(f"bootstrap_if_empty: {cat}/{filename} failed: {e}")

        if any(counts.values()):
            onto_logger.info(f"OntoDataService.bootstrap_if_empty: seeded {counts}")
        return counts

    def seed_defaults(self) -> Dict[str, int]:
        """Bootstrap entry point — loads the baked-in
        ``enterprise-knowledge/{policies,workflows,integrations}/``
        directories into DDB.

        Mirrors the old S3 ``seed_defaults`` contract (returns per-category
        upload counts), but reads from the rich enterprise-knowledge
        content directory rather than the legacy minimal
        ``sample-data/`` directory. For the dedicated CLI experience
        (``--dry-run``, ``--only category``, ``--force``), see
        ``nexus-deployer/backup-restore/scripts/bootstrap_foundry_from_files.py``.
        """
        repo = self._get_repo()
        if repo is None:
            return {cat: 0 for cat in VALID_CATEGORIES}

        # Prefer enterprise-knowledge (rich production set) over sample-data
        # (minimal toy set) when both are present.
        source_dirs = []
        if os.path.isdir(ENTERPRISE_KNOWLEDGE_DIR):
            source_dirs.append(ENTERPRISE_KNOWLEDGE_DIR)
        if os.path.isdir(SAMPLE_DATA_DIR):
            source_dirs.append(SAMPLE_DATA_DIR)

        counts: Dict[str, int] = {cat: 0 for cat in VALID_CATEGORIES}
        if not source_dirs:
            onto_logger.warning("OntoDataService.seed_defaults: no source directories found")
            return counts

        seen_slugs: Dict[str, set] = {cat: set() for cat in VALID_CATEGORIES}

        for src in source_dirs:
            for category in VALID_CATEGORIES:
                cat_dir = os.path.join(src, category)
                if not os.path.isdir(cat_dir):
                    continue
                for filename in sorted(os.listdir(cat_dir)):
                    filepath = os.path.join(cat_dir, filename)
                    if not os.path.isfile(filepath):
                        continue
                    slug = _filename_to_slug(filename)
                    if slug in seen_slugs[category]:
                        continue  # enterprise-knowledge wins over sample-data
                    seen_slugs[category].add(slug)
                    with open(filepath, "rb") as fh:
                        content = fh.read()
                    ext = os.path.splitext(filename)[1].lower()
                    ct = _content_type_for_extension(ext)
                    try:
                        self.upload_file(category, filename, content, ct)
                        counts[category] += 1
                    except Exception as e:
                        onto_logger.error(f"seed_defaults: failed to seed {filename}: {e}")

        onto_logger.info(f"OntoDataService.seed_defaults: counts={counts}")
        return counts

    def get_info(self) -> Dict[str, Any]:
        files = self.list_files()
        by_cat: Dict[str, List[Dict[str, Any]]] = {}
        for f in files:
            by_cat.setdefault(f["category"], []).append(f)

        return {
            # The "bucket" key is kept for API back-compat with the prior S3
            # implementation; the value now reports the DDB table.
            "bucket": self._backing_table_name(),
            "prefix": self._legacy_prefix,
            "total_files": len(files),
            "by_category": {cat: len(items) for cat, items in by_cat.items()},
            "sample_data_available": os.path.isdir(ENTERPRISE_KNOWLEDGE_DIR)
            or os.path.isdir(SAMPLE_DATA_DIR),
            "storage": "dynamodb",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _default_filename(self, category: str, slug: str) -> str:
        if not slug:
            return ""
        return f"{slug}{DEFAULT_EXTENSION.get(category, '')}"

    @staticmethod
    def _decode_content(content: bytes) -> str:
        """Decode bytes to UTF-8 string for storage as DDB string attribute.

        Falls back to ``latin-1`` to guarantee a lossless round-trip for
        odd-encoding payloads (PDF/binary not expected here but kept safe).
        """
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1")

    def _backing_table_name(self) -> str:
        repo = self._get_repo()
        if repo is None:
            return ""
        try:
            return repo.table_name
        except Exception:
            return ""
