"""
Procurement Analytics Processor

Implements the 6-step procurement & spend analytics pipeline. Each step queries the
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

pa_logger = logger.bind(component="procurement-analytics-processor")

try:
    from ...utils.sse_manager import emit_task_progress, emit_log
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    def emit_task_progress(*a, **kw): pass
    def emit_log(*a, **kw): pass

MATERIAL_CATEGORIES = [
    "Raw Materials", "MRO Supplies", "Packaging", "IT Equipment",
    "Office Supplies", "Professional Services", "Logistics", "Chemicals",
    "Electronics", "Facility Maintenance",
]

VENDOR_SCORE_WEIGHTS = {
    "delivery": 0.25,
    "quality": 0.25,
    "compliance": 0.25,
    "cost": 0.25,
}


class ProcurementAnalyticsProcessor:

    def __init__(self, log_callback: Optional[Callable] = None, job_id: str = "",
                 journey_id: str = "", s3_client=None, config=None):
        self._log_cb = log_callback
        self.job_id = job_id
        self.journey_id = journey_id
        self._s3 = s3_client
        self._config = config

        self._vendor_map: Dict[str, Dict] = {}
        self._po_list: List[Dict] = []
        self._invoice_list: List[Dict] = []
        self._gr_list: List[Dict] = []
        self._contract_list: List[Dict] = []
        self._commodity_prices: List[Dict] = []
        self._payments: List[Dict] = []
        self._invoice_uploads: List[Dict] = []

        self._classified_spend: List[Dict] = []
        self._matched_orders: List[Dict] = []
        self._price_analyzed: List[Dict] = []
        self._vendor_scores: List[Dict] = []
        self._alerts: List[Dict] = []
        self._kpis: Dict[str, Any] = {}

    # ─── Shared helpers ───────────────────────────────────────────────────

    def _log(self, level: str, msg: str, step_id: str = None):
        if self._log_cb:
            self._log_cb(level, msg, step_id)
        else:
            pa_logger.log(level.upper(), msg)
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
                "Purchase_Order": ("oracle_erp", "oracle", "Oracle_Purchase_Order"),
                "Goods_Receipt": ("sap_s4hana", "sap", None),
                "AP_Invoice": ("oracle_erp", "oracle", "Oracle_AP_Invoice"),
                "AP_Payment": ("oracle_erp", "oracle", "Oracle_AP_Payment"),
                "Vendor_Master": ("sap_s4hana", "sap", None),
                "Contract_Document": ("external_sources", "external", None),
                "Commodity_Price": ("external_sources", "external", None),
                "Invoice_Upload": ("external_sources", "external", None),
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

    # ─── Mapping-rule bootstrap ───────────────────────────────────────────

    async def _ensure_procurement_analytics_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_entities = {r.virtual_entity for r in existing}

            rules = [
                ("Purchase_Order", "oracle_erp", "Oracle_Purchase_Order", {
                    "PO_ID": "PO_ID", "Vendor_ID": "Vendor_ID", "Material_ID": "Material_ID",
                    "Quantity": "Quantity", "Unit_Price": "Unit_Price", "Total_Amount": "Total_Amount",
                    "PO_Date": "PO_Date", "Status": "Status", "Category": "Category"}),
                ("Goods_Receipt", "sap_s4hana", "Goods_Receipt", {
                    "GR_ID": "GR_ID", "PO_ID": "PO_ID", "Material_ID": "Material_ID",
                    "Quantity": "Quantity", "Receipt_Date": "Receipt_Date", "Quality_Status": "Quality_Status"}),
                ("AP_Invoice", "oracle_erp", "Oracle_AP_Invoice", {
                    "Invoice_ID": "Invoice_ID", "PO_ID": "PO_ID", "Vendor_ID": "Vendor_ID",
                    "Amount": "Amount", "Invoice_Date": "Invoice_Date", "Status": "Status", "Due_Date": "Due_Date"}),
                ("AP_Payment", "oracle_erp", "Oracle_AP_Payment", {
                    "Payment_ID": "Payment_ID", "Invoice_ID": "Invoice_ID", "Amount": "Amount",
                    "Payment_Date": "Payment_Date", "Method": "Method"}),
                ("Vendor_Master", "sap_s4hana", "Vendor_Master", {
                    "Vendor_ID": "Vendor_ID", "Vendor_Name": "Vendor_Name", "Country": "Country",
                    "Category": "Category", "Status": "Status", "Rating": "Rating"}),
                ("Contract_Document", "external_sources", "Contract_Document", {
                    "Contract_ID": "Contract_ID", "Vendor_ID": "Vendor_ID", "Start_Date": "Start_Date",
                    "End_Date": "End_Date", "Terms": "Terms", "Value": "Value", "Category": "Category"}),
                ("Commodity_Price", "external_sources", "Commodity_Price", {
                    "Commodity_ID": "Commodity_ID", "Material_Category": "Material_Category",
                    "Benchmark_Price": "Benchmark_Price", "Currency": "Currency", "Effective_Date": "Effective_Date"}),
                ("Invoice_Upload", "external_sources", "Invoice_Upload", {
                    "Upload_ID": "Upload_ID", "Invoice_ID": "Invoice_ID", "File_Path": "File_Path",
                    "Upload_Date": "Upload_Date", "OCR_Status": "OCR_Status"}),
            ]

            from src.models.mapping_rule_models import MappingRuleCreateRequest, MappingRuleUpdateRequest, MappingRuleSourceType, MappingRuleStatus, FieldMap
            created = 0
            for virtual_entity, schema, table, field_map in rules:
                if virtual_entity in existing_entities:
                    continue
                field_maps = [FieldMap(source_field=s, target_field=t) for s, t in field_map.items()]
                rule = MappingRuleCreateRequest(
                    name=f"PA: {virtual_entity}",
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
                self._log("INFO", f"Created {created} VDL mapping rules for procurement analytics")
        except Exception as e:
            self._log("WARNING", f"Could not ensure mapping rules: {e}")

    async def _ensure_pa_result_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_by_entity = {r.virtual_entity: r for r in existing}

            result_entities = [
                "PA_KPI_Snapshot", "PA_Spend_Result", "PA_Alert",
                "PA_Vendor_Summary", "PA_Category_Summary",
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
                    name=f"PA Result: {entity}",
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
                self._log("INFO", f"Created {created}, activated {activated} VDL mapping rules for PA result entities", "publish_results")
        except Exception as e:
            self._log("WARNING", f"PA result mapping rules failed (non-fatal): {e}", "publish_results")

    # ─── Step 1: Load Procurement Data ────────────────────────────────────

    async def step_load_procurement_data(self) -> Dict[str, Any]:
        self._log("INFO", "Step 1: Load Procurement Data — querying 8 entities...", "load_procurement_data")

        await self._ensure_procurement_analytics_mapping_rules()

        pos = await self._query_entity("Purchase_Order")
        grs = await self._query_entity("Goods_Receipt")
        invoices = await self._query_entity("AP_Invoice")
        payments = await self._query_entity("AP_Payment")
        vendors = await self._query_entity("Vendor_Master")
        contracts = await self._query_entity("Contract_Document")
        commodity_prices = await self._query_entity("Commodity_Price")
        invoice_uploads = await self._query_entity("Invoice_Upload")

        self._log("INFO", (
            f"Loaded entities — POs: {len(pos)}, GRs: {len(grs)}, "
            f"Invoices: {len(invoices)}, Payments: {len(payments)}, "
            f"Vendors: {len(vendors)}, Contracts: {len(contracts)}, "
            f"Commodity Prices: {len(commodity_prices)}, Invoice Uploads: {len(invoice_uploads)}"
        ), "load_procurement_data")

        self._vendor_map = {}
        for v in vendors:
            vid = v.get("Vendor_ID", "")
            if vid:
                self._vendor_map[vid] = v

        self._po_list = pos
        self._invoice_list = invoices
        self._gr_list = grs
        self._contract_list = contracts
        self._commodity_prices = commodity_prices
        self._payments = payments
        self._invoice_uploads = invoice_uploads

        self._log("INFO", (
            f"Built maps: {len(self._vendor_map)} vendors, {len(pos)} POs, "
            f"{len(invoices)} invoices, {len(grs)} GRs"
        ), "load_procurement_data")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "load_procurement_data", "completed", len(pos), len(pos))

        return {
            "status": "completed",
            "entities_queried": 8,
            "purchase_orders": len(pos),
            "goods_receipts": len(grs),
            "invoices": len(invoices),
            "vendors": len(self._vendor_map),
            "contracts": len(contracts),
        }

    # ─── Step 2: Spend Classification ─────────────────────────────────────

    async def step_spend_classification(self) -> Dict[str, Any]:
        self._log("INFO", "Step 2: Spend Classification — categorizing spend and detecting maverick purchases...", "spend_classification")

        if not self._po_list:
            return {"status": "error", "message": "No purchase orders — run step 1 first"}

        vendor_contracts = defaultdict(list)
        for c in self._contract_list:
            vid = c.get("Vendor_ID", "")
            if vid:
                vendor_contracts[vid].append(c)

        classified = []
        maverick_count = 0
        total_spend = 0.0
        maverick_spend = 0.0

        for po in self._po_list:
            po_id = po.get("PO_ID", "")
            vendor_id = po.get("Vendor_ID", "")
            amount = self._safe_float(po.get("Total_Amount", po.get("Amount", 0)))
            material_id = po.get("Material_ID", "")

            cat_idx = int(self._deterministic_seed(material_id or po_id, "category", 0) * len(MATERIAL_CATEGORIES))
            category = MATERIAL_CATEGORIES[min(cat_idx, len(MATERIAL_CATEGORIES) - 1)]

            has_contract = len(vendor_contracts.get(vendor_id, [])) > 0
            maverick = not has_contract

            if maverick:
                maverick_count += 1
                maverick_spend += amount
            total_spend += amount

            classified.append({
                "po_id": po_id,
                "vendor_id": vendor_id,
                "material_id": material_id,
                "amount": amount,
                "category": category,
                "contract_coverage": has_contract,
                "maverick_flag": maverick,
            })

        self._classified_spend = classified
        maverick_pct = round(maverick_spend / max(total_spend, 1) * 100, 1)
        self._log("INFO", f"Classified {len(classified)} POs: {maverick_count} maverick ({maverick_pct}% of spend)", "spend_classification")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "spend_classification", "completed", len(classified), len(classified))

        return {
            "status": "completed",
            "pos_classified": len(classified),
            "maverick_count": maverick_count,
            "maverick_spend_pct": maverick_pct,
            "total_spend": round(total_spend, 2),
            "categories_found": len({c["category"] for c in classified}),
        }

    # ─── Step 3: Three-Way Match ──────────────────────────────────────────

    async def step_three_way_match(self) -> Dict[str, Any]:
        self._log("INFO", "Step 3: Three-Way Match — reconciling POs vs GRs vs invoices...", "three_way_match")

        if not self._classified_spend:
            return {"status": "error", "message": "No classified spend — run step 2 first"}

        gr_by_po = defaultdict(list)
        for gr in self._gr_list:
            po_id = gr.get("PO_ID", "")
            if po_id:
                gr_by_po[po_id].append(gr)

        inv_by_po = defaultdict(list)
        for inv in self._invoice_list:
            po_id = inv.get("PO_ID", "")
            if po_id:
                inv_by_po[po_id].append(inv)

        po_by_id = {}
        for po in self._po_list:
            pid = po.get("PO_ID", "")
            if pid:
                po_by_id[pid] = po

        matched = []
        status_counts = defaultdict(int)

        for spend in self._classified_spend:
            po_id = spend["po_id"]
            has_gr = len(gr_by_po.get(po_id, [])) > 0
            has_inv = len(inv_by_po.get(po_id, [])) > 0

            if has_gr and has_inv:
                gr_qty = sum(self._safe_float(g.get("Quantity", 0)) for g in gr_by_po[po_id])
                po_qty = self._safe_float(po_by_id.get(po_id, {}).get("Quantity", 0))
                if po_qty > 0 and abs(gr_qty - po_qty) / po_qty > 0.05:
                    status = "qty_mismatch"
                else:
                    status = "matched"
            elif not has_gr:
                status = "gr_missing"
            else:
                status = "invoice_missing"

            status_counts[status] += 1

            row = dict(spend)
            row["match_status"] = status
            row["has_gr"] = has_gr
            row["has_invoice"] = has_inv
            matched.append(row)

        self._matched_orders = matched
        stp_rate = round(status_counts.get("matched", 0) / max(len(matched), 1) * 100, 1)
        self._log("INFO", (
            f"Three-way match: {len(matched)} POs — matched: {status_counts['matched']}, "
            f"gr_missing: {status_counts['gr_missing']}, invoice_missing: {status_counts['invoice_missing']}, "
            f"qty_mismatch: {status_counts['qty_mismatch']} (STP rate: {stp_rate}%)"
        ), "three_way_match")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "three_way_match", "completed", len(matched), len(matched))

        return {
            "status": "completed",
            "pos_matched": len(matched),
            "stp_rate_pct": stp_rate,
            "match_breakdown": dict(status_counts),
        }

    # ─── Step 4: Price Variance Analysis ──────────────────────────────────

    async def step_price_variance_analysis(self) -> Dict[str, Any]:
        self._log("INFO", "Step 4: Price Variance Analysis — comparing vs commodity benchmarks...", "price_variance_analysis")

        if not self._matched_orders:
            return {"status": "error", "message": "No matched orders — run step 3 first"}

        benchmark_map = {}
        for cp in self._commodity_prices:
            cat = cp.get("Material_Category", "")
            price = self._safe_float(cp.get("Benchmark_Price", 0))
            if cat and price > 0:
                benchmark_map[cat] = price

        po_by_id = {}
        for po in self._po_list:
            pid = po.get("PO_ID", "")
            if pid:
                po_by_id[pid] = po

        analyzed = []
        anomaly_count = 0

        for order in self._matched_orders:
            po_id = order["po_id"]
            category = order["category"]
            amount = order["amount"]

            po_data = po_by_id.get(po_id, {})
            unit_price = self._safe_float(po_data.get("Unit_Price", 0))
            quantity = self._safe_float(po_data.get("Quantity", 0))

            if unit_price == 0 and quantity > 0:
                unit_price = amount / quantity
            elif unit_price == 0:
                unit_price = 50 + self._deterministic_seed(po_id, "price", 0) * 450

            benchmark = benchmark_map.get(category, 0)
            if benchmark == 0:
                benchmark = unit_price * (0.85 + self._deterministic_seed(category, "bench", 0) * 0.25)

            variance_pct = round((unit_price - benchmark) / max(benchmark, 0.01) * 100, 2)
            flagged = abs(variance_pct) > 10.0

            if flagged:
                anomaly_count += 1

            row = dict(order)
            row["unit_price"] = round(unit_price, 2)
            row["benchmark_price"] = round(benchmark, 2)
            row["price_variance_pct"] = variance_pct
            row["price_flagged"] = flagged
            analyzed.append(row)

        self._price_analyzed = analyzed
        self._log("INFO", f"Price analysis: {anomaly_count}/{len(analyzed)} POs flagged (>10% variance)", "price_variance_analysis")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "price_variance_analysis", "completed", len(analyzed), len(analyzed))

        return {
            "status": "completed",
            "pos_analyzed": len(analyzed),
            "anomalies_flagged": anomaly_count,
            "avg_variance_pct": round(sum(a["price_variance_pct"] for a in analyzed) / max(len(analyzed), 1), 2),
        }

    # ─── Step 5: Vendor Scorecard ─────────────────────────────────────────

    async def step_vendor_scorecard(self) -> Dict[str, Any]:
        self._log("INFO", "Step 5: Vendor Scorecard — scoring vendors on multi-dimensional metrics...", "vendor_scorecard")

        if not self._price_analyzed:
            return {"status": "error", "message": "No price analysis — run step 4 first"}

        vendor_data = defaultdict(lambda: {
            "pos": [], "grs": [], "total_spend": 0.0,
            "contract_count": 0, "maverick_count": 0,
            "variance_sum": 0.0, "flagged_count": 0,
        })

        for order in self._price_analyzed:
            vid = order["vendor_id"]
            vendor_data[vid]["pos"].append(order)
            vendor_data[vid]["total_spend"] += order["amount"]
            if order.get("maverick_flag"):
                vendor_data[vid]["maverick_count"] += 1
            if order.get("contract_coverage"):
                vendor_data[vid]["contract_count"] += 1
            vendor_data[vid]["variance_sum"] += abs(order.get("price_variance_pct", 0))
            if order.get("price_flagged"):
                vendor_data[vid]["flagged_count"] += 1

        gr_po_vendor = {}
        for order in self._price_analyzed:
            gr_po_vendor[order["po_id"]] = order["vendor_id"]
        for gr in self._gr_list:
            po_id = gr.get("PO_ID", "")
            vid = gr_po_vendor.get(po_id)
            if vid:
                vendor_data[vid]["grs"].append(gr)

        scores = []
        for vid, data in vendor_data.items():
            po_count = len(data["pos"])
            vendor_info = self._vendor_map.get(vid, {})

            gr_count = len(data["grs"])
            delivery_ratio = gr_count / max(po_count, 1)
            delivery_score = round(min(delivery_ratio * 100, 100), 1)

            quality_seed = self._deterministic_seed(vid, "quality", 0)
            quality_score = round(60 + quality_seed * 40, 1)

            compliance_ratio = data["contract_count"] / max(po_count, 1)
            compliance_score = round(compliance_ratio * 100, 1)

            avg_variance = data["variance_sum"] / max(po_count, 1)
            cost_score = round(max(100 - avg_variance, 0), 1)

            composite = round(
                delivery_score * VENDOR_SCORE_WEIGHTS["delivery"] +
                quality_score * VENDOR_SCORE_WEIGHTS["quality"] +
                compliance_score * VENDOR_SCORE_WEIGHTS["compliance"] +
                cost_score * VENDOR_SCORE_WEIGHTS["cost"],
                1,
            )

            on_time_pct = round(delivery_ratio * 100, 1)

            scores.append({
                "vendor_id": vid,
                "vendor_name": vendor_info.get("Vendor_Name", vendor_info.get("Name", f"Vendor-{vid}")),
                "total_spend": round(data["total_spend"], 2),
                "po_count": po_count,
                "on_time_pct": on_time_pct,
                "delivery_score": delivery_score,
                "quality_score": quality_score,
                "compliance_score": compliance_score,
                "cost_score": cost_score,
                "composite_score": composite,
            })

        scores.sort(key=lambda s: s["composite_score"], reverse=True)
        self._vendor_scores = scores
        top_name = scores[0]["vendor_name"] if scores else "N/A"
        top_score = scores[0]["composite_score"] if scores else 0
        self._log("INFO", f"Scored {len(scores)} vendors (top: {top_name} @ {top_score})", "vendor_scorecard")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "vendor_scorecard", "completed", len(scores), len(scores))

        return {
            "status": "completed",
            "vendors_scored": len(scores),
            "avg_composite_score": round(sum(s["composite_score"] for s in scores) / max(len(scores), 1), 1),
            "top_vendor": top_name,
        }

    # ─── Step 6: Publish Results ──────────────────────────────────────────

    async def step_publish_results(self) -> Dict[str, Any]:
        self._log("INFO", "Step 6: Publish Results — generating KPIs, alerts, and writing to S3...", "publish_results")

        if not self._price_analyzed:
            return {"status": "error", "message": "No analyzed data — run steps 1-5 first"}

        self._generate_alerts()
        self._compute_kpis()

        spend_data = []
        for order in self._price_analyzed:
            spend_data.append({
                "po_id": order["po_id"],
                "vendor": order["vendor_id"],
                "category": order["category"],
                "amount": order["amount"],
                "maverick_flag": order.get("maverick_flag", False),
                "contract_coverage": order.get("contract_coverage", False),
                "match_status": order.get("match_status", "unknown"),
                "price_variance": order.get("price_variance_pct", 0),
            })

        now = datetime.now(timezone.utc)

        results = {
            "spend_data": spend_data,
            "kpis": self._kpis,
            "alerts": self._alerts,
            "vendor_scores": self._vendor_scores,
            "generated_at": now.isoformat(),
        }

        written = await self._write_to_s3(results)
        await self._push_to_simulator(spend_data, now)

        self._log("INFO", (
            f"Published {len(spend_data)} spend records, {len(self._alerts)} alerts, "
            f"{len(self._vendor_scores)} vendor scores"
        ), "publish_results")

        return {
            "status": "completed",
            "spend_records_published": len(spend_data),
            "alerts_generated": len(self._alerts),
            "kpis": self._kpis,
            "s3_written": written,
        }

    # ─── Simulator push ──────────────────────────────────────────────────

    async def _push_to_simulator(self, spend_data: List[Dict], now: datetime):
        try:
            from src.apis.fdw_api import _simulators
            ext = _simulators.get("external")
            if not ext or not getattr(ext, "loaded", False):
                self._log("INFO", "External simulator not available — skipping simulator push", "publish_results")
                return

            await ext.write_table("external_sources", "PA_KPI_Snapshot", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                **self._kpis,
            }])

            await ext.write_table("external_sources", "PA_Spend_Result", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in spend_data
            ])

            await ext.write_table("external_sources", "PA_Alert", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                "total_alerts": len(self._alerts),
                "alerts": json.dumps(self._alerts, default=str),
            }])

            await ext.write_table("external_sources", "PA_Vendor_Summary", [
                {
                    "vendor_id": vs["vendor_id"],
                    "vendor_name": vs["vendor_name"],
                    "total_spend": vs["total_spend"],
                    "po_count": vs["po_count"],
                    "on_time_pct": vs["on_time_pct"],
                    "quality_score": vs["quality_score"],
                    "compliance_score": vs["compliance_score"],
                    "job_id": self.job_id,
                    "processed_at": now.isoformat(),
                }
                for vs in self._vendor_scores
            ])

            by_category = defaultdict(lambda: {"total_spend": 0.0, "vendor_ids": set(), "maverick_count": 0, "total_count": 0})
            for order in self._price_analyzed:
                cat = order["category"]
                by_category[cat]["total_spend"] += order["amount"]
                by_category[cat]["vendor_ids"].add(order["vendor_id"])
                by_category[cat]["total_count"] += 1
                if order.get("maverick_flag"):
                    by_category[cat]["maverick_count"] += 1

            await ext.write_table("external_sources", "PA_Category_Summary", [
                {
                    "category": cat,
                    "total_spend": round(data["total_spend"], 2),
                    "vendor_count": len(data["vendor_ids"]),
                    "maverick_pct": round(data["maverick_count"] / max(data["total_count"], 1) * 100, 1),
                    "job_id": self.job_id,
                    "processed_at": now.isoformat(),
                }
                for cat, data in by_category.items()
            ])

            self._log("INFO", (
                f"Pushed to simulator: {len(spend_data)} spend records, "
                f"{len(self._vendor_scores)} vendor summaries, {len(by_category)} category summaries, "
                f"KPIs + {len(self._alerts)} alerts"
            ), "publish_results")

            await self._ensure_pa_result_mapping_rules()

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

    # ─── Alert generation ─────────────────────────────────────────────────

    def _generate_alerts(self):
        alerts = []

        for order in self._price_analyzed:
            if order.get("maverick_flag"):
                alerts.append({
                    "type": "maverick_purchase",
                    "severity": "Medium",
                    "po_id": order["po_id"],
                    "vendor_id": order["vendor_id"],
                    "amount": order["amount"],
                    "message": f"PO {order['po_id']} placed outside contract coverage (vendor: {order['vendor_id']})",
                    "action": "Review with procurement team; negotiate contract terms",
                })

        for order in self._price_analyzed:
            if abs(order.get("price_variance_pct", 0)) > 15.0:
                alerts.append({
                    "type": "price_anomaly",
                    "severity": "High",
                    "po_id": order["po_id"],
                    "vendor_id": order["vendor_id"],
                    "variance_pct": order["price_variance_pct"],
                    "message": f"Price variance {order['price_variance_pct']:.1f}% on PO {order['po_id']} exceeds 15% threshold",
                    "action": "Escalate to procurement manager; verify pricing terms",
                })

        for order in self._matched_orders:
            if order.get("match_status") != "matched":
                alerts.append({
                    "type": "invoice_mismatch",
                    "severity": "Medium",
                    "po_id": order["po_id"],
                    "match_status": order["match_status"],
                    "message": f"Three-way match failed for PO {order['po_id']}: {order['match_status']}",
                    "action": "Route to AP team for resolution",
                })

        self._alerts = alerts

    # ─── KPI computation ──────────────────────────────────────────────────

    def _compute_kpis(self):
        if not self._price_analyzed:
            self._kpis = {}
            return

        total_spend = sum(o["amount"] for o in self._price_analyzed)
        maverick_spend = sum(o["amount"] for o in self._price_analyzed if o.get("maverick_flag"))
        maverick_spend_pct = round(maverick_spend / max(total_spend, 1) * 100, 1)

        matched_count = sum(1 for o in self._matched_orders if o.get("match_status") == "matched")
        stp_rate_pct = round(matched_count / max(len(self._matched_orders), 1) * 100, 1)

        avg_processing_days = round(3 + self._deterministic_seed("global", "proc_days", 0) * 12, 1)

        avg_variance = round(
            sum(abs(o.get("price_variance_pct", 0)) for o in self._price_analyzed)
            / max(len(self._price_analyzed), 1), 1,
        )

        vendor_spends = defaultdict(float)
        for o in self._price_analyzed:
            vendor_spends[o["vendor_id"]] += o["amount"]
        shares = [s / max(total_spend, 1) for s in vendor_spends.values()]
        vendor_concentration_idx = round(sum(s ** 2 for s in shares) * 10000, 1)

        self._kpis = {
            "total_spend": round(total_spend, 2),
            "maverick_spend_pct": maverick_spend_pct,
            "stp_rate_pct": stp_rate_pct,
            "avg_processing_days": avg_processing_days,
            "price_variance_pct": avg_variance,
            "vendor_concentration_idx": vendor_concentration_idx,
            "alerts_count": len(self._alerts) if isinstance(getattr(self, "_alerts", None), list) else 0,
            "alerts": list(self._alerts) if isinstance(getattr(self, "_alerts", None), list) else [],
        }

    # ─── S3 output ────────────────────────────────────────────────────────

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
            prefix = f"procurement-analytics/{self.journey_id}/{timestamp}"

            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/spend-data.json",
                Body=json.dumps(results["spend_data"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/spend-kpis.json",
                Body=json.dumps(results["kpis"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/spend-alerts.json",
                Body=json.dumps(results["alerts"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/vendor-scores.json",
                Body=json.dumps(results["vendor_scores"], default=str),
                ContentType="application/json",
            )
            self._log("INFO", f"Written to s3://{bucket}/{prefix}/", "publish_results")
            return True
        except Exception as e:
            self._log("WARNING", f"S3 write failed: {e}", "publish_results")
            return False
