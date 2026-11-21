"""
VDL mapping + warehouse materialization for external sources — ETL-only path.

Startup seeders must not call this; the ETL pipeline stage invokes these
helpers after extract/transform/load/verify.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
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
from src.services.mapping_rule_service import MappingRuleService, index_rules_by_virtual_entity
from src.services.vdl_catalog_service import get_catalog

log = logger.bind(component="external-vdl-etl")

SCHEMA = "external_sources"
SIM_KEY = "external"

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

SOURCE_TYPE_TABLES: Dict[str, List[str]] = {
    "social_listening": ["Market_Signal", "Brand_Sentiment", "Commodity_Price"],
    "file_uploads": ["Invoice_Upload", "Lab_Report_Upload"],
    "google_drive": ["Contract_Document", "Sustainability_Report", "ContentVersion", "ContentDocumentLink"],
    "external_full": [
        "Market_Signal", "Brand_Sentiment", "Commodity_Price",
        "Invoice_Upload", "Lab_Report_Upload",
        "Contract_Document", "Sustainability_Report", "ContentVersion", "ContentDocumentLink",
    ],
}

VIRTUAL_BY_SOURCE: Dict[str, List[str]] = {
    "social_listening": ["MarketSignal", "BrandSentiment", "CommodityPrice"],
    "file_uploads": ["UploadedInvoice", "UploadedLabReport"],
    "google_drive": ["ContractDocument", "SustainabilityReport", "DocumentVersion", "DocumentLink"],
    "external_full": list(RAW_VIRTUAL_TO_TABLE.keys()),
}

WAREHOUSE_PREFIXES = ("DF_", "IO_", "PA_", "PQ_", "SCR_", "C360_", "ESG_", "O2C_")

ARTIFACT_BY_SOURCE = {
    "social_listening": "social_listening",
    "file_uploads": "file_uploads",
    "google_drive": "google_drive",
}


def vdl_mapping_via_etl_only() -> bool:
    return os.getenv("VDL_MAPPING_VIA_ETL_ONLY", "true").lower() != "false"


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
        log.warning("Could not read lineage yaml: {}", exc)
        return {}


async def _column_names(simulators: Dict[str, Any], table: str) -> List[str]:
    sim = simulators.get(SIM_KEY)
    if sim is None or not hasattr(sim, "get_table_columns"):
        return []
    try:
        cols = await sim.get_table_columns(SCHEMA, table)
        return [c.column_name for c in cols if c.column_name]
    except Exception:
        return []


async def _upsert_fdw_rule(
    mapping_service: MappingRuleService,
    *,
    virtual_entity: str,
    table: str,
    field_maps: List[FieldMap],
    name_prefix: str,
    business_logic: Optional[str] = None,
    existing_by_ve: Dict[str, Any],
) -> Tuple[str, Optional[str]]:
    try:
        rule, status = await mapping_service.upsert_binding(
            MappingRuleCreateRequest(
                name=f"{name_prefix}: {virtual_entity}",
                virtual_entity=virtual_entity,
                source_type=MappingRuleSourceType.FDW,
                source_system=SIM_KEY,
                source_schema=SCHEMA,
                source_table=table,
                field_maps=field_maps or [FieldMap(source_field=table, target_field=table)],
                business_logic=business_logic,
            ),
            activate=True,
            name_prefix=name_prefix,
        )
        existing_by_ve[virtual_entity] = rule
        return status, None
    except Exception as exc:
        return "error", str(exc)


def _field_maps_for_entity(virtual_entity: str, table: str, columns: List[str]) -> List[FieldMap]:
    field_maps = [FieldMap(source_field=c, target_field=c) for c in columns] if columns else []
    catalog_ent = get_catalog().get_entity(virtual_entity) or get_catalog().get_entity(table)
    if catalog_ent and catalog_ent.get("fields") and columns:
        col_by_lower = {c.lower(): c for c in columns}
        mapped: List[FieldMap] = []
        for f in catalog_ent["fields"]:
            n = f.get("name")
            if not n:
                continue
            mapped.append(FieldMap(source_field=col_by_lower.get(n.lower(), n), target_field=n))
        if mapped:
            field_maps = mapped
    return field_maps


async def register_vdl_for_source_type(
    mapping_service: MappingRuleService,
    simulators: Dict[str, Any],
    source_type: str,
    *,
    job_id: str = "",
) -> Dict[str, Any]:
    """Create/update FDW mapping rules for raw + warehouse entities for this ETL source."""
    virtual_names = VIRTUAL_BY_SOURCE.get(source_type, [])
    existing_rules = await mapping_service.list_all()
    existing_by_ve = index_rules_by_virtual_entity(existing_rules)

    created = skipped = errors = 0
    detail: List[Dict[str, Any]] = []

    for virtual_entity in virtual_names:
        table = RAW_VIRTUAL_TO_TABLE.get(virtual_entity, "")
        if not table:
            continue
        columns = await _column_names(simulators, table)
        field_maps = _field_maps_for_entity(virtual_entity, table, columns)
        bl = json.dumps({
            "source_kind": "raw_external",
            "source_table": table,
            "schema": SCHEMA,
            "etl_source_type": source_type,
            "job_id": job_id,
        })
        status, err = await _upsert_fdw_rule(
            mapping_service,
            virtual_entity=virtual_entity,
            table=table,
            field_maps=field_maps,
            name_prefix="ETL External source",
            business_logic=bl,
            existing_by_ve=existing_by_ve,
        )
        if status == "created":
            created += 1
        elif status == "skipped":
            skipped += 1
        else:
            errors += 1
        detail.append({"entity": virtual_entity, "status": status, "table": table, "error": err})

    lineage = _load_lineage().get("warehouse_tables") or {}
    artifact = ARTIFACT_BY_SOURCE.get(source_type)
    for wh_table, meta in lineage.items():
        artifacts = meta.get("artifacts") or []
        if source_type != "external_full" and artifact and artifact not in artifacts:
            continue
        columns = await _column_names(simulators, wh_table)
        if not columns and source_type != "external_full":
            continue
        field_maps = [FieldMap(source_field=c, target_field=c) for c in columns] if columns else []
        bl = json.dumps({
            "lineage": {
                "warehouse_table": wh_table,
                "journey": meta.get("journey"),
                "feeds_from": meta.get("feeds_from") or [],
                "source_artifacts": artifacts,
                "etl_source_type": source_type,
                "job_id": job_id,
            }
        })
        status, err = await _upsert_fdw_rule(
            mapping_service,
            virtual_entity=wh_table,
            table=wh_table,
            field_maps=field_maps,
            name_prefix="ETL External warehouse",
            business_logic=bl,
            existing_by_ve=existing_by_ve,
        )
        if status == "created":
            created += 1
        elif status == "skipped":
            skipped += 1
        else:
            errors += 1
        detail.append({"entity": wh_table, "status": status, "error": err})

    if source_type == "external_full":
        sim = simulators.get(SIM_KEY)
        if sim and hasattr(sim, "list_foreign_tables"):
            try:
                tables = await sim.list_foreign_tables()
                for t in tables:
                    if getattr(t, "schema_name", "") != SCHEMA:
                        continue
                    tn = getattr(t, "table_name", "")
                    if not tn or not tn.startswith(WAREHOUSE_PREFIXES):
                        continue
                    if tn in existing_by_ve:
                        skipped += 1
                        continue
                    columns = await _column_names(simulators, tn)
                    status, err = await _upsert_fdw_rule(
                        mapping_service,
                        virtual_entity=tn,
                        table=tn,
                        field_maps=[FieldMap(source_field=c, target_field=c) for c in columns],
                        name_prefix="ETL External warehouse",
                        business_logic=json.dumps({"warehouse_table": tn, "job_id": job_id}),
                        existing_by_ve=existing_by_ve,
                    )
                    if status == "created":
                        created += 1
                    elif status == "skipped":
                        skipped += 1
                    else:
                        errors += 1
            except Exception as exc:
                log.warning("Warehouse table sweep failed: {}", exc)

    return {"created": created, "skipped": skipped, "errors": errors, "detail": detail[:50]}


async def materialize_warehouse_for_source_type(
    simulators: Dict[str, Any],
    source_type: str,
    *,
    job_id: str = "",
) -> Dict[str, Any]:
    """
  Write lightweight warehouse snapshot rows derived from raw feeds for this ETL run.
  Full analytics still come from solution journeys; this gives ETL a visible warehouse hook.
    """
    from src.models.fdw_models import QueryRequest

    sim = simulators.get(SIM_KEY)
    if sim is None:
        return {"written": 0, "reason": "no_simulator"}

    if hasattr(sim, "ensure_loaded"):
        await sim.ensure_loaded()

    now = datetime.now(timezone.utc).isoformat()
    written = 0
    lineage = _load_lineage().get("warehouse_tables") or {}
    artifact = ARTIFACT_BY_SOURCE.get(source_type)

    async def _row_count(table: str) -> int:
        try:
            resp = await sim.execute_query(QueryRequest(table=table, schema_name=SCHEMA, limit=1, offset=0))
            return int(getattr(resp.metadata, "row_count", len(resp.rows or 0)) or 0)
        except Exception:
            return 0

    source_tables = set(SOURCE_TYPE_TABLES.get(source_type, []))

    for wh_table, meta in lineage.items():
        lineage_artifacts = meta.get("artifacts") or []
        feeds_from = meta.get("feeds_from") or []
        if source_type != "external_full":
            matches_artifact = artifact and artifact in lineage_artifacts
            matches_feed = bool(source_tables.intersection(feeds_from))
            if not matches_artifact and not matches_feed:
                continue

        feeds = feeds_from or SOURCE_TYPE_TABLES.get(source_type, [])
        feed_counts = {t: await _row_count(t) for t in feeds if isinstance(t, str)}

        row: Dict[str, Any] = {
            "job_id": job_id or f"etl-{source_type}",
            "processed_at": now,
            "etl_source_type": source_type,
            "feeds_row_count": sum(feed_counts.values()),
            "feed_tables": json.dumps(feed_counts),
        }

        if wh_table == "DF_KPI_Snapshot" and source_type in ("social_listening", "external_full"):
            signals = feed_counts.get("Market_Signal", 0)
            sentiments = feed_counts.get("Brand_Sentiment", 0)
            row.update({
                "mape": 16.1 if signals else 0,
                "bias": -2.4,
                "stockout_rate_pct": min(100, max(0, signals // 2)),
                "total_forecast_qty": signals * 120 + sentiments * 10,
                "sku_region_combos": max(1, signals // 5),
            })
        elif wh_table.endswith("_KPI_Snapshot"):
            row.update({"kpi_refreshed_at": now, "source_feed_count": sum(feed_counts.values())})
        else:
            row.update({"materialized_at": now, "source_feed_count": sum(feed_counts.values())})

        try:
            if hasattr(sim, "write_table"):
                await sim.write_table(SCHEMA, wh_table, [row])
                written += 1
            elif hasattr(sim, "insert_row"):
                await sim.insert_row(wh_table, row)
                written += 1
        except Exception as exc:
            log.warning("Materialize {} failed: {}", wh_table, exc)

    if hasattr(sim, "_rebuild_artifacts"):
        try:
            await sim._rebuild_artifacts()
        except Exception:
            pass

    return {"written": written, "source_type": source_type}