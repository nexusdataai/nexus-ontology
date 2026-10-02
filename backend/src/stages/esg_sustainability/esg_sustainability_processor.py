"""
ESG & Sustainability Processor

Implements the 6-step ESG sustainability tracking pipeline. Each step queries the
Virtual Data Layer, processes data using deterministic simulation logic, and
stores results for the final S3 write and alert generation.
"""

import hashlib
import json
import math
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

esg_logger = logger.bind(component="esg-sustainability-processor")

try:
    from ...utils.sse_manager import emit_task_progress, emit_log
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    def emit_task_progress(*a, **kw): pass
    def emit_log(*a, **kw): pass

CARBON_FACTOR_PER_ORDER = 2.5
ENERGY_INTENSITY_KWH_PER_UNIT = 0.35
TRANSPORT_EMISSION_PER_SHIPMENT = 1.8
WATER_INTENSITY_M3_PER_UNIT = 0.12
WASTE_RATIO_PER_UNIT = 0.015
RECYCLED_CONTENT_TARGET_PCT = 50.0
EMISSION_BREACH_THRESHOLD_TONS = 500.0
SENTIMENT_DECLINE_THRESHOLD = 40.0


class ESGSustainabilityProcessor:

    def __init__(self, log_callback: Optional[Callable] = None, job_id: str = "",
                 journey_id: str = "", s3_client=None, config=None):
        self._log_cb = log_callback
        self.job_id = job_id
        self.journey_id = journey_id
        self._s3 = s3_client
        self._config = config

        self._plant_map: Dict[str, Dict] = {}
        self._material_map: Dict[str, Dict] = {}
        self._production_by_plant: Dict[str, List[Dict]] = defaultdict(list)
        self._shipments: List[Dict] = []
        self._sustainability_reports: List[Dict] = []
        self._brand_sentiments: List[Dict] = []
        self._cost_accounting: List[Dict] = []
        self._fixed_assets: List[Dict] = []
        self._bom_data: List[Dict] = []

        self._carbon_data: Dict[str, Dict] = {}
        self._water_waste_data: Dict[str, Dict] = {}
        self._packaging_data: List[Dict] = []
        self._sentiment_data: Dict[str, Any] = {}
        self._alerts: List[Dict] = []
        self._kpis: Dict[str, Any] = {}

    def _log(self, level: str, msg: str, step_id: str = None):
        if self._log_cb:
            self._log_cb(level, msg, step_id)
        else:
            esg_logger.log(level.upper(), msg)
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
                "Sustainability_Report": ("external_sources", "external", None),
                "Material_Master": ("sap_s4hana", "sap", None),
                "Plant_Master": ("sap_s4hana", "sap", None),
                "Brand_Sentiment": ("external_sources", "external", None),
                "Production_Order": ("sap_s4hana", "sap", None),
                "Bill_of_Materials": ("sap_s4hana", "sap", None),
                "Shipment": ("sap_s4hana", "sap", None),
                "Cost_Accounting": ("oracle_erp", "oracle", "Oracle_Cost_Accounting"),
                "Fixed_Asset": ("oracle_erp", "oracle", "Oracle_Fixed_Asset"),
            }

            entry = schema_map.get(entity)
            if not entry:
                return []

            schema, sim_key, physical_table = entry
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

            req = QueryRequest(table=physical_table or entity, schema_name=schema, filters=query_filters, limit=limit)
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
    def _deterministic_seed(key1: str, key2: str, idx: int) -> float:
        h = hashlib.md5(f"{key1}-{key2}-{idx}".encode()).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF

    async def _ensure_esg_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_entities = {r.virtual_entity for r in existing}

            rules = [
                ("Sustainability_Report", "external_sources", "Sustainability_Report", {
                    "Report_ID": "Report_ID", "Plant_ID": "Plant_ID", "Period": "Period",
                    "Carbon_Emissions": "Carbon_Emissions", "Water_Usage": "Water_Usage",
                    "Waste_Generated": "Waste_Generated", "Energy_Consumed": "Energy_Consumed",
                    "Compliance_Status": "Compliance_Status"}),
                ("Material_Master", "sap_s4hana", "Material_Master", {
                    "Material_ID": "Material_ID", "Category": "Category", "Pack_Size": "Pack_Size",
                    "Shelf_Life_Days": "Shelf_Life_Days", "Status": "Status",
                    "Recycled_Content_Pct": "Recycled_Content_Pct",
                    "Recyclability_Score": "Recyclability_Score"}),
                ("Plant_Master", "sap_s4hana", "Plant_Master", {
                    "Plant_ID": "Plant_ID", "Plant_Name": "Plant_Name", "Region": "Region",
                    "Country": "Country", "Capacity": "Capacity", "Status": "Status"}),
                ("Brand_Sentiment", "external_sources", "Brand_Sentiment", {
                    "Sentiment_ID": "Sentiment_ID", "Brand": "Brand", "Topic": "Topic",
                    "Score": "Score", "Source": "Source", "Timestamp": "Timestamp"}),
                ("Production_Order", "sap_s4hana", "Production_Order", {
                    "Order_ID": "Order_ID", "Plant_ID": "Plant_ID", "Material_ID": "Material_ID",
                    "Quantity": "Quantity", "Status": "Status", "Start_Date": "Start_Date"}),
                ("Bill_of_Materials", "sap_s4hana", "Bill_of_Materials", {
                    "BOM_ID": "BOM_ID", "Material_ID": "Material_ID",
                    "Component_ID": "Component_ID", "Quantity": "Quantity"}),
                ("Shipment", "sap_s4hana", "Shipment", {
                    "Shipment_ID": "Shipment_ID", "Plant_ID": "Plant_ID",
                    "Destination": "Destination", "Weight_Tons": "Weight_Tons",
                    "Transport_Mode": "Transport_Mode", "Status": "Status"}),
                ("Cost_Accounting", "oracle_erp", "Oracle_Cost_Accounting", {
                    "Cost_ID": "Cost_ID", "Plant_ID": "Plant_ID", "Cost_Type": "Cost_Type",
                    "Amount": "Amount", "Period": "Period", "Currency": "Currency"}),
                ("Fixed_Asset", "oracle_erp", "Oracle_Fixed_Asset", {
                    "Asset_ID": "Asset_ID", "Plant_ID": "Plant_ID", "Asset_Type": "Asset_Type",
                    "Book_Value": "Book_Value", "Status": "Status"}),
            ]

            from src.models.mapping_rule_models import MappingRuleCreateRequest, MappingRuleUpdateRequest, MappingRuleSourceType, MappingRuleStatus, FieldMap
            created = 0
            for virtual_entity, schema, table, field_map in rules:
                if virtual_entity in existing_entities:
                    continue
                field_maps = [FieldMap(source_field=s, target_field=t) for s, t in field_map.items()]
                rule = MappingRuleCreateRequest(
                    name=f"ESG: {virtual_entity}",
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
                self._log("INFO", f"Created {created} VDL mapping rules for ESG sustainability")
        except Exception as e:
            self._log("WARNING", f"Could not ensure mapping rules: {e}")

    # ─── Step 1: Load ESG Data ───────────────────────────────────────────

    async def step_load_esg_data(self) -> Dict[str, Any]:
        self._log("INFO", "Step 1: Load ESG Data — querying 9 entities...", "load_esg_data")

        await self._ensure_esg_mapping_rules()

        sustainability_reports = await self._query_entity("Sustainability_Report")
        materials = await self._query_entity("Material_Master")
        plants = await self._query_entity("Plant_Master")
        brand_sentiments = await self._query_entity("Brand_Sentiment")
        production_orders = await self._query_entity("Production_Order")
        bom_data = await self._query_entity("Bill_of_Materials")
        shipments = await self._query_entity("Shipment")
        cost_accounting = await self._query_entity("Cost_Accounting")
        fixed_assets = await self._query_entity("Fixed_Asset")

        self._log("INFO", (
            f"Loaded entities — Plants: {len(plants)}, Materials: {len(materials)}, "
            f"ProductionOrders: {len(production_orders)}, SustainabilityReports: {len(sustainability_reports)}, "
            f"BrandSentiment: {len(brand_sentiments)}, BOM: {len(bom_data)}, "
            f"Shipments: {len(shipments)}, CostAccounting: {len(cost_accounting)}, "
            f"FixedAssets: {len(fixed_assets)}"
        ), "load_esg_data")

        self._plant_map = {}
        for p in plants:
            pid = p.get("Plant_ID", "")
            if pid:
                self._plant_map[pid] = p

        self._material_map = {}
        for m in materials:
            mid = m.get("Material_ID", "")
            if mid:
                self._material_map[mid] = m

        self._production_by_plant = defaultdict(list)
        for po in production_orders:
            pid = po.get("Plant_ID", "")
            if pid:
                self._production_by_plant[pid].append(po)

        self._shipments = shipments
        self._sustainability_reports = sustainability_reports
        self._brand_sentiments = brand_sentiments
        self._cost_accounting = cost_accounting
        self._fixed_assets = fixed_assets
        self._bom_data = bom_data

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "load_esg_data", "completed", 9, 9)

        return {
            "status": "completed",
            "entities_queried": 9,
            "plants": len(self._plant_map),
            "materials": len(self._material_map),
            "production_orders": len(production_orders),
            "sustainability_reports": len(sustainability_reports),
            "brand_sentiments": len(brand_sentiments),
            "shipments": len(shipments),
        }

    # ─── Step 2: Carbon Footprint ────────────────────────────────────────

    async def step_carbon_footprint(self) -> Dict[str, Any]:
        self._log("INFO", "Step 2: Carbon Footprint — calculating emissions per plant...", "carbon_footprint")

        if not self._plant_map:
            return {"status": "error", "message": "No plant data — run step 1 first"}

        shipments_by_plant = defaultdict(list)
        for s in self._shipments:
            pid = s.get("Plant_ID", "")
            if pid:
                shipments_by_plant[pid].append(s)

        carbon_data = {}
        for plant_id, plant in self._plant_map.items():
            orders = self._production_by_plant.get(plant_id, [])
            order_count = len(orders)
            production_volume = sum(self._safe_float(o.get("Quantity", 0)) for o in orders)
            plant_shipments = shipments_by_plant.get(plant_id, [])

            carbon_emissions_tons = round(order_count * CARBON_FACTOR_PER_ORDER, 2)
            energy_kwh = round(production_volume * ENERGY_INTENSITY_KWH_PER_UNIT, 2)
            transport_emissions = round(len(plant_shipments) * TRANSPORT_EMISSION_PER_SHIPMENT, 2)

            total_carbon = round(carbon_emissions_tons + transport_emissions, 2)

            carbon_data[plant_id] = {
                "plant_id": plant_id,
                "plant_name": plant.get("Plant_Name", plant_id),
                "order_count": order_count,
                "production_volume": production_volume,
                "carbon_emissions_tons": carbon_emissions_tons,
                "transport_emissions_tons": transport_emissions,
                "total_carbon_tons": total_carbon,
                "energy_kwh": energy_kwh,
                "shipment_count": len(plant_shipments),
            }

        self._carbon_data = carbon_data
        total_emissions = sum(d["total_carbon_tons"] for d in carbon_data.values())
        self._log("INFO", f"Carbon footprint calculated for {len(carbon_data)} plants, total: {total_emissions:.1f} tons CO₂", "carbon_footprint")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "carbon_footprint", "completed", len(carbon_data), len(carbon_data))

        return {
            "status": "completed",
            "plants_analyzed": len(carbon_data),
            "total_carbon_tons": total_emissions,
            "total_energy_kwh": sum(d["energy_kwh"] for d in carbon_data.values()),
        }

    # ─── Step 3: Water & Waste ───────────────────────────────────────────

    async def step_water_and_waste(self) -> Dict[str, Any]:
        self._log("INFO", "Step 3: Water & Waste — analyzing consumption and waste per plant...", "water_and_waste")

        if not self._plant_map:
            return {"status": "error", "message": "No plant data — run step 1 first"}

        water_waste_data = {}
        for plant_id, plant in self._plant_map.items():
            orders = self._production_by_plant.get(plant_id, [])
            production_volume = sum(self._safe_float(o.get("Quantity", 0)) for o in orders)

            water_usage_m3 = round(production_volume * WATER_INTENSITY_M3_PER_UNIT, 2)
            waste_tons = round(production_volume * WASTE_RATIO_PER_UNIT, 2)

            water_waste_data[plant_id] = {
                "plant_id": plant_id,
                "plant_name": plant.get("Plant_Name", plant_id),
                "production_volume": production_volume,
                "water_usage_m3": water_usage_m3,
                "waste_tons": waste_tons,
                "water_per_unit": WATER_INTENSITY_M3_PER_UNIT if production_volume > 0 else 0,
                "waste_per_unit": WASTE_RATIO_PER_UNIT if production_volume > 0 else 0,
            }

        self._water_waste_data = water_waste_data
        total_water = sum(d["water_usage_m3"] for d in water_waste_data.values())
        total_waste = sum(d["waste_tons"] for d in water_waste_data.values())
        self._log("INFO", f"Water & waste analyzed for {len(water_waste_data)} plants: {total_water:.1f} m³ water, {total_waste:.1f} tons waste", "water_and_waste")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "water_and_waste", "completed", len(water_waste_data), len(water_waste_data))

        return {
            "status": "completed",
            "plants_analyzed": len(water_waste_data),
            "total_water_m3": total_water,
            "total_waste_tons": total_waste,
        }

    # ─── Step 4: Packaging Analysis ──────────────────────────────────────

    async def step_packaging_analysis(self) -> Dict[str, Any]:
        self._log("INFO", "Step 4: Packaging Analysis — evaluating recycled content vs targets...", "packaging_analysis")

        if not self._material_map:
            return {"status": "error", "message": "No material data — run step 1 first"}

        packaging_data = []
        below_target = 0
        for material_id, mat in self._material_map.items():
            recycled_content_pct = self._safe_float(mat.get("Recycled_Content_Pct", 0))
            recyclability_score = self._safe_float(mat.get("Recyclability_Score", 0))

            if recycled_content_pct == 0:
                recycled_content_pct = round(self._deterministic_seed(material_id, "recycled", 0) * 80, 1)
            if recyclability_score == 0:
                recyclability_score = round(self._deterministic_seed(material_id, "recyclability", 0) * 100, 1)

            meets_target = recycled_content_pct >= RECYCLED_CONTENT_TARGET_PCT
            if not meets_target:
                below_target += 1

            carbon_footprint = round(self._deterministic_seed(material_id, "carbon", 0) * 5.0, 2)

            packaging_data.append({
                "material_id": material_id,
                "category": mat.get("Category", "Unknown"),
                "recycled_content_pct": recycled_content_pct,
                "recyclability_score": recyclability_score,
                "meets_target": meets_target,
                "target_pct": RECYCLED_CONTENT_TARGET_PCT,
                "gap_pct": round(max(RECYCLED_CONTENT_TARGET_PCT - recycled_content_pct, 0), 1),
                "carbon_footprint": carbon_footprint,
            })

        self._packaging_data = packaging_data
        self._log("INFO", f"Packaging analysis: {len(packaging_data)} materials, {below_target} below {RECYCLED_CONTENT_TARGET_PCT}% target", "packaging_analysis")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "packaging_analysis", "completed", len(packaging_data), len(packaging_data))

        return {
            "status": "completed",
            "materials_analyzed": len(packaging_data),
            "below_target_count": below_target,
            "avg_recycled_pct": round(sum(p["recycled_content_pct"] for p in packaging_data) / max(len(packaging_data), 1), 1),
        }

    # ─── Step 5: Sentiment Integration ───────────────────────────────────

    async def step_sentiment_integration(self) -> Dict[str, Any]:
        self._log("INFO", "Step 5: Sentiment Integration — analyzing brand sustainability perception...", "sentiment_integration")

        sustainability_sentiments = [
            s for s in self._brand_sentiments
            if "sustain" in str(s.get("Topic", "")).lower()
            or "esg" in str(s.get("Topic", "")).lower()
            or "green" in str(s.get("Topic", "")).lower()
            or "carbon" in str(s.get("Topic", "")).lower()
            or "environment" in str(s.get("Topic", "")).lower()
        ]

        if not sustainability_sentiments:
            sustainability_sentiments = self._brand_sentiments

        sentiment_by_brand = defaultdict(list)
        for s in sustainability_sentiments:
            brand = s.get("Brand", "Unknown")
            score = self._safe_float(s.get("Score", 0))
            sentiment_by_brand[brand].append(score)

        brand_scores = {}
        for brand, scores in sentiment_by_brand.items():
            avg_raw = sum(scores) / len(scores) if scores else 0
            sustainability_sentiment_score = round(min(max(avg_raw * 10, 0), 100), 1)
            brand_scores[brand] = {
                "brand": brand,
                "sample_count": len(scores),
                "avg_raw_score": round(avg_raw, 2),
                "sustainability_sentiment_score": sustainability_sentiment_score,
            }

        all_scores = [b["sustainability_sentiment_score"] for b in brand_scores.values()]
        overall_sentiment = round(sum(all_scores) / max(len(all_scores), 1), 1)

        self._sentiment_data = {
            "brand_scores": brand_scores,
            "overall_sentiment": overall_sentiment,
            "total_entries": len(sustainability_sentiments),
            "brands_analyzed": len(brand_scores),
        }

        self._log("INFO", f"Sentiment integration: {len(brand_scores)} brands, overall score: {overall_sentiment}/100", "sentiment_integration")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "sentiment_integration", "completed", len(brand_scores), len(brand_scores))

        return {
            "status": "completed",
            "brands_analyzed": len(brand_scores),
            "overall_sentiment_score": overall_sentiment,
            "sentiment_entries_processed": len(sustainability_sentiments),
        }

    # ─── Step 6: Publish Results ─────────────────────────────────────────

    async def step_publish_results(self) -> Dict[str, Any]:
        self._log("INFO", "Step 6: Publish Results — generating KPIs, alerts, and writing to S3...", "publish_results")

        if not self._carbon_data and not self._water_waste_data:
            return {"status": "error", "message": "No ESG data — run steps 1-5 first"}

        self._generate_alerts()
        self._compute_kpis()

        plant_results = self._build_plant_results()
        material_summaries = self._build_material_summaries()
        category_summaries = self._build_category_summaries()

        now = datetime.now(timezone.utc)

        results = {
            "kpis": self._kpis,
            "plant_results": plant_results,
            "material_summaries": material_summaries,
            "category_summaries": category_summaries,
            "alerts": self._alerts,
            "sentiment": self._sentiment_data,
            "generated_at": now.isoformat(),
        }

        written = await self._write_to_s3(results)
        await self._push_to_simulator(plant_results, material_summaries, category_summaries, now)

        self._log("INFO", (
            f"Published {len(plant_results)} plant results, {len(material_summaries)} material summaries, "
            f"{len(self._alerts)} alerts, sentiment={self._kpis.get('sustainability_sentiment', 'N/A')}"
        ), "publish_results")

        return {
            "status": "completed",
            "plant_results_published": len(plant_results),
            "material_summaries_published": len(material_summaries),
            "category_summaries_published": len(category_summaries),
            "alerts_generated": len(self._alerts),
            "kpis": self._kpis,
            "s3_written": written,
        }

    def _build_plant_results(self) -> List[Dict]:
        results = []
        for plant_id in self._plant_map:
            carbon = self._carbon_data.get(plant_id, {})
            water_waste = self._water_waste_data.get(plant_id, {})

            packaging_scores = [p["recycled_content_pct"] for p in self._packaging_data]
            avg_recycled = sum(packaging_scores) / max(len(packaging_scores), 1)

            esg_score = self._compute_plant_esg_score(carbon, water_waste, avg_recycled)

            results.append({
                "plant_id": plant_id,
                "plant_name": carbon.get("plant_name", water_waste.get("plant_name", plant_id)),
                "carbon_emissions": carbon.get("total_carbon_tons", 0),
                "water_usage": water_waste.get("water_usage_m3", 0),
                "energy_kwh": carbon.get("energy_kwh", 0),
                "waste_tons": water_waste.get("waste_tons", 0),
                "recycled_pct": round(avg_recycled, 1),
                "esg_score": esg_score,
            })
        return results

    def _compute_plant_esg_score(self, carbon: Dict, water_waste: Dict, avg_recycled: float) -> float:
        carbon_score = max(0, 100 - (carbon.get("total_carbon_tons", 0) / max(EMISSION_BREACH_THRESHOLD_TONS, 1)) * 50)
        water_score = max(0, 100 - water_waste.get("water_usage_m3", 0) * 0.01)
        waste_score = max(0, 100 - water_waste.get("waste_tons", 0) * 0.5)
        recycled_score = min(avg_recycled * 2, 100)
        return round((carbon_score * 0.35 + water_score * 0.25 + waste_score * 0.20 + recycled_score * 0.20), 1)

    def _build_material_summaries(self) -> List[Dict]:
        summaries = []
        for pkg in self._packaging_data:
            summaries.append({
                "material_id": pkg["material_id"],
                "category": pkg["category"],
                "recycled_content_pct": pkg["recycled_content_pct"],
                "recyclability_score": pkg["recyclability_score"],
                "carbon_footprint": pkg["carbon_footprint"],
            })
        return summaries

    def _build_category_summaries(self) -> List[Dict]:
        by_category = defaultdict(lambda: {"recycled_pcts": [], "recyclability_scores": [], "carbon_footprints": []})
        for pkg in self._packaging_data:
            cat = pkg["category"]
            by_category[cat]["recycled_pcts"].append(pkg["recycled_content_pct"])
            by_category[cat]["recyclability_scores"].append(pkg["recyclability_score"])
            by_category[cat]["carbon_footprints"].append(pkg["carbon_footprint"])

        summaries = []
        for category, data in by_category.items():
            summaries.append({
                "category": category,
                "avg_recycled_pct": round(sum(data["recycled_pcts"]) / max(len(data["recycled_pcts"]), 1), 1),
                "avg_recyclability": round(sum(data["recyclability_scores"]) / max(len(data["recyclability_scores"]), 1), 1),
                "material_count": len(data["recycled_pcts"]),
                "carbon_footprint": round(sum(data["carbon_footprints"]), 2),
            })
        return summaries

    def _generate_alerts(self):
        alerts = []

        for plant_id, carbon in self._carbon_data.items():
            if carbon.get("total_carbon_tons", 0) > EMISSION_BREACH_THRESHOLD_TONS:
                alerts.append({
                    "type": "emission_breach",
                    "severity": "High",
                    "plant_id": plant_id,
                    "plant_name": carbon.get("plant_name", plant_id),
                    "value": carbon["total_carbon_tons"],
                    "threshold": EMISSION_BREACH_THRESHOLD_TONS,
                    "message": f"Plant {carbon.get('plant_name', plant_id)} carbon emissions {carbon['total_carbon_tons']:.1f} tons exceed threshold {EMISSION_BREACH_THRESHOLD_TONS:.0f} tons",
                    "action": "Review production processes; consider carbon offset programs",
                })

        for pkg in self._packaging_data:
            if pkg["recycled_content_pct"] < RECYCLED_CONTENT_TARGET_PCT:
                alerts.append({
                    "type": "recycled_below_target",
                    "severity": "Medium",
                    "material_id": pkg["material_id"],
                    "value": pkg["recycled_content_pct"],
                    "target": RECYCLED_CONTENT_TARGET_PCT,
                    "message": f"Material {pkg['material_id']} recycled content {pkg['recycled_content_pct']:.1f}% below target {RECYCLED_CONTENT_TARGET_PCT:.0f}%",
                    "action": "Engage supplier for higher recycled content alternatives",
                })

        overall_sentiment = self._sentiment_data.get("overall_sentiment", 100)
        if overall_sentiment < SENTIMENT_DECLINE_THRESHOLD:
            alerts.append({
                "type": "sentiment_decline",
                "severity": "High",
                "value": overall_sentiment,
                "threshold": SENTIMENT_DECLINE_THRESHOLD,
                "message": f"Sustainability sentiment score {overall_sentiment:.1f} below threshold {SENTIMENT_DECLINE_THRESHOLD:.0f}",
                "action": "Escalate to communications team; review sustainability messaging",
            })

        brand_scores = self._sentiment_data.get("brand_scores", {})
        for brand, data in brand_scores.items():
            if data.get("sustainability_sentiment_score", 100) < SENTIMENT_DECLINE_THRESHOLD:
                alerts.append({
                    "type": "sentiment_decline",
                    "severity": "Medium",
                    "brand": brand,
                    "value": data["sustainability_sentiment_score"],
                    "threshold": SENTIMENT_DECLINE_THRESHOLD,
                    "message": f"Brand '{brand}' sustainability sentiment {data['sustainability_sentiment_score']:.1f} below threshold",
                    "action": f"Review brand '{brand}' sustainability communications",
                })

        self._alerts = alerts

    def _compute_kpis(self):
        total_carbon = sum(d.get("total_carbon_tons", 0) for d in self._carbon_data.values())
        total_production = sum(d.get("production_volume", 0) for d in self._carbon_data.values())
        carbon_intensity = round(total_carbon / max(total_production, 1) * 1000, 2)

        total_water = sum(d.get("water_usage_m3", 0) for d in self._water_waste_data.values())
        water_ratio = round(total_water / max(total_production, 1), 4)

        recycled_pcts = [p["recycled_content_pct"] for p in self._packaging_data]
        avg_recycled = round(sum(recycled_pcts) / max(len(recycled_pcts), 1), 1)

        total_energy = sum(d.get("energy_kwh", 0) for d in self._carbon_data.values())
        energy_efficiency_pct = round(min((total_production / max(total_energy, 1)) * 100, 100), 1)

        reports_with_data = len([r for r in self._sustainability_reports if r.get("Compliance_Status")])
        reporting_completeness = round(reports_with_data / max(len(self._plant_map), 1) * 100, 1)

        overall_sentiment = self._sentiment_data.get("overall_sentiment", 0)

        self._kpis = {
            "carbon_intensity": carbon_intensity,
            "water_ratio": water_ratio,
            "recycled_content_pct": avg_recycled,
            "energy_efficiency_pct": energy_efficiency_pct,
            "reporting_completeness_pct": min(reporting_completeness, 100),
            "sustainability_sentiment": overall_sentiment,
            "total_carbon_tons": total_carbon,
            "total_water_m3": total_water,
            "total_energy_kwh": total_energy,
            "plants_analyzed": len(self._plant_map),
            "materials_analyzed": len(self._packaging_data),
            "alerts_count": len(self._alerts),
            # Surface the alert list itself so the journey-report
            # schema's alerts_list section resolves at Data.kpis.alerts.
            "alerts": list(self._alerts) if isinstance(self._alerts, list) else [],
        }

    async def _push_to_simulator(self, plant_results: List[Dict], material_summaries: List[Dict],
                                  category_summaries: List[Dict], now: datetime):
        try:
            from src.apis.fdw_api import _simulators
            ext = _simulators.get("external")
            if not ext or not getattr(ext, "loaded", False):
                self._log("INFO", "External simulator not available — skipping simulator push", "publish_results")
                return

            await ext.write_table("external_sources", "ESG_KPI_Snapshot", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                **self._kpis,
            }])

            await ext.write_table("external_sources", "ESG_Plant_Result", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in plant_results
            ])

            await ext.write_table("external_sources", "ESG_Alert", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                "total_alerts": len(self._alerts),
                "alerts": json.dumps(self._alerts, default=str),
            }])

            await ext.write_table("external_sources", "ESG_Material_Summary", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in material_summaries
            ])

            await ext.write_table("external_sources", "ESG_Category_Summary", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in category_summaries
            ])

            self._log("INFO", (
                f"Pushed to simulator: {len(plant_results)} plant results, "
                f"{len(material_summaries)} material summaries, {len(category_summaries)} category summaries, "
                f"KPIs + {len(self._alerts)} alerts"
            ), "publish_results")

            await self._ensure_esg_result_mapping_rules()

            try:
                save_result = await ext.save_to_s3()
                if save_result.get("success"):
                    self._log("INFO", f"Persisted simulator to S3 ({save_result.get('tables')} tables, {save_result.get('rows')} rows)", "publish_results")
                    await self._broadcast_simulator_reload()
                else:
                    self._log("WARNING", f"S3 persist skipped: {save_result.get('message')}", "publish_results")
            except Exception as se:
                self._log("WARNING", f"Simulator S3 persist failed (non-fatal): {se}", "publish_results")

        except Exception as e:
            self._log("WARNING", f"Simulator push failed (non-fatal): {e}", "publish_results")

    async def _broadcast_simulator_reload(self):
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
                self._log("INFO", f"Broadcast simulator reload ({reloaded} calls)", "publish_results")
        except Exception as e:
            self._log("WARNING", f"Simulator reload broadcast failed (non-fatal): {e}", "publish_results")

    async def _ensure_esg_result_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_by_entity = {r.virtual_entity: r for r in existing}

            result_entities = [
                "ESG_KPI_Snapshot", "ESG_Plant_Result", "ESG_Alert",
                "ESG_Material_Summary", "ESG_Category_Summary",
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
                    name=f"ESG Result: {entity}",
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
                self._log("INFO", f"Created {created}, activated {activated} VDL mapping rules for ESG result entities", "publish_results")
        except Exception as e:
            self._log("WARNING", f"ESG result mapping rules failed (non-fatal): {e}", "publish_results")

    async def _write_to_s3(self, results: Dict) -> bool:
        if not self._s3:
            self._log("WARNING", "No S3 client configured — skipping S3 write", "publish_results")
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
                self._log("WARNING", "No S3 bucket configured", "publish_results")
                return False

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            prefix = f"esg-sustainability/{self.journey_id}/{timestamp}"

            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/esg-plant-results.json",
                Body=json.dumps(results["plant_results"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/esg-kpis.json",
                Body=json.dumps(results["kpis"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/esg-alerts.json",
                Body=json.dumps(results["alerts"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/esg-material-summaries.json",
                Body=json.dumps(results["material_summaries"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/esg-category-summaries.json",
                Body=json.dumps(results["category_summaries"], default=str),
                ContentType="application/json",
            )
            self._log("INFO", f"Written to s3://{bucket}/{prefix}/", "publish_results")
            return True
        except Exception as e:
            self._log("WARNING", f"S3 write failed: {e}", "publish_results")
            return False
