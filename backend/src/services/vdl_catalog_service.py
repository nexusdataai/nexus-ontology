"""
VDL Catalog Service

Single source of truth for VDL entity definitions and alias resolution.

**Storage model (Supply Chain Foundry consolidation, Stage 2):**

The authoritative source is the ``foundry-workspace`` DynamoDB table
(``VDLENTITY#{name} / META`` rows, queryable via ``GSI1PK=VDLENTITY``).
On first use, this service queries DDB and caches the result
process-locally.

When DDB returns zero entities AND ``enterprise-knowledge/`` files exist
on disk, the service transparently falls back to the legacy file loader
(``canonical-entities.yaml`` + ``*schema*.yaml``) so that brand-new
clusters that have not yet run ``bootstrap_foundry_from_files.py``
still serve a working catalog. A WARNING log is emitted in that case
instructing the operator to run the bootstrap.

Consumers:
  - :func:`src.apis.control_plane_api._parse_schema_entities` reads the
    catalog to serve ``GET /entities``.
  - :class:`src.services.virtual_query_service.VirtualQueryService` calls
    :meth:`resolve_alias` to translate legacy entity names to canonical
    ones before mapping-rule lookup.
  - :class:`src.stages.semantic-rag.extractors.unified_schema_extractor.UnifiedSchemaExtractor`
    consumes :meth:`list_entities` to build the Knowledge Index.
"""

from __future__ import annotations

import glob
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

cat_logger = logger.bind(component="vdl-catalog")


def _candidate_dirs() -> List[str]:
    """All places enterprise-knowledge could live, in priority order."""
    candidates = [
        os.path.join(os.environ.get("APP_ROOT", "/app"), "enterprise-knowledge"),
        str(Path(__file__).resolve().parent.parent.parent / "enterprise-knowledge"),
        "/app/enterprise-knowledge",
    ]
    return [c for c in candidates if c]


def _find_enterprise_knowledge_dir() -> Optional[str]:
    for c in _candidate_dirs():
        if os.path.isdir(c):
            return c
    return None


class VdlCatalogService:
    """Loads canonical-entities.yaml + legacy *schema*.yaml; serves the
    in-memory entity catalog plus an alias-resolution function."""

    CANONICAL_FILENAME = "canonical-entities.yaml"
    LEGACY_GLOB = "*schema*.yaml"

    def __init__(self, ek_dir: Optional[str] = None) -> None:
        self._lock = threading.Lock()
        self._ek_dir: Optional[str] = ek_dir or _find_enterprise_knowledge_dir()
        self._loaded: bool = False
        # Built on load:
        self._entities: List[Dict[str, Any]] = []
        self._alias_to_canonical: Dict[str, str] = {}
        self._entities_by_name: Dict[str, Dict[str, Any]] = {}

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def list_entities(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """Return the merged entity catalog. Cached after first call."""
        self._ensure_loaded(refresh=refresh)
        return list(self._entities)

    def get_entity(self, name: str, refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Look up an entity by canonical name OR by legacy alias."""
        self._ensure_loaded(refresh=refresh)
        canonical = self.resolve_alias(name) or name
        return self._entities_by_name.get(canonical)

    def resolve_alias(self, name: str, refresh: bool = False) -> Optional[str]:
        """
        Resolve a legacy entity name to its canonical name. Returns the
        canonical name on a hit, ``None`` when ``name`` is already canonical
        or unknown. Callers should treat ``None`` as "use name as-is".
        """
        if not name:
            return None
        self._ensure_loaded(refresh=refresh)
        return self._alias_to_canonical.get(name)

    def refresh(self) -> None:
        """Force a re-read of the YAML files."""
        self._ensure_loaded(refresh=True)

    @property
    def stats(self) -> Dict[str, int]:
        self._ensure_loaded()
        return {
            "entities": len(self._entities),
            "aliases": len(self._alias_to_canonical),
        }

    # -------------------------------------------------------------------
    # Loader
    # -------------------------------------------------------------------

    def _ensure_loaded(self, refresh: bool = False) -> None:
        if self._loaded and not refresh:
            return
        with self._lock:
            if self._loaded and not refresh:
                return
            self._load_into_self()

    def _load_into_self(self) -> None:
        entities: Dict[str, Dict[str, Any]] = {}
        alias_index: Dict[str, str] = {}

        # ----- Primary source: foundry-workspace DDB (VDLENTITY# rows) -----
        ddb_count = self._load_from_ddb(entities, alias_index)

        # ----- Fallback: enterprise-knowledge files (bootstrap helper) -----
        # If DDB has zero entities the cluster has not yet been bootstrapped.
        # Load files transparently so the catalog is non-empty for /entities
        # API consumers and the Knowledge Processor pipeline, and emit a
        # WARNING instructing the operator to run the bootstrap. Once
        # bootstrap_foundry_from_files.py has been run, this branch becomes
        # inert (DDB returns the full set first).
        if ddb_count == 0 and self._ek_dir:
            cat_logger.warning(
                "VDL catalog: foundry-workspace DDB has 0 VDLENTITY rows — "
                "falling back to file-based load. Run "
                "bootstrap_foundry_from_files.py to populate DDB and silence "
                "this warning."
            )
            canonical_path = os.path.join(self._ek_dir, self.CANONICAL_FILENAME)
            if os.path.isfile(canonical_path):
                self._load_canonical_file(canonical_path, entities, alias_index)
            for path in sorted(glob.glob(os.path.join(self._ek_dir, self.LEGACY_GLOB))):
                base = os.path.basename(path)
                if base == self.CANONICAL_FILENAME:
                    continue
                self._load_legacy_file(path, entities, alias_index)
        elif ddb_count == 0 and not self._ek_dir:
            cat_logger.error(
                "VDL catalog: foundry-workspace DDB is empty AND no "
                "enterprise-knowledge directory found in any candidate path. "
                "The catalog will be empty."
            )

        self._entities = list(entities.values())
        self._entities_by_name = entities
        self._alias_to_canonical = alias_index
        self._loaded = True
        cat_logger.info(
            "VDL catalog loaded",
            source="ddb" if ddb_count > 0 else "files",
            ek_dir=self._ek_dir,
            entities=len(self._entities),
            aliases=len(self._alias_to_canonical),
        )

    # -------------------------------------------------------------------
    # DDB loader
    # -------------------------------------------------------------------

    # DynamoDB bookkeeping attributes that should not leak into the public
    # entity dict.
    _DDB_INTERNAL_KEYS = frozenset({"PK", "SK", "GSI1PK", "GSI1SK"})

    def _load_from_ddb(
        self,
        entities: Dict[str, Dict[str, Any]],
        alias_index: Dict[str, str],
    ) -> int:
        """Populate ``entities`` and ``alias_index`` from foundry-workspace.

        Returns the number of rows loaded so callers can decide whether to
        fall back to the file loader.
        """
        try:
            from src.repositories.foundry_workspace_repository import (
                FoundryWorkspaceRepository,
            )
            repo = FoundryWorkspaceRepository()
        except Exception as e:
            cat_logger.warning(f"VDL catalog: foundry-workspace not available: {e}")
            return 0

        try:
            rows = repo.list_canonical_entities()
        except Exception as e:
            cat_logger.warning(f"VDL catalog: list_canonical_entities failed: {e}")
            return 0

        for row in rows:
            ent = {k: v for k, v in row.items() if k not in self._DDB_INTERNAL_KEYS}
            name = ent.get("name")
            if not name:
                continue
            entities[name] = ent
            for alias in ent.get("aliases", []) or []:
                if alias and alias != name:
                    alias_index[alias] = name
        return len(rows)

    def _load_canonical_file(
        self,
        path: str,
        entities: Dict[str, Dict[str, Any]],
        alias_index: Dict[str, str],
    ) -> None:
        try:
            data = yaml.safe_load(open(path, "r"))
        except Exception as e:
            cat_logger.warning(f"Failed to read canonical catalog {path}: {e}")
            return

        if not data or data.get("schema_kind") != "canonical-entity-catalog":
            cat_logger.warning(f"{path}: missing or unexpected schema_kind")
            return

        for domain in data.get("domains", []) or []:
            domain_name = domain.get("name", "")
            scor = domain.get("scor_process", "")
            for ent in domain.get("entities", []) or []:
                name = ent.get("name")
                if not name:
                    continue
                fields = ent.get("key_fields", []) or []
                relationships = ent.get("relationships", []) or []
                aliases = ent.get("aliases", []) or []

                entities[name] = {
                    "name": name,
                    "aliases": aliases,
                    "system": "",  # derived at request time from active mapping rule
                    "domain": domain_name,
                    "semantic": ent.get("semantic", ""),
                    "riskLevel": ent.get("risk_level", "medium"),
                    "isVirtual": False,
                    "fdwMappingStatus": "canonical",
                    "scorProcess": scor,
                    "fields": [
                        {
                            "name": f.get("name"),
                            "dataType": f.get("data_type", "Text"),
                            "semantic": f.get("semantic", ""),
                            "riskLevel": f.get("risk_level", "low"),
                            "constraints": f.get("constraints", []),
                        }
                        for f in fields if f.get("name")
                    ],
                    "relationships": [
                        {
                            "type": r.get("type", ""),
                            "targetEntity": r.get("target_entity", ""),
                            "targetCategory": r.get("target_category", ""),
                            "description": r.get("description", ""),
                        }
                        for r in relationships
                    ],
                }
                for alias in aliases:
                    if alias and alias != name:
                        alias_index[alias] = name

    # -------------------------------------------------------------------
    # Bootstrap (file -> DDB)
    # -------------------------------------------------------------------

    def seed_from_file(
        self,
        canonical_path: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Read ``canonical-entities.yaml`` and write each entity into
        the foundry-workspace DDB as a ``VDLENTITY#{name}`` row.

        Used by ``bootstrap_foundry_from_files.py`` (script) and the
        ``POST /api/v1/control-plane/foundry/bootstrap`` endpoint to
        populate a freshly provisioned cluster's DDB from the baked-in
        image files.

        Returns ``{created, skipped_existing, errors, total}``. Idempotent
        — re-runs are no-ops unless ``force=True``.
        """
        result = {"created": 0, "skipped_existing": 0, "errors": 0, "total": 0, "details": []}

        # Resolve the file path: explicit arg > catalog's own ek_dir.
        path = canonical_path
        if not path and self._ek_dir:
            path = os.path.join(self._ek_dir, self.CANONICAL_FILENAME)
        if not path or not os.path.isfile(path):
            cat_logger.warning(f"seed_from_file: canonical file not found at {path!r}")
            return result

        try:
            data = yaml.safe_load(open(path, "r"))
        except Exception as e:
            cat_logger.error(f"seed_from_file: failed to parse {path}: {e}")
            result["errors"] += 1
            return result

        if not data or data.get("schema_kind") != "canonical-entity-catalog":
            cat_logger.error(f"seed_from_file: {path} is not a canonical entity catalog")
            result["errors"] += 1
            return result

        # Build entity dicts using the same shape that _load_canonical_file
        # produces (so DDB rows and live-loaded entries are identical).
        entities: Dict[str, Dict[str, Any]] = {}
        alias_index: Dict[str, str] = {}
        self._load_canonical_file(path, entities, alias_index)
        result["total"] = len(entities)

        if dry_run:
            result["details"] = [{"name": n, "action": "would_create"} for n in entities.keys()]
            return result

        try:
            from src.repositories.foundry_workspace_repository import (
                FoundryWorkspaceRepository,
            )
            repo = FoundryWorkspaceRepository()
        except Exception as e:
            cat_logger.error(f"seed_from_file: foundry-workspace not available: {e}")
            result["errors"] = result["total"]
            return result

        for name, ent in entities.items():
            try:
                existing = repo.get_canonical_entity(name)
                if existing and not force:
                    result["skipped_existing"] += 1
                    continue
                repo.put_canonical_entity(name, ent)
                result["created"] += 1
            except Exception as e:
                cat_logger.warning(f"seed_from_file: put {name} failed: {e}")
                result["errors"] += 1

        cat_logger.info(
            "seed_from_file complete",
            created=result["created"],
            skipped_existing=result["skipped_existing"],
            errors=result["errors"],
            total=result["total"],
        )
        return result

    def _load_legacy_file(
        self,
        path: str,
        entities: Dict[str, Dict[str, Any]],
        alias_index: Dict[str, str],
    ) -> None:
        """Read a legacy supply-chain-schema-shaped YAML; skip entities that
        already appear in ``entities`` (canonical wins) or whose name maps
        through ``alias_index`` to an already-loaded canonical entity."""
        try:
            data = yaml.safe_load(open(path, "r"))
        except Exception as e:
            cat_logger.warning(f"Failed to read legacy schema {path}: {e}")
            return
        if not data or "domains" not in data:
            return

        for domain in data["domains"]:
            system = domain.get("system", "Unknown")
            domain_name = domain.get("name", "")
            scor = domain.get("scor_process", "")
            for table in domain.get("tables", []) or []:
                fdw_table = table.get("fdw_table")
                if not fdw_table:
                    continue
                if fdw_table in entities:
                    continue
                if fdw_table in alias_index:
                    continue

                is_virtual = bool(table.get("virtual", False))
                fields = [
                    {
                        "name": f.get("name"),
                        "dataType": f.get("data_type", "Text"),
                        "semantic": f.get("semantic", ""),
                        "riskLevel": f.get("risk_level", "low"),
                        "constraints": f.get("constraints", []),
                    }
                    for f in table.get("key_fields", []) or [] if f.get("name")
                ]
                rels = [
                    {
                        "type": r.get("type", ""),
                        "targetEntity": r.get("target_entity", ""),
                        "targetCategory": r.get("target_category", ""),
                        "description": r.get("description", ""),
                    }
                    for r in table.get("relationships", []) or []
                ]
                entities[fdw_table] = {
                    "name": fdw_table,
                    "aliases": [],
                    "system": system,  # legacy: source-coupled — kept for back-compat display
                    "domain": domain_name,
                    "semantic": table.get("semantic", ""),
                    "riskLevel": table.get("risk_level", "medium"),
                    "isVirtual": is_virtual,
                    "fdwMappingStatus": "legacy",
                    "scorProcess": scor,
                    "physicalSourceTable": table.get("physical_source_table"),
                    "fields": fields,
                    "relationships": rels,
                }


# ---------------------------------------------------------------------------
# Module-level singleton (lazy-initialized)
# ---------------------------------------------------------------------------

_singleton: Optional[VdlCatalogService] = None
_singleton_lock = threading.Lock()


def get_catalog() -> VdlCatalogService:
    """Return the process-global :class:`VdlCatalogService` (lazy init)."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = VdlCatalogService()
    return _singleton


def reset_catalog() -> None:
    """Test hook — drop the cached singleton."""
    global _singleton
    with _singleton_lock:
        _singleton = None
