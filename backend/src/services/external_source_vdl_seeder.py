"""
Ensure VDL mapping rules for external raw sources and warehouse tables.

Raw artifacts (Google Drive, social listening, uploads) map to canonical
entities; journey warehouse tables in ``external_sources`` map 1:1 by table
name with identity field maps discovered from the simulator. Lineage metadata
from ``external-source-lineage.yaml`` is attached to warehouse rules.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml
from loguru import logger

from src.models.mapping_rule_models import (
    FieldMap,
    MappingRuleCreateRequest,
    MappingRuleSourceType,
    MappingRuleStatus,
    MappingRuleUpdateRequest,
)
from src.services.mapping_rule_service import MappingRuleService
from src.services.vdl_catalog_service import get_catalog

seed_logger = logger.bind(component="external-source-vdl")

SCHEMA = "external_sources"
SIM_KEY = "external"

# Canonical VDL entity -> simulator source table
RAW_VIRTUAL_TO_TABLE: Dict[str, str] = {
    "ContractDocument": "Contract_Document",
    "SustainabilityReport": "Sustainability_Report",
    "DocumentVersion": "ContentVersion",
    "DocumentLink": "ContentDocumentLink",
    "MarketSignal": "Market_Signal",
    "BrandSentiment": "Brand_Sentiment",
    "CommodityPrice": "Commodity_Price",
    "UploadedInvoice": "Invoice_Upload",
    "UploadedLabReport": "Lab_Report_Upload",
}

WAREHOUSE_PREFIXES = (
    "DF_", "IO_", "PA_", "PQ_", "SCR_", "C360_", "ESG_", "O2C_",
)


def _ek_dir() -> Optional[Path]:
    for candidate in (
        Path(os.environ.get("APP_ROOT", "/app")) / "enterprise-knowledge",
        Path(__file__).resolve().parent.parent.parent / "enterprise-knowledge",
    ):
        if candidate.is_dir():
            return candidate
    return None


def _load_lineage() -> Dict[str, Any]:
    ek = _ek_dir()
    if not ek:
        return {}
    path = ek / "external-source-lineage.yaml"
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except Exception as exc:
        seed_logger.warning("Could not read lineage yaml: {}", exc)
        return {}


async def _list_external_tables(simulators: Dict[str, Any]) -> Dict[str, Set[str]]:
    sim = simulators.get(SIM_KEY)
    by_schema: Dict[str, Set[str]] = {SCHEMA: set()}
    if sim is None:
        return by_schema
    try:
        if hasattr(sim, "ensure_loaded"):
            await sim.ensure_loaded()
        if hasattr(sim, "list_foreign_tables"):
            for t in await sim.list_foreign_tables():
                sch = getattr(t, "schema_name", None) or SCHEMA
                tn = getattr(t, "table_name", None) or ""
                if sch and tn:
                    by_schema.setdefault(sch, set()).add(tn)
    except Exception as exc:
        seed_logger.warning("Failed to list external simulator tables: {}", exc)
    return by_schema


async def _column_names(simulators: Dict[str, Any], table: str) -> List[str]:
    sim = simulators.get(SIM_KEY)
    if sim is None or not hasattr(sim, "get_table_columns"):
        return []
    try:
        cols = await sim.get_table_columns(SCHEMA, table)
        return [c.column_name for c in cols if c.column_name]
    except Exception:
        return []


def _identity_field_maps(columns: List[str]) -> List[FieldMap]:
    if columns:
        return [FieldMap(source_field=c, target_field=c) for c in columns]
    return []


def _lineage_for_table(table: str, lineage_doc: Dict[str, Any]) -> Optional[str]:
    wh = (lineage_doc.get("warehouse_tables") or {}).get(table)
    if not wh:
        return None
    payload = {
        "lineage": {
            "warehouse_table": table,
            "journey": wh.get("journey"),
            "feeds_from": wh.get("feeds_from") or [],
            "source_artifacts": wh.get("artifacts") or [],
        }
    }
    return json.dumps(payload)


async def _upsert_fdw_rule(
    mapping_service: MappingRuleService,
    *,
    virtual_entity: str,
    table: str,
    field_maps: List[FieldMap],
    name_prefix: str,
    business_logic: Optional[str] = None,
    existing_by_ve: Dict[str, Any],
    force_recreate: bool,
) -> Tuple[str, Optional[str]]:
    existing = existing_by_ve.get(virtual_entity)
    desired_name = f"{name_prefix}: {virtual_entity}"

    if existing and not force_recreate:
        needs_update = (
            existing.source_table != table
            or existing.source_schema != SCHEMA
            or (business_logic and existing.business_logic != business_logic)
        )
        if not needs_update and existing.status.value == "active":
            return "skipped", None
        if needs_update and (existing.name or "").startswith(name_prefix):
            try:
                await mapping_service.delete(existing.id)
                existing_by_ve.pop(virtual_entity, None)
            except Exception as exc:
                return "error", str(exc)

    try:
        rule = await mapping_service.create(
            MappingRuleCreateRequest(
                name=desired_name,
                virtual_entity=virtual_entity,
                source_type=MappingRuleSourceType.FDW,
                source_system=SIM_KEY,
                source_schema=SCHEMA,
                source_table=table,
                field_maps=field_maps or [FieldMap(source_field=table, target_field=table)],
                business_logic=business_logic,
            )
        )
        await mapping_service.update(
            rule.id,
            MappingRuleUpdateRequest(status=MappingRuleStatus.active, business_logic=business_logic),
        )
        existing_by_ve[virtual_entity] = rule
        return "created", None
    except Exception as exc:
        return "error", str(exc)


async def ensure_external_source_vdl_mappings(
    mapping_service: MappingRuleService,
    simulators: Optional[Dict[str, Any]] = None,
    *,
    force_recreate: bool = False,
) -> Dict[str, Any]:
    """
    Idempotent: raw external entities + warehouse tables in external_sources.
    """
    simulators = simulators or {}
    lineage_doc = _load_lineage()
    tables = await _list_external_tables(simulators)
    ext_tables = tables.get(SCHEMA) or set()

    try:
        existing_rules = await mapping_service.list_all()
    except Exception as exc:
        seed_logger.warning("Could not list mapping rules: {}", exc)
        existing_rules = []
    existing_by_ve = {r.virtual_entity: r for r in existing_rules}

    created = 0
    skipped = 0
    errors = 0
    detail: List[Dict[str, Any]] = []

    # 1) Raw sources -> canonical VDL entities
    for virtual_entity, source_table in RAW_VIRTUAL_TO_TABLE.items():
        if source_table not in ext_tables:
            detail.append({"entity": virtual_entity, "status": "no_source_table", "table": source_table})
            continue
        columns = await _column_names(simulators, source_table)
        field_maps = _identity_field_maps(columns)
        catalog_ent = get_catalog().get_entity(virtual_entity) or get_catalog().get_entity(source_table)
        if catalog_ent and catalog_ent.get("fields") and columns:
            col_by_lower = {c.lower(): c for c in columns}
            mapped: List[FieldMap] = []
            for f in catalog_ent["fields"]:
                n = f.get("name")
                if not n:
                    continue
                src = col_by_lower.get(n.lower(), n)
                mapped.append(FieldMap(source_field=src, target_field=n))
            if mapped:
                field_maps = mapped

        status, err = await _upsert_fdw_rule(
            mapping_service,
            virtual_entity=virtual_entity,
            table=source_table,
            field_maps=field_maps,
            name_prefix="External source",
            business_logic=json.dumps(
                {"source_kind": "raw_external", "source_table": source_table, "schema": SCHEMA}
            ),
            existing_by_ve=existing_by_ve,
            force_recreate=force_recreate,
        )
        if status == "created":
            created += 1
        elif status == "skipped":
            skipped += 1
        else:
            errors += 1
        detail.append({"entity": virtual_entity, "status": status, "table": source_table, "error": err})

    # 2) Warehouse tables (journey outputs) — virtual entity name = table name
    raw_tables = set(RAW_VIRTUAL_TO_TABLE.values())
    for table in sorted(ext_tables):
        if table in raw_tables:
            continue
        is_warehouse = table.startswith(WAREHOUSE_PREFIXES)
        in_lineage = table in (lineage_doc.get("warehouse_tables") or {})
        in_catalog = get_catalog().get_entity(table) is not None
        if not (is_warehouse or in_lineage or in_catalog):
            continue

        columns = await _column_names(simulators, table)
        field_maps = _identity_field_maps(columns)
        bl = _lineage_for_table(table, lineage_doc)

        status, err = await _upsert_fdw_rule(
            mapping_service,
            virtual_entity=table,
            table=table,
            field_maps=field_maps,
            name_prefix="External warehouse",
            business_logic=bl,
            existing_by_ve=existing_by_ve,
            force_recreate=force_recreate,
        )
        if status == "created":
            created += 1
        elif status == "skipped":
            skipped += 1
        else:
            errors += 1
        detail.append({"entity": table, "status": status, "error": err})

    summary = {
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "detail": detail[:40],
    }
    seed_logger.info(
        "External source VDL mappings: created={} skipped={} errors={}",
        created,
        skipped,
        errors,
    )
    return summary