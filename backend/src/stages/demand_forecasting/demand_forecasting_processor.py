"""
Demand Forecasting Processor

Implements the 6-step demand forecast generation pipeline. Each step queries the
Virtual Data Layer, processes data using deterministic simulation logic, and
stores results for the final S3 write and alert generation.
"""

import hashlib
import json
import math
import random
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

df_logger = logger.bind(component="demand-forecast-processor")

try:
    from ...utils.sse_manager import emit_task_progress, emit_log
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    def emit_task_progress(*a, **kw): pass
    def emit_log(*a, **kw): pass

REGIONS = ["North", "South", "East", "West", "Central"]
WEEKS_HORIZON = 8

PROMOTION_LIFT = {
    "Discount": 1.15,
    "BOGO": 1.40,
    "Bundle": 1.20,
    "Display": 1.08,
    "Sampling": 1.05,
}

CATEGORY_SEASONALITY = {
    "Carbonated": [1.0, 1.0, 1.1, 1.2, 1.3, 1.3, 1.2, 1.1, 1.0, 0.9, 0.9, 1.0],
    "Juice": [0.9, 0.9, 1.0, 1.1, 1.2, 1.3, 1.3, 1.2, 1.0, 0.9, 0.9, 0.9],
    "Water": [0.8, 0.9, 1.0, 1.2, 1.4, 1.5, 1.5, 1.3, 1.1, 0.9, 0.8, 0.8],
    "Energy": [1.0, 1.0, 1.0, 1.1, 1.1, 1.2, 1.2, 1.1, 1.0, 1.0, 1.0, 1.0],
    "Sports": [0.9, 0.9, 1.0, 1.1, 1.3, 1.4, 1.3, 1.2, 1.0, 0.9, 0.8, 0.8],
    "Tea": [1.2, 1.1, 1.0, 0.9, 0.8, 0.8, 0.8, 0.9, 1.0, 1.1, 1.2, 1.2],
    "Snacks": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.2],
}

CANNIBALIZATION_FACTOR = 0.05


class DemandForecastProcessor:

    def __init__(self, log_callback: Optional[Callable] = None, job_id: str = "",
                 journey_id: str = "", s3_client=None, config=None):
        self._log_cb = log_callback
        self.job_id = job_id
        self.journey_id = journey_id
        self._s3 = s3_client
        self._config = config

        self._feature_matrix: List[Dict] = []
        self._base_forecasts: List[Dict] = []
        self._promo_adjusted: List[Dict] = []
        self._cannib_adjusted: List[Dict] = []
        self._consensus_forecast: List[Dict] = []
        self._alerts: List[Dict] = []
        self._kpis: Dict[str, Any] = {}

    def _log(self, level: str, msg: str, step_id: str = None):
        if self._log_cb:
            self._log_cb(level, msg, step_id)
        else:
            df_logger.log(level.upper(), msg)
        if SSE_AVAILABLE and self.job_id and step_id:
            emit_log(self.job_id, step_id, level.upper(), msg)

    def _get_vq_service(self):
        from src.apis.control_plane_api import _virtual_query_service
        return _virtual_query_service

    async def _query_entity(self, entity: str, filters=None, limit=2000) -> List[Dict]:
        vq = self._get_vq_service()
        if not vq:
            self._log("WARNING", f"VirtualQueryService not available for {entity}")
            return []
        from src.models.mapping_rule_models import VirtualQueryRequest, VirtualFilter
        vf = [VirtualFilter(field=f["field"], operator=f["operator"], value=f["value"]) for f in (filters or [])]
        req = VirtualQueryRequest(virtual_entity=entity, filters=vf if vf else None, limit=limit)
        try:
            resp = await vq.query_virtual_entity(req)
            return resp.rows
        except Exception as e:
            self._log("WARNING", f"VDL query {entity} failed: {e}, trying direct simulator...", entity)
            return await self._query_simulator_direct(entity, filters, limit)

    async def _query_simulator_direct(self, entity: str, filters=None, limit=2000) -> List[Dict]:
        try:
            from src.apis.fdw_api import _simulators
            from src.models.fdw_models import QueryRequest, QueryFilter, FilterOperator

            schema_map = {
                "Account": ("sfdc_itxp2dev", "simulator"),
                "Opportunity": ("sfdc_itxp2dev", "simulator"),
                "Opportunity_Line_Item": ("sfdc_itxp2dev", "simulator"),
                "Campaign": ("sfdc_itxp2dev", "simulator"),
                "Forecast_Override": ("sfdc_itxp2dev", "simulator"),
                "Material_Master": ("sap_s4hana", "sap"),
                "Material_Plant": ("sap_s4hana", "sap"),
                "Inventory_Position": ("sap_s4hana", "sap"),
                "Market_Signal": ("external_sources", "external"),
            }

            entry = schema_map.get(entity)
            if not entry:
                return []

            schema, sim_key = entry
            sim = _simulators.get(sim_key)
            if not sim or not getattr(sim, "loaded", False):
                self._log("WARNING", f"Simulator '{sim_key}' not loaded for {entity}")
                return []

            query_filters = None
            if filters:
                query_filters = [
                    QueryFilter(column=f["field"], operator=FilterOperator(f["operator"]), value=f["value"])
                    for f in filters
                ]

            req = QueryRequest(table=entity, schema_name=schema, filters=query_filters, limit=limit)
            resp = await sim.execute_query(req)
            return resp.rows
        except Exception as e:
            self._log("WARNING", f"Direct simulator query {entity} failed: {e}")
            return []

    @staticmethod
    def _safe_float(val, default=0.0) -> float:
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _deterministic_seed(sku: str, region: str, week: int) -> float:
        h = hashlib.md5(f"{sku}-{region}-{week}".encode()).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF

    async def _ensure_demand_forecast_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_entities = {r.virtual_entity for r in existing}

            rules = [
                ("Opportunity", "sfdc_itxp2dev", "Opportunity", {
                    "Opportunity_ID": "Opportunity_ID", "Account_ID": "Account_ID",
                    "Total_Value": "Amount", "Stage": "Stage", "Close_Date": "Close_Date", "Region": "Region"}),
                ("Opportunity_Line_Item", "sfdc_itxp2dev", "Opportunity_Line_Item", {
                    "Line_ID": "Line_Item_ID", "Opportunity_ID": "Opportunity_ID",
                    "Product_ID": "Product_ID", "Quantity": "Quantity", "Unit_Price": "Unit_Price"}),
                ("Account", "sfdc_itxp2dev", "Account", {
                    "Account_ID": "Account_ID", "Channel_Type": "Channel_Type", "Region": "Region", "Tier": "Tier"}),
                ("Campaign", "sfdc_itxp2dev", "Campaign", {
                    "Campaign_ID": "Campaign_ID", "Type": "Type", "Start_Date": "Start_Date",
                    "End_Date": "End_Date", "Target_Segment": "Target_Segment", "Status": "Status"}),
                ("Forecast_Override", "sfdc_itxp2dev", "Forecast_Override", {
                    "Override_ID": "Forecast_ID", "Product_ID": "Product_ID", "Region": "Region",
                    "Period": "Period", "Override_Qty": "Override_Quantity", "Justification": "Justification"}),
                ("Material_Master", "sap_s4hana", "Material_Master", {
                    "Material_ID": "Material_ID", "Category": "Category", "Pack_Size": "Pack_Size",
                    "Shelf_Life_Days": "Shelf_Life_Days", "Status": "Status"}),
                ("Material_Plant", "sap_s4hana", "Material_Plant", {
                    "Material_ID": "Material_ID", "Plant_ID": "Plant_ID", "MRP_Type": "MRP_Type",
                    "Safety_Stock": "Safety_Stock", "Lead_Time_Days": "Lead_Time_Days",
                    "ABC_Classification": "ABC_Classification"}),
                ("Inventory_Position", "sap_s4hana", "Inventory_Position", {
                    "Material_ID": "Material_ID", "Plant_ID": "Plant_ID",
                    "Unrestricted_Qty": "Quantity_On_Hand", "Reserved_Qty": "Quantity_Reserved",
                    "Valuation_Price": "Valuation_Price"}),
                ("Market_Signal", "external_sources", "Market_Signal", {
                    "Signal_ID": "Signal_ID", "Source": "Source", "Event_Type": "Event_Type",
                    "Severity": "Severity", "Affected_Commodity": "Affected_Commodity", "Timestamp": "Timestamp"}),
            ]

            from src.models.mapping_rule_models import MappingRuleCreateRequest, MappingRuleUpdateRequest, MappingRuleSourceType, MappingRuleStatus, FieldMap
            created = 0
            for virtual_entity, schema, table, field_map in rules:
                if virtual_entity in existing_entities:
                    continue
                field_maps = [FieldMap(source_field=s, target_field=t) for s, t in field_map.items()]
                rule = MappingRuleCreateRequest(
                    name=f"DF: {virtual_entity}",
                    virtual_entity=virtual_entity,
                    source_schema=schema,
                    source_table=table,
                    source_system=schema,
                    source_type=MappingRuleSourceType.FDW,
                    field_maps=field_maps,
                )
                resp = await service.create(rule)
                await service.update(resp.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
                created += 1

            if created:
                self._log("INFO", f"Created {created} VDL mapping rules for demand forecasting")
        except Exception as e:
            self._log("WARNING", f"Could not ensure mapping rules: {e}")

    # ─── Step 1: Feature Engineering ─────────────────────────────────────

    async def step_feature_engineering(self) -> Dict[str, Any]:
        self._log("INFO", "Step 1: Feature Engineering — aggregating data from 9 entities...", "feature_engineering")

        await self._ensure_demand_forecast_mapping_rules()

        materials = await self._query_entity("Material_Master")
        line_items = await self._query_entity("Opportunity_Line_Item")
        opps = await self._query_entity("Opportunity")
        accounts = await self._query_entity("Account")
        campaigns = await self._query_entity("Campaign")
        inventory = await self._query_entity("Inventory_Position")
        mat_plants = await self._query_entity("Material_Plant")
        market_signals = await self._query_entity("Market_Signal")

        self._log("INFO", (
            f"Loaded entities — Materials: {len(materials)}, LineItems: {len(line_items)}, "
            f"Opps: {len(opps)}, Accounts: {len(accounts)}, Campaigns: {len(campaigns)}, "
            f"Inventory: {len(inventory)}, MatPlants: {len(mat_plants)}, Signals: {len(market_signals)}"
        ), "feature_engineering")

        opp_map = {}
        for o in opps:
            oid = o.get("Opportunity_ID", "")
            if oid:
                opp_map[oid] = o

        mat_map = {}
        for m in materials:
            mid = m.get("Material_ID", "")
            if mid:
                mat_map[mid] = m

        demand_by_sku_region = defaultdict(lambda: {"qty": 0, "revenue": 0.0, "order_count": 0})
        for li in line_items:
            oid = li.get("Opportunity_ID", "")
            opp = opp_map.get(oid, {})
            if opp.get("Stage") not in ("Closed_Won", "Fulfilled"):
                continue
            sku = li.get("Product_ID", "")
            region = opp.get("Region", "Central")
            qty = self._safe_float(li.get("Quantity", 0))
            price = self._safe_float(li.get("Unit_Price", 0))
            key = (sku, region)
            demand_by_sku_region[key]["qty"] += qty
            demand_by_sku_region[key]["revenue"] += qty * price
            demand_by_sku_region[key]["order_count"] += 1

        inv_by_sku = defaultdict(float)
        for inv in inventory:
            mid = inv.get("Material_ID", "")
            qty = self._safe_float(inv.get("Quantity_On_Hand", inv.get("Unrestricted_Qty", 0)))
            inv_by_sku[mid] += qty

        signal_severity_count = defaultdict(int)
        for sig in market_signals:
            sev = sig.get("Severity", "Low")
            if sev in ("High", "Critical"):
                signal_severity_count[sig.get("Affected_Commodity", "Unknown")] += 1

        all_categories = list(CATEGORY_SEASONALITY.keys())

        feature_rows = []
        for (sku, region), demand in demand_by_sku_region.items():
            mat = mat_map.get(sku, {})
            category = mat.get("Category", "") or all_categories[int(self._deterministic_seed(sku, "", 0) * len(all_categories))]
            now = datetime.now(timezone.utc)
            month_idx = now.month - 1
            seasonality = CATEGORY_SEASONALITY.get(category, [1.0] * 12)[month_idx]

            feature_rows.append({
                "sku": sku,
                "region": region,
                "category": category,
                "historical_qty": demand["qty"],
                "historical_revenue": round(demand["revenue"], 2),
                "order_count": demand["order_count"],
                "current_inventory": inv_by_sku.get(sku, 0),
                "seasonality_factor": seasonality,
                "high_severity_signals": signal_severity_count.get(category, 0),
            })

        self._feature_matrix = feature_rows
        self._log("INFO", f"Built feature matrix: {len(feature_rows)} SKU x Region combinations", "feature_engineering")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "feature_engineering", "completed", len(feature_rows), len(feature_rows))

        return {
            "status": "completed",
            "sku_region_combos": len(feature_rows),
            "entities_queried": 8,
            "total_historical_orders": sum(f["order_count"] for f in feature_rows),
        }

    # ─── Step 2: Model Ensemble ──────────────────────────────────────────

    async def step_model_ensemble(self) -> Dict[str, Any]:
        self._log("INFO", "Step 2: Model Ensemble — generating base forecasts...", "model_ensemble")

        if not self._feature_matrix:
            return {"status": "error", "message": "No feature matrix — run step 1 first"}

        now = datetime.now(timezone.utc)
        forecasts = []

        for feat in self._feature_matrix:
            sku = feat["sku"]
            region = feat["region"]
            avg_weekly_demand = feat["historical_qty"] / 52 if feat["historical_qty"] > 0 else 100
            seasonality = feat["seasonality_factor"]

            for w in range(1, WEEKS_HORIZON + 1):
                future_month = (now + timedelta(weeks=w)).month - 1
                season_factor = CATEGORY_SEASONALITY.get(feat["category"], [1.0] * 12)[future_month]
                noise = self._deterministic_seed(sku, region, w)
                noise_factor = 0.85 + noise * 0.30

                ts_forecast = avg_weekly_demand * season_factor * noise_factor
                ml_forecast = avg_weekly_demand * season_factor * (0.90 + noise * 0.20)
                ensemble = round(ts_forecast * 0.4 + ml_forecast * 0.6)

                week_num = (now + timedelta(weeks=w)).isocalendar()[1]
                year = (now + timedelta(weeks=w)).year

                forecasts.append({
                    "sku": sku,
                    "region": region,
                    "category": feat["category"],
                    "period": f"{year}-W{week_num:02d}",
                    "ts_forecast": round(ts_forecast),
                    "ml_forecast": round(ml_forecast),
                    "ensemble_forecast": ensemble,
                    "current_inventory": feat["current_inventory"],
                })

        self._base_forecasts = forecasts
        self._log("INFO", f"Generated {len(forecasts)} base forecasts ({len(self._feature_matrix)} combos x {WEEKS_HORIZON} weeks)", "model_ensemble")

        return {
            "status": "completed",
            "forecasts_generated": len(forecasts),
            "horizon_weeks": WEEKS_HORIZON,
        }

    # ─── Step 3: Promotion Overlay ───────────────────────────────────────

    async def step_promotion_overlay(self) -> Dict[str, Any]:
        self._log("INFO", "Step 3: Promotion Overlay — applying campaign lift curves...", "promotion_overlay")

        campaigns = await self._query_entity("Campaign")
        active_campaigns = [c for c in campaigns if c.get("Status") in ("Active", "Planned")]
        self._log("INFO", f"Found {len(active_campaigns)} active/planned campaigns", "promotion_overlay")

        campaign_by_region = defaultdict(list)
        for c in active_campaigns:
            region = c.get("Target_Region", "")
            if region:
                campaign_by_region[region].append(c)

        adjusted = []
        promo_applied = 0
        for fc in self._base_forecasts:
            region_campaigns = campaign_by_region.get(fc["region"], [])
            lift = 1.0
            promo_name = None

            for camp in region_campaigns:
                camp_type = camp.get("Type", "Discount")
                camp_lift = PROMOTION_LIFT.get(camp_type, 1.0)
                if camp_lift > lift:
                    lift = min(camp_lift, 1.25)
                    promo_name = camp.get("Campaign_Name", camp.get("Campaign_ID", ""))

            promo_forecast = round(fc["ensemble_forecast"] * lift)
            if lift > 1.0:
                promo_applied += 1

            row = dict(fc)
            row["promo_lift"] = round(lift, 3)
            row["promo_forecast"] = promo_forecast
            row["promo_campaign"] = promo_name
            adjusted.append(row)

        self._promo_adjusted = adjusted
        self._log("INFO", f"Promotion overlay applied to {promo_applied}/{len(adjusted)} forecasts", "promotion_overlay")

        return {
            "status": "completed",
            "forecasts_adjusted": len(adjusted),
            "promo_applied_count": promo_applied,
            "active_campaigns": len(active_campaigns),
        }

    # ─── Step 4: Cannibalization Adjustment ──────────────────────────────

    async def step_cannibalization_adjustment(self) -> Dict[str, Any]:
        self._log("INFO", "Step 4: Cannibalization Adjustment — cross-product substitution...", "cannibalization_adjustment")

        by_cat_region_period = defaultdict(list)
        for fc in self._promo_adjusted:
            key = (fc["category"], fc["region"], fc["period"])
            by_cat_region_period[key].append(fc)

        adjusted = []
        cannib_count = 0
        for fc in self._promo_adjusted:
            key = (fc["category"], fc["region"], fc["period"])
            siblings = by_cat_region_period[key]

            promo_siblings = [s for s in siblings if s.get("promo_lift", 1.0) > 1.0 and s["sku"] != fc["sku"]]
            cannib_reduction = 0.0
            if promo_siblings and fc.get("promo_lift", 1.0) <= 1.0:
                cannib_reduction = CANNIBALIZATION_FACTOR * len(promo_siblings)
                cannib_count += 1

            cannib_forecast = round(fc["promo_forecast"] * (1.0 - cannib_reduction))
            row = dict(fc)
            row["cannib_reduction"] = round(cannib_reduction, 3)
            row["cannib_forecast"] = max(cannib_forecast, 0)
            adjusted.append(row)

        self._cannib_adjusted = adjusted
        self._log("INFO", f"Cannibalization applied to {cannib_count}/{len(adjusted)} forecasts", "cannibalization_adjustment")

        return {
            "status": "completed",
            "forecasts_adjusted": len(adjusted),
            "cannibalization_applied": cannib_count,
        }

    # ─── Step 5: Consensus Integration ───────────────────────────────────

    async def step_consensus_integration(self) -> Dict[str, Any]:
        self._log("INFO", "Step 5: Consensus Integration — merging with sales overrides...", "consensus_integration")

        overrides = await self._query_entity("Forecast_Override")
        approved = [o for o in overrides if o.get("Status") == "Approved"]
        self._log("INFO", f"Found {len(approved)} approved overrides out of {len(overrides)} total", "consensus_integration")

        override_map = {}
        for o in approved:
            sku = o.get("Product_ID", "")
            region = o.get("Region", "")
            period = o.get("Period", "")
            if sku and region and period:
                override_map[(sku, region, period)] = self._safe_float(
                    o.get("Override_Quantity", o.get("Override_Qty", 0))
                )

        consensus = []
        override_applied = 0
        for fc in self._cannib_adjusted:
            key = (fc["sku"], fc["region"], fc["period"])
            override_qty = override_map.get(key)

            row = dict(fc)
            if override_qty and override_qty > 0:
                row["final_forecast"] = round(override_qty)
                row["override_applied"] = True
                override_applied += 1
            else:
                row["final_forecast"] = fc["cannib_forecast"]
                row["override_applied"] = False
            consensus.append(row)

        self._consensus_forecast = consensus
        self._log("INFO", f"Consensus complete: {override_applied} overrides applied to {len(consensus)} forecasts", "consensus_integration")

        return {
            "status": "completed",
            "total_forecasts": len(consensus),
            "overrides_applied": override_applied,
            "approved_overrides_available": len(approved),
        }

    # ─── Step 6: Publish Forecast ────────────────────────────────────────

    async def step_publish_forecast(self) -> Dict[str, Any]:
        self._log("INFO", "Step 6: Publish Forecast — generating KPIs, alerts, and writing to S3...", "publish_forecast")

        if not self._consensus_forecast:
            return {"status": "error", "message": "No consensus forecast — run steps 1-5 first"}

        self._generate_alerts()
        self._compute_kpis()

        forecast_data = []
        for fc in self._consensus_forecast:
            forecast_data.append({
                "sku": fc["sku"],
                "region": fc["region"],
                "category": fc["category"],
                "period": fc["period"],
                "forecast_qty": fc["final_forecast"],
                "base_forecast": fc["ensemble_forecast"],
                "promo_lift": fc.get("promo_lift", 1.0),
                "cannib_reduction": fc.get("cannib_reduction", 0.0),
                "override_applied": fc.get("override_applied", False),
                "current_inventory": fc.get("current_inventory", 0),
            })

        now = datetime.now(timezone.utc)

        results = {
            "forecast_data": forecast_data,
            "kpis": self._kpis,
            "alerts": self._alerts,
            "generated_at": now.isoformat(),
        }

        written = await self._write_to_s3(results)
        await self._push_to_simulator(forecast_data, now)

        self._log("INFO", (
            f"Published {len(forecast_data)} forecasts, {len(self._alerts)} alerts, "
            f"MAPE={self._kpis.get('mape', 'N/A')}%"
        ), "publish_forecast")

        return {
            "status": "completed",
            "forecasts_published": len(forecast_data),
            "alerts_generated": len(self._alerts),
            "kpis": self._kpis,
            "s3_written": written,
        }

    async def _push_to_simulator(self, forecast_data: List[Dict], now: datetime):
        try:
            from src.apis.fdw_api import _simulators
            ext = _simulators.get("external")
            if not ext or not getattr(ext, "loaded", False):
                self._log("INFO", "External simulator not available — skipping simulator push", "publish_forecast")
                return

            await ext.write_table("external_sources", "DF_Forecast_Result", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in forecast_data
            ])

            await ext.write_table("external_sources", "DF_KPI_Snapshot", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                **self._kpis,
            }])

            await ext.write_table("external_sources", "DF_Alert", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                "total_alerts": len(self._alerts),
                "alerts": json.dumps(self._alerts, default=str),
            }])

            by_region = defaultdict(lambda: {"total_qty": 0, "sku_count": 0, "promo_count": 0, "override_count": 0})
            for fc in forecast_data:
                r = by_region[fc["region"]]
                r["total_qty"] += fc["forecast_qty"]
                r["sku_count"] += 1
                if fc.get("promo_lift", 1.0) > 1.0:
                    r["promo_count"] += 1
                if fc.get("override_applied"):
                    r["override_count"] += 1

            await ext.write_table("external_sources", "DF_Region_Summary", [
                {"region": region, "job_id": self.job_id, "processed_at": now.isoformat(), **vals}
                for region, vals in by_region.items()
            ])

            by_category = defaultdict(lambda: {"total_qty": 0, "sku_count": 0})
            for fc in forecast_data:
                c = by_category[fc["category"]]
                c["total_qty"] += fc["forecast_qty"]
                c["sku_count"] += 1

            await ext.write_table("external_sources", "DF_Category_Summary", [
                {"category": cat, "job_id": self.job_id, "processed_at": now.isoformat(), **vals}
                for cat, vals in by_category.items()
            ])

            self._log("INFO", (
                f"Pushed to simulator: {len(forecast_data)} forecast rows, "
                f"{len(by_region)} region summaries, {len(by_category)} category summaries, "
                f"KPIs + {len(self._alerts)} alerts"
            ), "publish_forecast")

            await self._ensure_df_result_mapping_rules()

            try:
                save_result = await ext.save_to_s3()
                if save_result.get("success"):
                    self._log("INFO", f"Persisted simulator to S3 ({save_result.get('tables')} tables, {save_result.get('rows')} rows)", "publish_forecast")
                    await self._broadcast_simulator_reload()
                else:
                    self._log("WARNING", f"S3 persist skipped: {save_result.get('message')}", "publish_forecast")
            except Exception as se:
                self._log("WARNING", f"Simulator S3 persist failed (non-fatal): {se}", "publish_forecast")

        except Exception as e:
            self._log("WARNING", f"Simulator push failed (non-fatal): {e}", "publish_forecast")

    async def _broadcast_simulator_reload(self):
        """Tell peer pods to reload external simulator from S3."""
        try:
            import aiohttp, os
            namespace = os.getenv("NAMESPACE", "nexus-ai-dev")
            svc = f"nexus-ai-dev-backend-svc.{namespace}.svc.cluster.local"
            reloaded = 0
            async with aiohttp.ClientSession() as session:
                for _ in range(6):
                    try:
                        async with session.post(f"http://{svc}:8000/api/v1/external-simulator/reset", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                            if resp.status == 200:
                                reloaded += 1
                    except Exception:
                        pass
            if reloaded:
                self._log("INFO", f"Broadcast simulator reload ({reloaded} calls)", "publish_forecast")
        except Exception as e:
            self._log("WARNING", f"Simulator reload broadcast failed (non-fatal): {e}", "publish_forecast")

    async def _ensure_df_result_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_by_entity = {r.virtual_entity: r for r in existing}

            result_entities = [
                "DF_Forecast_Result", "DF_KPI_Snapshot", "DF_Alert",
                "DF_Region_Summary", "DF_Category_Summary",
            ]

            from src.models.mapping_rule_models import MappingRuleCreateRequest, MappingRuleUpdateRequest, MappingRuleSourceType, MappingRuleStatus, FieldMap
            created = 0
            activated = 0
            for entity in result_entities:
                existing_rule = existing_by_entity.get(entity)
                if existing_rule:
                    if existing_rule.status.value != "active":
                        await service.update(existing_rule.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
                        activated += 1
                    continue
                rule = MappingRuleCreateRequest(
                    name=f"DF Result: {entity}",
                    virtual_entity=entity,
                    source_schema="external_sources",
                    source_table=entity,
                    source_system="external_sources",
                    source_type=MappingRuleSourceType.FDW,
                    field_maps=[],
                )
                resp = await service.create(rule)
                await service.update(resp.id, MappingRuleUpdateRequest(status=MappingRuleStatus.active))
                created += 1
            if created or activated:
                self._log("INFO", f"Created {created}, activated {activated} VDL mapping rules for DF result entities", "publish_forecast")
        except Exception as e:
            self._log("WARNING", f"DF result mapping rules failed (non-fatal): {e}", "publish_forecast")

    def _generate_alerts(self):
        alerts = []
        by_sku_region = defaultdict(list)
        for fc in self._consensus_forecast:
            by_sku_region[(fc["sku"], fc["region"])].append(fc)

        for (sku, region), forecasts in by_sku_region.items():
            if not forecasts:
                continue

            base_avg = sum(f["ensemble_forecast"] for f in forecasts) / len(forecasts)
            base_std = math.sqrt(sum((f["ensemble_forecast"] - base_avg) ** 2 for f in forecasts) / max(len(forecasts), 1))

            for fc in forecasts:
                if base_std > 0 and fc["final_forecast"] > base_avg + 2 * base_std:
                    alerts.append({
                        "type": "demand_spike",
                        "severity": "High",
                        "sku": sku, "region": region, "period": fc["period"],
                        "message": f"Forecast {fc['final_forecast']:,} exceeds 2σ above baseline ({base_avg + 2 * base_std:,.0f})",
                        "action": "Notify supply planning; trigger expedited production review",
                    })

            first_week = forecasts[0] if forecasts else {}
            last_week = forecasts[-1] if len(forecasts) > 1 else first_week
            if first_week.get("final_forecast", 0) > 0:
                growth = (last_week.get("final_forecast", 0) - first_week["final_forecast"]) / first_week["final_forecast"]
                if growth > 0.25:
                    alerts.append({
                        "type": "seasonal_ramp",
                        "severity": "Info",
                        "sku": sku, "region": region,
                        "period": f"{forecasts[0]['period']}..{forecasts[-1]['period']}",
                        "message": f"{growth:.0%} volume increase over {WEEKS_HORIZON}-week horizon",
                        "action": "Pre-position inventory; alert warehouse operations",
                    })

        promo_skus_by_region_period = defaultdict(set)
        for fc in self._consensus_forecast:
            if fc.get("promo_lift", 1.0) > 1.0:
                promo_skus_by_region_period[(fc["region"], fc["period"], fc["category"])].add(fc["sku"])

        for (region, period, category), skus in promo_skus_by_region_period.items():
            if len(skus) > 1:
                alerts.append({
                    "type": "promotion_conflict",
                    "severity": "Medium",
                    "region": region, "period": period,
                    "category": category,
                    "conflicting_skus": list(skus)[:5],
                    "message": f"{len(skus)} substitutable SKUs in {category} have overlapping promotions",
                    "action": "Notify trade marketing team",
                })

        total = len(self._consensus_forecast)
        if total > 0:
            simulated_mape = 12 + self._deterministic_seed("global", "mape", 0) * 15
            if simulated_mape > 20:
                alerts.append({
                    "type": "forecast_degradation",
                    "severity": "Medium",
                    "message": f"Simulated MAPE {simulated_mape:.1f}% exceeds 20% threshold",
                    "action": "Retrain model; flag for manual review",
                })

        self._alerts = alerts

    def _compute_kpis(self):
        if not self._consensus_forecast:
            self._kpis = {}
            return

        total_forecast_qty = sum(f["final_forecast"] for f in self._consensus_forecast)
        total_base_qty = sum(f["ensemble_forecast"] for f in self._consensus_forecast)
        override_count = sum(1 for f in self._consensus_forecast if f.get("override_applied"))

        mape = round(12 + self._deterministic_seed("global", "mape", 1) * 6, 1)
        bias = round(-3 + self._deterministic_seed("global", "bias", 2) * 6, 1)

        inv_skus = {f["sku"] for f in self._consensus_forecast if f.get("current_inventory", 0) == 0}
        total_skus = {f["sku"] for f in self._consensus_forecast}
        stockout_rate = round(len(inv_skus) / max(len(total_skus), 1) * 100, 1)

        self._kpis = {
            "mape": mape,
            "bias": bias,
            "stockout_rate_pct": stockout_rate,
            "total_forecast_qty": total_forecast_qty,
            "total_base_qty": total_base_qty,
            "override_count": override_count,
            "sku_region_combos": len(self._feature_matrix),
            "forecast_horizon_weeks": WEEKS_HORIZON,
            "alerts_count": len(self._alerts),
            "alerts": list(self._alerts) if isinstance(self._alerts, list) else [],
        }

    async def _write_to_s3(self, results: Dict) -> bool:
        if not self._s3:
            self._log("WARNING", "No S3 client configured — skipping S3 write", "publish_forecast")
            return False

        try:
            bucket = None
            if self._config:
                bucket = (
                    getattr(self._config, "s3_bucket", None)
                    or getattr(self._config, "stage_bucket", None)
                    or getattr(self._config, "s3_journey_reports_bucket", None)
                )
            if not bucket:
                import os
                bucket = os.getenv("STAGE_BUCKET", "") or os.getenv("S3_JOURNEY_REPORTS_BUCKET", "")
            if not bucket:
                self._log("WARNING", "No S3 bucket configured", "publish_forecast")
                return False

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            prefix = f"demand-forecasting/{self.journey_id}/{timestamp}"

            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/forecast-data.json",
                Body=json.dumps(results["forecast_data"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/forecast-kpis.json",
                Body=json.dumps(results["kpis"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/forecast-alerts.json",
                Body=json.dumps(results["alerts"], default=str),
                ContentType="application/json",
            )
            self._log("INFO", f"Written to s3://{bucket}/{prefix}/", "publish_forecast")
            return True
        except Exception as e:
            self._log("WARNING", f"S3 write failed: {e}", "publish_forecast")
            return False
