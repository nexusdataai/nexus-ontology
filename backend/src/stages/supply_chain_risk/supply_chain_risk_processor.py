"""
Supply Chain Risk Processor

Implements the 6-step supplier risk scoring pipeline. Each step queries the
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

scr_logger = logger.bind(component="supply-chain-risk-processor")

try:
    from ...utils.sse_manager import emit_task_progress, emit_log
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    def emit_task_progress(*a, **kw): pass
    def emit_log(*a, **kw): pass

REGIONS = ["North", "South", "East", "West", "Central"]

RISK_WEIGHTS = {
    "delivery": 0.25,
    "quality": 0.25,
    "financial": 0.25,
    "market": 0.25,
}


class SupplyChainRiskProcessor:

    def __init__(self, log_callback: Optional[Callable] = None, job_id: str = "",
                 journey_id: str = "", s3_client=None, config=None):
        self._log_cb = log_callback
        self.job_id = job_id
        self.journey_id = journey_id
        self._s3 = s3_client
        self._config = config

        self._vendor_map: Dict[str, Dict] = {}
        self._po_by_vendor: Dict[str, List[Dict]] = defaultdict(list)
        self._gr_by_vendor: Dict[str, List[Dict]] = defaultdict(list)
        self._materials: List[Dict] = []
        self._source_lists: List[Dict] = []
        self._market_signals: List[Dict] = []
        self._quality_lots: List[Dict] = []
        self._contracts: List[Dict] = []

        self._vendor_scores: Dict[str, Dict] = {}
        self._alerts: List[Dict] = []
        self._kpis: Dict[str, Any] = {}

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _log(self, level: str, msg: str, step_id: str = None):
        if self._log_cb:
            self._log_cb(level, msg, step_id)
        else:
            scr_logger.log(level.upper(), msg)
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
                "Vendor_Master": ("sap_s4hana", "sap", None),
                "Purchase_Order": ("oracle_erp", "oracle", "Oracle_Purchase_Order"),
                "Source_List": ("sap_s4hana", "sap", None),
                "Market_Signal": ("external_sources", "external", None),
                "Contract_Document": ("external_sources", "external", None),
                "Goods_Receipt": ("sap_s4hana", "sap", None),
                "Quality_Inspection_Lot": ("sap_s4hana", "sap", None),
                "Material_Master": ("sap_s4hana", "sap", None),
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
    def _deterministic_seed(key1: str, key2: str, key3: int) -> float:
        h = hashlib.md5(f"{key1}-{key2}-{key3}".encode()).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF

    # ─── Mapping Rules (source entities) ─────────────────────────────────

    async def _ensure_scr_source_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_entities = {r.virtual_entity for r in existing}

            rules = [
                ("Vendor_Master", "sap_s4hana", "Vendor_Master", {
                    "Vendor_ID": "Vendor_ID", "Vendor_Name": "Vendor_Name",
                    "Region": "Region", "Payment_Terms": "Payment_Terms",
                    "Status": "Status"}),
                ("Purchase_Order", "oracle_erp", "Oracle_Purchase_Order", {
                    "PO_ID": "PO_ID", "Vendor_ID": "Vendor_ID",
                    "Material_ID": "Material_ID", "Quantity": "Quantity",
                    "Unit_Price": "Unit_Price", "Total_Value": "Total_Value",
                    "Order_Date": "Order_Date", "Expected_Delivery": "Expected_Delivery"}),
                ("Source_List", "sap_s4hana", "Source_List", {
                    "Material_ID": "Material_ID", "Vendor_ID": "Vendor_ID",
                    "Valid_From": "Valid_From", "Valid_To": "Valid_To",
                    "Priority": "Priority"}),
                ("Market_Signal", "external_sources", "Market_Signal", {
                    "Signal_ID": "Signal_ID", "Source": "Source",
                    "Event_Type": "Event_Type", "Severity": "Severity",
                    "Affected_Commodity": "Affected_Commodity", "Timestamp": "Timestamp"}),
                ("Contract_Document", "external_sources", "Contract_Document", {
                    "Contract_ID": "Contract_ID", "Vendor_ID": "Vendor_ID",
                    "Start_Date": "Start_Date", "End_Date": "End_Date",
                    "Status": "Status", "Value": "Value"}),
                ("Goods_Receipt", "sap_s4hana", "Goods_Receipt", {
                    "GR_ID": "GR_ID", "PO_ID": "PO_ID", "Vendor_ID": "Vendor_ID",
                    "Material_ID": "Material_ID", "Quantity": "Quantity",
                    "Receipt_Date": "Receipt_Date", "Expected_Date": "Expected_Date"}),
                ("Quality_Inspection_Lot", "sap_s4hana", "Quality_Inspection_Lot", {
                    "Lot_ID": "Lot_ID", "Material_ID": "Material_ID",
                    "Vendor_ID": "Vendor_ID", "Inspection_Date": "Inspection_Date",
                    "Result": "Result", "Defect_Count": "Defect_Count"}),
                ("Material_Master", "sap_s4hana", "Material_Master", {
                    "Material_ID": "Material_ID", "Category": "Category",
                    "Pack_Size": "Pack_Size", "Shelf_Life_Days": "Shelf_Life_Days",
                    "Status": "Status"}),
            ]

            from src.models.mapping_rule_models import (
                MappingRuleCreateRequest, MappingRuleUpdateRequest,
                MappingRuleSourceType, MappingRuleStatus, FieldMap,
            )
            created = 0
            for virtual_entity, schema, table, field_map in rules:
                if virtual_entity in existing_entities:
                    continue
                field_maps = [FieldMap(source_field=s, target_field=t) for s, t in field_map.items()]
                rule = MappingRuleCreateRequest(
                    name=f"SCR: {virtual_entity}",
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
                self._log("INFO", f"Created {created} VDL mapping rules for supply chain risk")
        except Exception as e:
            self._log("WARNING", f"Could not ensure mapping rules: {e}")

    # ─── Mapping Rules (result entities) ─────────────────────────────────

    async def _ensure_scr_result_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_by_entity = {r.virtual_entity: r for r in existing}

            result_entities = [
                "SCR_KPI_Snapshot", "SCR_Vendor_Result", "SCR_Alert",
                "SCR_Region_Summary", "SCR_Category_Summary",
            ]

            from src.models.mapping_rule_models import (
                MappingRuleCreateRequest, MappingRuleUpdateRequest,
                MappingRuleSourceType, MappingRuleStatus, FieldMap,
            )
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
                    name=f"SCR Result: {entity}",
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
                self._log("INFO", f"Created {created}, activated {activated} VDL mapping rules for SCR result entities", "publish_results")
        except Exception as e:
            self._log("WARNING", f"SCR result mapping rules failed (non-fatal): {e}", "publish_results")

    # ─── Step 1: Load Supplier Data ──────────────────────────────────────

    async def step_load_supplier_data(self) -> Dict[str, Any]:
        self._log("INFO", "Step 1: Load Supplier Data — querying 8 entities...", "load_supplier_data")

        await self._ensure_scr_source_mapping_rules()

        vendors = await self._query_entity("Vendor_Master")
        purchase_orders = await self._query_entity("Purchase_Order")
        source_lists = await self._query_entity("Source_List")
        market_signals = await self._query_entity("Market_Signal")
        contracts = await self._query_entity("Contract_Document")
        goods_receipts = await self._query_entity("Goods_Receipt")
        quality_lots = await self._query_entity("Quality_Inspection_Lot")
        materials = await self._query_entity("Material_Master")

        self._log("INFO", (
            f"Loaded entities — Vendors: {len(vendors)}, POs: {len(purchase_orders)}, "
            f"SourceLists: {len(source_lists)}, Signals: {len(market_signals)}, "
            f"Contracts: {len(contracts)}, GoodsReceipts: {len(goods_receipts)}, "
            f"QualityLots: {len(quality_lots)}, Materials: {len(materials)}"
        ), "load_supplier_data")

        self._vendor_map = {}
        for v in vendors:
            vid = v.get("Vendor_ID", "")
            if vid:
                self._vendor_map[vid] = v

        self._po_by_vendor = defaultdict(list)
        for po in purchase_orders:
            vid = po.get("Vendor_ID", "")
            if vid:
                self._po_by_vendor[vid].append(po)

        self._gr_by_vendor = defaultdict(list)
        for gr in goods_receipts:
            vid = gr.get("Vendor_ID", "")
            if vid:
                self._gr_by_vendor[vid].append(gr)

        self._materials = materials
        self._source_lists = source_lists
        self._market_signals = market_signals
        self._quality_lots = quality_lots
        self._contracts = contracts

        for vid in self._vendor_map:
            self._vendor_scores[vid] = {
                "delivery_score": 0.0,
                "quality_score": 0.0,
                "financial_risk_score": 0.0,
                "market_risk_score": 0.0,
                "risk_score": 0.0,
                "otd_pct": 0.0,
                "single_source_materials": [],
            }

        self._log("INFO", f"Built lookup maps: {len(self._vendor_map)} vendors, "
                  f"{sum(len(v) for v in self._po_by_vendor.values())} POs mapped, "
                  f"{sum(len(v) for v in self._gr_by_vendor.values())} GRs mapped",
                  "load_supplier_data")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "load_supplier_data", "completed", len(self._vendor_map), len(self._vendor_map))

        return {
            "status": "completed",
            "vendors_loaded": len(self._vendor_map),
            "entities_queried": 8,
            "purchase_orders": len(purchase_orders),
            "goods_receipts": len(goods_receipts),
            "quality_lots": len(quality_lots),
        }

    # ─── Step 2: Delivery Scoring ────────────────────────────────────────

    async def step_delivery_scoring(self) -> Dict[str, Any]:
        self._log("INFO", "Step 2: Delivery Scoring — calculating OTD rate per vendor...", "delivery_scoring")

        if not self._vendor_map:
            return {"status": "error", "message": "No vendor data — run step 1 first"}

        scored = 0
        for vid, vendor in self._vendor_map.items():
            receipts = self._gr_by_vendor.get(vid, [])
            if not receipts:
                seed = self._deterministic_seed(vid, "delivery", 0)
                otd_rate = 0.50 + seed * 0.45
                delivery_score = round(otd_rate * 100)
            else:
                on_time = 0
                for gr in receipts:
                    receipt_date = gr.get("Receipt_Date", "")
                    expected_date = gr.get("Expected_Date", "")
                    if receipt_date and expected_date:
                        on_time += 1 if receipt_date <= expected_date else 0
                    else:
                        seed = self._deterministic_seed(vid, gr.get("GR_ID", ""), 1)
                        on_time += 1 if seed > 0.25 else 0
                otd_rate = on_time / len(receipts)
                delivery_score = round(otd_rate * 100)

            self._vendor_scores[vid]["otd_pct"] = round(otd_rate * 100, 1)
            self._vendor_scores[vid]["delivery_score"] = min(max(delivery_score, 0), 100)
            scored += 1

        self._log("INFO", f"Delivery scoring complete: {scored} vendors scored", "delivery_scoring")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "delivery_scoring", "completed", scored, scored)

        return {
            "status": "completed",
            "vendors_scored": scored,
            "avg_otd_pct": round(
                sum(s["otd_pct"] for s in self._vendor_scores.values()) / max(len(self._vendor_scores), 1), 1
            ),
        }

    # ─── Step 3: Quality Scoring ─────────────────────────────────────────

    async def step_quality_scoring(self) -> Dict[str, Any]:
        self._log("INFO", "Step 3: Quality Scoring — evaluating inspection pass rates...", "quality_scoring")

        if not self._vendor_map:
            return {"status": "error", "message": "No vendor data — run step 1 first"}

        lots_by_vendor = defaultdict(list)
        for lot in self._quality_lots:
            lot_vid = lot.get("Vendor_ID", "")
            if lot_vid:
                lots_by_vendor[lot_vid].append(lot)
                continue
            mat_id = lot.get("Material_ID", "")
            if mat_id:
                for vid, pos in self._po_by_vendor.items():
                    for po in pos:
                        if po.get("Material_ID") == mat_id:
                            lots_by_vendor[vid].append(lot)
                            break

        scored = 0
        for vid in self._vendor_map:
            vendor_lots = lots_by_vendor.get(vid, [])
            if not vendor_lots:
                seed = self._deterministic_seed(vid, "quality", 0)
                pass_rate = 0.60 + seed * 0.35
            else:
                passed = sum(1 for lot in vendor_lots if lot.get("Result", "").lower() in ("pass", "passed", "accepted"))
                pass_rate = passed / len(vendor_lots)

            quality_score = round(pass_rate * 100)
            self._vendor_scores[vid]["quality_score"] = min(max(quality_score, 0), 100)
            scored += 1

        self._log("INFO", f"Quality scoring complete: {scored} vendors scored", "quality_scoring")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "quality_scoring", "completed", scored, scored)

        return {
            "status": "completed",
            "vendors_scored": scored,
            "avg_quality_score": round(
                sum(s["quality_score"] for s in self._vendor_scores.values()) / max(len(self._vendor_scores), 1), 1
            ),
        }

    # ─── Step 4: Financial Risk ──────────────────────────────────────────

    async def step_financial_risk(self) -> Dict[str, Any]:
        self._log("INFO", "Step 4: Financial Risk — spend concentration and single-source analysis...", "financial_risk")

        if not self._vendor_map:
            return {"status": "error", "message": "No vendor data — run step 1 first"}

        vendor_spend = {}
        total_spend = 0.0
        for vid, pos in self._po_by_vendor.items():
            spend = sum(self._safe_float(po.get("Total_Value", 0)) for po in pos)
            if spend == 0:
                spend = sum(
                    self._safe_float(po.get("Quantity", 0)) * self._safe_float(po.get("Unit_Price", 0))
                    for po in pos
                )
            vendor_spend[vid] = spend
            total_spend += spend

        for vid in self._vendor_map:
            if vid not in vendor_spend:
                seed = self._deterministic_seed(vid, "spend", 0)
                vendor_spend[vid] = seed * 100000
                total_spend += vendor_spend[vid]

        material_vendors = defaultdict(set)
        for sl in self._source_lists:
            mat_id = sl.get("Material_ID", "")
            v_id = sl.get("Vendor_ID", "")
            if mat_id and v_id:
                material_vendors[mat_id].add(v_id)

        single_source_materials = defaultdict(list)
        for mat_id, v_set in material_vendors.items():
            if len(v_set) == 1:
                sole_vendor = list(v_set)[0]
                single_source_materials[sole_vendor].append(mat_id)

        scored = 0
        for vid in self._vendor_map:
            spend = vendor_spend.get(vid, 0)
            concentration = (spend / total_spend * 100) if total_spend > 0 else 0
            ss_count = len(single_source_materials.get(vid, []))

            concentration_risk = min(concentration * 2, 50)
            single_source_risk = min(ss_count * 15, 50)
            financial_risk_score = round(concentration_risk + single_source_risk)
            financial_risk_score = min(max(financial_risk_score, 0), 100)

            self._vendor_scores[vid]["financial_risk_score"] = financial_risk_score
            self._vendor_scores[vid]["spend_concentration_pct"] = round(concentration, 1)
            self._vendor_scores[vid]["single_source_materials"] = single_source_materials.get(vid, [])
            scored += 1

        total_single_source = sum(len(v) for v in single_source_materials.values())
        self._log("INFO", f"Financial risk complete: {scored} vendors scored, "
                  f"{total_single_source} single-source materials flagged", "financial_risk")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "financial_risk", "completed", scored, scored)

        return {
            "status": "completed",
            "vendors_scored": scored,
            "total_spend": round(total_spend, 2),
            "single_source_materials": total_single_source,
        }

    # ─── Step 5: Market Signal Integration ───────────────────────────────

    async def step_market_signal_integration(self) -> Dict[str, Any]:
        self._log("INFO", "Step 5: Market Signal Integration — disruption signals and composite scoring...", "market_signal_integration")

        if not self._vendor_map:
            return {"status": "error", "message": "No vendor data — run step 1 first"}

        mat_map = {}
        for m in self._materials:
            mid = m.get("Material_ID", "")
            if mid:
                mat_map[mid] = m

        vendor_commodities = defaultdict(set)
        for vid, pos in self._po_by_vendor.items():
            for po in pos:
                mat_id = po.get("Material_ID", "")
                mat = mat_map.get(mat_id, {})
                category = mat.get("Category", "")
                if category:
                    vendor_commodities[vid].add(category)

        signal_by_commodity = defaultdict(list)
        for sig in self._market_signals:
            commodity = sig.get("Affected_Commodity", "")
            if commodity:
                signal_by_commodity[commodity].append(sig)

        scored = 0
        high_signal_vendors = 0
        for vid in self._vendor_map:
            commodities = vendor_commodities.get(vid, set())
            market_risk = 0.0
            signal_count = 0

            for commodity in commodities:
                for sig in signal_by_commodity.get(commodity, []):
                    severity = sig.get("Severity", "Low")
                    if severity == "Critical":
                        market_risk += 30
                        signal_count += 1
                    elif severity == "High":
                        market_risk += 20
                        signal_count += 1
                    elif severity == "Medium":
                        market_risk += 5

            if signal_count == 0:
                seed = self._deterministic_seed(vid, "market", 0)
                market_risk = seed * 30

            market_risk_score = min(round(market_risk), 100)
            self._vendor_scores[vid]["market_risk_score"] = market_risk_score

            d = self._vendor_scores[vid]["delivery_score"]
            q = self._vendor_scores[vid]["quality_score"]
            f = self._vendor_scores[vid]["financial_risk_score"]
            m_score = market_risk_score

            inv_delivery = 100 - d
            inv_quality = 100 - q

            composite = (
                RISK_WEIGHTS["delivery"] * inv_delivery +
                RISK_WEIGHTS["quality"] * inv_quality +
                RISK_WEIGHTS["financial"] * f +
                RISK_WEIGHTS["market"] * m_score
            )
            self._vendor_scores[vid]["risk_score"] = round(min(max(composite, 0), 100), 1)

            if market_risk_score > 40:
                high_signal_vendors += 1
            scored += 1

        self._log("INFO", f"Market signal integration complete: {scored} vendors scored, "
                  f"{high_signal_vendors} with elevated market risk", "market_signal_integration")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "market_signal_integration", "completed", scored, scored)

        return {
            "status": "completed",
            "vendors_scored": scored,
            "market_signals_processed": len(self._market_signals),
            "high_signal_vendors": high_signal_vendors,
            "avg_risk_score": round(
                sum(s["risk_score"] for s in self._vendor_scores.values()) / max(len(self._vendor_scores), 1), 1
            ),
        }

    # ─── Step 6: Publish Results ─────────────────────────────────────────

    async def step_publish_results(self) -> Dict[str, Any]:
        self._log("INFO", "Step 6: Publish Results — generating KPIs, alerts, and writing to S3...", "publish_results")

        if not self._vendor_scores:
            return {"status": "error", "message": "No vendor scores — run steps 1-5 first"}

        self._generate_alerts()
        self._compute_kpis()

        vendor_results = []
        for vid, scores in self._vendor_scores.items():
            vendor = self._vendor_map.get(vid, {})
            vendor_results.append({
                "vendor_id": vid,
                "vendor_name": vendor.get("Vendor_Name", vid),
                "risk_score": scores["risk_score"],
                "otd_pct": scores["otd_pct"],
                "quality_score": scores["quality_score"],
                "financial_risk": scores["financial_risk_score"],
                "delivery_score": scores["delivery_score"],
                "single_source_materials": scores.get("single_source_materials", []),
                "region": vendor.get("Region", REGIONS[int(self._deterministic_seed(vid, "region", 0) * len(REGIONS))]),
            })

        now = datetime.now(timezone.utc)

        results = {
            "vendor_results": vendor_results,
            "kpis": self._kpis,
            "alerts": self._alerts,
            "generated_at": now.isoformat(),
        }

        written = await self._write_to_s3(results)
        await self._push_to_simulator(vendor_results, now)

        self._log("INFO", (
            f"Published {len(vendor_results)} vendor risk scores, {len(self._alerts)} alerts, "
            f"avg_risk={self._kpis.get('avg_risk_score', 'N/A')}"
        ), "publish_results")

        return {
            "status": "completed",
            "vendors_published": len(vendor_results),
            "alerts_generated": len(self._alerts),
            "kpis": self._kpis,
            "s3_written": written,
        }

    # ─── Simulator Push ──────────────────────────────────────────────────

    async def _push_to_simulator(self, vendor_results: List[Dict], now: datetime):
        try:
            from src.apis.fdw_api import _simulators
            ext = _simulators.get("external")
            if not ext or not getattr(ext, "loaded", False):
                self._log("INFO", "External simulator not available — skipping simulator push", "publish_results")
                return

            await ext.write_table("external_sources", "SCR_Vendor_Result", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in vendor_results
            ])

            await ext.write_table("external_sources", "SCR_KPI_Snapshot", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                **self._kpis,
            }])

            await ext.write_table("external_sources", "SCR_Alert", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                "total_alerts": len(self._alerts),
                "alerts": json.dumps(self._alerts, default=str),
            }])

            by_region = defaultdict(lambda: {"avg_risk": 0.0, "vendor_count": 0, "high_risk_count": 0, "_risk_sum": 0.0})
            for vr in vendor_results:
                r = by_region[vr["region"]]
                r["vendor_count"] += 1
                r["_risk_sum"] += vr["risk_score"]
                if vr["risk_score"] > 70:
                    r["high_risk_count"] += 1

            for region, vals in by_region.items():
                vals["avg_risk"] = round(vals["_risk_sum"] / max(vals["vendor_count"], 1), 1)
                del vals["_risk_sum"]

            await ext.write_table("external_sources", "SCR_Region_Summary", [
                {"region": region, "job_id": self.job_id, "processed_at": now.isoformat(), **vals}
                for region, vals in by_region.items()
            ])

            mat_map = {}
            for m in self._materials:
                mid = m.get("Material_ID", "")
                if mid:
                    mat_map[mid] = m

            by_category = defaultdict(lambda: {"avg_risk": 0.0, "vendor_count": 0, "single_source_count": 0, "_risk_sum": 0.0, "_vendors": set()})
            for vr in vendor_results:
                vendor_pos = self._po_by_vendor.get(vr["vendor_id"], [])
                categories = set()
                for po in vendor_pos:
                    mat = mat_map.get(po.get("Material_ID", ""), {})
                    cat = mat.get("Category", "")
                    if cat:
                        categories.add(cat)
                if not categories:
                    seed = self._deterministic_seed(vr["vendor_id"], "cat", 0)
                    categories.add(f"Category_{int(seed * 5) + 1}")
                for cat in categories:
                    c = by_category[cat]
                    c["_vendors"].add(vr["vendor_id"])
                    c["_risk_sum"] += vr["risk_score"]
                    c["single_source_count"] += len(vr.get("single_source_materials", []))

            for cat, vals in by_category.items():
                vals["vendor_count"] = len(vals["_vendors"])
                vals["avg_risk"] = round(vals["_risk_sum"] / max(vals["vendor_count"], 1), 1)
                del vals["_risk_sum"]
                del vals["_vendors"]

            await ext.write_table("external_sources", "SCR_Category_Summary", [
                {"category": cat, "job_id": self.job_id, "processed_at": now.isoformat(), **vals}
                for cat, vals in by_category.items()
            ])

            self._log("INFO", (
                f"Pushed to simulator: {len(vendor_results)} vendor scores, "
                f"{len(by_region)} region summaries, {len(by_category)} category summaries, "
                f"KPIs + {len(self._alerts)} alerts"
            ), "publish_results")

            await self._ensure_scr_result_mapping_rules()

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
                self._log("INFO", f"Broadcast simulator reload ({reloaded} calls)", "publish_results")
        except Exception as e:
            self._log("WARNING", f"Simulator reload broadcast failed (non-fatal): {e}", "publish_results")

    # ─── S3 Write ────────────────────────────────────────────────────────

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
            prefix = f"supply-chain-risk/{self.journey_id}/{timestamp}"

            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/vendor-results.json",
                Body=json.dumps(results["vendor_results"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/risk-kpis.json",
                Body=json.dumps(results["kpis"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/risk-alerts.json",
                Body=json.dumps(results["alerts"], default=str),
                ContentType="application/json",
            )
            self._log("INFO", f"Written to s3://{bucket}/{prefix}/", "publish_results")
            return True
        except Exception as e:
            self._log("WARNING", f"S3 write failed: {e}", "publish_results")
            return False

    # ─── Alert Generation ────────────────────────────────────────────────

    def _generate_alerts(self):
        alerts = []

        for vid, scores in self._vendor_scores.items():
            vendor = self._vendor_map.get(vid, {})
            vendor_name = vendor.get("Vendor_Name", vid)

            if scores["risk_score"] > 70:
                alerts.append({
                    "type": "high_risk_vendor",
                    "severity": "High",
                    "vendor_id": vid,
                    "vendor_name": vendor_name,
                    "risk_score": scores["risk_score"],
                    "message": f"Vendor {vendor_name} risk score {scores['risk_score']} exceeds threshold (70)",
                    "action": "Escalate to procurement; initiate backup vendor qualification",
                })

            for mat_id in scores.get("single_source_materials", []):
                alerts.append({
                    "type": "single_source",
                    "severity": "Medium",
                    "vendor_id": vid,
                    "vendor_name": vendor_name,
                    "material_id": mat_id,
                    "message": f"Material {mat_id} has only one approved vendor ({vendor_name})",
                    "action": "Qualify alternative supplier; update source list",
                })

        for sig in self._market_signals:
            severity = sig.get("Severity", "Low")
            if severity in ("High", "Critical"):
                alerts.append({
                    "type": "disruption_signal",
                    "severity": "High" if severity == "Critical" else "Medium",
                    "signal_id": sig.get("Signal_ID", ""),
                    "source": sig.get("Source", ""),
                    "event_type": sig.get("Event_Type", ""),
                    "affected_commodity": sig.get("Affected_Commodity", ""),
                    "message": f"{severity} signal: {sig.get('Event_Type', 'disruption')} affecting {sig.get('Affected_Commodity', 'unknown')}",
                    "action": "Review affected vendors; activate contingency plans",
                })

        self._alerts = alerts

    # ─── KPI Computation ─────────────────────────────────────────────────

    def _compute_kpis(self):
        if not self._vendor_scores:
            self._kpis = {}
            return

        risk_scores = [s["risk_score"] for s in self._vendor_scores.values()]
        otd_values = [s["otd_pct"] for s in self._vendor_scores.values()]
        total_single_source = sum(len(s.get("single_source_materials", [])) for s in self._vendor_scores.values())

        avg_risk = round(sum(risk_scores) / len(risk_scores), 1)
        otd_pct = round(sum(otd_values) / len(otd_values), 1)

        early_warning_days = round(7 + self._deterministic_seed("global", "ew", 0) * 14)

        active_contracts = [c for c in self._contracts if c.get("Status", "").lower() in ("active", "signed")]
        contract_compliance_pct = round(
            (len(active_contracts) / max(len(self._contracts), 1)) * 100, 1
        ) if self._contracts else round(75 + self._deterministic_seed("global", "cc", 0) * 20, 1)

        emergency_count = sum(1 for s in self._vendor_scores.values() if s["risk_score"] > 80)
        emergency_procurement_pct = round(
            (emergency_count / max(len(self._vendor_scores), 1)) * 100, 1
        )

        self._kpis = {
            "avg_risk_score": avg_risk,
            "otd_pct": otd_pct,
            "single_source_count": total_single_source,
            "early_warning_days": early_warning_days,
            "contract_compliance_pct": contract_compliance_pct,
            "emergency_procurement_pct": emergency_procurement_pct,
            # Surface the alert list + count on _kpis so the journey-
            # report schema's alerts_list section can resolve at
            # Data.kpis.alerts and the summary card at
            # Data.kpis.alerts_count.
            "alerts": list(self._alerts) if isinstance(self._alerts, list) else [],
            "alerts_count": len(self._alerts) if isinstance(self._alerts, list) else 0,
        }
