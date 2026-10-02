"""
Solution Four Views - Result Entity Catalogue.

Registry of all new VDL virtual entities introduced by the Four-Views
expansion (one set per solution: ``O2C_*``, ``DF_*``, ``IO_*``, ``PA_*``,
``PQ_*``, ``SCR_*``, ``C360_*``, ``ESG_*``).

Each entry carries:

  * ``storage`` - "MIMIR" | "ATHENA" | "SIMULATOR"
  * ``columns`` - canonical list of (column_name, prom_label_name | None)
                  pairs used both to seed the field_maps and (for Mimir)
                  the label_map.
  * ``metric``  - Mimir metric base name (only when storage == "MIMIR")
  * ``schema``  - source schema for ATHENA / SIMULATOR (e.g.
                  "external_sources" or the Glue database name)

The ``ensure_solution_entities()`` helper is idempotent: it consults the
mapping-rule service and creates any missing rules pointing at the
correct adapter so dashboards have a queryable target on day 1, even
before the first journey run populates the data.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

cat_logger = logger.bind(component="solution-entity-catalogue")


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

SOLUTION_PREFIXES: Dict[str, str] = {
    "order-to-cash": "O2C",
    "demand-forecasting": "DF",
    "inventory-optimization": "IO",
    "procurement-analytics": "PA",
    "production-quality": "PQ",
    "supply-chain-risk": "SCR",
    "customer-360": "C360",
    "esg-sustainability": "ESG",
}


def _common_kpi_metrics(prefix: str) -> List[str]:
    """KPI gauge names per solution (used for <PREFIX>_KPI_Trend Mimir series)."""
    if prefix == "O2C":
        return ["o2c_dso", "o2c_match_rate", "o2c_leakage_rate", "o2c_open_ar", "o2c_past_due_ar"]
    if prefix == "DF":
        return ["df_mape", "df_bias", "df_stockout_rate", "df_promo_lift_accuracy"]
    if prefix == "IO":
        return ["io_turns", "io_fill_rate", "io_expiry_rate", "io_doh"]
    if prefix == "PA":
        return ["pa_maverick_rate", "pa_stp_rate", "pa_price_variance", "pa_cycle_time"]
    if prefix == "PQ":
        return ["pq_oee", "pq_yield", "pq_first_pass", "pq_downtime_minutes"]
    if prefix == "SCR":
        return ["scr_risk_score", "scr_otd_rate", "scr_early_warning_days"]
    if prefix == "C360":
        return ["c360_churn_rate", "c360_wallet_share", "c360_clv", "c360_health_score"]
    if prefix == "ESG":
        return ["esg_co2_intensity", "esg_water_ratio", "esg_recycled_pct", "esg_renewable_pct"]
    return []


def build_catalogue() -> Dict[str, Dict[str, Any]]:
    """
    Return ``{ virtual_entity_name: {storage, schema, columns, metric?, label_map? } }``.

    Generated programmatically because every solution shares the same
    eight result archetypes (KPI_Trend, Cohort_Summary, Forecast_Result,
    Anomaly_Score, Scenario_Result, Action_Log, Outcome_Tracker, Audit_Event)
    plus a few solution-specific extras.
    """
    catalogue: Dict[str, Dict[str, Any]] = {}

    for app_id, prefix in SOLUTION_PREFIXES.items():
        # --- Mimir (TSDB) entities -----------------------------------------
        catalogue[f"{prefix}_KPI_Trend"] = {
            "storage": "MIMIR",
            "metric": f"{prefix.lower()}_kpi",
            "label_map": {"kpi": "kpi", "region": "region", "segment": "segment"},
            "columns": [
                ("kpi", "kpi"), ("region", "region"), ("segment", "segment"),
                ("value", None), ("timestamp", None),
            ],
        }
        catalogue[f"{prefix}_Anomaly_Score"] = {
            "storage": "MIMIR",
            "metric": f"{prefix.lower()}_anomaly",
            "label_map": {"entity_id": "entity_id", "entity_type": "entity_type"},
            "columns": [
                ("entity_id", "entity_id"), ("entity_type", "entity_type"),
                ("value", None), ("timestamp", None),
            ],
        }

        # --- Athena (relational rows) entities ------------------------------
        catalogue[f"{prefix}_Action_Log"] = {
            "storage": "ATHENA",
            "schema": "external_sources",
            "columns": [
                ("action_id", None), ("action_type", None), ("target_entity", None),
                ("target_id", None), ("status", None), ("notes", None),
                ("taken_by", None), ("taken_at", None), ("job_id", None),
            ],
        }
        catalogue[f"{prefix}_Outcome_Tracker"] = {
            "storage": "ATHENA",
            "schema": "external_sources",
            "columns": [
                ("outcome_id", None), ("action_id", None), ("kpi_name", None),
                ("kpi_before", None), ("kpi_after", None), ("delta_value", None),
                ("currency", None), ("measured_at", None),
            ],
        }
        catalogue[f"{prefix}_Audit_Event"] = {
            "storage": "ATHENA",
            "schema": "external_sources",
            "columns": [
                ("event_id", None), ("actor", None), ("verb", None),
                ("target", None), ("payload", None), ("event_ts", None),
            ],
        }
        catalogue[f"{prefix}_Forecast_Result"] = {
            "storage": "ATHENA",
            "schema": "external_sources",
            "columns": [
                ("forecast_id", None), ("entity_id", None), ("kpi_name", None),
                ("horizon_period", None), ("point_value", None),
                ("lower_80", None), ("upper_80", None),
                ("model", None), ("created_at", None),
            ],
        }
        catalogue[f"{prefix}_Scenario_Result"] = {
            "storage": "ATHENA",
            "schema": "external_sources",
            "columns": [
                ("scenario_id", None), ("name", None), ("lever", None),
                ("kpi_name", None), ("baseline_value", None), ("scenario_value", None),
                ("delta_pct", None), ("computed_at", None),
            ],
        }
        catalogue[f"{prefix}_Cohort_Summary"] = {
            "storage": "ATHENA",
            "schema": "external_sources",
            "columns": [
                ("cohort_id", None), ("dimension", None), ("dimension_value", None),
                ("metric_name", None), ("metric_value", None), ("rolled_up_at", None),
            ],
        }

    # --- Solution-specific extras (not all 8 share these) -------------------
    catalogue["O2C_Funnel_Event"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("opportunity_id", None), ("stage", None), ("entered_at", None), ("exited_at", None)],
    }
    catalogue["DF_Demand_Actual_Daily"] = {
        "storage": "MIMIR", "metric": "df_demand_actual",
        "label_map": {"region": "region", "category": "category"},
        "columns": [("region", "region"), ("category", "category"), ("value", None), ("timestamp", None)],
    }
    catalogue["DF_Campaign_Lift"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("campaign_id", None), ("lift_pct", None), ("uplift_units", None), ("attributed_revenue", None)],
    }
    catalogue["DF_Error_Decomposition"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("region", None), ("category", None), ("bias", None), ("variance", None), ("noise", None)],
    }
    catalogue["IO_Stock_Snapshot_Daily"] = {
        "storage": "MIMIR", "metric": "io_stock_qty",
        "label_map": {"plant_id": "plant_id", "category": "category"},
        "columns": [("plant_id", "plant_id"), ("category", "category"), ("value", None), ("timestamp", None)],
    }
    catalogue["IO_Reorder_Recommendation"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("material_id", None), ("plant_id", None), ("recommended_qty", None), ("reason", None)],
    }
    catalogue["IO_Stock_Health"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("material_id", None), ("plant_id", None), ("doh", None), ("expiry_30d_qty", None)],
    }
    catalogue["PA_Match_Result"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("po_id", None), ("pr_id", None), ("gr_id", None), ("invoice_id", None),
                    ("match_status", None), ("price_variance_pct", None), ("cycle_time_days", None)],
    }
    catalogue["PA_Spend_Cube"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("category", None), ("vendor_id", None), ("plant_id", None), ("spend_amount", None)],
    }
    catalogue["PA_Contract_Leakage"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("month", None), ("contract_id", None), ("leakage_pct", None), ("leakage_amount", None)],
    }
    catalogue["PA_Vendor_Risk_Forecast"] = {
        "storage": "MIMIR", "metric": "pa_vendor_risk",
        "label_map": {"vendor_id": "vendor_id"},
        "columns": [("vendor_id", "vendor_id"), ("value", None), ("timestamp", None)],
    }
    catalogue["PQ_Line_State"] = {
        "storage": "MIMIR", "metric": "pq_line_state",
        "label_map": {"line_id": "line_id", "plant_id": "plant_id"},
        "columns": [("line_id", "line_id"), ("plant_id", "plant_id"), ("value", None), ("timestamp", None)],
    }
    catalogue["PQ_Yield_Loss"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("line_id", None), ("category", None), ("loss_pct", None), ("root_cause", None)],
    }
    catalogue["PQ_Maintenance_Forecast"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("line_id", None), ("predicted_failure_date", None), ("probability", None), ("reason", None)],
    }
    catalogue["PQ_Yield_Forecast"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("line_id", None), ("horizon_period", None), ("predicted_yield_pct", None), ("lower_80", None), ("upper_80", None)],
    }
    catalogue["PQ_CAPA_Record"] = {
        "storage": "SIMULATOR", "schema": "external_sources",
        "columns": [("capa_id", None), ("status", None), ("root_cause", None)],
    }
    catalogue["SCR_Risk_History"] = {
        "storage": "MIMIR", "metric": "scr_vendor_risk",
        "label_map": {"vendor_id": "vendor_id", "region": "region"},
        "columns": [("vendor_id", "vendor_id"), ("region", "region"), ("value", None), ("timestamp", None)],
    }
    catalogue["SCR_Single_Source_Risk"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("material_id", None), ("active_vendor_count", None), ("spend_pct", None)],
    }
    catalogue["SCR_Disruption_Forecast"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("region", None), ("horizon_period", None), ("probability", None), ("expected_impact_usd", None)],
    }
    catalogue["C360_Account_Health"] = {
        "storage": "MIMIR", "metric": "c360_health",
        "label_map": {"account_id": "account_id", "tier": "tier"},
        "columns": [("account_id", "account_id"), ("tier", "tier"), ("value", None), ("timestamp", None)],
    }
    catalogue["C360_Funnel_Result"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("stage", None), ("count", None), ("conversion_pct", None), ("period", None)],
    }
    catalogue["C360_Churn_Forecast"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("account_id", None), ("churn_probability", None), ("expected_revenue_loss", None)],
    }
    catalogue["C360_NBA_Result"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("account_id", None), ("recommended_action", None), ("expected_uplift_usd", None)],
    }
    catalogue["C360_Campaign_ROI"] = {
        "storage": "ATHENA", "schema": "external_sources",
        "columns": [("campaign_id", None), ("spend", None), ("realised_revenue", None), ("roi_pct", None)],
    }
    catalogue["ESG_Pathway_Forecast"] = {
        "storage": "MIMIR", "metric": "esg_pathway_co2",
        "label_map": {"plant_id": "plant_id"},
        "columns": [("plant_id", "plant_id"), ("value", None), ("timestamp", None)],
    }
    catalogue["ESG_Sentiment_Score"] = {
        "storage": "MIMIR", "metric": "esg_sentiment",
        "label_map": {"brand": "brand"},
        "columns": [("brand", "brand"), ("value", None), ("timestamp", None)],
    }

    return catalogue


CATALOGUE: Dict[str, Dict[str, Any]] = build_catalogue()


def entities_for_app(app_id: str) -> List[str]:
    prefix = SOLUTION_PREFIXES.get(app_id)
    if not prefix:
        return []
    return [name for name in CATALOGUE if name.startswith(prefix + "_")]


# ---------------------------------------------------------------------------
# Mapping-rule registration
# ---------------------------------------------------------------------------


async def ensure_solution_entities(
    mapping_service: Any = None,
    apps: Optional[List[str]] = None,
    force_recreate: bool = False,
) -> Dict[str, Any]:
    """
    Idempotently create VDL mapping rules for all (or a subset of)
    Four-Views catalogue entities. Returns a summary dict for logging.

    Safe to call on every backend startup.
    """
    if mapping_service is None:
        try:
            from src.apis import mapping_rule_api
            mapping_service = getattr(mapping_rule_api, "_service", None)
        except Exception:
            mapping_service = None
    if mapping_service is None:
        cat_logger.warning("Solution entity catalogue skipped - mapping-rule service not initialised")
        return {"created": 0, "skipped": 0, "errors": 1, "reason": "no mapping-rule service"}

    # Storage flip:
    # - SOLUTION_STORAGE_MODE=simulator (default in environments without Mimir +
    #   Athena + Glue properly provisioned): route every catalogue entity to the
    #   Redis-backed simulator. Result rows already land there via
    #   ResultSink.write_rows() / write_metric_batch() fallback paths, so VDL
    #   queries return the same data without depending on Athena IAM perms or
    #   a running Mimir StatefulSet.
    # - SOLUTION_STORAGE_MODE=production: honour each entity's catalogued
    #   storage (MIMIR / ATHENA / SIMULATOR).
    storage_mode = os.getenv("SOLUTION_STORAGE_MODE", "simulator").lower()
    cat_logger.info(
        "Solution entity catalogue ensure starting ({} target entities, mode={})",
        len(CATALOGUE), storage_mode,
    )

    from src.models.mapping_rule_models import (
        MappingRuleCreateRequest, MappingRuleUpdateRequest,
        MappingRuleSourceType, MappingRuleStatus, FieldMap,
    )

    targets: List[str]
    if apps:
        targets = [name for app_id in apps for name in entities_for_app(app_id)]
    else:
        targets = list(CATALOGUE.keys())

    try:
        existing = await mapping_service.list_all()
        existing_by_ve: Dict[str, Any] = {r.virtual_entity: r for r in existing}
    except Exception as e:
        cat_logger.warning("Could not list existing mapping rules: {}", e)
        existing_by_ve = {}
    existing_ve = set(existing_by_ve.keys())

    if force_recreate:
        # Wipe any rule we previously seeded for these target entities so the
        # routing flips when SOLUTION_STORAGE_MODE changes between deploys.
        deleted = 0
        for ve_name in list(existing_ve):
            if ve_name in CATALOGUE:
                rule = existing_by_ve[ve_name]
                # Only delete rules we own (auto-seeded ones have name prefix).
                if (rule.name or "").startswith(("Auto Mimir:", "Auto Athena:", "Auto Sim:")):
                    try:
                        await mapping_service.delete(rule.id)
                        deleted += 1
                        existing_ve.discard(ve_name)
                    except Exception as de:
                        cat_logger.warning("Failed to delete stale rule for {}: {}", ve_name, de)
        if deleted:
            cat_logger.info("Reset {} stale mapping rules for re-seed", deleted)

    created = 0
    skipped = 0
    errors = 0
    detail: List[Dict[str, str]] = []
    glue_db = os.getenv("GLUE_DATABASE", "default")
    mimir_tenant = os.getenv("MIMIR_TENANT_ID", "nexus-default")

    # Mapping from catalogue effective_storage to MappingRuleSourceType value
    _expected_source_type = {
        "MIMIR": "MIMIR",
        "ATHENA": "ATHENA",
        "SIMULATOR": "FDW",
    }

    for entity in targets:
        spec = CATALOGUE[entity]
        # In simulator mode, every entity becomes an FDW lookup against the
        # external simulator. The columns list still drives the field_maps so
        # the rows we write through ResultSink are queryable as-is.
        effective_storage = "SIMULATOR" if storage_mode == "simulator" else spec["storage"]

        if entity in existing_ve:
            existing_rule = existing_by_ve[entity]
            wanted_source = _expected_source_type[effective_storage]
            current_source = existing_rule.source_type.value
            is_auto = (existing_rule.name or "").startswith(("Auto Mimir:", "Auto Athena:", "Auto Sim:"))
            if current_source == wanted_source or not is_auto:
                # Either already correctly routed, or a hand-authored rule we
                # must not touch.
                skipped += 1
                continue
            # Routing changed (e.g. ATHENA -> SIMULATOR after the storage flip).
            # Delete the auto rule and fall through to create a new one.
            try:
                await mapping_service.delete(existing_rule.id)
                cat_logger.info(
                    "Re-routing {}: {} -> {}", entity, current_source, wanted_source
                )
            except Exception as de:
                cat_logger.warning("Failed to re-route {}: {}", entity, de)
                skipped += 1
                continue

        try:
            field_maps = [FieldMap(source_field=col_or_label or name, target_field=name)
                          for name, col_or_label in spec["columns"]]

            if effective_storage == "MIMIR":
                business_logic = json.dumps({
                    "label_map": spec.get("label_map", {}),
                    "default_aggregation": "avg",
                    "default_step_seconds": 3600,
                    "default_lookback_seconds": 7 * 24 * 3600,
                    "tenant_resolver": f"fixed:{mimir_tenant}",
                })
                rule = await mapping_service.create(MappingRuleCreateRequest(
                    name=f"Auto Mimir: {entity}",
                    virtual_entity=entity,
                    source_type=MappingRuleSourceType.MIMIR,
                    source_system="mimir",
                    source_table=spec["metric"],
                    source_schema="mimir",
                    field_maps=field_maps,
                    business_logic=business_logic,
                ))
            elif effective_storage == "ATHENA":
                rule = await mapping_service.create(MappingRuleCreateRequest(
                    name=f"Auto Athena: {entity}",
                    virtual_entity=entity,
                    source_type=MappingRuleSourceType.ATHENA,
                    source_system="athena",
                    source_table=entity.lower(),
                    source_schema=glue_db,
                    field_maps=field_maps,
                ))
            else:
                rule = await mapping_service.create(MappingRuleCreateRequest(
                    name=f"Auto Sim: {entity}",
                    virtual_entity=entity,
                    source_type=MappingRuleSourceType.FDW,
                    source_system="external_simulator",
                    source_table=entity,
                    source_schema="external_sources",
                    field_maps=field_maps,
                ))
            await mapping_service.update(rule.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
            created += 1
            detail.append({"entity": entity, "storage": effective_storage, "status": "created"})
        except Exception as e:
            errors += 1
            cat_logger.warning("Failed to register mapping rule for {}: {}", entity, e)
            detail.append({"entity": entity, "storage": effective_storage, "status": "error", "reason": str(e)})

    cat_logger.info("Solution entity catalogue: created={} skipped={} errors={}", created, skipped, errors)
    return {"created": created, "skipped": skipped, "errors": errors, "detail": detail}
