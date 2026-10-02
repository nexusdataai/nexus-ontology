"""
Diagnostics REST API

Provides per-solution diagnostic endpoints (O2C, Demand Forecasting,
Inventory, Procurement, Production Quality, Supply Chain Risk,
Customer 360, ESG) plus simulator health checks.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
from loguru import logger

# Create router with prefix
router = APIRouter()


# ==========================================
# O2C Solution Diagnostics
# ==========================================

O2C_SOURCE_ENTITIES = [
    {"name": "Opportunity", "system": "Salesforce", "critical_fields": ["Opportunity_ID", "Account_ID", "Stage", "Close_Date", "Total_Value"]},
    {"name": "Account", "system": "Salesforce", "critical_fields": ["Account_ID", "Name", "Tier", "Status"]},
    {"name": "Delivery_Document", "system": "SAP", "critical_fields": ["Delivery_ID", "Sales_Order_ID", "Ship_To_Account_ID", "Material_ID"]},
    {"name": "AR_Invoice", "system": "Oracle", "critical_fields": ["Invoice_ID", "Customer_ID", "Status", "Linked_Delivery_ID"]},
    {"name": "AR_Payment", "system": "Oracle", "critical_fields": ["Payment_ID", "Invoice_ID"]},
    {"name": "AR_Credit_Note", "system": "Oracle", "critical_fields": ["Credit_Note_ID", "Invoice_ID"]},
]

O2C_RESULT_ENTITIES = [
    {"name": "O2C_Order_Result", "critical_fields": ["opportunity_id", "match_status", "order_amount", "anomaly_score", "risk_rank"]},
    {"name": "O2C_KPI_Snapshot", "critical_fields": ["dso", "match_rate", "total_open_ar", "leakage_rate"]},
    {"name": "O2C_Alert", "critical_fields": ["total_alerts", "alerts"]},
]


_ENTITY_SIMULATOR_MAP = {
    "Account": ("sfdc_itxp2dev", "simulator", None),
    "Opportunity": ("sfdc_itxp2dev", "simulator", None),
    "Contact": ("sfdc_itxp2dev", "simulator", None),
    "Campaign": ("sfdc_itxp2dev", "simulator", None),
    "Opportunity_Line_Item": ("sfdc_itxp2dev", "simulator", None),
    "Lead": ("sfdc_itxp2dev", "simulator", None),
    "Delivery_Document": ("sap_s4hana", "sap", None),
    "Shipment": ("sap_s4hana", "sap", None),
    "AR_Invoice": ("oracle_erp", "oracle", "Oracle_AR_Invoice"),
    "AR_Payment": ("oracle_erp", "oracle", "Oracle_AR_Payment"),
    "AR_Customer": ("oracle_erp", "oracle", "Oracle_AR_Customer"),
    "AR_Credit_Note": ("oracle_erp", "oracle", "Oracle_AR_Credit_Note"),
}


async def _query_simulator_direct(entity: str, limit: int = 100):
    try:
        from src.apis.fdw_api import _simulators
        from src.models.fdw_models import QueryRequest
        entry = _ENTITY_SIMULATOR_MAP.get(entity)
        if not entry:
            return [], f"No simulator mapping for {entity}"
        schema, sim_key, physical_table = entry
        sim = _simulators.get(sim_key)
        if not sim:
            return [], f"Simulator '{sim_key}' not registered"
        req = QueryRequest(table=physical_table or entity, schema_name=schema, limit=limit)
        resp = await sim.execute_query(req)
        return resp.rows, None
    except Exception as e:
        return [], str(e)


async def _vdl_query(entity: str, limit: int = 100):
    try:
        from src.apis.control_plane_api import _virtual_query_service
        if not _virtual_query_service:
            return await _query_simulator_direct(entity, limit)
        from src.models.mapping_rule_models import VirtualQueryRequest
        req = VirtualQueryRequest(virtual_entity=entity, limit=limit)
        resp = await _virtual_query_service.query_virtual_entity(req)
        return resp.rows, None
    except Exception as e:
        rows, sim_err = await _query_simulator_direct(entity, limit)
        if rows:
            return rows, None
        return [], f"VDL: {e}; Simulator: {sim_err}"


async def _get_mapping_rules():
    try:
        from src.apis.mapping_rule_api import _service
        if not _service:
            return []
        return await _service.list_all()
    except Exception:
        return []


def _check_status(ok: bool, warn: bool = False) -> str:
    if ok and not warn:
        return "pass"
    return "warn" if warn else "fail"


@router.post("/o2c")
async def run_o2c_diagnostics() -> Dict[str, Any]:
    """Run comprehensive O2C solution diagnostics across data, mapping, quality, and results."""
    ts = datetime.utcnow().isoformat()
    sections = {}

    all_rules = await _get_mapping_rules()
    rule_map = {}
    for r in all_rules:
        ve = r.virtual_entity if hasattr(r, "virtual_entity") else getattr(r, "virtualEntity", "")
        rule_map[ve] = r

    # ── 1. Data Adequacy ────────────────────────────────────
    adequacy_entities = []
    for spec in O2C_SOURCE_ENTITIES:
        rows, err = await _vdl_query(spec["name"], limit=5)
        row_count = len(rows) if rows else 0
        if rows is None:
            row_count = -1
        field_count = len(rows[0].keys()) if rows else 0
        status = "ok" if row_count > 0 else ("error" if err else "no_data")
        adequacy_entities.append({
            "name": spec["name"], "system": spec["system"],
            "rows": row_count, "fields": field_count,
            "status": status, "error": err,
        })

    with_data = sum(1 for e in adequacy_entities if e["status"] == "ok")
    missing = sum(1 for e in adequacy_entities if e["status"] != "ok")
    sections["data_adequacy"] = {
        "status": _check_status(missing == 0, missing > 0 and with_data > 0),
        "entities": adequacy_entities,
        "summary": {"total_entities": len(adequacy_entities), "with_data": with_data, "missing": missing},
    }

    # ── 2. Mapping Correctness ──────────────────────────────
    mapping_rules = []
    for spec in O2C_SOURCE_ENTITIES + [{"name": e["name"]} for e in O2C_RESULT_ENTITIES]:
        ename = spec["name"]
        rule = rule_map.get(ename)
        if rule:
            src_table = getattr(rule, "source_table", "")
            src_schema = getattr(rule, "source_schema", "")
            src_type = getattr(rule, "source_type", "")
            field_maps = getattr(rule, "field_maps", [])
            mapped = sum(1 for fm in field_maps if getattr(fm, "source_field", ""))
            unmapped = len(field_maps) - mapped
            status_val = getattr(rule, "status", None)
            raw_status = status_val.value if hasattr(status_val, "value") else str(status_val)
            active = raw_status == "active"
            rule_name = getattr(rule, "name", "")
            issue = ""
            if raw_status == "draft":
                issue = "Rule is in draft status — activate it in Mapping Rules"
            elif raw_status == "inactive":
                issue = "Rule is inactive — set status to active"
            mapping_rules.append({
                "entity": ename, "source_table": src_table, "source_schema": src_schema,
                "source_type": str(getattr(src_type, "value", src_type)),
                "mapped_fields": mapped, "unmapped_fields": unmapped,
                "rule_name": rule_name, "rule_status": raw_status,
                "status": "ok" if active else "inactive",
                "issue": issue,
            })
        else:
            mapping_rules.append({
                "entity": ename, "source_table": "", "source_schema": "",
                "source_type": "", "mapped_fields": 0, "unmapped_fields": 0,
                "status": "missing",
            })

    active_count = sum(1 for r in mapping_rules if r["status"] == "ok")
    issues_count = sum(1 for r in mapping_rules if r["status"] != "ok")
    sections["mapping_correctness"] = {
        "status": _check_status(issues_count == 0, issues_count > 0 and active_count > 0),
        "rules": mapping_rules,
        "summary": {"total_rules": len(mapping_rules), "active": active_count, "issues": issues_count},
    }

    # ── 3. Data after Mapping ───────────────────────────────
    vdl_queries = []
    vdl_data_cache = {}
    for spec in O2C_SOURCE_ENTITIES:
        rows, err = await _vdl_query(spec["name"], limit=200)
        actual_rows = rows if rows else []
        vdl_data_cache[spec["name"]] = actual_rows
        sample_row = actual_rows[0] if actual_rows else {}
        vdl_queries.append({
            "entity": spec["name"], "rows_returned": len(actual_rows),
            "field_keys": sorted(sample_row.keys()) if sample_row else [],
            "sample_row": {k: repr(v)[:60] for k, v in list(sample_row.items())[:8]} if sample_row else {},
            "status": "ok" if actual_rows else "no_data",
            "error": err,
        })

    vdl_ok = sum(1 for q in vdl_queries if q["status"] == "ok")
    sections["data_after_mapping"] = {
        "status": _check_status(vdl_ok == len(vdl_queries), vdl_ok > 0 and vdl_ok < len(vdl_queries)),
        "queries": vdl_queries,
    }

    # ── 4. Data Quality ─────────────────────────────────────
    quality_checks = []
    for spec in O2C_SOURCE_ENTITIES:
        rows = vdl_data_cache.get(spec["name"], [])
        if not rows:
            continue
        total = len(rows)
        for field in spec["critical_fields"]:
            null_count = sum(1 for r in rows if r.get(field) is None)
            null_pct = round(null_count / total * 100, 1) if total else 0
            present_vals = [r.get(field) for r in rows if r.get(field) is not None]
            detected_type = "unknown"
            if present_vals:
                sample = present_vals[0]
                if isinstance(sample, (int, float)):
                    detected_type = "numeric"
                elif isinstance(sample, bool):
                    detected_type = "boolean"
                else:
                    detected_type = "text"

            field_present = any(field in r for r in rows)
            if not field_present:
                status = "fail"
            elif null_pct > 50:
                status = "fail"
            elif null_pct > 10:
                status = "warn"
            else:
                status = "ok"

            quality_checks.append({
                "entity": spec["name"], "field": field,
                "null_count": null_count, "null_pct": null_pct,
                "total_rows": total, "field_present": field_present,
                "type": detected_type, "status": status,
            })

    passed = sum(1 for c in quality_checks if c["status"] == "ok")
    warnings = sum(1 for c in quality_checks if c["status"] == "warn")
    failures = sum(1 for c in quality_checks if c["status"] == "fail")
    sections["data_quality"] = {
        "status": _check_status(failures == 0, warnings > 0),
        "checks": quality_checks,
        "summary": {"total_checks": len(quality_checks), "passed": passed, "warnings": warnings, "failures": failures},
    }

    # ── 5. Results Analysis ─────────────────────────────────
    result_entities = []
    for spec in O2C_RESULT_ENTITIES:
        rows, err = await _vdl_query(spec["name"], limit=500)
        actual_rows = rows if rows else []
        entry = {
            "name": spec["name"], "rows": len(actual_rows),
            "status": "ok" if actual_rows else "no_data",
            "sample_keys": sorted(actual_rows[0].keys()) if actual_rows else [],
            "error": err,
        }
        if spec["name"] == "O2C_KPI_Snapshot" and actual_rows:
            kpi = actual_rows[0]
            entry["kpis"] = {k: kpi.get(k) for k in spec["critical_fields"] if k in kpi}
        if spec["name"] == "O2C_Alert" and actual_rows:
            entry["alert_count"] = actual_rows[0].get("total_alerts", 0)
        if spec["name"] == "O2C_Order_Result" and actual_rows:
            matched = sum(1 for r in actual_rows if r.get("match_status") == "matched")
            total_val = sum(float(r.get("order_amount", 0) or 0) for r in actual_rows)
            high_risk = sum(1 for r in actual_rows if float(r.get("anomaly_score", 0) or 0) > 50)
            entry["summary"] = {
                "matched": matched, "mismatched": len(actual_rows) - matched,
                "match_rate_pct": round(matched / len(actual_rows) * 100, 1) if actual_rows else 0,
                "total_value": round(total_val, 2), "high_risk": high_risk,
            }
        result_entities.append(entry)

    results_ok = sum(1 for e in result_entities if e["status"] == "ok")
    sections["results_analysis"] = {
        "status": _check_status(results_ok == len(result_entities), results_ok > 0 and results_ok < len(result_entities)),
        "entities": result_entities,
    }

    statuses = [s["status"] for s in sections.values()]
    overall = "pass" if all(s == "pass" for s in statuses) else ("fail" if any(s == "fail" for s in statuses) else "warn")

    return {"timestamp": ts, "overall_status": overall, "sections": sections}


# ==========================================
# Demand Forecasting Diagnostics
# ==========================================

DF_SOURCE_ENTITIES = [
    {"name": "Opportunity", "system": "Salesforce", "critical_fields": ["Opportunity_ID", "Account_ID", "Stage", "Close_Date", "Region"]},
    {"name": "Opportunity_Line_Item", "system": "Salesforce", "critical_fields": ["Line_ID", "Opportunity_ID", "Product_ID", "Quantity", "Unit_Price"]},
    {"name": "Account", "system": "Salesforce", "critical_fields": ["Account_ID", "Channel_Type", "Region", "Tier"]},
    {"name": "Campaign", "system": "Salesforce", "critical_fields": ["Campaign_ID", "Type", "Start_Date", "End_Date", "Status"]},
    {"name": "Forecast_Override", "system": "Salesforce", "critical_fields": ["Override_ID", "Product_ID", "Region", "Period", "Override_Qty"]},
    {"name": "Material_Master", "system": "SAP", "critical_fields": ["Material_ID", "Category", "Pack_Size", "Shelf_Life_Days", "Status"]},
    {"name": "Material_Plant", "system": "SAP", "critical_fields": ["Material_ID", "Plant_ID", "MRP_Type", "Safety_Stock", "Lead_Time_Days"]},
    {"name": "Inventory_Position", "system": "SAP", "critical_fields": ["Material_ID", "Plant_ID", "Unrestricted_Qty", "Reserved_Qty"]},
    {"name": "Market_Signal", "system": "External", "critical_fields": ["Signal_ID", "Source", "Event_Type", "Severity", "Affected_Commodity"]},
]

DF_RESULT_ENTITIES = [
    {"name": "DF_Forecast_Result", "critical_fields": ["sku", "region", "category", "period", "forecast_qty", "base_forecast"]},
    {"name": "DF_KPI_Snapshot", "critical_fields": ["mape", "bias", "stockout_rate_pct", "total_forecast_qty", "sku_region_combos"]},
    {"name": "DF_Alert", "critical_fields": ["total_alerts", "alerts"]},
    {"name": "DF_Region_Summary", "critical_fields": ["region", "total_qty", "sku_count"]},
    {"name": "DF_Category_Summary", "critical_fields": ["category", "total_qty", "sku_count"]},
]

_DF_ENTITY_SIMULATOR_MAP = {
    **_ENTITY_SIMULATOR_MAP,
    "Forecast_Override": ("sfdc_itxp2dev", "simulator", None),
    "Material_Master": ("sap_s4hana", "sap", None),
    "Material_Plant": ("sap_s4hana", "sap", None),
    "Inventory_Position": ("sap_s4hana", "sap", None),
    "Market_Signal": ("external_sources", "external", None),
    "Goods_Receipt": ("sap_s4hana", "sap", None),
    "Vendor_Master": ("sap_s4hana", "sap", None),
    "Production_Order": ("sap_s4hana", "sap", None),
    "Production_Line": ("sap_s4hana", "sap", None),
    "Bill_of_Materials": ("sap_s4hana", "sap", None),
    "Quality_Inspection_Lot": ("sap_s4hana", "sap", None),
    "Quality_Test_Result": ("sap_s4hana", "sap", None),
    "Batch_Master": ("sap_s4hana", "sap", None),
    "Storage_Location": ("sap_s4hana", "sap", None),
    "Plant_Master": ("sap_s4hana", "sap", None),
    "Source_List": ("sap_s4hana", "sap", None),
    "Return_Order": ("sap_s4hana", "sap", None),
    "Warehouse_Transfer": ("sap_s4hana", "sap", None),
    "Purchase_Order": ("oracle_erp", "oracle", "Oracle_Purchase_Order"),
    "AP_Invoice": ("oracle_erp", "oracle", "Oracle_AP_Invoice"),
    "AP_Payment": ("oracle_erp", "oracle", "Oracle_AP_Payment"),
    "Cost_Accounting": ("oracle_erp", "oracle", "Oracle_Cost_Accounting"),
    "Fixed_Asset": ("oracle_erp", "oracle", "Oracle_Fixed_Asset"),
    "Brand_Sentiment": ("external_sources", "external", None),
    "Sustainability_Report": ("external_sources", "external", None),
    "Contract_Document": ("external_sources", "external", None),
    "Commodity_Price": ("external_sources", "external", None),
    "Invoice_Upload": ("external_sources", "external", None),
    "Lab_Report_Upload": ("external_sources", "external", None),
    "DF_Forecast_Result": ("external_sources", "external"),
    "DF_KPI_Snapshot": ("external_sources", "external"),
    "DF_Alert": ("external_sources", "external", None),
    "DF_Region_Summary": ("external_sources", "external", None),
    "DF_Category_Summary": ("external_sources", "external", None),
    "IO_KPI_Snapshot": ("external_sources", "external", None),
    "IO_Position_Result": ("external_sources", "external", None),
    "IO_Alert": ("external_sources", "external", None),
    "IO_Plant_Summary": ("external_sources", "external", None),
    "IO_Category_Summary": ("external_sources", "external", None),
    "PA_KPI_Snapshot": ("external_sources", "external", None),
    "PA_Spend_Result": ("external_sources", "external", None),
    "PA_Alert": ("external_sources", "external", None),
    "PA_Vendor_Summary": ("external_sources", "external", None),
    "PA_Category_Summary": ("external_sources", "external", None),
    "PQ_KPI_Snapshot": ("external_sources", "external", None),
    "PQ_Production_Result": ("external_sources", "external", None),
    "PQ_Alert": ("external_sources", "external", None),
    "PQ_Line_Summary": ("external_sources", "external", None),
    "PQ_Quality_Summary": ("external_sources", "external", None),
    "SCR_KPI_Snapshot": ("external_sources", "external", None),
    "SCR_Vendor_Result": ("external_sources", "external", None),
    "SCR_Alert": ("external_sources", "external", None),
    "SCR_Region_Summary": ("external_sources", "external", None),
    "SCR_Category_Summary": ("external_sources", "external", None),
    "C360_KPI_Snapshot": ("external_sources", "external", None),
    "C360_Customer_Result": ("external_sources", "external", None),
    "C360_Alert": ("external_sources", "external", None),
    "C360_Segment_Summary": ("external_sources", "external", None),
    "C360_Revenue_Summary": ("external_sources", "external", None),
    "ESG_KPI_Snapshot": ("external_sources", "external", None),
    "ESG_Plant_Result": ("external_sources", "external", None),
    "ESG_Alert": ("external_sources", "external", None),
    "ESG_Material_Summary": ("external_sources", "external", None),
    "ESG_Category_Summary": ("external_sources", "external", None),
}


async def _df_query(entity: str, limit: int = 100):
    try:
        from src.apis.fdw_api import _simulators
        from src.models.fdw_models import QueryRequest
        entry = _DF_ENTITY_SIMULATOR_MAP.get(entity) or _ENTITY_SIMULATOR_MAP.get(entity)
        if not entry:
            return await _vdl_query(entity, limit)
        schema, sim_key, physical_table = entry
        sim = _simulators.get(sim_key)
        if not sim:
            return await _vdl_query(entity, limit)
        req = QueryRequest(table=physical_table or entity, schema_name=schema, limit=limit)
        resp = await sim.execute_query(req)
        return resp.rows, None
    except Exception as e:
        return await _vdl_query(entity, limit)


@router.post("/df")
async def run_df_diagnostics() -> Dict[str, Any]:
    """Run comprehensive Demand Forecasting diagnostics across data, mapping, quality, and results."""
    ts = datetime.utcnow().isoformat()
    sections = {}

    all_rules = await _get_mapping_rules()
    rule_map = {}
    for r in all_rules:
        ve = r.virtual_entity if hasattr(r, "virtual_entity") else getattr(r, "virtualEntity", "")
        rule_map[ve] = r

    # ── 1. Data Adequacy ────────────────────────────────────
    adequacy_entities = []
    for spec in DF_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=5)
        row_count = len(rows) if rows else 0
        if rows is None:
            row_count = -1
        field_count = len(rows[0].keys()) if rows else 0
        status = "ok" if row_count > 0 else ("error" if err else "no_data")
        adequacy_entities.append({
            "name": spec["name"], "system": spec["system"],
            "rows": row_count, "fields": field_count,
            "status": status, "error": err,
        })

    with_data = sum(1 for e in adequacy_entities if e["status"] == "ok")
    missing = sum(1 for e in adequacy_entities if e["status"] != "ok")
    sections["data_adequacy"] = {
        "status": _check_status(missing == 0, missing > 0 and with_data > 0),
        "entities": adequacy_entities,
        "summary": {"total_entities": len(adequacy_entities), "with_data": with_data, "missing": missing},
    }

    # ── 2. Mapping Correctness ──────────────────────────────
    mapping_rules = []
    for spec in DF_SOURCE_ENTITIES + [{"name": e["name"]} for e in DF_RESULT_ENTITIES]:
        ename = spec["name"]
        rule = rule_map.get(ename)
        if rule:
            src_table = getattr(rule, "source_table", "")
            src_schema = getattr(rule, "source_schema", "")
            src_type = getattr(rule, "source_type", "")
            field_maps = getattr(rule, "field_maps", [])
            mapped = sum(1 for fm in field_maps if getattr(fm, "source_field", ""))
            unmapped = len(field_maps) - mapped
            status_val = getattr(rule, "status", None)
            raw_status = status_val.value if hasattr(status_val, "value") else str(status_val)
            active = raw_status == "active"
            rule_name = getattr(rule, "name", "")
            issue = ""
            if raw_status == "draft":
                issue = "Rule is in draft status — activate it in Mapping Rules"
            elif raw_status == "inactive":
                issue = "Rule is inactive — set status to active"
            mapping_rules.append({
                "entity": ename, "source_table": src_table, "source_schema": src_schema,
                "source_type": str(getattr(src_type, "value", src_type)),
                "mapped_fields": mapped, "unmapped_fields": unmapped,
                "rule_name": rule_name, "rule_status": raw_status,
                "status": "ok" if active else "inactive",
                "issue": issue,
            })
        else:
            mapping_rules.append({
                "entity": ename, "source_table": "", "source_schema": "",
                "source_type": "", "mapped_fields": 0, "unmapped_fields": 0,
                "status": "missing",
            })

    active_count = sum(1 for r in mapping_rules if r["status"] == "ok")
    issues_count = sum(1 for r in mapping_rules if r["status"] != "ok")
    sections["mapping_correctness"] = {
        "status": _check_status(issues_count == 0, issues_count > 0 and active_count > 0),
        "rules": mapping_rules,
        "summary": {"total_rules": len(mapping_rules), "active": active_count, "issues": issues_count},
    }

    # ── 3. Data after Mapping ───────────────────────────────
    vdl_queries = []
    vdl_data_cache = {}
    for spec in DF_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=200)
        actual_rows = rows if rows else []
        vdl_data_cache[spec["name"]] = actual_rows
        sample_row = actual_rows[0] if actual_rows else {}
        vdl_queries.append({
            "entity": spec["name"], "rows_returned": len(actual_rows),
            "field_keys": sorted(sample_row.keys()) if sample_row else [],
            "sample_row": {k: repr(v)[:60] for k, v in list(sample_row.items())[:8]} if sample_row else {},
            "status": "ok" if actual_rows else "no_data",
            "error": err,
        })

    vdl_ok = sum(1 for q in vdl_queries if q["status"] == "ok")
    sections["data_after_mapping"] = {
        "status": _check_status(vdl_ok == len(vdl_queries), vdl_ok > 0 and vdl_ok < len(vdl_queries)),
        "queries": vdl_queries,
    }

    # ── 4. Data Quality ─────────────────────────────────────
    quality_checks = []
    for spec in DF_SOURCE_ENTITIES:
        rows = vdl_data_cache.get(spec["name"], [])
        if not rows:
            continue
        total = len(rows)
        for field in spec["critical_fields"]:
            null_count = sum(1 for r in rows if r.get(field) is None)
            null_pct = round(null_count / total * 100, 1) if total else 0
            present_vals = [r.get(field) for r in rows if r.get(field) is not None]
            detected_type = "unknown"
            if present_vals:
                sample = present_vals[0]
                if isinstance(sample, (int, float)):
                    detected_type = "numeric"
                elif isinstance(sample, bool):
                    detected_type = "boolean"
                else:
                    detected_type = "text"

            field_present = any(field in r for r in rows)
            if not field_present:
                status = "fail"
            elif null_pct > 50:
                status = "fail"
            elif null_pct > 10:
                status = "warn"
            else:
                status = "ok"

            quality_checks.append({
                "entity": spec["name"], "field": field,
                "null_count": null_count, "null_pct": null_pct,
                "total_rows": total, "field_present": field_present,
                "type": detected_type, "status": status,
            })

    passed = sum(1 for c in quality_checks if c["status"] == "ok")
    warnings = sum(1 for c in quality_checks if c["status"] == "warn")
    failures = sum(1 for c in quality_checks if c["status"] == "fail")
    sections["data_quality"] = {
        "status": _check_status(failures == 0, warnings > 0),
        "checks": quality_checks,
        "summary": {"total_checks": len(quality_checks), "passed": passed, "warnings": warnings, "failures": failures},
    }

    # ── 5. Results Analysis ─────────────────────────────────
    result_entities = []
    for spec in DF_RESULT_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=500)
        actual_rows = rows if rows else []
        entry = {
            "name": spec["name"], "rows": len(actual_rows),
            "status": "ok" if actual_rows else "no_data",
            "sample_keys": sorted(actual_rows[0].keys()) if actual_rows else [],
            "error": err,
        }
        if spec["name"] == "DF_KPI_Snapshot" and actual_rows:
            kpi = actual_rows[0]
            entry["kpis"] = {k: kpi.get(k) for k in spec["critical_fields"] if k in kpi}
        if spec["name"] == "DF_Alert" and actual_rows:
            entry["alert_count"] = actual_rows[0].get("total_alerts", 0)
        if spec["name"] == "DF_Forecast_Result" and actual_rows:
            categories = {}
            regions = {}
            for r in actual_rows:
                cat = r.get("category", "Unknown")
                categories[cat] = categories.get(cat, 0) + float(r.get("forecast_qty", 0) or 0)
                reg = r.get("region", "Unknown")
                regions[reg] = regions.get(reg, 0) + float(r.get("forecast_qty", 0) or 0)
            entry["summary"] = {
                "total_rows": len(actual_rows),
                "categories": len(categories),
                "regions": len(regions),
                "total_forecast_qty": round(sum(categories.values())),
                "top_category": max(categories, key=categories.get) if categories else "—",
            }
        if spec["name"] == "DF_Region_Summary" and actual_rows:
            entry["breakdown"] = [{"region": r.get("region"), "total_qty": r.get("total_qty"), "sku_count": r.get("sku_count")} for r in actual_rows]
        if spec["name"] == "DF_Category_Summary" and actual_rows:
            entry["breakdown"] = [{"category": r.get("category"), "total_qty": r.get("total_qty"), "sku_count": r.get("sku_count")} for r in actual_rows]
        result_entities.append(entry)

    results_ok = sum(1 for e in result_entities if e["status"] == "ok")
    sections["results_analysis"] = {
        "status": _check_status(results_ok == len(result_entities), results_ok > 0 and results_ok < len(result_entities)),
        "entities": result_entities,
    }

    statuses = [s["status"] for s in sections.values()]
    overall = "pass" if all(s == "pass" for s in statuses) else ("fail" if any(s == "fail" for s in statuses) else "warn")

    return {"timestamp": ts, "overall_status": overall, "sections": sections}


# ==========================================
# Inventory Optimization Diagnostics
# ==========================================

IO_SOURCE_ENTITIES = [
    {"name": "Inventory_Position", "system": "SAP", "critical_fields": ["Material_ID", "Plant_ID", "Unrestricted_Qty", "Reserved_Qty"]},
    {"name": "Batch_Master", "system": "SAP", "critical_fields": ["Batch_ID", "Material_ID", "Production_Date", "Shelf_Life_Remaining_Days"]},
    {"name": "Plant_Master", "system": "SAP", "critical_fields": ["Plant_ID", "Name", "Type"]},
    {"name": "Storage_Location", "system": "SAP", "critical_fields": ["Storage_Location_ID", "Plant_ID", "Type"]},
    {"name": "Material_Master", "system": "SAP", "critical_fields": ["Material_ID", "Category", "Status"]},
    {"name": "Material_Plant", "system": "SAP", "critical_fields": ["Material_ID", "Plant_ID", "Safety_Stock", "Lead_Time_Days"]},
]

IO_RESULT_ENTITIES = [
    {"name": "IO_KPI_Snapshot", "critical_fields": ["turns", "fill_rate_pct", "days_of_supply", "expired_write_off_pct"]},
    {"name": "IO_Position_Result", "critical_fields": ["sku", "plant", "current_qty", "abc_class", "expiry_risk"]},
    {"name": "IO_Alert", "critical_fields": ["total_alerts", "alerts"]},
    {"name": "IO_Plant_Summary", "critical_fields": ["plant", "total_qty", "avg_days_supply"]},
    {"name": "IO_Category_Summary", "critical_fields": ["category", "total_qty", "avg_turns"]},
]


@router.post("/io")
async def run_io_diagnostics() -> Dict[str, Any]:
    """Run comprehensive Inventory Optimization diagnostics across data, mapping, quality, and results."""
    ts = datetime.utcnow().isoformat()
    sections = {}

    all_rules = await _get_mapping_rules()
    rule_map = {}
    for r in all_rules:
        ve = r.virtual_entity if hasattr(r, "virtual_entity") else getattr(r, "virtualEntity", "")
        rule_map[ve] = r

    # ── 1. Data Adequacy ────────────────────────────────────
    adequacy_entities = []
    for spec in IO_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=5)
        row_count = len(rows) if rows else 0
        if rows is None:
            row_count = -1
        field_count = len(rows[0].keys()) if rows else 0
        status = "ok" if row_count > 0 else ("error" if err else "no_data")
        adequacy_entities.append({
            "name": spec["name"], "system": spec["system"],
            "rows": row_count, "fields": field_count,
            "status": status, "error": err,
        })

    with_data = sum(1 for e in adequacy_entities if e["status"] == "ok")
    missing = sum(1 for e in adequacy_entities if e["status"] != "ok")
    sections["data_adequacy"] = {
        "status": _check_status(missing == 0, missing > 0 and with_data > 0),
        "entities": adequacy_entities,
        "summary": {"total_entities": len(adequacy_entities), "with_data": with_data, "missing": missing},
    }

    # ── 2. Mapping Correctness ──────────────────────────────
    mapping_rules = []
    for spec in IO_SOURCE_ENTITIES + [{"name": e["name"]} for e in IO_RESULT_ENTITIES]:
        ename = spec["name"]
        rule = rule_map.get(ename)
        if rule:
            src_table = getattr(rule, "source_table", "")
            src_schema = getattr(rule, "source_schema", "")
            src_type = getattr(rule, "source_type", "")
            field_maps = getattr(rule, "field_maps", [])
            mapped = sum(1 for fm in field_maps if getattr(fm, "source_field", ""))
            unmapped = len(field_maps) - mapped
            status_val = getattr(rule, "status", None)
            raw_status = status_val.value if hasattr(status_val, "value") else str(status_val)
            active = raw_status == "active"
            rule_name = getattr(rule, "name", "")
            issue = ""
            if raw_status == "draft":
                issue = "Rule is in draft status — activate it in Mapping Rules"
            elif raw_status == "inactive":
                issue = "Rule is inactive — set status to active"
            mapping_rules.append({
                "entity": ename, "source_table": src_table, "source_schema": src_schema,
                "source_type": str(getattr(src_type, "value", src_type)),
                "mapped_fields": mapped, "unmapped_fields": unmapped,
                "rule_name": rule_name, "rule_status": raw_status,
                "status": "ok" if active else "inactive",
                "issue": issue,
            })
        else:
            mapping_rules.append({
                "entity": ename, "source_table": "", "source_schema": "",
                "source_type": "", "mapped_fields": 0, "unmapped_fields": 0,
                "status": "missing",
            })

    active_count = sum(1 for r in mapping_rules if r["status"] == "ok")
    issues_count = sum(1 for r in mapping_rules if r["status"] != "ok")
    sections["mapping_correctness"] = {
        "status": _check_status(issues_count == 0, issues_count > 0 and active_count > 0),
        "rules": mapping_rules,
        "summary": {"total_rules": len(mapping_rules), "active": active_count, "issues": issues_count},
    }

    # ── 3. Data after Mapping ───────────────────────────────
    vdl_queries = []
    vdl_data_cache = {}
    for spec in IO_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=200)
        actual_rows = rows if rows else []
        vdl_data_cache[spec["name"]] = actual_rows
        sample_row = actual_rows[0] if actual_rows else {}
        vdl_queries.append({
            "entity": spec["name"], "rows_returned": len(actual_rows),
            "field_keys": sorted(sample_row.keys()) if sample_row else [],
            "sample_row": {k: repr(v)[:60] for k, v in list(sample_row.items())[:8]} if sample_row else {},
            "status": "ok" if actual_rows else "no_data",
            "error": err,
        })

    vdl_ok = sum(1 for q in vdl_queries if q["status"] == "ok")
    sections["data_after_mapping"] = {
        "status": _check_status(vdl_ok == len(vdl_queries), vdl_ok > 0 and vdl_ok < len(vdl_queries)),
        "queries": vdl_queries,
    }

    # ── 4. Data Quality ─────────────────────────────────────
    quality_checks = []
    for spec in IO_SOURCE_ENTITIES:
        rows = vdl_data_cache.get(spec["name"], [])
        if not rows:
            continue
        total = len(rows)
        for field in spec["critical_fields"]:
            null_count = sum(1 for r in rows if r.get(field) is None)
            null_pct = round(null_count / total * 100, 1) if total else 0
            present_vals = [r.get(field) for r in rows if r.get(field) is not None]
            detected_type = "unknown"
            if present_vals:
                sample = present_vals[0]
                if isinstance(sample, (int, float)):
                    detected_type = "numeric"
                elif isinstance(sample, bool):
                    detected_type = "boolean"
                else:
                    detected_type = "text"

            field_present = any(field in r for r in rows)
            if not field_present:
                status = "fail"
            elif null_pct > 50:
                status = "fail"
            elif null_pct > 10:
                status = "warn"
            else:
                status = "ok"

            quality_checks.append({
                "entity": spec["name"], "field": field,
                "null_count": null_count, "null_pct": null_pct,
                "total_rows": total, "field_present": field_present,
                "type": detected_type, "status": status,
            })

    passed = sum(1 for c in quality_checks if c["status"] == "ok")
    warnings = sum(1 for c in quality_checks if c["status"] == "warn")
    failures = sum(1 for c in quality_checks if c["status"] == "fail")
    sections["data_quality"] = {
        "status": _check_status(failures == 0, warnings > 0),
        "checks": quality_checks,
        "summary": {"total_checks": len(quality_checks), "passed": passed, "warnings": warnings, "failures": failures},
    }

    # ── 5. Results Analysis ─────────────────────────────────
    result_entities = []
    for spec in IO_RESULT_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=500)
        actual_rows = rows if rows else []
        entry = {
            "name": spec["name"], "rows": len(actual_rows),
            "status": "ok" if actual_rows else "no_data",
            "sample_keys": sorted(actual_rows[0].keys()) if actual_rows else [],
            "error": err,
        }
        if spec["name"] == "IO_KPI_Snapshot" and actual_rows:
            kpi = actual_rows[0]
            entry["kpis"] = {k: kpi.get(k) for k in spec["critical_fields"] if k in kpi}
        if spec["name"] == "IO_Alert" and actual_rows:
            entry["alert_count"] = actual_rows[0].get("total_alerts", 0)
        if spec["name"] == "IO_Position_Result" and actual_rows:
            plants = set()
            total_qty = 0
            expiry_risk_count = 0
            for r in actual_rows:
                plants.add(r.get("plant", "Unknown"))
                total_qty += float(r.get("current_qty", 0) or 0)
                if r.get("expiry_risk") in ("high", True):
                    expiry_risk_count += 1
            entry["summary"] = {
                "total_rows": len(actual_rows),
                "plants": len(plants),
                "total_qty": round(total_qty),
                "expiry_risk_count": expiry_risk_count,
            }
        if spec["name"] == "IO_Plant_Summary" and actual_rows:
            entry["breakdown"] = [{"plant": r.get("plant"), "total_qty": r.get("total_qty"), "avg_days_supply": r.get("avg_days_supply")} for r in actual_rows]
        if spec["name"] == "IO_Category_Summary" and actual_rows:
            entry["breakdown"] = [{"category": r.get("category"), "total_qty": r.get("total_qty"), "avg_turns": r.get("avg_turns")} for r in actual_rows]
        result_entities.append(entry)

    results_ok = sum(1 for e in result_entities if e["status"] == "ok")
    sections["results_analysis"] = {
        "status": _check_status(results_ok == len(result_entities), results_ok > 0 and results_ok < len(result_entities)),
        "entities": result_entities,
    }

    statuses = [s["status"] for s in sections.values()]
    overall = "pass" if all(s == "pass" for s in statuses) else ("fail" if any(s == "fail" for s in statuses) else "warn")

    return {"timestamp": ts, "overall_status": overall, "sections": sections}


# ==========================================
# Procurement Analytics Diagnostics
# ==========================================

PA_SOURCE_ENTITIES = [
    {"name": "Purchase_Order", "system": "Oracle", "critical_fields": ["PO_ID", "Vendor_ID", "Total_Amount", "Status"]},
    {"name": "Goods_Receipt", "system": "SAP", "critical_fields": ["GRN_ID", "PO_ID", "Material_ID"]},
    {"name": "AP_Invoice", "system": "Oracle", "critical_fields": ["Invoice_ID", "Vendor_ID", "Total_Amount"]},
    {"name": "AP_Payment", "system": "Oracle", "critical_fields": ["Payment_ID", "Invoice_ID"]},
    {"name": "Vendor_Master", "system": "SAP", "critical_fields": ["Vendor_ID", "Name", "Country"]},
    {"name": "Contract_Document", "system": "External", "critical_fields": ["Contract_ID", "Vendor_ID"]},
    {"name": "Commodity_Price", "system": "External", "critical_fields": ["Commodity", "Price_Per_Unit"]},
]

PA_RESULT_ENTITIES = [
    {"name": "PA_KPI_Snapshot", "critical_fields": ["total_spend", "maverick_spend_pct", "stp_rate_pct"]},
    {"name": "PA_Spend_Result", "critical_fields": ["po_id", "vendor", "amount", "maverick_flag"]},
    {"name": "PA_Alert", "critical_fields": ["total_alerts", "alerts"]},
    {"name": "PA_Vendor_Summary", "critical_fields": ["vendor_name", "total_spend", "po_count"]},
    {"name": "PA_Category_Summary", "critical_fields": ["category", "total_spend", "vendor_count"]},
]


@router.post("/pa")
async def run_pa_diagnostics() -> Dict[str, Any]:
    """Run comprehensive Procurement Analytics diagnostics across data, mapping, quality, and results."""
    ts = datetime.utcnow().isoformat()
    sections = {}

    all_rules = await _get_mapping_rules()
    rule_map = {}
    for r in all_rules:
        ve = r.virtual_entity if hasattr(r, "virtual_entity") else getattr(r, "virtualEntity", "")
        rule_map[ve] = r

    # ── 1. Data Adequacy ────────────────────────────────────
    adequacy_entities = []
    for spec in PA_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=5)
        row_count = len(rows) if rows else 0
        if rows is None:
            row_count = -1
        field_count = len(rows[0].keys()) if rows else 0
        status = "ok" if row_count > 0 else ("error" if err else "no_data")
        adequacy_entities.append({
            "name": spec["name"], "system": spec["system"],
            "rows": row_count, "fields": field_count,
            "status": status, "error": err,
        })

    with_data = sum(1 for e in adequacy_entities if e["status"] == "ok")
    missing = sum(1 for e in adequacy_entities if e["status"] != "ok")
    sections["data_adequacy"] = {
        "status": _check_status(missing == 0, missing > 0 and with_data > 0),
        "entities": adequacy_entities,
        "summary": {"total_entities": len(adequacy_entities), "with_data": with_data, "missing": missing},
    }

    # ── 2. Mapping Correctness ──────────────────────────────
    mapping_rules = []
    for spec in PA_SOURCE_ENTITIES + [{"name": e["name"]} for e in PA_RESULT_ENTITIES]:
        ename = spec["name"]
        rule = rule_map.get(ename)
        if rule:
            src_table = getattr(rule, "source_table", "")
            src_schema = getattr(rule, "source_schema", "")
            src_type = getattr(rule, "source_type", "")
            field_maps = getattr(rule, "field_maps", [])
            mapped = sum(1 for fm in field_maps if getattr(fm, "source_field", ""))
            unmapped = len(field_maps) - mapped
            status_val = getattr(rule, "status", None)
            raw_status = status_val.value if hasattr(status_val, "value") else str(status_val)
            active = raw_status == "active"
            rule_name = getattr(rule, "name", "")
            issue = ""
            if raw_status == "draft":
                issue = "Rule is in draft status — activate it in Mapping Rules"
            elif raw_status == "inactive":
                issue = "Rule is inactive — set status to active"
            mapping_rules.append({
                "entity": ename, "source_table": src_table, "source_schema": src_schema,
                "source_type": str(getattr(src_type, "value", src_type)),
                "mapped_fields": mapped, "unmapped_fields": unmapped,
                "rule_name": rule_name, "rule_status": raw_status,
                "status": "ok" if active else "inactive",
                "issue": issue,
            })
        else:
            mapping_rules.append({
                "entity": ename, "source_table": "", "source_schema": "",
                "source_type": "", "mapped_fields": 0, "unmapped_fields": 0,
                "status": "missing",
            })

    active_count = sum(1 for r in mapping_rules if r["status"] == "ok")
    issues_count = sum(1 for r in mapping_rules if r["status"] != "ok")
    sections["mapping_correctness"] = {
        "status": _check_status(issues_count == 0, issues_count > 0 and active_count > 0),
        "rules": mapping_rules,
        "summary": {"total_rules": len(mapping_rules), "active": active_count, "issues": issues_count},
    }

    # ── 3. Data after Mapping ───────────────────────────────
    vdl_queries = []
    vdl_data_cache = {}
    for spec in PA_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=200)
        actual_rows = rows if rows else []
        vdl_data_cache[spec["name"]] = actual_rows
        sample_row = actual_rows[0] if actual_rows else {}
        vdl_queries.append({
            "entity": spec["name"], "rows_returned": len(actual_rows),
            "field_keys": sorted(sample_row.keys()) if sample_row else [],
            "sample_row": {k: repr(v)[:60] for k, v in list(sample_row.items())[:8]} if sample_row else {},
            "status": "ok" if actual_rows else "no_data",
            "error": err,
        })

    vdl_ok = sum(1 for q in vdl_queries if q["status"] == "ok")
    sections["data_after_mapping"] = {
        "status": _check_status(vdl_ok == len(vdl_queries), vdl_ok > 0 and vdl_ok < len(vdl_queries)),
        "queries": vdl_queries,
    }

    # ── 4. Data Quality ─────────────────────────────────────
    quality_checks = []
    for spec in PA_SOURCE_ENTITIES:
        rows = vdl_data_cache.get(spec["name"], [])
        if not rows:
            continue
        total = len(rows)
        for field in spec["critical_fields"]:
            null_count = sum(1 for r in rows if r.get(field) is None)
            null_pct = round(null_count / total * 100, 1) if total else 0
            present_vals = [r.get(field) for r in rows if r.get(field) is not None]
            detected_type = "unknown"
            if present_vals:
                sample = present_vals[0]
                if isinstance(sample, (int, float)):
                    detected_type = "numeric"
                elif isinstance(sample, bool):
                    detected_type = "boolean"
                else:
                    detected_type = "text"

            field_present = any(field in r for r in rows)
            if not field_present:
                status = "fail"
            elif null_pct > 50:
                status = "fail"
            elif null_pct > 10:
                status = "warn"
            else:
                status = "ok"

            quality_checks.append({
                "entity": spec["name"], "field": field,
                "null_count": null_count, "null_pct": null_pct,
                "total_rows": total, "field_present": field_present,
                "type": detected_type, "status": status,
            })

    passed = sum(1 for c in quality_checks if c["status"] == "ok")
    warnings = sum(1 for c in quality_checks if c["status"] == "warn")
    failures = sum(1 for c in quality_checks if c["status"] == "fail")
    sections["data_quality"] = {
        "status": _check_status(failures == 0, warnings > 0),
        "checks": quality_checks,
        "summary": {"total_checks": len(quality_checks), "passed": passed, "warnings": warnings, "failures": failures},
    }

    # ── 5. Results Analysis ─────────────────────────────────
    result_entities = []
    for spec in PA_RESULT_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=500)
        actual_rows = rows if rows else []
        entry = {
            "name": spec["name"], "rows": len(actual_rows),
            "status": "ok" if actual_rows else "no_data",
            "sample_keys": sorted(actual_rows[0].keys()) if actual_rows else [],
            "error": err,
        }
        if spec["name"] == "PA_KPI_Snapshot" and actual_rows:
            kpi = actual_rows[0]
            entry["kpis"] = {k: kpi.get(k) for k in spec["critical_fields"] if k in kpi}
        if spec["name"] == "PA_Alert" and actual_rows:
            entry["alert_count"] = actual_rows[0].get("total_alerts", 0)
        if spec["name"] == "PA_Spend_Result" and actual_rows:
            vendors = set()
            total_spend = 0
            maverick_count = 0
            for r in actual_rows:
                vendors.add(r.get("vendor", "Unknown"))
                total_spend += float(r.get("amount", 0) or 0)
                if r.get("maverick_flag") in ("Y", True, 1):
                    maverick_count += 1
            entry["summary"] = {
                "total_rows": len(actual_rows),
                "vendors": len(vendors),
                "total_spend": round(total_spend, 2),
                "maverick_count": maverick_count,
            }
        if spec["name"] == "PA_Vendor_Summary" and actual_rows:
            entry["breakdown"] = [{"vendor_name": r.get("vendor_name"), "total_spend": r.get("total_spend"), "po_count": r.get("po_count")} for r in actual_rows]
        if spec["name"] == "PA_Category_Summary" and actual_rows:
            entry["breakdown"] = [{"category": r.get("category"), "total_spend": r.get("total_spend"), "vendor_count": r.get("vendor_count")} for r in actual_rows]
        result_entities.append(entry)

    results_ok = sum(1 for e in result_entities if e["status"] == "ok")
    sections["results_analysis"] = {
        "status": _check_status(results_ok == len(result_entities), results_ok > 0 and results_ok < len(result_entities)),
        "entities": result_entities,
    }

    statuses = [s["status"] for s in sections.values()]
    overall = "pass" if all(s == "pass" for s in statuses) else ("fail" if any(s == "fail" for s in statuses) else "warn")

    return {"timestamp": ts, "overall_status": overall, "sections": sections}


# ==========================================
# Production & Quality Diagnostics
# ==========================================

PQ_SOURCE_ENTITIES = [
    {"name": "Production_Order", "system": "SAP", "critical_fields": ["Order_ID", "Material_ID", "Qty_Planned", "Status"]},
    {"name": "Production_Line", "system": "SAP", "critical_fields": ["Line_ID", "Plant_ID"]},
    {"name": "Bill_of_Materials", "system": "SAP", "critical_fields": ["BOM_ID", "Finished_Material_ID"]},
    {"name": "Quality_Inspection_Lot", "system": "SAP", "critical_fields": ["Inspection_ID", "Batch_ID", "Result"]},
    {"name": "Quality_Test_Result", "system": "SAP", "critical_fields": ["Result_ID", "Inspection_ID", "Pass_Flag"]},
    {"name": "Batch_Master", "system": "SAP", "critical_fields": ["Batch_ID", "Material_ID"]},
    {"name": "Material_Master", "system": "SAP", "critical_fields": ["Material_ID", "Category"]},
]

PQ_RESULT_ENTITIES = [
    {"name": "PQ_KPI_Snapshot", "critical_fields": ["oee_pct", "yield_pct", "first_pass_rate_pct"]},
    {"name": "PQ_Production_Result", "critical_fields": ["order_id", "material", "yield_pct", "oee"]},
    {"name": "PQ_Alert", "critical_fields": ["total_alerts", "alerts"]},
    {"name": "PQ_Line_Summary", "critical_fields": ["line_id", "avg_oee", "avg_yield"]},
    {"name": "PQ_Quality_Summary", "critical_fields": ["category", "pass_rate", "defect_rate"]},
]


@router.post("/pq")
async def run_pq_diagnostics() -> Dict[str, Any]:
    """Run comprehensive Production & Quality diagnostics across data, mapping, quality, and results."""
    ts = datetime.utcnow().isoformat()
    sections = {}

    all_rules = await _get_mapping_rules()
    rule_map = {}
    for r in all_rules:
        ve = r.virtual_entity if hasattr(r, "virtual_entity") else getattr(r, "virtualEntity", "")
        rule_map[ve] = r

    # ── 1. Data Adequacy ────────────────────────────────────
    adequacy_entities = []
    for spec in PQ_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=5)
        row_count = len(rows) if rows else 0
        if rows is None:
            row_count = -1
        field_count = len(rows[0].keys()) if rows else 0
        status = "ok" if row_count > 0 else ("error" if err else "no_data")
        adequacy_entities.append({
            "name": spec["name"], "system": spec["system"],
            "rows": row_count, "fields": field_count,
            "status": status, "error": err,
        })

    with_data = sum(1 for e in adequacy_entities if e["status"] == "ok")
    missing = sum(1 for e in adequacy_entities if e["status"] != "ok")
    sections["data_adequacy"] = {
        "status": _check_status(missing == 0, missing > 0 and with_data > 0),
        "entities": adequacy_entities,
        "summary": {"total_entities": len(adequacy_entities), "with_data": with_data, "missing": missing},
    }

    # ── 2. Mapping Correctness ──────────────────────────────
    mapping_rules = []
    for spec in PQ_SOURCE_ENTITIES + [{"name": e["name"]} for e in PQ_RESULT_ENTITIES]:
        ename = spec["name"]
        rule = rule_map.get(ename)
        if rule:
            src_table = getattr(rule, "source_table", "")
            src_schema = getattr(rule, "source_schema", "")
            src_type = getattr(rule, "source_type", "")
            field_maps = getattr(rule, "field_maps", [])
            mapped = sum(1 for fm in field_maps if getattr(fm, "source_field", ""))
            unmapped = len(field_maps) - mapped
            status_val = getattr(rule, "status", None)
            raw_status = status_val.value if hasattr(status_val, "value") else str(status_val)
            active = raw_status == "active"
            rule_name = getattr(rule, "name", "")
            issue = ""
            if raw_status == "draft":
                issue = "Rule is in draft status — activate it in Mapping Rules"
            elif raw_status == "inactive":
                issue = "Rule is inactive — set status to active"
            mapping_rules.append({
                "entity": ename, "source_table": src_table, "source_schema": src_schema,
                "source_type": str(getattr(src_type, "value", src_type)),
                "mapped_fields": mapped, "unmapped_fields": unmapped,
                "rule_name": rule_name, "rule_status": raw_status,
                "status": "ok" if active else "inactive",
                "issue": issue,
            })
        else:
            mapping_rules.append({
                "entity": ename, "source_table": "", "source_schema": "",
                "source_type": "", "mapped_fields": 0, "unmapped_fields": 0,
                "status": "missing",
            })

    active_count = sum(1 for r in mapping_rules if r["status"] == "ok")
    issues_count = sum(1 for r in mapping_rules if r["status"] != "ok")
    sections["mapping_correctness"] = {
        "status": _check_status(issues_count == 0, issues_count > 0 and active_count > 0),
        "rules": mapping_rules,
        "summary": {"total_rules": len(mapping_rules), "active": active_count, "issues": issues_count},
    }

    # ── 3. Data after Mapping ───────────────────────────────
    vdl_queries = []
    vdl_data_cache = {}
    for spec in PQ_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=200)
        actual_rows = rows if rows else []
        vdl_data_cache[spec["name"]] = actual_rows
        sample_row = actual_rows[0] if actual_rows else {}
        vdl_queries.append({
            "entity": spec["name"], "rows_returned": len(actual_rows),
            "field_keys": sorted(sample_row.keys()) if sample_row else [],
            "sample_row": {k: repr(v)[:60] for k, v in list(sample_row.items())[:8]} if sample_row else {},
            "status": "ok" if actual_rows else "no_data",
            "error": err,
        })

    vdl_ok = sum(1 for q in vdl_queries if q["status"] == "ok")
    sections["data_after_mapping"] = {
        "status": _check_status(vdl_ok == len(vdl_queries), vdl_ok > 0 and vdl_ok < len(vdl_queries)),
        "queries": vdl_queries,
    }

    # ── 4. Data Quality ─────────────────────────────────────
    quality_checks = []
    for spec in PQ_SOURCE_ENTITIES:
        rows = vdl_data_cache.get(spec["name"], [])
        if not rows:
            continue
        total = len(rows)
        for field in spec["critical_fields"]:
            null_count = sum(1 for r in rows if r.get(field) is None)
            null_pct = round(null_count / total * 100, 1) if total else 0
            present_vals = [r.get(field) for r in rows if r.get(field) is not None]
            detected_type = "unknown"
            if present_vals:
                sample = present_vals[0]
                if isinstance(sample, (int, float)):
                    detected_type = "numeric"
                elif isinstance(sample, bool):
                    detected_type = "boolean"
                else:
                    detected_type = "text"

            field_present = any(field in r for r in rows)
            if not field_present:
                status = "fail"
            elif null_pct > 50:
                status = "fail"
            elif null_pct > 10:
                status = "warn"
            else:
                status = "ok"

            quality_checks.append({
                "entity": spec["name"], "field": field,
                "null_count": null_count, "null_pct": null_pct,
                "total_rows": total, "field_present": field_present,
                "type": detected_type, "status": status,
            })

    passed = sum(1 for c in quality_checks if c["status"] == "ok")
    warnings = sum(1 for c in quality_checks if c["status"] == "warn")
    failures = sum(1 for c in quality_checks if c["status"] == "fail")
    sections["data_quality"] = {
        "status": _check_status(failures == 0, warnings > 0),
        "checks": quality_checks,
        "summary": {"total_checks": len(quality_checks), "passed": passed, "warnings": warnings, "failures": failures},
    }

    # ── 5. Results Analysis ─────────────────────────────────
    result_entities = []
    for spec in PQ_RESULT_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=500)
        actual_rows = rows if rows else []
        entry = {
            "name": spec["name"], "rows": len(actual_rows),
            "status": "ok" if actual_rows else "no_data",
            "sample_keys": sorted(actual_rows[0].keys()) if actual_rows else [],
            "error": err,
        }
        if spec["name"] == "PQ_KPI_Snapshot" and actual_rows:
            kpi = actual_rows[0]
            entry["kpis"] = {k: kpi.get(k) for k in spec["critical_fields"] if k in kpi}
        if spec["name"] == "PQ_Alert" and actual_rows:
            entry["alert_count"] = actual_rows[0].get("total_alerts", 0)
        if spec["name"] == "PQ_Production_Result" and actual_rows:
            materials = set()
            yields = []
            oees = []
            for r in actual_rows:
                materials.add(r.get("material", "Unknown"))
                y = r.get("yield_pct")
                if y is not None:
                    yields.append(float(y))
                o = r.get("oee")
                if o is not None:
                    oees.append(float(o))
            entry["summary"] = {
                "total_rows": len(actual_rows),
                "materials": len(materials),
                "avg_yield": round(sum(yields) / len(yields), 1) if yields else 0,
                "avg_oee": round(sum(oees) / len(oees), 1) if oees else 0,
            }
        if spec["name"] == "PQ_Line_Summary" and actual_rows:
            entry["breakdown"] = [{"line_id": r.get("line_id"), "avg_oee": r.get("avg_oee"), "avg_yield": r.get("avg_yield")} for r in actual_rows]
        if spec["name"] == "PQ_Quality_Summary" and actual_rows:
            entry["breakdown"] = [{"category": r.get("category"), "pass_rate": r.get("pass_rate"), "defect_rate": r.get("defect_rate")} for r in actual_rows]
        result_entities.append(entry)

    results_ok = sum(1 for e in result_entities if e["status"] == "ok")
    sections["results_analysis"] = {
        "status": _check_status(results_ok == len(result_entities), results_ok > 0 and results_ok < len(result_entities)),
        "entities": result_entities,
    }

    statuses = [s["status"] for s in sections.values()]
    overall = "pass" if all(s == "pass" for s in statuses) else ("fail" if any(s == "fail" for s in statuses) else "warn")

    return {"timestamp": ts, "overall_status": overall, "sections": sections}


# ==========================================
# Supply Chain Risk Diagnostics
# ==========================================

SCR_SOURCE_ENTITIES = [
    {"name": "Vendor_Master", "system": "SAP", "critical_fields": ["Vendor_ID", "Name", "Country", "Risk_Rating"]},
    {"name": "Purchase_Order", "system": "Oracle", "critical_fields": ["PO_ID", "Vendor_ID", "Total_Amount"]},
    {"name": "Source_List", "system": "SAP", "critical_fields": ["Material_ID", "Vendor_ID"]},
    {"name": "Market_Signal", "system": "External", "critical_fields": ["Signal_ID", "Severity", "Event_Type"]},
    {"name": "Contract_Document", "system": "External", "critical_fields": ["Contract_ID", "Vendor_ID"]},
    {"name": "Goods_Receipt", "system": "SAP", "critical_fields": ["GRN_ID", "PO_ID"]},
    {"name": "Quality_Inspection_Lot", "system": "SAP", "critical_fields": ["Inspection_ID", "Result"]},
    {"name": "Material_Master", "system": "SAP", "critical_fields": ["Material_ID", "Category"]},
]

SCR_RESULT_ENTITIES = [
    {"name": "SCR_KPI_Snapshot", "critical_fields": ["avg_risk_score", "otd_pct", "single_source_count"]},
    {"name": "SCR_Vendor_Result", "critical_fields": ["vendor_name", "risk_score", "otd_pct"]},
    {"name": "SCR_Alert", "critical_fields": ["total_alerts", "alerts"]},
    {"name": "SCR_Region_Summary", "critical_fields": ["region", "avg_risk", "vendor_count"]},
    {"name": "SCR_Category_Summary", "critical_fields": ["category", "avg_risk", "vendor_count"]},
]


@router.post("/scr")
async def run_scr_diagnostics() -> Dict[str, Any]:
    """Run comprehensive Supply Chain Risk diagnostics across data, mapping, quality, and results."""
    ts = datetime.utcnow().isoformat()
    sections = {}

    all_rules = await _get_mapping_rules()
    rule_map = {}
    for r in all_rules:
        ve = r.virtual_entity if hasattr(r, "virtual_entity") else getattr(r, "virtualEntity", "")
        rule_map[ve] = r

    # ── 1. Data Adequacy ────────────────────────────────────
    adequacy_entities = []
    for spec in SCR_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=5)
        row_count = len(rows) if rows else 0
        if rows is None:
            row_count = -1
        field_count = len(rows[0].keys()) if rows else 0
        status = "ok" if row_count > 0 else ("error" if err else "no_data")
        adequacy_entities.append({
            "name": spec["name"], "system": spec["system"],
            "rows": row_count, "fields": field_count,
            "status": status, "error": err,
        })

    with_data = sum(1 for e in adequacy_entities if e["status"] == "ok")
    missing = sum(1 for e in adequacy_entities if e["status"] != "ok")
    sections["data_adequacy"] = {
        "status": _check_status(missing == 0, missing > 0 and with_data > 0),
        "entities": adequacy_entities,
        "summary": {"total_entities": len(adequacy_entities), "with_data": with_data, "missing": missing},
    }

    # ── 2. Mapping Correctness ──────────────────────────────
    mapping_rules = []
    for spec in SCR_SOURCE_ENTITIES + [{"name": e["name"]} for e in SCR_RESULT_ENTITIES]:
        ename = spec["name"]
        rule = rule_map.get(ename)
        if rule:
            src_table = getattr(rule, "source_table", "")
            src_schema = getattr(rule, "source_schema", "")
            src_type = getattr(rule, "source_type", "")
            field_maps = getattr(rule, "field_maps", [])
            mapped = sum(1 for fm in field_maps if getattr(fm, "source_field", ""))
            unmapped = len(field_maps) - mapped
            status_val = getattr(rule, "status", None)
            raw_status = status_val.value if hasattr(status_val, "value") else str(status_val)
            active = raw_status == "active"
            rule_name = getattr(rule, "name", "")
            issue = ""
            if raw_status == "draft":
                issue = "Rule is in draft status — activate it in Mapping Rules"
            elif raw_status == "inactive":
                issue = "Rule is inactive — set status to active"
            mapping_rules.append({
                "entity": ename, "source_table": src_table, "source_schema": src_schema,
                "source_type": str(getattr(src_type, "value", src_type)),
                "mapped_fields": mapped, "unmapped_fields": unmapped,
                "rule_name": rule_name, "rule_status": raw_status,
                "status": "ok" if active else "inactive",
                "issue": issue,
            })
        else:
            mapping_rules.append({
                "entity": ename, "source_table": "", "source_schema": "",
                "source_type": "", "mapped_fields": 0, "unmapped_fields": 0,
                "status": "missing",
            })

    active_count = sum(1 for r in mapping_rules if r["status"] == "ok")
    issues_count = sum(1 for r in mapping_rules if r["status"] != "ok")
    sections["mapping_correctness"] = {
        "status": _check_status(issues_count == 0, issues_count > 0 and active_count > 0),
        "rules": mapping_rules,
        "summary": {"total_rules": len(mapping_rules), "active": active_count, "issues": issues_count},
    }

    # ── 3. Data after Mapping ───────────────────────────────
    vdl_queries = []
    vdl_data_cache = {}
    for spec in SCR_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=200)
        actual_rows = rows if rows else []
        vdl_data_cache[spec["name"]] = actual_rows
        sample_row = actual_rows[0] if actual_rows else {}
        vdl_queries.append({
            "entity": spec["name"], "rows_returned": len(actual_rows),
            "field_keys": sorted(sample_row.keys()) if sample_row else [],
            "sample_row": {k: repr(v)[:60] for k, v in list(sample_row.items())[:8]} if sample_row else {},
            "status": "ok" if actual_rows else "no_data",
            "error": err,
        })

    vdl_ok = sum(1 for q in vdl_queries if q["status"] == "ok")
    sections["data_after_mapping"] = {
        "status": _check_status(vdl_ok == len(vdl_queries), vdl_ok > 0 and vdl_ok < len(vdl_queries)),
        "queries": vdl_queries,
    }

    # ── 4. Data Quality ─────────────────────────────────────
    quality_checks = []
    for spec in SCR_SOURCE_ENTITIES:
        rows = vdl_data_cache.get(spec["name"], [])
        if not rows:
            continue
        total = len(rows)
        for field in spec["critical_fields"]:
            null_count = sum(1 for r in rows if r.get(field) is None)
            null_pct = round(null_count / total * 100, 1) if total else 0
            present_vals = [r.get(field) for r in rows if r.get(field) is not None]
            detected_type = "unknown"
            if present_vals:
                sample = present_vals[0]
                if isinstance(sample, (int, float)):
                    detected_type = "numeric"
                elif isinstance(sample, bool):
                    detected_type = "boolean"
                else:
                    detected_type = "text"

            field_present = any(field in r for r in rows)
            if not field_present:
                status = "fail"
            elif null_pct > 50:
                status = "fail"
            elif null_pct > 10:
                status = "warn"
            else:
                status = "ok"

            quality_checks.append({
                "entity": spec["name"], "field": field,
                "null_count": null_count, "null_pct": null_pct,
                "total_rows": total, "field_present": field_present,
                "type": detected_type, "status": status,
            })

    passed = sum(1 for c in quality_checks if c["status"] == "ok")
    warnings = sum(1 for c in quality_checks if c["status"] == "warn")
    failures = sum(1 for c in quality_checks if c["status"] == "fail")
    sections["data_quality"] = {
        "status": _check_status(failures == 0, warnings > 0),
        "checks": quality_checks,
        "summary": {"total_checks": len(quality_checks), "passed": passed, "warnings": warnings, "failures": failures},
    }

    # ── 5. Results Analysis ─────────────────────────────────
    result_entities = []
    for spec in SCR_RESULT_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=500)
        actual_rows = rows if rows else []
        entry = {
            "name": spec["name"], "rows": len(actual_rows),
            "status": "ok" if actual_rows else "no_data",
            "sample_keys": sorted(actual_rows[0].keys()) if actual_rows else [],
            "error": err,
        }
        if spec["name"] == "SCR_KPI_Snapshot" and actual_rows:
            kpi = actual_rows[0]
            entry["kpis"] = {k: kpi.get(k) for k in spec["critical_fields"] if k in kpi}
        if spec["name"] == "SCR_Alert" and actual_rows:
            entry["alert_count"] = actual_rows[0].get("total_alerts", 0)
        if spec["name"] == "SCR_Vendor_Result" and actual_rows:
            vendors = set()
            risk_scores = []
            for r in actual_rows:
                vendors.add(r.get("vendor_name", "Unknown"))
                rs = r.get("risk_score")
                if rs is not None:
                    risk_scores.append(float(rs))
            high_risk = sum(1 for s in risk_scores if s > 70)
            entry["summary"] = {
                "total_rows": len(actual_rows),
                "vendors": len(vendors),
                "avg_risk": round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else 0,
                "high_risk": high_risk,
            }
        if spec["name"] == "SCR_Region_Summary" and actual_rows:
            entry["breakdown"] = [{"region": r.get("region"), "avg_risk": r.get("avg_risk"), "vendor_count": r.get("vendor_count")} for r in actual_rows]
        if spec["name"] == "SCR_Category_Summary" and actual_rows:
            entry["breakdown"] = [{"category": r.get("category"), "avg_risk": r.get("avg_risk"), "vendor_count": r.get("vendor_count")} for r in actual_rows]
        result_entities.append(entry)

    results_ok = sum(1 for e in result_entities if e["status"] == "ok")
    sections["results_analysis"] = {
        "status": _check_status(results_ok == len(result_entities), results_ok > 0 and results_ok < len(result_entities)),
        "entities": result_entities,
    }

    statuses = [s["status"] for s in sections.values()]
    overall = "pass" if all(s == "pass" for s in statuses) else ("fail" if any(s == "fail" for s in statuses) else "warn")

    return {"timestamp": ts, "overall_status": overall, "sections": sections}


# ==========================================
# Customer 360 Diagnostics
# ==========================================

C360_SOURCE_ENTITIES = [
    {"name": "Account", "system": "Salesforce", "critical_fields": ["Account_ID", "Region", "Tier"]},
    {"name": "Contact", "system": "Salesforce", "critical_fields": ["Contact_ID", "Account_ID"]},
    {"name": "Opportunity", "system": "Salesforce", "critical_fields": ["Opportunity_ID", "Total_Value", "Stage"]},
    {"name": "AR_Customer", "system": "Oracle", "critical_fields": ["Customer_ID", "Credit_Limit"]},
    {"name": "AR_Invoice", "system": "Oracle", "critical_fields": ["Invoice_ID", "Customer_ID", "Total_Amount"]},
    {"name": "AR_Payment", "system": "Oracle", "critical_fields": ["Payment_ID", "Invoice_ID"]},
    {"name": "Brand_Sentiment", "system": "External", "critical_fields": ["Brand", "Sentiment_Score"]},
    {"name": "Campaign", "system": "Salesforce", "critical_fields": ["Campaign_ID", "Type", "Status"]},
]

C360_RESULT_ENTITIES = [
    {"name": "C360_KPI_Snapshot", "critical_fields": ["avg_clv", "churn_risk_pct", "wallet_share_avg"]},
    {"name": "C360_Customer_Result", "critical_fields": ["account_id", "clv", "churn_score", "wallet_share"]},
    {"name": "C360_Alert", "critical_fields": ["total_alerts", "alerts"]},
    {"name": "C360_Segment_Summary", "critical_fields": ["segment", "customer_count", "avg_clv"]},
    {"name": "C360_Revenue_Summary", "critical_fields": ["region", "total_revenue"]},
]


@router.post("/c360")
async def run_c360_diagnostics() -> Dict[str, Any]:
    """Run comprehensive Customer 360 diagnostics across data, mapping, quality, and results."""
    ts = datetime.utcnow().isoformat()
    sections = {}

    all_rules = await _get_mapping_rules()
    rule_map = {}
    for r in all_rules:
        ve = r.virtual_entity if hasattr(r, "virtual_entity") else getattr(r, "virtualEntity", "")
        rule_map[ve] = r

    # ── 1. Data Adequacy ────────────────────────────────────
    adequacy_entities = []
    for spec in C360_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=5)
        row_count = len(rows) if rows else 0
        if rows is None:
            row_count = -1
        field_count = len(rows[0].keys()) if rows else 0
        status = "ok" if row_count > 0 else ("error" if err else "no_data")
        adequacy_entities.append({
            "name": spec["name"], "system": spec["system"],
            "rows": row_count, "fields": field_count,
            "status": status, "error": err,
        })

    with_data = sum(1 for e in adequacy_entities if e["status"] == "ok")
    missing = sum(1 for e in adequacy_entities if e["status"] != "ok")
    sections["data_adequacy"] = {
        "status": _check_status(missing == 0, missing > 0 and with_data > 0),
        "entities": adequacy_entities,
        "summary": {"total_entities": len(adequacy_entities), "with_data": with_data, "missing": missing},
    }

    # ── 2. Mapping Correctness ──────────────────────────────
    mapping_rules = []
    for spec in C360_SOURCE_ENTITIES + [{"name": e["name"]} for e in C360_RESULT_ENTITIES]:
        ename = spec["name"]
        rule = rule_map.get(ename)
        if rule:
            src_table = getattr(rule, "source_table", "")
            src_schema = getattr(rule, "source_schema", "")
            src_type = getattr(rule, "source_type", "")
            field_maps = getattr(rule, "field_maps", [])
            mapped = sum(1 for fm in field_maps if getattr(fm, "source_field", ""))
            unmapped = len(field_maps) - mapped
            status_val = getattr(rule, "status", None)
            raw_status = status_val.value if hasattr(status_val, "value") else str(status_val)
            active = raw_status == "active"
            rule_name = getattr(rule, "name", "")
            issue = ""
            if raw_status == "draft":
                issue = "Rule is in draft status — activate it in Mapping Rules"
            elif raw_status == "inactive":
                issue = "Rule is inactive — set status to active"
            mapping_rules.append({
                "entity": ename, "source_table": src_table, "source_schema": src_schema,
                "source_type": str(getattr(src_type, "value", src_type)),
                "mapped_fields": mapped, "unmapped_fields": unmapped,
                "rule_name": rule_name, "rule_status": raw_status,
                "status": "ok" if active else "inactive",
                "issue": issue,
            })
        else:
            mapping_rules.append({
                "entity": ename, "source_table": "", "source_schema": "",
                "source_type": "", "mapped_fields": 0, "unmapped_fields": 0,
                "status": "missing",
            })

    active_count = sum(1 for r in mapping_rules if r["status"] == "ok")
    issues_count = sum(1 for r in mapping_rules if r["status"] != "ok")
    sections["mapping_correctness"] = {
        "status": _check_status(issues_count == 0, issues_count > 0 and active_count > 0),
        "rules": mapping_rules,
        "summary": {"total_rules": len(mapping_rules), "active": active_count, "issues": issues_count},
    }

    # ── 3. Data after Mapping ───────────────────────────────
    vdl_queries = []
    vdl_data_cache = {}
    for spec in C360_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=200)
        actual_rows = rows if rows else []
        vdl_data_cache[spec["name"]] = actual_rows
        sample_row = actual_rows[0] if actual_rows else {}
        vdl_queries.append({
            "entity": spec["name"], "rows_returned": len(actual_rows),
            "field_keys": sorted(sample_row.keys()) if sample_row else [],
            "sample_row": {k: repr(v)[:60] for k, v in list(sample_row.items())[:8]} if sample_row else {},
            "status": "ok" if actual_rows else "no_data",
            "error": err,
        })

    vdl_ok = sum(1 for q in vdl_queries if q["status"] == "ok")
    sections["data_after_mapping"] = {
        "status": _check_status(vdl_ok == len(vdl_queries), vdl_ok > 0 and vdl_ok < len(vdl_queries)),
        "queries": vdl_queries,
    }

    # ── 4. Data Quality ─────────────────────────────────────
    quality_checks = []
    for spec in C360_SOURCE_ENTITIES:
        rows = vdl_data_cache.get(spec["name"], [])
        if not rows:
            continue
        total = len(rows)
        for field in spec["critical_fields"]:
            null_count = sum(1 for r in rows if r.get(field) is None)
            null_pct = round(null_count / total * 100, 1) if total else 0
            present_vals = [r.get(field) for r in rows if r.get(field) is not None]
            detected_type = "unknown"
            if present_vals:
                sample = present_vals[0]
                if isinstance(sample, (int, float)):
                    detected_type = "numeric"
                elif isinstance(sample, bool):
                    detected_type = "boolean"
                else:
                    detected_type = "text"

            field_present = any(field in r for r in rows)
            if not field_present:
                status = "fail"
            elif null_pct > 50:
                status = "fail"
            elif null_pct > 10:
                status = "warn"
            else:
                status = "ok"

            quality_checks.append({
                "entity": spec["name"], "field": field,
                "null_count": null_count, "null_pct": null_pct,
                "total_rows": total, "field_present": field_present,
                "type": detected_type, "status": status,
            })

    passed = sum(1 for c in quality_checks if c["status"] == "ok")
    warnings = sum(1 for c in quality_checks if c["status"] == "warn")
    failures = sum(1 for c in quality_checks if c["status"] == "fail")
    sections["data_quality"] = {
        "status": _check_status(failures == 0, warnings > 0),
        "checks": quality_checks,
        "summary": {"total_checks": len(quality_checks), "passed": passed, "warnings": warnings, "failures": failures},
    }

    # ── 5. Results Analysis ─────────────────────────────────
    result_entities = []
    for spec in C360_RESULT_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=500)
        actual_rows = rows if rows else []
        entry = {
            "name": spec["name"], "rows": len(actual_rows),
            "status": "ok" if actual_rows else "no_data",
            "sample_keys": sorted(actual_rows[0].keys()) if actual_rows else [],
            "error": err,
        }
        if spec["name"] == "C360_KPI_Snapshot" and actual_rows:
            kpi = actual_rows[0]
            entry["kpis"] = {k: kpi.get(k) for k in spec["critical_fields"] if k in kpi}
        if spec["name"] == "C360_Alert" and actual_rows:
            entry["alert_count"] = actual_rows[0].get("total_alerts", 0)
        if spec["name"] == "C360_Customer_Result" and actual_rows:
            clvs = []
            high_churn = 0
            for r in actual_rows:
                clvs.append(float(r.get("clv", 0) or 0))
                cs = r.get("churn_score")
                if cs is not None and float(cs) > 50:
                    high_churn += 1
            entry["summary"] = {
                "total_rows": len(actual_rows),
                "avg_clv": round(sum(clvs) / len(clvs), 2) if clvs else 0,
                "high_churn_risk": high_churn,
            }
        if spec["name"] == "C360_Segment_Summary" and actual_rows:
            entry["breakdown"] = [{"segment": r.get("segment"), "customer_count": r.get("customer_count"), "avg_clv": r.get("avg_clv")} for r in actual_rows]
        if spec["name"] == "C360_Revenue_Summary" and actual_rows:
            entry["breakdown"] = [{"region": r.get("region"), "total_revenue": r.get("total_revenue")} for r in actual_rows]
        result_entities.append(entry)

    results_ok = sum(1 for e in result_entities if e["status"] == "ok")
    sections["results_analysis"] = {
        "status": _check_status(results_ok == len(result_entities), results_ok > 0 and results_ok < len(result_entities)),
        "entities": result_entities,
    }

    statuses = [s["status"] for s in sections.values()]
    overall = "pass" if all(s == "pass" for s in statuses) else ("fail" if any(s == "fail" for s in statuses) else "warn")

    return {"timestamp": ts, "overall_status": overall, "sections": sections}


# ==========================================
# ESG & Sustainability Diagnostics
# ==========================================

ESG_SOURCE_ENTITIES = [
    {"name": "Sustainability_Report", "system": "External", "critical_fields": ["Report_ID", "Report_Type"]},
    {"name": "Material_Master", "system": "SAP", "critical_fields": ["Material_ID", "Recycled_Content_Pct", "Recyclability_Score"]},
    {"name": "Plant_Master", "system": "SAP", "critical_fields": ["Plant_ID", "Name"]},
    {"name": "Brand_Sentiment", "system": "External", "critical_fields": ["Brand", "Sentiment_Score"]},
    {"name": "Production_Order", "system": "SAP", "critical_fields": ["Order_ID", "Plant_ID"]},
    {"name": "Shipment", "system": "SAP", "critical_fields": ["Shipment_ID", "Route"]},
]

ESG_RESULT_ENTITIES = [
    {"name": "ESG_KPI_Snapshot", "critical_fields": ["carbon_intensity", "water_ratio", "recycled_content_pct"]},
    {"name": "ESG_Plant_Result", "critical_fields": ["plant_id", "carbon_emissions", "water_usage"]},
    {"name": "ESG_Alert", "critical_fields": ["total_alerts", "alerts"]},
    {"name": "ESG_Material_Summary", "critical_fields": ["material_id", "recycled_content_pct", "carbon_footprint"]},
    {"name": "ESG_Category_Summary", "critical_fields": ["category", "avg_recycled_pct"]},
]


@router.post("/esg")
async def run_esg_diagnostics() -> Dict[str, Any]:
    """Run comprehensive ESG & Sustainability diagnostics across data, mapping, quality, and results."""
    ts = datetime.utcnow().isoformat()
    sections = {}

    all_rules = await _get_mapping_rules()
    rule_map = {}
    for r in all_rules:
        ve = r.virtual_entity if hasattr(r, "virtual_entity") else getattr(r, "virtualEntity", "")
        rule_map[ve] = r

    # ── 1. Data Adequacy ────────────────────────────────────
    adequacy_entities = []
    for spec in ESG_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=5)
        row_count = len(rows) if rows else 0
        if rows is None:
            row_count = -1
        field_count = len(rows[0].keys()) if rows else 0
        status = "ok" if row_count > 0 else ("error" if err else "no_data")
        adequacy_entities.append({
            "name": spec["name"], "system": spec["system"],
            "rows": row_count, "fields": field_count,
            "status": status, "error": err,
        })

    with_data = sum(1 for e in adequacy_entities if e["status"] == "ok")
    missing = sum(1 for e in adequacy_entities if e["status"] != "ok")
    sections["data_adequacy"] = {
        "status": _check_status(missing == 0, missing > 0 and with_data > 0),
        "entities": adequacy_entities,
        "summary": {"total_entities": len(adequacy_entities), "with_data": with_data, "missing": missing},
    }

    # ── 2. Mapping Correctness ──────────────────────────────
    mapping_rules = []
    for spec in ESG_SOURCE_ENTITIES + [{"name": e["name"]} for e in ESG_RESULT_ENTITIES]:
        ename = spec["name"]
        rule = rule_map.get(ename)
        if rule:
            src_table = getattr(rule, "source_table", "")
            src_schema = getattr(rule, "source_schema", "")
            src_type = getattr(rule, "source_type", "")
            field_maps = getattr(rule, "field_maps", [])
            mapped = sum(1 for fm in field_maps if getattr(fm, "source_field", ""))
            unmapped = len(field_maps) - mapped
            status_val = getattr(rule, "status", None)
            raw_status = status_val.value if hasattr(status_val, "value") else str(status_val)
            active = raw_status == "active"
            rule_name = getattr(rule, "name", "")
            issue = ""
            if raw_status == "draft":
                issue = "Rule is in draft status — activate it in Mapping Rules"
            elif raw_status == "inactive":
                issue = "Rule is inactive — set status to active"
            mapping_rules.append({
                "entity": ename, "source_table": src_table, "source_schema": src_schema,
                "source_type": str(getattr(src_type, "value", src_type)),
                "mapped_fields": mapped, "unmapped_fields": unmapped,
                "rule_name": rule_name, "rule_status": raw_status,
                "status": "ok" if active else "inactive",
                "issue": issue,
            })
        else:
            mapping_rules.append({
                "entity": ename, "source_table": "", "source_schema": "",
                "source_type": "", "mapped_fields": 0, "unmapped_fields": 0,
                "status": "missing",
            })

    active_count = sum(1 for r in mapping_rules if r["status"] == "ok")
    issues_count = sum(1 for r in mapping_rules if r["status"] != "ok")
    sections["mapping_correctness"] = {
        "status": _check_status(issues_count == 0, issues_count > 0 and active_count > 0),
        "rules": mapping_rules,
        "summary": {"total_rules": len(mapping_rules), "active": active_count, "issues": issues_count},
    }

    # ── 3. Data after Mapping ───────────────────────────────
    vdl_queries = []
    vdl_data_cache = {}
    for spec in ESG_SOURCE_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=200)
        actual_rows = rows if rows else []
        vdl_data_cache[spec["name"]] = actual_rows
        sample_row = actual_rows[0] if actual_rows else {}
        vdl_queries.append({
            "entity": spec["name"], "rows_returned": len(actual_rows),
            "field_keys": sorted(sample_row.keys()) if sample_row else [],
            "sample_row": {k: repr(v)[:60] for k, v in list(sample_row.items())[:8]} if sample_row else {},
            "status": "ok" if actual_rows else "no_data",
            "error": err,
        })

    vdl_ok = sum(1 for q in vdl_queries if q["status"] == "ok")
    sections["data_after_mapping"] = {
        "status": _check_status(vdl_ok == len(vdl_queries), vdl_ok > 0 and vdl_ok < len(vdl_queries)),
        "queries": vdl_queries,
    }

    # ── 4. Data Quality ─────────────────────────────────────
    quality_checks = []
    for spec in ESG_SOURCE_ENTITIES:
        rows = vdl_data_cache.get(spec["name"], [])
        if not rows:
            continue
        total = len(rows)
        for field in spec["critical_fields"]:
            null_count = sum(1 for r in rows if r.get(field) is None)
            null_pct = round(null_count / total * 100, 1) if total else 0
            present_vals = [r.get(field) for r in rows if r.get(field) is not None]
            detected_type = "unknown"
            if present_vals:
                sample = present_vals[0]
                if isinstance(sample, (int, float)):
                    detected_type = "numeric"
                elif isinstance(sample, bool):
                    detected_type = "boolean"
                else:
                    detected_type = "text"

            field_present = any(field in r for r in rows)
            if not field_present:
                status = "fail"
            elif null_pct > 50:
                status = "fail"
            elif null_pct > 10:
                status = "warn"
            else:
                status = "ok"

            quality_checks.append({
                "entity": spec["name"], "field": field,
                "null_count": null_count, "null_pct": null_pct,
                "total_rows": total, "field_present": field_present,
                "type": detected_type, "status": status,
            })

    passed = sum(1 for c in quality_checks if c["status"] == "ok")
    warnings = sum(1 for c in quality_checks if c["status"] == "warn")
    failures = sum(1 for c in quality_checks if c["status"] == "fail")
    sections["data_quality"] = {
        "status": _check_status(failures == 0, warnings > 0),
        "checks": quality_checks,
        "summary": {"total_checks": len(quality_checks), "passed": passed, "warnings": warnings, "failures": failures},
    }

    # ── 5. Results Analysis ─────────────────────────────────
    result_entities = []
    for spec in ESG_RESULT_ENTITIES:
        rows, err = await _df_query(spec["name"], limit=500)
        actual_rows = rows if rows else []
        entry = {
            "name": spec["name"], "rows": len(actual_rows),
            "status": "ok" if actual_rows else "no_data",
            "sample_keys": sorted(actual_rows[0].keys()) if actual_rows else [],
            "error": err,
        }
        if spec["name"] == "ESG_KPI_Snapshot" and actual_rows:
            kpi = actual_rows[0]
            entry["kpis"] = {k: kpi.get(k) for k in spec["critical_fields"] if k in kpi}
        if spec["name"] == "ESG_Alert" and actual_rows:
            entry["alert_count"] = actual_rows[0].get("total_alerts", 0)
        if spec["name"] == "ESG_Plant_Result" and actual_rows:
            plants = set()
            total_emissions = 0
            for r in actual_rows:
                plants.add(r.get("plant_id", "Unknown"))
                total_emissions += float(r.get("carbon_emissions", 0) or 0)
            entry["summary"] = {
                "total_rows": len(actual_rows),
                "plants": len(plants),
                "total_carbon_emissions": round(total_emissions, 2),
            }
        if spec["name"] == "ESG_Material_Summary" and actual_rows:
            entry["breakdown"] = [{"material_id": r.get("material_id"), "recycled_content_pct": r.get("recycled_content_pct"), "carbon_footprint": r.get("carbon_footprint")} for r in actual_rows]
        if spec["name"] == "ESG_Category_Summary" and actual_rows:
            entry["breakdown"] = [{"category": r.get("category"), "avg_recycled_pct": r.get("avg_recycled_pct")} for r in actual_rows]
        result_entities.append(entry)

    results_ok = sum(1 for e in result_entities if e["status"] == "ok")
    sections["results_analysis"] = {
        "status": _check_status(results_ok == len(result_entities), results_ok > 0 and results_ok < len(result_entities)),
        "entities": result_entities,
    }

    statuses = [s["status"] for s in sections.values()]
    overall = "pass" if all(s == "pass" for s in statuses) else ("fail" if any(s == "fail" for s in statuses) else "warn")

    return {"timestamp": ts, "overall_status": overall, "sections": sections}


# ==========================================
# Simulator Infrastructure Diagnostics
# ==========================================

_SIM_REGISTRY = [
    {"key": "simulator", "label": "SFDC", "svc_name": "sfdc"},
    {"key": "sap", "label": "SAP", "svc_name": "sap"},
    {"key": "oracle", "label": "Oracle ERP", "svc_name": "oracle"},
    {"key": "external", "label": "External", "svc_name": "external"},
    {"key": "tpm", "label": "TPM (Trade CPQ)", "svc_name": "tpm"},
    {"key": "sourcing", "label": "Sourcing (Buy CPQ)", "svc_name": "sourcing"},
]


def _get_all_simulator_services():
    from src.apis.fdw_api import _simulators
    result = {}
    for entry in _SIM_REGISTRY:
        svc = _simulators.get(entry["key"])
        if svc:
            result[entry["key"]] = {"service": svc, "label": entry["label"], "svc_name": entry["svc_name"]}
    return result


@router.post("/simulators")
async def run_simulator_diagnostics():
    """Reachability + catalog summary against the remote nexus-simulator service."""
    ts = datetime.utcnow().isoformat() + "Z"
    sections: Dict[str, Any] = {}
    from src.services.simulator_fdw_client import (
        get_simulator_http_client,
        simulator_base_url,
        simulator_ui_url,
    )

    base = simulator_base_url()
    reach_checks: List[Dict[str, Any]] = []
    if not base:
        reach_checks.append({
            "name": "SIMULATOR_BASE_URL",
            "status": "fail",
            "message": "SIMULATOR_BASE_URL is not set",
            "details": {},
        })
    else:
        try:
            client = get_simulator_http_client()
            resp = await client.get(f"{base}/health")
            body = resp.json() if resp.content else {}
            ok = resp.status_code < 400
            reach_checks.append({
                "name": "nexus-simulator /health",
                "status": "pass" if ok else "fail",
                "message": f"HTTP {resp.status_code}",
                "details": {"url": base, "body": body, "uiUrl": simulator_ui_url()},
            })
        except Exception as exc:
            reach_checks.append({
                "name": "nexus-simulator /health",
                "status": "fail",
                "message": str(exc),
                "details": {"url": base},
            })
    sections["s3_source_data"] = {"status": reach_checks[0]["status"], "checks": reach_checks}
    sections["redis_cache_health"] = {
        "status": "pass" if reach_checks[0]["status"] == "pass" else "fail",
        "checks": [{
            "name": "Remote Redis",
            "status": reach_checks[0]["status"],
            "message": "Owned by nexus-simulator; ontology does not inspect Redis",
            "details": {},
        }],
    }

    catalog_checks: List[Dict[str, Any]] = []
    if base:
        try:
            client = get_simulator_http_client()
            resp = await client.get(f"{base}/api/v1/simulators")
            catalog = resp.json() if resp.content else {}
            items = catalog.get("items") or []
            for item in items:
                rows = item.get("total_rows") or item.get("totalRowsHint") or 0
                tables = item.get("table_count") or item.get("tableCount") or 0
                catalog_checks.append({
                    "name": item.get("service") or "unknown",
                    "status": "pass" if rows or tables else "warn",
                    "message": f"{tables} tables, {rows:,} rows",
                    "details": item,
                })
            if not catalog_checks:
                catalog_checks.append({
                    "name": "catalog",
                    "status": "warn",
                    "message": "Simulator catalog returned no services",
                    "details": catalog,
                })
        except Exception as exc:
            catalog_checks.append({
                "name": "catalog",
                "status": "fail",
                "message": str(exc),
                "details": {},
            })
    else:
        catalog_checks.append({
            "name": "catalog",
            "status": "fail",
            "message": "SIMULATOR_BASE_URL is not set",
            "details": {},
        })

    cat_ok = all(c["status"] == "pass" for c in catalog_checks)
    cat_warn = any(c["status"] == "warn" for c in catalog_checks)
    for section in ("data_loading", "ttl_and_refresh", "data_access", "data_volume"):
        sections[section] = {"status": _check_status(cat_ok, cat_warn), "checks": catalog_checks}

    statuses = [s["status"] for s in sections.values()]
    overall = "pass" if all(s == "pass" for s in statuses) else ("fail" if any(s == "fail" for s in statuses) else "warn")
    return {"timestamp": ts, "overall_status": overall, "sections": sections}


# CPQ Solution Diagnostics (Trade CPQ + Sourcing CPQ)
# ==========================================

CPQ_SELL_SOURCE_ENTITIES = [
    {"name": "Quote_Header", "system": "TPM_Simulator", "critical_fields": ["Quote_ID", "Account_ID", "Status", "Total_Net", "Margin_Pct", "Discount_Pct"]},
    {"name": "Quote_Line", "system": "TPM_Simulator", "critical_fields": ["Line_ID", "Quote_ID", "Offering_ID", "Qty", "Unit_Price"]},
    {"name": "Quote_Promotion", "system": "TPM_Simulator", "critical_fields": ["Promo_ID", "Quote_ID", "Campaign_ID", "Mechanic", "Value"]},
    {"name": "Product_Offering", "system": "TPM_Simulator", "critical_fields": ["Offering_ID", "Name", "Type", "Channel_Eligibility", "Status"]},
    {"name": "Offering_Component", "system": "TPM_Simulator", "critical_fields": ["Component_ID", "Offering_ID", "Material_ID", "Qty", "Component_Role"]},
    {"name": "Price_Book", "system": "TPM_Simulator", "critical_fields": ["Price_Book_ID", "Channel_Type", "Tier", "Region", "Status"]},
    {"name": "Price_Book_Entry", "system": "TPM_Simulator", "critical_fields": ["Entry_ID", "Price_Book_ID", "Offering_ID", "List_Price", "Floor_Price"]},
    {"name": "Serviceability_Footprint", "system": "TPM_Simulator", "critical_fields": ["Footprint_ID", "Plant_ID", "Region", "Channel_Type", "SLA_Days"]},
    {"name": "Configuration_Rule", "system": "TPM_Simulator", "critical_fields": ["Rule_ID", "Type", "Expression", "Severity"]},
]

CPQ_BUY_SOURCE_ENTITIES = [
    {"name": "RFx_Event", "system": "Sourcing_Simulator", "critical_fields": ["Event_ID", "Type", "Category", "Status", "Open_Date", "Close_Date"]},
    {"name": "RFx_Line", "system": "Sourcing_Simulator", "critical_fields": ["Line_ID", "Event_ID", "Material_ID", "Qty_Target", "Plant_ID"]},
    {"name": "RFx_Invitation", "system": "Sourcing_Simulator", "critical_fields": ["Invitation_ID", "Event_ID", "Vendor_ID", "Status"]},
    {"name": "Vendor_Quote", "system": "Sourcing_Simulator", "critical_fields": ["Vendor_Quote_ID", "Event_ID", "Vendor_ID", "Total_Value", "Status"]},
    {"name": "Vendor_Quote_Line", "system": "Sourcing_Simulator", "critical_fields": ["Line_ID", "Vendor_Quote_ID", "RFx_Line_ID", "Unit_Price", "Lead_Time_Days"]},
    {"name": "Should_Cost_Model", "system": "Sourcing_Simulator", "critical_fields": ["Model_ID", "Material_ID", "Modeled_Cost", "Confidence"]},
    {"name": "Sourcing_Scenario", "system": "Sourcing_Simulator", "critical_fields": ["Scenario_ID", "Event_ID", "Modeled_Savings", "Modeled_Risk_Score", "Concentration_Pct"]},
    {"name": "Sourcing_Award", "system": "Sourcing_Simulator", "critical_fields": ["Award_ID", "Event_ID", "Scenario_ID", "Status"]},
]

CPQ_SELL_TOOLS = [
    "lookup_material", "create_quote",
    "configure_bundle", "validate_configuration", "check_serviceability",
    "price_quote", "apply_promotion", "check_credit_and_margin",
    "route_approval", "generate_proposal_doc", "convert_quote_to_order",
    "suggest_upsell_crosssell", "forecast_quote_win_probability",
]

CPQ_BUY_TOOLS = [
    "launch_rfx", "recommend_vendor_panel", "solicit_vendors",
    "score_vendor_response", "should_cost_model",
    "run_award_scenario", "recommend_award_split",
    "draft_contract", "convert_award_to_po",
]

CPQ_SELL_WORKFLOWS = [
    "WORKFLOW_QUOTE_CONFIGURE_VALIDATE_V1_0",
    "WORKFLOW_QUOTE_PRICE_CALCULATE_V1_0",
    "WORKFLOW_QUOTE_APPROVAL_ROUTE_V1_0",
    "WORKFLOW_QUOTE_TO_ORDER_V1_0",
]

CPQ_BUY_WORKFLOWS = [
    "WORKFLOW_RFX_LAUNCH_V1_0",
    "WORKFLOW_RFX_BID_EVALUATE_V1_0",
    "WORKFLOW_RFX_AWARD_V1_0",
    "WORKFLOW_CONTRACT_GENERATION_V1_0",
]

CPQ_POLICIES = [
    "cpq-configuration-policy",
    "cpq-quote-approval-policy",
    "sourcing-award-policy",
]


async def _check_cpq_data(entities, rule_map):
    """Run data adequacy + mapping correctness for a CPQ side."""
    adequacy = []
    mapping = []
    quality = []
    vdl_cache = {}
    for spec in entities:
        rows, err = await _vdl_query(spec["name"], limit=200)
        actual = rows if rows else []
        vdl_cache[spec["name"]] = actual
        status = "ok" if len(actual) > 0 else ("error" if err else "no_data")
        adequacy.append({
            "name": spec["name"], "system": spec["system"],
            "rows": len(actual),
            "fields": len(actual[0].keys()) if actual else 0,
            "status": status, "error": err,
        })

        rule = rule_map.get(spec["name"])
        if rule:
            src_table = getattr(rule, "source_table", "")
            src_schema = getattr(rule, "source_schema", "")
            field_maps = getattr(rule, "field_maps", [])
            mapped = sum(1 for fm in field_maps if getattr(fm, "source_field", ""))
            status_val = getattr(rule, "status", None)
            raw_status = status_val.value if hasattr(status_val, "value") else str(status_val)
            mapping.append({
                "entity": spec["name"], "source_schema": src_schema, "source_table": src_table,
                "mapped_fields": mapped, "rule_status": raw_status,
                "status": "ok" if raw_status == "active" else "inactive",
            })
        else:
            mapping.append({
                "entity": spec["name"], "source_schema": "", "source_table": "",
                "mapped_fields": 0, "rule_status": "missing", "status": "missing",
            })

        if actual:
            for field in spec["critical_fields"]:
                total = len(actual)
                null_count = sum(1 for r in actual if r.get(field) is None)
                null_pct = round(null_count / total * 100, 1) if total else 0
                field_present = any(field in r for r in actual)
                if not field_present:
                    status = "fail"
                elif null_pct > 50:
                    status = "fail"
                elif null_pct > 10:
                    status = "warn"
                else:
                    status = "ok"
                quality.append({
                    "entity": spec["name"], "field": field,
                    "total_rows": total, "null_count": null_count, "null_pct": null_pct,
                    "field_present": field_present, "status": status,
                })

    return adequacy, mapping, quality, vdl_cache


def _check_cpq_tools(expected_names, registry_tools):
    """Check that CPQ ReAct tools are registered with correct risk + bucket."""
    by_name = {t.get("name"): t for t in registry_tools}
    checks = []
    for n in expected_names:
        t = by_name.get(n)
        if not t:
            checks.append({"name": n, "registered": False, "status": "fail",
                           "risk": "", "bucket": "", "requires_approval": False})
        else:
            checks.append({
                "name": n, "registered": True,
                "risk": t.get("risk_level", ""),
                "bucket": t.get("bucket", ""),
                "requires_approval": t.get("requires_approval", False),
                "connector_api": t.get("connector_api"),
                "status": "ok",
            })
    return checks


async def _list_registered_tools():
    try:
        from src.apis.control_plane_api import _agent_executor
        if _agent_executor is None:
            return []
        registry = getattr(_agent_executor, "_tools", None)
        if registry is None:
            return []
        tools_list = registry.list_tools()
        tools = []
        for tool in tools_list:
            name = getattr(tool, "name", "")
            risk = tool.risk_level.value if hasattr(tool.risk_level, "value") else str(tool.risk_level)
            tools.append({
                "name": name,
                "risk_level": risk,
                "bucket": getattr(tool, "bucket", None),
                "requires_approval": getattr(tool, "requires_approval", False),
                "connector_api": getattr(tool, "connector_api", None),
            })
        return tools
    except Exception as e:
        logger.warning(f"Failed to list registered tools for CPQ diagnostic: {e}")
        return []


async def _check_workflow_yamls(expected_ids):
    """Check that the named workflow YAML files load and parse cleanly."""
    import os
    import yaml as _yaml
    base = os.path.join(os.environ.get("APP_ROOT", "/app"), "enterprise-knowledge", "workflows")
    if not os.path.exists(base):
        from pathlib import Path
        base = str(Path(__file__).resolve().parent.parent.parent / "enterprise-knowledge" / "workflows")
    found = {}
    if os.path.exists(base):
        for fname in os.listdir(base):
            if not fname.endswith(".yaml"):
                continue
            path = os.path.join(base, fname)
            try:
                with open(path) as f:
                    doc = _yaml.safe_load(f) or {}
                found[doc.get("id")] = {"name": doc.get("name"), "file": fname}
            except Exception:
                pass
    checks = []
    for wid in expected_ids:
        if wid in found:
            checks.append({"id": wid, "name": found[wid]["name"], "file": found[wid]["file"], "status": "ok"})
        else:
            checks.append({"id": wid, "name": "", "file": "", "status": "missing"})
    return checks


@router.post("/cpq")
async def run_cpq_diagnostics() -> Dict[str, Any]:
    """Run comprehensive CPQ diagnostics for Trade CPQ (sell) and Sourcing CPQ (buy).

    Sections: simulator_status, data_adequacy_sell, data_adequacy_buy,
    mapping_correctness, data_quality, tool_registry, workflows, policies.
    """
    ts = datetime.utcnow().isoformat()
    sections: Dict[str, Any] = {}

    # ── 1. Simulator status (tpm + sourcing) ────────────────
    try:
        from src.apis.fdw_api import _simulators
    except Exception:
        _simulators = {}

    sim_checks = []
    for key, label in [("tpm", "TPM Simulator (Trade CPQ)"),
                        ("sourcing", "Sourcing Simulator (Buy CPQ)")]:
        sim = _simulators.get(key)
        if not sim:
            sim_checks.append({"name": label, "key": key, "status": "fail",
                                "message": "simulator not registered", "details": {}})
            continue
        try:
            tables = await sim.list_foreign_tables()
            total_tables = len(tables)
            loaded = getattr(sim, "loaded", True)
            sim_checks.append({
                "name": label, "key": key,
                "status": "pass" if loaded and total_tables > 0 else ("warn" if loaded else "fail"),
                "message": f"{total_tables} tables reachable via nexus-simulator",
                "details": {"loaded": loaded, "tables": total_tables},
            })
        except Exception as e:
            sim_checks.append({"name": label, "key": key, "status": "fail",
                                "message": str(e), "details": {}})
    sim_ok = all(c["status"] == "pass" for c in sim_checks)
    sim_warn = any(c["status"] == "warn" for c in sim_checks)
    sections["simulator_status"] = {
        "status": _check_status(sim_ok, sim_warn),
        "checks": sim_checks,
    }

    # ── 2 + 3. Data adequacy / mapping / quality per side ──
    all_rules = await _get_mapping_rules()
    rule_map = {}
    for r in all_rules:
        ve = r.virtual_entity if hasattr(r, "virtual_entity") else getattr(r, "virtualEntity", "")
        rule_map[ve] = r

    sell_adequacy, sell_mapping, sell_quality, _ = await _check_cpq_data(CPQ_SELL_SOURCE_ENTITIES, rule_map)
    buy_adequacy, buy_mapping, buy_quality, _ = await _check_cpq_data(CPQ_BUY_SOURCE_ENTITIES, rule_map)

    sell_ok = sum(1 for e in sell_adequacy if e["status"] == "ok")
    buy_ok = sum(1 for e in buy_adequacy if e["status"] == "ok")
    sections["data_adequacy_sell"] = {
        "status": _check_status(sell_ok == len(sell_adequacy), 0 < sell_ok < len(sell_adequacy)),
        "entities": sell_adequacy,
        "summary": {"total": len(sell_adequacy), "with_data": sell_ok,
                    "missing": len(sell_adequacy) - sell_ok},
    }
    sections["data_adequacy_buy"] = {
        "status": _check_status(buy_ok == len(buy_adequacy), 0 < buy_ok < len(buy_adequacy)),
        "entities": buy_adequacy,
        "summary": {"total": len(buy_adequacy), "with_data": buy_ok,
                    "missing": len(buy_adequacy) - buy_ok},
    }

    all_mapping = sell_mapping + buy_mapping
    active = sum(1 for m in all_mapping if m["status"] == "ok")
    issues = sum(1 for m in all_mapping if m["status"] != "ok")
    sections["mapping_correctness"] = {
        "status": _check_status(issues == 0, issues > 0 and active > 0),
        "rules": all_mapping,
        "summary": {"total": len(all_mapping), "active": active, "issues": issues},
    }

    all_quality = sell_quality + buy_quality
    q_pass = sum(1 for c in all_quality if c["status"] == "ok")
    q_warn = sum(1 for c in all_quality if c["status"] == "warn")
    q_fail = sum(1 for c in all_quality if c["status"] == "fail")
    sections["data_quality"] = {
        "status": _check_status(q_fail == 0, q_warn > 0),
        "checks": all_quality,
        "summary": {"total_checks": len(all_quality), "passed": q_pass,
                    "warnings": q_warn, "failures": q_fail},
    }

    # ── 4. Tool registry (CPQ tools) ───────────────────────
    registry_tools = await _list_registered_tools()
    sell_tool_checks = _check_cpq_tools(CPQ_SELL_TOOLS, registry_tools)
    buy_tool_checks = _check_cpq_tools(CPQ_BUY_TOOLS, registry_tools)
    tools_all = sell_tool_checks + buy_tool_checks
    tools_ok = sum(1 for t in tools_all if t["status"] == "ok")
    sections["tool_registry"] = {
        "status": _check_status(tools_ok == len(tools_all), tools_ok > 0 and tools_ok < len(tools_all)),
        "sell_tools": sell_tool_checks,
        "buy_tools": buy_tool_checks,
        "summary": {"expected": len(tools_all), "registered": tools_ok,
                    "missing": len(tools_all) - tools_ok},
    }

    # ── 5. Workflows ───────────────────────────────────────
    wf_checks_sell = await _check_workflow_yamls(CPQ_SELL_WORKFLOWS)
    wf_checks_buy = await _check_workflow_yamls(CPQ_BUY_WORKFLOWS)
    wf_all = wf_checks_sell + wf_checks_buy
    wf_ok = sum(1 for w in wf_all if w["status"] == "ok")
    sections["workflows"] = {
        "status": _check_status(wf_ok == len(wf_all), wf_ok > 0 and wf_ok < len(wf_all)),
        "sell_workflows": wf_checks_sell,
        "buy_workflows": wf_checks_buy,
        "summary": {"expected": len(wf_all), "present": wf_ok,
                    "missing": len(wf_all) - wf_ok},
    }

    # ── 6. Policies ────────────────────────────────────────
    # Phase 3 (data-organization spec): DynamoDB is authoritative. Ask
    # OntoDataService for the current policy inventory rather than
    # stat-ing enterprise-knowledge/policies/ on disk.
    policy_checks = []
    try:
        from src.services.onto_data_service import OntoDataService as _OntoDataService
        _onto = _OntoDataService()
        _rows = _onto.list_files("policies") or []
        _size_by_slug: dict = {}
        _slugs_present: set = set()
        for r in _rows:
            _fname = str(r.get("filename") or "")
            _slug = _fname.rsplit(".", 1)[0] if _fname else ""
            if _slug:
                _slugs_present.add(_slug)
                _size_by_slug[_slug] = int(r.get("size") or 0)
        for p in CPQ_POLICIES:
            present = p in _slugs_present
            size = _size_by_slug.get(p, 0) if present else 0
            policy_checks.append({
                "id": p,
                "file": f"{p}.md",
                "status": "ok" if present and size > 0 else "missing",
                "size_bytes": size,
            })
    except Exception as _pe:
        # Fall back to a defensive shape so the diagnostic still renders
        # if DDB is unreachable.
        for p in CPQ_POLICIES:
            policy_checks.append({
                "id": p,
                "file": f"{p}.md",
                "status": "missing",
                "size_bytes": 0,
                "error": str(_pe),
            })
    p_ok = sum(1 for c in policy_checks if c["status"] == "ok")
    sections["policies"] = {
        "status": _check_status(p_ok == len(policy_checks), 0 < p_ok < len(policy_checks)),
        "policies": policy_checks,
        "summary": {"expected": len(policy_checks), "present": p_ok,
                    "missing": len(policy_checks) - p_ok},
    }

    statuses = [s["status"] for s in sections.values()]
    overall = "pass" if all(s == "pass" for s in statuses) else ("fail" if any(s == "fail" for s in statuses) else "warn")

    return {"timestamp": ts, "overall_status": overall, "sections": sections}
