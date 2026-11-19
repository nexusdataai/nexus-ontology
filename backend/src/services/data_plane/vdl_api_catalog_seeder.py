"""
Generate Virtual Data API specs for every mapped canonical entity (read/list).

Hand-authored write APIs live under ``enterprise-knowledge/vdl-apis/*.yaml``.
This module auto-builds the read surface so the API Registry is complete
without maintaining one YAML per entity.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from loguru import logger

from src.models.vdl_api_models import DirectSqlBinding, VdlApiSpec

seed_logger = logger.bind(component="vdl-api-catalog-seeder")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(name: str) -> str:
    base = name.strip().replace(" ", "_")
    out = _SLUG_RE.sub("_", base.lower()).strip("_")
    return out or "entity"


def _pick_id_field(entity: Dict[str, Any]) -> Optional[str]:
    for f in entity.get("fields") or []:
        fname = f.get("name") or ""
        dtype = (f.get("dataType") or "").lower()
        if fname.endswith("_ID") or fname.endswith("_Id") or dtype == "id":
            return fname
    for f in entity.get("fields") or []:
        if f.get("name"):
            return str(f["name"])
    return None


def build_catalog_read_specs() -> List[VdlApiSpec]:
    """One list + optional get-by-id API per non-virtual catalog entity."""
    from src.services.vdl_catalog_service import get_catalog

    specs: List[VdlApiSpec] = []
    for ent in get_catalog().list_entities():
        if ent.get("isVirtual"):
            continue
        name = str(ent.get("name") or "").strip()
        if not name:
            continue
        slug = _slug(name)
        domain = str(ent.get("domain") or "").strip()
        tags = ["read", "vdl", "auto-catalog"]
        if domain:
            tags.append(domain)

        list_id = f"vdl.{slug}.list"
        specs.append(
            VdlApiSpec(
                api_id=list_id,
                verb="read",
                virtual_entity=name,
                description=f"List {name} rows through the Virtual Data Layer (mapping rules → simulator/FDW).",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 50},
                        "offset": {"type": "integer", "minimum": 0, "default": 0},
                    },
                },
                direct_sql=DirectSqlBinding(virtual_entity=name, limit=50),
                risk_level="read_only",
                tags=tags,
            )
        )

        id_field = _pick_id_field(ent)
        if id_field:
            get_id = f"vdl.{slug}.get"
            specs.append(
                VdlApiSpec(
                    api_id=get_id,
                    verb="read",
                    virtual_entity=name,
                    description=f"Read one {name} by {id_field}.",
                    parameters_schema={
                        "type": "object",
                        "properties": {id_field: {"type": "string"}},
                        "required": [id_field],
                    },
                    direct_sql=DirectSqlBinding(
                        virtual_entity=name,
                        filters={id_field: f"${{{id_field}}}"},
                        limit=1,
                    ),
                    risk_level="read_only",
                    tags=tags + ["get"],
                )
            )

    seed_logger.info("Built {} auto-catalog VDL API specs", len(specs))
    return specs