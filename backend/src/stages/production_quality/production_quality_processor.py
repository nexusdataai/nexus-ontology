"""
Production & Quality Copilot Processor

Implements the 6-step production quality pipeline. Each step queries the
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

pq_logger = logger.bind(component="production-quality-processor")

try:
    from ...utils.sse_manager import emit_task_progress, emit_log
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    def emit_task_progress(*a, **kw): pass
    def emit_log(*a, **kw): pass


class ProductionQualityProcessor:

    def __init__(self, log_callback: Optional[Callable] = None, job_id: str = "",
                 journey_id: str = "", s3_client=None, config=None):
        self._log_cb = log_callback
        self.job_id = job_id
        self.journey_id = journey_id
        self._s3 = s3_client
        self._config = config

        self._order_map: Dict[str, Dict] = {}
        self._line_map: Dict[str, Dict] = {}
        self._batch_by_order: Dict[str, List[Dict]] = defaultdict(list)
        self._inspection_lots: List[Dict] = []
        self._test_results: List[Dict] = []
        self._materials: Dict[str, Dict] = {}
        self._lab_reports: List[Dict] = []

        self._oee_by_line: Dict[str, Dict] = {}
        self._yield_analysis: List[Dict] = []
        self._quality_scores: Dict[str, Dict] = {}
        self._schedule_data: List[Dict] = []
        self._alerts: List[Dict] = []
        self._kpis: Dict[str, Any] = {}

    # ─── Logging ──────────────────────────────────────────────────────────

    def _log(self, level: str, msg: str, step_id: str = None):
        if self._log_cb:
            self._log_cb(level, msg, step_id)
        else:
            pq_logger.log(level.upper(), msg)
        if SSE_AVAILABLE and self.job_id and step_id:
            emit_log(self.job_id, step_id, level.upper(), msg)

    # ─── Virtual Data Layer helpers ───────────────────────────────────────

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
                "Production_Order": ("sap_s4hana", "sap"),
                "Production_Line": ("sap_s4hana", "sap"),
                "Bill_of_Materials": ("sap_s4hana", "sap"),
                "Quality_Inspection_Lot": ("sap_s4hana", "sap"),
                "Quality_Test_Result": ("sap_s4hana", "sap"),
                "Batch_Master": ("sap_s4hana", "sap"),
                "Material_Master": ("sap_s4hana", "sap"),
                "Lab_Report_Upload": ("external_sources", "external"),
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

    # ─── Utility helpers ──────────────────────────────────────────────────

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

    # ─── Mapping rules ────────────────────────────────────────────────────

    async def _ensure_pq_source_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_entities = {r.virtual_entity for r in existing}

            rules = [
                ("Production_Order", "sap_s4hana", "Production_Order", {
                    "Order_ID": "Order_ID", "Material_ID": "Material_ID", "Line_ID": "Line_ID",
                    "Plant_ID": "Plant_ID", "Planned_Qty": "Planned_Qty", "Actual_Qty": "Actual_Qty",
                    "Planned_Start": "Planned_Start", "Planned_End": "Planned_End",
                    "Actual_Start": "Actual_Start", "Actual_End": "Actual_End", "Status": "Status"}),
                ("Production_Line", "sap_s4hana", "Production_Line", {
                    "Line_ID": "Line_ID", "Plant_ID": "Plant_ID", "Line_Name": "Line_Name",
                    "Capacity_Per_Hour": "Capacity_Per_Hour", "Status": "Status"}),
                ("Bill_of_Materials", "sap_s4hana", "Bill_of_Materials", {
                    "BOM_ID": "BOM_ID", "Material_ID": "Material_ID", "Component_ID": "Component_ID",
                    "Quantity_Per": "Quantity_Per", "UOM": "UOM"}),
                ("Quality_Inspection_Lot", "sap_s4hana", "Quality_Inspection_Lot", {
                    "Inspection_Lot_ID": "Inspection_Lot_ID", "Order_ID": "Order_ID",
                    "Material_ID": "Material_ID", "Plant_ID": "Plant_ID",
                    "Lot_Size": "Lot_Size", "Status": "Status"}),
                ("Quality_Test_Result", "sap_s4hana", "Quality_Test_Result", {
                    "Result_ID": "Result_ID", "Inspection_Lot_ID": "Inspection_Lot_ID",
                    "Test_Type": "Test_Type", "Result": "Result", "Pass_Fail": "Pass_Fail",
                    "Measured_Value": "Measured_Value", "Spec_Lower": "Spec_Lower", "Spec_Upper": "Spec_Upper"}),
                ("Batch_Master", "sap_s4hana", "Batch_Master", {
                    "Batch_ID": "Batch_ID", "Material_ID": "Material_ID", "Order_ID": "Order_ID",
                    "Production_Date": "Production_Date", "Expiry_Date": "Expiry_Date", "Status": "Status"}),
                ("Material_Master", "sap_s4hana", "Material_Master", {
                    "Material_ID": "Material_ID", "Category": "Category", "Pack_Size": "Pack_Size",
                    "Shelf_Life_Days": "Shelf_Life_Days", "Status": "Status"}),
                ("Lab_Report_Upload", "external_sources", "Lab_Report_Upload", {
                    "Report_ID": "Report_ID", "Batch_ID": "Batch_ID", "Test_Date": "Test_Date",
                    "Result_Summary": "Result_Summary", "Status": "Status"}),
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
                    name=f"PQ: {virtual_entity}",
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
                self._log("INFO", f"Created {created} VDL mapping rules for production quality")
        except Exception as e:
            self._log("WARNING", f"Could not ensure mapping rules: {e}")

    async def _ensure_pq_result_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_by_entity = {r.virtual_entity: r for r in existing}

            result_entities = [
                "PQ_KPI_Snapshot", "PQ_Production_Result", "PQ_Alert",
                "PQ_Line_Summary", "PQ_Quality_Summary",
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
                    name=f"PQ Result: {entity}",
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
                self._log("INFO", f"Created {created}, activated {activated} VDL mapping rules for PQ result entities", "publish_results")
        except Exception as e:
            self._log("WARNING", f"PQ result mapping rules failed (non-fatal): {e}", "publish_results")

    # ─── Step 1: Load Production Data ─────────────────────────────────────

    async def step_load_production_data(self) -> Dict[str, Any]:
        self._log("INFO", "Step 1: Load Production Data — querying 8 entities...", "load_production_data")

        await self._ensure_pq_source_mapping_rules()

        orders = await self._query_entity("Production_Order")
        lines = await self._query_entity("Production_Line")
        boms = await self._query_entity("Bill_of_Materials")
        inspection_lots = await self._query_entity("Quality_Inspection_Lot")
        test_results = await self._query_entity("Quality_Test_Result")
        batches = await self._query_entity("Batch_Master")
        materials = await self._query_entity("Material_Master")
        lab_reports = await self._query_entity("Lab_Report_Upload")

        self._log("INFO", (
            f"Loaded entities — Orders: {len(orders)}, Lines: {len(lines)}, "
            f"BOMs: {len(boms)}, InspectionLots: {len(inspection_lots)}, "
            f"TestResults: {len(test_results)}, Batches: {len(batches)}, "
            f"Materials: {len(materials)}, LabReports: {len(lab_reports)}"
        ), "load_production_data")

        for o in orders:
            oid = o.get("Production_Order_ID") or o.get("Order_ID", "")
            if oid:
                self._order_map[oid] = o

        for ln in lines:
            lid = ln.get("Line_ID", "")
            if lid:
                self._line_map[lid] = ln

        for b in batches:
            oid = b.get("Order_ID", "")
            if oid:
                self._batch_by_order[oid].append(b)

        self._inspection_lots = inspection_lots
        self._test_results = test_results
        self._lab_reports = lab_reports

        for m in materials:
            mid = m.get("Material_ID", "")
            if mid:
                self._materials[mid] = m

        self._log("INFO", (
            f"Built maps — order_map: {len(self._order_map)}, line_map: {len(self._line_map)}, "
            f"batch_by_order: {len(self._batch_by_order)}, materials: {len(self._materials)}"
        ), "load_production_data")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "load_production_data", "completed",
                               len(self._order_map), len(self._order_map))

        return {
            "status": "completed",
            "orders": len(self._order_map),
            "lines": len(self._line_map),
            "inspection_lots": len(inspection_lots),
            "test_results": len(test_results),
            "batches": len(batches),
            "materials": len(self._materials),
            "entities_queried": 8,
        }

    # ─── Step 2: OEE Calculation ──────────────────────────────────────────

    async def step_oee_calculation(self) -> Dict[str, Any]:
        self._log("INFO", "Step 2: OEE Calculation — computing per-line effectiveness...", "oee_calculation")

        if not self._line_map:
            return {"status": "error", "message": "No production lines loaded — run step 1 first"}

        oee_results = {}
        for line_id, line in self._line_map.items():
            availability = self._deterministic_seed(line_id, "avail", 0) * 0.15 + 0.80
            performance = self._deterministic_seed(line_id, "perf", 0) * 0.15 + 0.82
            quality_rate = self._deterministic_seed(line_id, "qual", 0) * 0.08 + 0.90
            oee = availability * performance * quality_rate

            oee_results[line_id] = {
                "line_id": line_id,
                "plant": line.get("Plant_ID", ""),
                "availability": round(availability, 4),
                "performance": round(performance, 4),
                "quality_rate": round(quality_rate, 4),
                "oee": round(oee, 4),
            }

        self._oee_by_line = oee_results

        avg_oee = sum(v["oee"] for v in oee_results.values()) / max(len(oee_results), 1)
        self._log("INFO", f"Computed OEE for {len(oee_results)} lines, avg OEE={avg_oee:.2%}", "oee_calculation")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "oee_calculation", "completed",
                               len(oee_results), len(oee_results))

        return {
            "status": "completed",
            "lines_computed": len(oee_results),
            "avg_oee": round(avg_oee * 100, 2),
        }

    # ─── Step 3: Yield Analysis ───────────────────────────────────────────

    async def step_yield_analysis(self) -> Dict[str, Any]:
        self._log("INFO", "Step 3: Yield Analysis — planned vs actual quantities...", "yield_analysis")

        if not self._order_map:
            return {"status": "error", "message": "No production orders loaded — run step 1 first"}

        results = []
        for order_id, order in self._order_map.items():
            planned_qty = self._safe_float(order.get("Planned_Qty", 1000))
            if planned_qty <= 0:
                planned_qty = 1000

            seed = self._deterministic_seed(order_id, "yield", 0)
            actual_qty = round(planned_qty * (0.85 + seed * 0.15))
            yield_pct = round(actual_qty / planned_qty * 100, 2)

            defect_seed = self._deterministic_seed(order_id, "defect", 0)
            defect_count = int((planned_qty - actual_qty) * (0.5 + defect_seed * 0.5))

            line_id = order.get("Line_ID", "")
            oee_data = self._oee_by_line.get(line_id, {})

            results.append({
                "order_id": order_id,
                "material": order.get("Material_ID", ""),
                "line_id": line_id,
                "planned_qty": planned_qty,
                "actual_qty": actual_qty,
                "yield_pct": yield_pct,
                "defect_count": defect_count,
                "oee": oee_data.get("oee", 0.0),
                "status": order.get("Status", ""),
            })

        self._yield_analysis = results

        avg_yield = sum(r["yield_pct"] for r in results) / max(len(results), 1)
        self._log("INFO", f"Analyzed yield for {len(results)} orders, avg yield={avg_yield:.1f}%", "yield_analysis")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "yield_analysis", "completed",
                               len(results), len(results))

        return {
            "status": "completed",
            "orders_analyzed": len(results),
            "avg_yield_pct": round(avg_yield, 2),
            "total_defects": sum(r["defect_count"] for r in results),
        }

    # ─── Step 4: Quality Scoring ──────────────────────────────────────────

    async def step_quality_scoring(self) -> Dict[str, Any]:
        self._log("INFO", "Step 4: Quality Scoring — evaluating inspection lots...", "quality_scoring")

        results_by_lot = defaultdict(list)
        for tr in self._test_results:
            lot_id = tr.get("Inspection_ID") or tr.get("Inspection_Lot_ID", "")
            if lot_id:
                results_by_lot[lot_id].append(tr)

        lot_by_material = defaultdict(list)
        for lot in self._inspection_lots:
            mat_id = lot.get("Material_ID", "")
            lot_id = lot.get("Inspection_ID") or lot.get("Inspection_Lot_ID", "")
            if mat_id and lot_id:
                test_list = results_by_lot.get(lot_id, [])
                total = len(test_list)
                passed = sum(1 for t in test_list if str(t.get("Pass_Flag") or t.get("Pass_Fail", "")).upper() in ("PASS", "P", "Y", "YES", "TRUE", "1"))
                if total == 0:
                    seed = self._deterministic_seed(lot_id, "qscore", 0)
                    pass_rate = round((0.85 + seed * 0.15) * 100, 2)
                else:
                    pass_rate = round(passed / total * 100, 2)
                lot_by_material[mat_id].append({
                    "lot_id": lot_id,
                    "total_tests": total,
                    "passed": passed,
                    "pass_rate": pass_rate,
                })

        quality_scores = {}
        for mat_id, lots in lot_by_material.items():
            mat = self._materials.get(mat_id, {})
            avg_pass_rate = sum(l["pass_rate"] for l in lots) / max(len(lots), 1)
            first_pass_seed = self._deterministic_seed(mat_id, "firstpass", 0)
            first_pass_pct = round((0.82 + first_pass_seed * 0.16) * 100, 2)

            quality_scores[mat_id] = {
                "material_id": mat_id,
                "category": mat.get("Category", ""),
                "inspections": len(lots),
                "pass_rate": round(avg_pass_rate, 2),
                "defect_rate": round(100 - avg_pass_rate, 2),
                "first_pass_pct": first_pass_pct,
            }

        self._quality_scores = quality_scores

        avg_pass = sum(v["pass_rate"] for v in quality_scores.values()) / max(len(quality_scores), 1)
        self._log("INFO", (
            f"Scored {len(quality_scores)} materials across {len(self._inspection_lots)} lots, "
            f"avg pass rate={avg_pass:.1f}%"
        ), "quality_scoring")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "quality_scoring", "completed",
                               len(quality_scores), len(quality_scores))

        return {
            "status": "completed",
            "materials_scored": len(quality_scores),
            "total_inspections": len(self._inspection_lots),
            "avg_pass_rate": round(avg_pass, 2),
        }

    # ─── Step 5: Schedule Adherence ───────────────────────────────────────

    async def step_schedule_adherence(self) -> Dict[str, Any]:
        self._log("INFO", "Step 5: Schedule Adherence — planned vs actual dates...", "schedule_adherence")

        if not self._order_map:
            return {"status": "error", "message": "No production orders loaded — run step 1 first"}

        results = []
        for order_id, order in self._order_map.items():
            planned_start = order.get("Planned_Start", "")
            planned_end = order.get("Planned_End", "")
            actual_start = order.get("Actual_Start", "")
            actual_end = order.get("Actual_End", "")

            seed = self._deterministic_seed(order_id, "sched", 0)
            delay_days = round(seed * 5 - 1, 1)

            planned_duration = 5.0
            if planned_start and planned_end:
                try:
                    ps = datetime.fromisoformat(str(planned_start).replace("Z", "+00:00"))
                    pe = datetime.fromisoformat(str(planned_end).replace("Z", "+00:00"))
                    planned_duration = max((pe - ps).total_seconds() / 86400, 1.0)
                except (ValueError, TypeError):
                    pass

            actual_duration = planned_duration + delay_days
            if actual_duration < 1.0:
                actual_duration = 1.0

            adherence_pct = round(min(planned_duration / actual_duration, 1.0) * 100, 2)

            results.append({
                "order_id": order_id,
                "material": order.get("Material_ID", ""),
                "line_id": order.get("Line_ID", ""),
                "planned_duration_days": round(planned_duration, 1),
                "actual_duration_days": round(actual_duration, 1),
                "delay_days": round(delay_days, 1),
                "adherence_pct": adherence_pct,
                "on_time": delay_days <= 0,
            })

        self._schedule_data = results

        avg_adherence = sum(r["adherence_pct"] for r in results) / max(len(results), 1)
        on_time_count = sum(1 for r in results if r["on_time"])
        self._log("INFO", (
            f"Computed schedule adherence for {len(results)} orders, "
            f"avg adherence={avg_adherence:.1f}%, on-time={on_time_count}/{len(results)}"
        ), "schedule_adherence")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "schedule_adherence", "completed",
                               len(results), len(results))

        return {
            "status": "completed",
            "orders_analyzed": len(results),
            "avg_adherence_pct": round(avg_adherence, 2),
            "on_time_count": on_time_count,
            "late_count": len(results) - on_time_count,
        }

    # ─── Step 6: Publish Results ──────────────────────────────────────────

    async def step_publish_results(self) -> Dict[str, Any]:
        self._log("INFO", "Step 6: Publish Results — generating KPIs, alerts, and writing to S3...", "publish_results")

        if not self._yield_analysis:
            return {"status": "error", "message": "No yield analysis — run steps 1-5 first"}

        self._generate_alerts()
        self._compute_kpis()

        production_data = []
        for ya in self._yield_analysis:
            production_data.append({
                "order_id": ya["order_id"],
                "material": ya["material"],
                "line_id": ya["line_id"],
                "planned_qty": ya["planned_qty"],
                "actual_qty": ya["actual_qty"],
                "yield_pct": ya["yield_pct"],
                "oee": ya["oee"],
                "defect_count": ya["defect_count"],
                "status": ya["status"],
            })

        now = datetime.now(timezone.utc)

        results = {
            "production_data": production_data,
            "kpis": self._kpis,
            "alerts": self._alerts,
            "generated_at": now.isoformat(),
        }

        written = await self._write_to_s3(results)
        await self._push_to_simulator(production_data, now)

        self._log("INFO", (
            f"Published {len(production_data)} production results, {len(self._alerts)} alerts, "
            f"OEE={self._kpis.get('oee_pct', 'N/A')}%, Yield={self._kpis.get('yield_pct', 'N/A')}%"
        ), "publish_results")

        return {
            "status": "completed",
            "results_published": len(production_data),
            "alerts_generated": len(self._alerts),
            "kpis": self._kpis,
            "s3_written": written,
        }

    # ─── Simulator push ──────────────────────────────────────────────────

    async def _push_to_simulator(self, production_data: List[Dict], now: datetime):
        try:
            from src.apis.fdw_api import _simulators
            ext = _simulators.get("external")
            if not ext or not getattr(ext, "loaded", False):
                self._log("INFO", "External simulator not available — skipping simulator push", "publish_results")
                return

            await ext.write_table("external_sources", "PQ_Production_Result", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in production_data
            ])

            await ext.write_table("external_sources", "PQ_KPI_Snapshot", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                **self._kpis,
            }])

            await ext.write_table("external_sources", "PQ_Alert", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                "total_alerts": len(self._alerts),
                "alerts": json.dumps(self._alerts, default=str),
            }])

            line_summaries = self._build_line_summaries()
            await ext.write_table("external_sources", "PQ_Line_Summary", [
                {"job_id": self.job_id, "processed_at": now.isoformat(), **ls}
                for ls in line_summaries
            ])

            quality_summaries = self._build_quality_summaries()
            await ext.write_table("external_sources", "PQ_Quality_Summary", [
                {"job_id": self.job_id, "processed_at": now.isoformat(), **qs}
                for qs in quality_summaries
            ])

            self._log("INFO", (
                f"Pushed to simulator: {len(production_data)} production rows, "
                f"{len(line_summaries)} line summaries, {len(quality_summaries)} quality summaries, "
                f"KPIs + {len(self._alerts)} alerts"
            ), "publish_results")

            await self._ensure_pq_result_mapping_rules()

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

    # ─── Line summaries ───────────────────────────────────────────────────

    def _build_line_summaries(self) -> List[Dict]:
        by_line = defaultdict(lambda: {"orders": 0, "oee_sum": 0.0, "yield_sum": 0.0})
        for ya in self._yield_analysis:
            lid = ya["line_id"]
            entry = by_line[lid]
            entry["orders"] += 1
            entry["oee_sum"] += ya["oee"]
            entry["yield_sum"] += ya["yield_pct"]

        summaries = []
        for line_id, agg in by_line.items():
            line = self._line_map.get(line_id, {})
            n = max(agg["orders"], 1)
            util_seed = self._deterministic_seed(line_id, "util", 0)
            summaries.append({
                "line_id": line_id,
                "plant": line.get("Plant_ID", ""),
                "total_orders": agg["orders"],
                "avg_oee": round(agg["oee_sum"] / n, 4),
                "avg_yield": round(agg["yield_sum"] / n, 2),
                "utilization_pct": round((0.60 + util_seed * 0.35) * 100, 2),
            })
        return summaries

    # ─── Quality summaries ────────────────────────────────────────────────

    def _build_quality_summaries(self) -> List[Dict]:
        summaries = []
        for mat_id, qs in self._quality_scores.items():
            summaries.append({
                "material_id": qs["material_id"],
                "category": qs["category"],
                "inspections": qs["inspections"],
                "pass_rate": qs["pass_rate"],
                "defect_rate": qs["defect_rate"],
                "first_pass_pct": qs["first_pass_pct"],
            })
        return summaries

    # ─── Alert generation ─────────────────────────────────────────────────

    def _generate_alerts(self):
        alerts = []

        for line_id, oee_data in self._oee_by_line.items():
            if oee_data["oee"] < 0.65:
                alerts.append({
                    "type": "oee_breach",
                    "severity": "High",
                    "line_id": line_id,
                    "plant": oee_data.get("plant", ""),
                    "oee": round(oee_data["oee"] * 100, 2),
                    "message": f"OEE {oee_data['oee'] * 100:.1f}% is below 65% threshold on line {line_id}",
                    "action": "Investigate availability, performance, and quality losses; schedule maintenance review",
                })

        for ya in self._yield_analysis:
            if ya["yield_pct"] < 85:
                alerts.append({
                    "type": "yield_drop",
                    "severity": "High",
                    "order_id": ya["order_id"],
                    "material": ya["material"],
                    "line_id": ya["line_id"],
                    "yield_pct": ya["yield_pct"],
                    "message": f"Yield {ya['yield_pct']:.1f}% below 85% for order {ya['order_id']}",
                    "action": "Review production parameters; check raw material quality; inspect line calibration",
                })

        for mat_id, qs in self._quality_scores.items():
            if qs["pass_rate"] < 90:
                alerts.append({
                    "type": "quality_deviation",
                    "severity": "Medium",
                    "material_id": mat_id,
                    "category": qs["category"],
                    "pass_rate": qs["pass_rate"],
                    "message": f"Pass rate {qs['pass_rate']:.1f}% below 90% for material {mat_id}",
                    "action": "Trigger quality hold; escalate to QA team for root cause analysis",
                })

        self._alerts = alerts

    # ─── KPI computation ──────────────────────────────────────────────────

    def _compute_kpis(self):
        if not self._yield_analysis:
            self._kpis = {}
            return

        avg_oee = sum(v["oee"] for v in self._oee_by_line.values()) / max(len(self._oee_by_line), 1)
        avg_yield = sum(ya["yield_pct"] for ya in self._yield_analysis) / max(len(self._yield_analysis), 1)

        all_first_pass = [qs["first_pass_pct"] for qs in self._quality_scores.values()]
        avg_first_pass = sum(all_first_pass) / max(len(all_first_pass), 1) if all_first_pass else 0.0

        changeover_seed = self._deterministic_seed("global", "changeover", 0)
        changeover_avg = round(15 + changeover_seed * 30, 1)

        avg_adherence = 0.0
        if self._schedule_data:
            avg_adherence = sum(s["adherence_pct"] for s in self._schedule_data) / len(self._schedule_data)

        trace_seed = self._deterministic_seed("global", "trace", 0)
        batch_traceability_time = round(2 + trace_seed * 8, 1)

        self._kpis = {
            "oee_pct": round(avg_oee * 100, 2),
            "yield_pct": round(avg_yield, 2),
            "first_pass_rate_pct": round(avg_first_pass, 2),
            "changeover_time_avg": changeover_avg,
            "schedule_adherence_pct": round(avg_adherence, 2),
            "batch_traceability_time": batch_traceability_time,
            "total_orders": len(self._yield_analysis),
            "total_lines": len(self._oee_by_line),
            "total_materials_scored": len(self._quality_scores),
            "alerts_count": len(self._alerts),
            "alerts": list(self._alerts) if isinstance(self._alerts, list) else [],
        }

    # ─── S3 write ─────────────────────────────────────────────────────────

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
            prefix = f"production-quality/{self.journey_id}/{timestamp}"

            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/production-data.json",
                Body=json.dumps(results["production_data"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/production-kpis.json",
                Body=json.dumps(results["kpis"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/production-alerts.json",
                Body=json.dumps(results["alerts"], default=str),
                ContentType="application/json",
            )
            self._log("INFO", f"Written to s3://{bucket}/{prefix}/", "publish_results")
            return True
        except Exception as e:
            self._log("WARNING", f"S3 write failed: {e}", "publish_results")
            return False
