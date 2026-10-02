"""
Inventory Optimization Processor

Implements the 6-step inventory optimization pipeline. Each step queries the
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

io_logger = logger.bind(component="inventory-optimization-processor")

try:
    from ...utils.sse_manager import emit_task_progress, emit_log
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    def emit_task_progress(*a, **kw): pass
    def emit_log(*a, **kw): pass


class InventoryOptimizationProcessor:

    def __init__(self, log_callback: Optional[Callable] = None, job_id: str = "",
                 journey_id: str = "", s3_client=None, config=None):
        self._log_cb = log_callback
        self.job_id = job_id
        self.journey_id = journey_id
        self._s3 = s3_client
        self._config = config

        self._position_matrix: List[Dict] = []
        self._classified_positions: List[Dict] = []
        self._reorder_positions: List[Dict] = []
        self._expiry_analyzed: List[Dict] = []
        self._rebalance_suggestions: List[Dict] = []
        self._alerts: List[Dict] = []
        self._kpis: Dict[str, Any] = {}

    def _log(self, level: str, msg: str, step_id: str = None):
        if self._log_cb:
            self._log_cb(level, msg, step_id)
        else:
            io_logger.log(level.upper(), msg)
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
                "Inventory_Position": ("sap_s4hana", "sap"),
                "Batch_Master": ("sap_s4hana", "sap"),
                "Plant_Master": ("sap_s4hana", "sap"),
                "Storage_Location": ("sap_s4hana", "sap"),
                "Material_Master": ("sap_s4hana", "sap"),
                "Material_Plant": ("sap_s4hana", "sap"),
                "Warehouse_Transfer": ("sap_s4hana", "sap"),
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

    # ─── Mapping Rules ────────────────────────────────────────────────────

    async def _ensure_inventory_optimization_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_entities = {r.virtual_entity for r in existing}

            rules = [
                ("Inventory_Position", "sap_s4hana", "Inventory_Position", {
                    "Material_ID": "Material_ID", "Plant_ID": "Plant_ID",
                    "Unrestricted_Qty": "Quantity_On_Hand", "Reserved_Qty": "Quantity_Reserved",
                    "Valuation_Price": "Valuation_Price"}),
                ("Batch_Master", "sap_s4hana", "Batch_Master", {
                    "Batch_ID": "Batch_ID", "Material_ID": "Material_ID",
                    "Production_Date": "Production_Date", "Shelf_Life_Days": "Shelf_Life_Days",
                    "Batch_Status": "Batch_Status"}),
                ("Plant_Master", "sap_s4hana", "Plant_Master", {
                    "Plant_ID": "Plant_ID", "Plant_Name": "Plant_Name",
                    "Region": "Region", "Plant_Type": "Plant_Type"}),
                ("Storage_Location", "sap_s4hana", "Storage_Location", {
                    "Storage_Location_ID": "Storage_Location_ID", "Plant_ID": "Plant_ID",
                    "Description": "Description", "Capacity": "Capacity"}),
                ("Material_Master", "sap_s4hana", "Material_Master", {
                    "Material_ID": "Material_ID", "Category": "Category", "Pack_Size": "Pack_Size",
                    "Shelf_Life_Days": "Shelf_Life_Days", "Status": "Status"}),
                ("Material_Plant", "sap_s4hana", "Material_Plant", {
                    "Material_ID": "Material_ID", "Plant_ID": "Plant_ID", "MRP_Type": "MRP_Type",
                    "Safety_Stock": "Safety_Stock", "Lead_Time_Days": "Lead_Time_Days",
                    "ABC_Classification": "ABC_Classification"}),
                ("Warehouse_Transfer", "sap_s4hana", "Warehouse_Transfer", {
                    "Transfer_ID": "Transfer_ID", "Material_ID": "Material_ID",
                    "Source_Plant": "Source_Plant", "Dest_Plant": "Dest_Plant",
                    "Quantity": "Quantity", "Status": "Status"}),
            ]

            from src.models.mapping_rule_models import MappingRuleCreateRequest, MappingRuleUpdateRequest, MappingRuleSourceType, MappingRuleStatus, FieldMap
            created = 0
            for virtual_entity, schema, table, field_map in rules:
                if virtual_entity in existing_entities:
                    continue
                field_maps = [FieldMap(source_field=s, target_field=t) for s, t in field_map.items()]
                rule = MappingRuleCreateRequest(
                    name=f"IO: {virtual_entity}",
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
                self._log("INFO", f"Created {created} VDL mapping rules for inventory optimization")
        except Exception as e:
            self._log("WARNING", f"Could not ensure mapping rules: {e}")

    async def _ensure_io_result_mapping_rules(self):
        try:
            from src.services.mapping_rule_service import MappingRuleService

            service = MappingRuleService()
            await service.initialize()

            existing = await service.list_all()
            existing_by_entity = {r.virtual_entity: r for r in existing}

            result_entities = [
                "IO_KPI_Snapshot", "IO_Position_Result", "IO_Alert",
                "IO_Plant_Summary", "IO_Category_Summary",
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
                    name=f"IO Result: {entity}",
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
                self._log("INFO", f"Created {created}, activated {activated} VDL mapping rules for IO result entities", "publish_results")
        except Exception as e:
            self._log("WARNING", f"IO result mapping rules failed (non-fatal): {e}", "publish_results")

    # ─── Step 1: Load Positions ───────────────────────────────────────────

    async def step_load_positions(self) -> Dict[str, Any]:
        self._log("INFO", "Step 1: Load Positions — querying 7 source entities...", "load_positions")

        await self._ensure_inventory_optimization_mapping_rules()

        inventory = await self._query_entity("Inventory_Position")
        batches = await self._query_entity("Batch_Master")
        plants = await self._query_entity("Plant_Master")
        storage_locs = await self._query_entity("Storage_Location")
        materials = await self._query_entity("Material_Master")
        mat_plants = await self._query_entity("Material_Plant")
        transfers = await self._query_entity("Warehouse_Transfer")

        self._log("INFO", (
            f"Loaded entities — Inventory: {len(inventory)}, Batches: {len(batches)}, "
            f"Plants: {len(plants)}, StorageLocs: {len(storage_locs)}, Materials: {len(materials)}, "
            f"MatPlants: {len(mat_plants)}, Transfers: {len(transfers)}"
        ), "load_positions")

        mat_map = {}
        for m in materials:
            mid = m.get("Material_ID", "")
            if mid:
                mat_map[mid] = m

        plant_map = {}
        for p in plants:
            pid = p.get("Plant_ID", "")
            if pid:
                plant_map[pid] = p

        mat_plant_map = {}
        for mp in mat_plants:
            key = (mp.get("Material_ID", ""), mp.get("Plant_ID", ""))
            if key[0] and key[1]:
                mat_plant_map[key] = mp

        batch_map = defaultdict(list)
        for b in batches:
            mid = b.get("Material_ID", "")
            if mid:
                batch_map[mid].append(b)

        position_matrix = []
        for inv in inventory:
            mid = inv.get("Material_ID", "")
            pid = inv.get("Plant_ID", "")
            if not mid:
                continue

            mat = mat_map.get(mid, {})
            plant = plant_map.get(pid, {})
            mp = mat_plant_map.get((mid, pid), {})

            qty = self._safe_float(inv.get("Quantity_On_Hand", inv.get("Unrestricted_Qty", 0)))
            reserved = self._safe_float(inv.get("Quantity_Reserved", inv.get("Reserved_Qty", 0)))
            valuation = self._safe_float(inv.get("Valuation_Price", 0))

            position_matrix.append({
                "material_id": mid,
                "plant_id": pid,
                "category": mat.get("Category", "General"),
                "plant_name": plant.get("Plant_Name", pid),
                "region": plant.get("Region", "Central"),
                "current_qty": qty,
                "reserved_qty": reserved,
                "valuation_price": valuation,
                "lead_time_days": self._safe_float(mp.get("Lead_Time_Days", 14)),
                "safety_stock_config": self._safe_float(mp.get("Safety_Stock", 0)),
                "shelf_life_days": self._safe_float(mat.get("Shelf_Life_Days", 365)),
                "batches": batch_map.get(mid, []),
            })

        self._position_matrix = position_matrix
        self._log("INFO", f"Built position matrix: {len(position_matrix)} inventory positions", "load_positions")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "load_positions", "completed", len(position_matrix), len(position_matrix))

        return {
            "status": "completed",
            "positions_loaded": len(position_matrix),
            "entities_queried": 7,
            "unique_materials": len({p["material_id"] for p in position_matrix}),
            "unique_plants": len({p["plant_id"] for p in position_matrix}),
        }

    # ─── Step 2: ABC Classification ──────────────────────────────────────

    async def step_abc_classification(self) -> Dict[str, Any]:
        self._log("INFO", "Step 2: ABC Classification — classifying SKUs by volume and value...", "abc_classification")

        if not self._position_matrix:
            return {"status": "error", "message": "No position matrix — run step 1 first"}

        material_value = defaultdict(float)
        for pos in self._position_matrix:
            material_value[pos["material_id"]] += pos["current_qty"] * pos["valuation_price"]

        sorted_materials = sorted(material_value.items(), key=lambda x: x[1], reverse=True)
        total_materials = len(sorted_materials)

        a_cutoff = max(int(total_materials * 0.20), 1)
        b_cutoff = a_cutoff + max(int(total_materials * 0.30), 1)

        abc_map = {}
        for idx, (mid, _) in enumerate(sorted_materials):
            if idx < a_cutoff:
                abc_map[mid] = "A"
            elif idx < b_cutoff:
                abc_map[mid] = "B"
            else:
                abc_map[mid] = "C"

        classified = []
        for pos in self._position_matrix:
            row = dict(pos)
            row["abc_class"] = abc_map.get(pos["material_id"], "C")
            classified.append(row)

        self._classified_positions = classified

        counts = defaultdict(int)
        for pos in classified:
            counts[pos["abc_class"]] += 1

        self._log("INFO", f"ABC classification complete: A={counts['A']}, B={counts['B']}, C={counts['C']}", "abc_classification")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "abc_classification", "completed", len(classified), len(classified))

        return {
            "status": "completed",
            "positions_classified": len(classified),
            "class_a": counts["A"],
            "class_b": counts["B"],
            "class_c": counts["C"],
        }

    # ─── Step 3: Reorder Calculation ─────────────────────────────────────

    async def step_reorder_calculation(self) -> Dict[str, Any]:
        self._log("INFO", "Step 3: Reorder Calculation — computing safety stock and reorder points...", "reorder_calculation")

        if not self._classified_positions:
            return {"status": "error", "message": "No classified positions — run step 2 first"}

        reorder_positions = []
        for pos in self._classified_positions:
            seed = self._deterministic_seed(pos["material_id"], pos["plant_id"], 0)
            historical_qty = pos["current_qty"] * (8 + seed * 10)
            avg_daily_demand = historical_qty / 365
            lead_time_days = pos["lead_time_days"]

            safety_stock = avg_daily_demand * lead_time_days * 1.5
            reorder_point = safety_stock + (avg_daily_demand * lead_time_days)
            days_of_supply = pos["current_qty"] / max(avg_daily_demand, 0.1)

            row = dict(pos)
            row["avg_daily_demand"] = round(avg_daily_demand, 2)
            row["safety_stock"] = round(safety_stock, 2)
            row["reorder_point"] = round(reorder_point, 2)
            row["days_of_supply"] = round(days_of_supply, 1)
            reorder_positions.append(row)

        self._reorder_positions = reorder_positions

        below_reorder = sum(1 for p in reorder_positions if p["current_qty"] < p["reorder_point"])
        self._log("INFO", f"Reorder calculation complete: {below_reorder}/{len(reorder_positions)} positions below reorder point", "reorder_calculation")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "reorder_calculation", "completed", len(reorder_positions), len(reorder_positions))

        return {
            "status": "completed",
            "positions_calculated": len(reorder_positions),
            "below_reorder_point": below_reorder,
            "avg_days_of_supply": round(sum(p["days_of_supply"] for p in reorder_positions) / max(len(reorder_positions), 1), 1),
        }

    # ─── Step 4: Expiry Analysis ─────────────────────────────────────────

    async def step_expiry_analysis(self) -> Dict[str, Any]:
        self._log("INFO", "Step 4: Expiry Analysis — scoring batch-level shelf-life risk...", "expiry_analysis")

        if not self._reorder_positions:
            return {"status": "error", "message": "No reorder positions — run step 3 first"}

        expiry_analyzed = []
        critical_count = 0
        warning_count = 0

        for pos in self._reorder_positions:
            row = dict(pos)
            shelf_life_days = pos["shelf_life_days"]

            seed = self._deterministic_seed(pos["material_id"], pos["plant_id"], 1)
            days_since_production = seed * shelf_life_days * 0.95
            days_to_expiry = shelf_life_days - days_since_production

            if days_to_expiry < 30:
                expiry_risk = "critical"
                critical_count += 1
            elif days_to_expiry < 90:
                expiry_risk = "warning"
                warning_count += 1
            else:
                expiry_risk = "ok"

            row["days_to_expiry"] = round(days_to_expiry, 1)
            row["expiry_risk"] = expiry_risk
            expiry_analyzed.append(row)

        self._expiry_analyzed = expiry_analyzed
        self._log("INFO", f"Expiry analysis complete: {critical_count} critical, {warning_count} warning, {len(expiry_analyzed) - critical_count - warning_count} ok", "expiry_analysis")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "expiry_analysis", "completed", len(expiry_analyzed), len(expiry_analyzed))

        return {
            "status": "completed",
            "positions_analyzed": len(expiry_analyzed),
            "critical_expiry": critical_count,
            "warning_expiry": warning_count,
        }

    # ─── Step 5: Rebalance Recommendations ───────────────────────────────

    async def step_rebalance_recommendations(self) -> Dict[str, Any]:
        self._log("INFO", "Step 5: Rebalance Recommendations — analyzing cross-plant distribution...", "rebalance_recommendations")

        if not self._expiry_analyzed:
            return {"status": "error", "message": "No expiry-analyzed positions — run step 4 first"}

        by_material = defaultdict(list)
        for pos in self._expiry_analyzed:
            by_material[pos["material_id"]].append(pos)

        rebalance_suggestions = []
        for mid, positions in by_material.items():
            if len(positions) < 2:
                continue

            avg_qty = sum(p["current_qty"] for p in positions) / len(positions)
            if avg_qty <= 0:
                continue

            overstocked = [p for p in positions if p["current_qty"] > avg_qty * 1.5]
            understocked = [p for p in positions if p["current_qty"] < avg_qty * 0.5]

            if overstocked and understocked:
                for source in overstocked:
                    for dest in understocked:
                        transfer_qty = round(min(
                            source["current_qty"] - avg_qty,
                            avg_qty - dest["current_qty"],
                        ), 2)
                        if transfer_qty > 0:
                            rebalance_suggestions.append({
                                "material_id": mid,
                                "category": source["category"],
                                "source_plant": source["plant_id"],
                                "source_plant_name": source["plant_name"],
                                "dest_plant": dest["plant_id"],
                                "dest_plant_name": dest["plant_name"],
                                "transfer_qty": transfer_qty,
                                "source_qty": source["current_qty"],
                                "dest_qty": dest["current_qty"],
                                "avg_qty": round(avg_qty, 2),
                            })

        self._rebalance_suggestions = rebalance_suggestions
        self._log("INFO", f"Rebalance recommendations: {len(rebalance_suggestions)} transfer suggestions across {len(by_material)} materials", "rebalance_recommendations")

        if SSE_AVAILABLE and self.job_id:
            emit_task_progress(self.job_id, "rebalance_recommendations", "completed", len(rebalance_suggestions), len(rebalance_suggestions))

        return {
            "status": "completed",
            "rebalance_suggestions": len(rebalance_suggestions),
            "materials_analyzed": len(by_material),
            "materials_with_imbalance": len({s["material_id"] for s in rebalance_suggestions}),
        }

    # ─── Step 6: Publish Results ─────────────────────────────────────────

    async def step_publish_results(self) -> Dict[str, Any]:
        self._log("INFO", "Step 6: Publish Results — generating KPIs, alerts, and writing to S3...", "publish_results")

        if not self._expiry_analyzed:
            return {"status": "error", "message": "No analyzed positions — run steps 1-5 first"}

        self._generate_alerts()
        self._compute_kpis()

        position_data = []
        for pos in self._expiry_analyzed:
            position_data.append({
                "sku": pos["material_id"],
                "plant": pos["plant_id"],
                "category": pos["category"],
                "current_qty": pos["current_qty"],
                "safety_stock": pos["safety_stock"],
                "reorder_point": pos["reorder_point"],
                "days_of_supply": pos["days_of_supply"],
                "abc_class": pos["abc_class"],
                "expiry_risk": pos["expiry_risk"],
            })

        now = datetime.now(timezone.utc)

        results = {
            "position_data": position_data,
            "kpis": self._kpis,
            "alerts": self._alerts,
            "rebalance_suggestions": self._rebalance_suggestions,
            "generated_at": now.isoformat(),
        }

        written = await self._write_to_s3(results)
        await self._push_to_simulator(position_data, now)

        self._log("INFO", (
            f"Published {len(position_data)} positions, {len(self._alerts)} alerts, "
            f"turns={self._kpis.get('turns', 'N/A')}, fill_rate={self._kpis.get('fill_rate_pct', 'N/A')}%"
        ), "publish_results")

        return {
            "status": "completed",
            "positions_published": len(position_data),
            "alerts_generated": len(self._alerts),
            "kpis": self._kpis,
            "s3_written": written,
        }

    async def _push_to_simulator(self, position_data: List[Dict], now: datetime):
        try:
            from src.apis.fdw_api import _simulators
            ext = _simulators.get("external")
            if not ext or not getattr(ext, "loaded", False):
                self._log("INFO", "External simulator not available — skipping simulator push", "publish_results")
                return

            await ext.write_table("external_sources", "IO_KPI_Snapshot", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                **self._kpis,
            }])

            await ext.write_table("external_sources", "IO_Position_Result", [
                {**row, "job_id": self.job_id, "processed_at": now.isoformat()}
                for row in position_data
            ])

            await ext.write_table("external_sources", "IO_Alert", [{
                "job_id": self.job_id,
                "processed_at": now.isoformat(),
                "total_alerts": len(self._alerts),
                "alerts": json.dumps(self._alerts, default=str),
            }])

            by_plant = defaultdict(lambda: {"total_skus": 0, "total_days_supply": 0.0, "expiry_risk_count": 0, "total_qty": 0.0})
            for pos in self._expiry_analyzed:
                p = by_plant[pos["plant_id"]]
                p["total_skus"] += 1
                p["total_days_supply"] += pos["days_of_supply"]
                if pos["expiry_risk"] in ("critical", "warning"):
                    p["expiry_risk_count"] += 1
                p["total_qty"] += pos["current_qty"]

            await ext.write_table("external_sources", "IO_Plant_Summary", [
                {
                    "plant": plant,
                    "total_skus": vals["total_skus"],
                    "avg_days_supply": round(vals["total_days_supply"] / max(vals["total_skus"], 1), 1),
                    "expiry_risk_count": vals["expiry_risk_count"],
                    "total_qty": round(vals["total_qty"], 2),
                    "job_id": self.job_id,
                    "processed_at": now.isoformat(),
                }
                for plant, vals in by_plant.items()
            ])

            by_category = defaultdict(lambda: {"total_qty": 0.0, "total_demand": 0.0, "sku_count": 0})
            for pos in self._expiry_analyzed:
                c = by_category[pos["category"]]
                c["total_qty"] += pos["current_qty"]
                c["total_demand"] += pos["avg_daily_demand"] * 365
                c["sku_count"] += 1

            await ext.write_table("external_sources", "IO_Category_Summary", [
                {
                    "category": cat,
                    "total_qty": round(vals["total_qty"], 2),
                    "avg_turns": round(vals["total_demand"] / max(vals["total_qty"], 0.1), 1),
                    "sku_count": vals["sku_count"],
                    "job_id": self.job_id,
                    "processed_at": now.isoformat(),
                }
                for cat, vals in by_category.items()
            ])

            self._log("INFO", (
                f"Pushed to simulator: {len(position_data)} position rows, "
                f"{len(by_plant)} plant summaries, {len(by_category)} category summaries, "
                f"KPIs + {len(self._alerts)} alerts"
            ), "publish_results")

            await self._ensure_io_result_mapping_rules()

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

    def _generate_alerts(self):
        alerts = []

        stockout_risk = [p for p in self._expiry_analyzed if p["days_of_supply"] < 7]
        if stockout_risk:
            for pos in stockout_risk:
                alerts.append({
                    "type": "stockout_risk",
                    "severity": "High",
                    "sku": pos["material_id"],
                    "plant": pos["plant_id"],
                    "days_of_supply": pos["days_of_supply"],
                    "message": f"SKU {pos['material_id']} at {pos['plant_id']} has only {pos['days_of_supply']:.1f} days of supply",
                    "action": "Expedite replenishment; review safety stock levels",
                })

        expiry_warnings = [p for p in self._expiry_analyzed if p["expiry_risk"] in ("critical", "warning")]
        if expiry_warnings:
            for pos in expiry_warnings:
                alerts.append({
                    "type": "expiry_warning",
                    "severity": "High" if pos["expiry_risk"] == "critical" else "Medium",
                    "sku": pos["material_id"],
                    "plant": pos["plant_id"],
                    "days_to_expiry": pos["days_to_expiry"],
                    "expiry_risk": pos["expiry_risk"],
                    "message": f"SKU {pos['material_id']} at {pos['plant_id']} has {pos['days_to_expiry']:.0f} days to expiry ({pos['expiry_risk']})",
                    "action": "Prioritize FIFO dispatch; consider markdown or transfer",
                })

        if self._rebalance_suggestions:
            materials_needing_rebalance = {s["material_id"] for s in self._rebalance_suggestions}
            for mid in materials_needing_rebalance:
                suggestions = [s for s in self._rebalance_suggestions if s["material_id"] == mid]
                alerts.append({
                    "type": "rebalance_needed",
                    "severity": "Medium",
                    "material_id": mid,
                    "transfer_count": len(suggestions),
                    "message": f"Material {mid} has significant cross-plant imbalance ({len(suggestions)} transfer suggestions)",
                    "action": "Review and approve inter-plant transfers",
                })

        self._alerts = alerts

    def _compute_kpis(self):
        if not self._expiry_analyzed:
            self._kpis = {}
            return

        total_qty = sum(p["current_qty"] for p in self._expiry_analyzed)
        total_demand = sum(p["avg_daily_demand"] * 365 for p in self._expiry_analyzed)

        seed_turns = self._deterministic_seed("global", "turns", 0)
        turns = round(total_demand / max(total_qty, 0.1) if total_qty > 0 else 12 * (0.9 + seed_turns * 0.2), 1)

        above_reorder = sum(1 for p in self._expiry_analyzed if p["current_qty"] >= p["reorder_point"])
        fill_rate_pct = round(above_reorder / max(len(self._expiry_analyzed), 1) * 100, 1)

        avg_days_of_supply = round(
            sum(p["days_of_supply"] for p in self._expiry_analyzed) / max(len(self._expiry_analyzed), 1), 1
        )

        at_risk = sum(1 for p in self._expiry_analyzed if p["expiry_risk"] in ("critical", "warning"))
        expired_write_off_pct = round(at_risk / max(len(self._expiry_analyzed), 1) * 100, 1)

        seed_cost = self._deterministic_seed("global", "carrying_cost", 0)
        carrying_cost_pct = round(2.5 + (seed_cost - 0.5) * 1.0, 2)

        by_material = defaultdict(list)
        for pos in self._expiry_analyzed:
            by_material[pos["material_id"]].append(pos)

        balanced = 0
        total_multi = 0
        for mid, positions in by_material.items():
            if len(positions) < 2:
                continue
            total_multi += 1
            avg = sum(p["current_qty"] for p in positions) / len(positions)
            if avg <= 0:
                continue
            all_balanced = all(0.5 * avg <= p["current_qty"] <= 1.5 * avg for p in positions)
            if all_balanced:
                balanced += 1

        rebalance_efficiency = round(balanced / max(total_multi, 1) * 100, 1)

        self._kpis = {
            "turns": turns,
            "fill_rate_pct": fill_rate_pct,
            "days_of_supply": avg_days_of_supply,
            "expired_write_off_pct": expired_write_off_pct,
            "carrying_cost_pct": carrying_cost_pct,
            "rebalance_efficiency": rebalance_efficiency,
            "total_positions": len(self._expiry_analyzed),
            "total_alerts": len(self._alerts),
            "rebalance_suggestions": len(self._rebalance_suggestions),
            "alerts": list(self._alerts) if isinstance(self._alerts, list) else [],
        }

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
            prefix = f"inventory-optimization/{self.journey_id}/{timestamp}"

            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/position-data.json",
                Body=json.dumps(results["position_data"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/inventory-kpis.json",
                Body=json.dumps(results["kpis"], default=str),
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=bucket,
                Key=f"{prefix}/inventory-alerts.json",
                Body=json.dumps(results["alerts"], default=str),
                ContentType="application/json",
            )
            self._log("INFO", f"Written to s3://{bucket}/{prefix}/", "publish_results")
            return True
        except Exception as e:
            self._log("WARNING", f"S3 write failed: {e}", "publish_results")
            return False
