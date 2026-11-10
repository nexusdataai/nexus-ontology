"""
App Data API

Serves dashboard data for App Catalogue applications from both
S3/Glue (historical) and live VDL (real-time) sources.
Includes a generic widget query endpoint used by the DashboardRenderer.
"""

import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/v1/apps", tags=["App Data"])

_virtual_query_service = None


def configure(vqs):
    global _virtual_query_service
    _virtual_query_service = vqs


class WidgetQueryRequest(BaseModel):
    entity: str
    columns: Optional[List[str]] = None
    aggregation: Optional[str] = None
    groupBy: Optional[str] = None
    orderBy: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = 100


APP_S3_PREFIXES = {
    "order-to-cash": {"kpis": "o2c-kpis", "alerts": "o2c-alerts", "data": "o2c-data"},
    "demand-forecasting": {"kpis": "forecast-kpis", "alerts": "forecast-alerts", "data": "forecast-data"},
    "inventory-optimization": {"kpis": "inventory-kpis", "alerts": "inventory-alerts", "data": "inventory-data"},
}


def _get_latest_s3(prefix: str) -> Optional[dict]:
    try:
        import boto3
        from src.config.config_provider import get_config
        config = get_config()
        bucket = config.s3_recordings_bucket
        if not bucket:
            return None

        s3 = boto3.client("s3")
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=50)
        objects = response.get("Contents", [])
        if not objects:
            return None

        latest = max(objects, key=lambda o: o["LastModified"])
        body = s3.get_object(Bucket=bucket, Key=latest["Key"])["Body"].read()
        return json.loads(body)
    except Exception as e:
        logger.debug(f"S3 read failed for {prefix}: {e}")
        return None


@router.get("/{app_id}/dashboard")
async def get_dashboard(app_id: str):
    prefixes = APP_S3_PREFIXES.get(app_id, {})
    kpis_prefix = prefixes.get("kpis", f"{app_id}-kpis")
    data_prefix = prefixes.get("data", f"{app_id}-data")

    kpis = _get_latest_s3(f"{kpis_prefix}/")
    records_data = _get_latest_s3(f"{data_prefix}/")

    records = []
    if isinstance(records_data, dict):
        records = [records_data]
    elif isinstance(records_data, list):
        records = records_data

    return {
        "app_id": app_id,
        "kpis": kpis or {},
        "records": records[:50],
        "total_records": len(records),
        "source": "s3" if kpis else "empty",
    }


@router.get("/{app_id}/alerts")
async def get_alerts(app_id: str):
    prefixes = APP_S3_PREFIXES.get(app_id, {})
    alerts_prefix = prefixes.get("alerts", f"{app_id}-alerts")

    data = _get_latest_s3(f"{alerts_prefix}/")
    alerts = []
    if isinstance(data, dict):
        alerts = data.get("alerts", [])
    elif isinstance(data, list):
        alerts = data

    return {"app_id": app_id, "alerts": alerts, "total": len(alerts)}


@router.get("/{app_id}/live/{entity}")
async def get_live_entity(app_id: str, entity: str, limit: int = Query(default=10, ge=1, le=100)):
    if not _virtual_query_service:
        return {"entity": entity, "rows": [], "total": 0, "error": "VDL not available"}

    try:
        from src.models.mapping_rule_models import VirtualQueryRequest
        req = VirtualQueryRequest(virtual_entity=entity, limit=limit)
        resp = await _virtual_query_service.query_virtual_entity(req)
        return {"entity": entity, "rows": resp.rows[:limit], "total": len(resp.rows)}
    except Exception as e:
        return {"entity": entity, "rows": [], "total": 0, "error": str(e)}


@router.post("/{app_id}/query")
async def widget_query(app_id: str, req: WidgetQueryRequest):
    """Generic widget data endpoint. Routes to VDL (simulator or Athena) based on mapping rule source type."""
    if not _virtual_query_service:
        return {"rows": [], "total": 0, "error": "VDL not available"}

    try:
        from src.models.mapping_rule_models import VirtualQueryRequest as VQR, VirtualFilter

        filters_list = None
        if req.filters:
            filters_list = [VirtualFilter(field=k, operator="eq", value=v) for k, v in req.filters.items()]

        # An aggregate must see every row, not the first `limit` rows: the
        # limit applies to the aggregated result instead.
        read_limit = 10000 if req.aggregation else req.limit
        vq = VQR(virtual_entity=req.entity, fields=req.columns, filters=filters_list, limit=read_limit)
        resp = await _virtual_query_service.query_virtual_entity(vq)
        rows = resp.rows

        if req.aggregation and req.groupBy:
            rows = _aggregate(rows, column=req.columns[0] if req.columns else None,
                              aggregation=req.aggregation, group_by=req.groupBy)
        elif req.aggregation:
            # No group: one row with the figure under the requested column,
            # which is how KPI widgets read it (rows[0][columns[0]]).
            rows = [_aggregate_all(rows, column=req.columns[0] if req.columns else None,
                                   aggregation=req.aggregation)]

        if req.orderBy:
            desc = False
            order_field = req.orderBy
            if " DESC" in req.orderBy.upper():
                desc = True
                order_field = req.orderBy.replace(" DESC", "").replace(" desc", "").strip()
            elif " ASC" in req.orderBy.upper():
                order_field = req.orderBy.replace(" ASC", "").replace(" asc", "").strip()
            rows = sorted(rows, key=lambda r: _sort_key(r.get(order_field)), reverse=desc)

        if req.limit and len(rows) > req.limit:
            rows = rows[:req.limit]

        return {
            "entity": req.entity,
            "rows": rows,
            "total": len(rows),
            "source": resp.metadata.get("source_type", "unknown") if resp.metadata else "unknown",
        }
    except Exception as e:
        logger.warning(f"Widget query failed for {req.entity}: {e}")
        return {"rows": [], "total": 0, "error": str(e)}


def _sort_key(val):
    if val is None:
        return 0
    try:
        return float(val)
    except (ValueError, TypeError):
        return str(val)


def _aggregate_all(rows: List[Dict], column: Optional[str], aggregation: str) -> Dict:
    agg = aggregation.lower()
    key = column or "value"
    if agg == "count" or not column:
        return {key: len(rows)}
    vals = []
    for r in rows:
        try:
            v = r.get(column)
            if v is not None and v != "":
                vals.append(float(v))
        except (ValueError, TypeError):
            pass
    if not vals:
        return {key: None}
    if agg == "sum":
        return {key: sum(vals)}
    if agg == "min":
        return {key: min(vals)}
    if agg == "max":
        return {key: max(vals)}
    return {key: sum(vals) / len(vals)}


def _aggregate(rows: List[Dict], column: Optional[str], aggregation: str, group_by: str) -> List[Dict]:
    groups: Dict[str, list] = {}
    for row in rows:
        key = str(row.get(group_by, "unknown"))
        groups.setdefault(key, []).append(row)

    agg = aggregation.lower()
    result = []
    for key, group_rows in groups.items():
        if agg == "count":
            result.append({group_by: key, "value": len(group_rows)})
        elif agg in ("sum", "avg") and column:
            vals = []
            for r in group_rows:
                try:
                    vals.append(float(r.get(column, 0)))
                except (ValueError, TypeError):
                    pass
            total = sum(vals)
            result.append({group_by: key, "value": total if agg == "sum" else (total / len(vals) if vals else 0)})
        else:
            result.append({group_by: key, "value": len(group_rows)})

    return result
