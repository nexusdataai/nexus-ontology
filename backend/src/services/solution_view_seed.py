"""
Solution Four Views - first-boot seeder.

Generates the 32 Foundry Views (4 per solution, 8 solutions) plus their
~80 backing Dashboards in DynamoDB and links each set of 4 views to the
matching Solution row, so the sidebar VIEWS section in the Solution shell
renders Monitor / Diagnose / Predict / Outcomes immediately on a fresh
install.

Idempotent: safe to call on every backend startup. Uses deterministic
UIDs derived from the app_id + view archetype + dashboard slug, so re-runs
do not create duplicates.

Usage::

    from src.services.solution_view_seed import ensure_solution_views
    await ensure_solution_views()
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from loguru import logger

from src.services.solution_entity_catalogue import SOLUTION_PREFIXES

seed_logger = logger.bind(component="solution-view-seed")


# ---------------------------------------------------------------------------
# Identifier helpers (deterministic UIDs)
# ---------------------------------------------------------------------------

def _stable_uid(*parts: str) -> str:
    h = hashlib.sha1(":".join(parts).encode("utf-8")).hexdigest()
    return f"sfv-{h[:12]}"


def _dashboard_uid(app_id: str, view_key: str, slug: str) -> str:
    return _stable_uid("dash", app_id, view_key, slug)


def _view_uid(app_id: str, view_key: str) -> str:
    return _stable_uid("view", app_id, view_key)


# ---------------------------------------------------------------------------
# Catalogue: per-solution view structure
# ---------------------------------------------------------------------------

VIEW_KEYS = ("monitor", "diagnose", "predict", "outcomes")
VIEW_LABELS: Dict[str, str] = {
    "monitor": "Monitor",
    "diagnose": "Diagnose",
    "predict": "Predict",
    "outcomes": "Outcomes",
}
VIEW_ICONS: Dict[str, str] = {
    "monitor": "activity",
    "diagnose": "search",
    "predict": "trending-up",
    "outcomes": "check-circle",
}

# Per-solution dashboard titles, taken verbatim from Section 2 of the
# Solution Four Views Expansion plan. Each entry yields 2 dashboards per
# (solution, view) pair.
SOLUTION_DASHBOARD_TITLES: Dict[str, Dict[str, List[str]]] = {
    "order-to-cash": {
        "monitor": ["Today's Exception Queue", "Cash Watchtower"],
        "diagnose": ["Match-Rate Anatomy", "Customer & Product Drill-down"],
        "predict": ["AI Risk Forecast", "Cash-Flow Scenarios"],
        "outcomes": ["Action Centre", "Value Realised"],
    },
    "demand-forecasting": {
        "monitor": ["Forecast Accuracy Today", "Demand Signal Watch"],
        "diagnose": ["Bias Decomposition", "Promo & Event Attribution"],
        "predict": ["Forecast Horizon", "Scenario Lab"],
        "outcomes": ["Plan Adoption", "Bias Reduction Value"],
    },
    "inventory-optimization": {
        "monitor": ["Live Stock Health", "Expiry Watch"],
        "diagnose": ["Multi-Echelon View", "ABC/XYZ Slice"],
        "predict": ["Reorder Recommender", "Disruption Stress-Test"],
        "outcomes": ["Action Replay", "Working Capital Released"],
    },
    "procurement-analytics": {
        "monitor": ["3-Way Match Centre", "Maverick Spend Today"],
        "diagnose": ["Spend Cube", "Vendor Concentration"],
        "predict": ["Price Forecast", "Vendor Risk Predict"],
        "outcomes": ["Savings Tracker", "Auto-Approval Audit"],
    },
    "production-quality": {
        "monitor": ["Live OEE", "Quality Reject Wall"],
        "diagnose": ["Defect Pareto", "Yield Loss Tree"],
        "predict": ["Predictive Maintenance", "Yield Forecast"],
        "outcomes": ["CAPA Tracker", "Throughput Gain"],
    },
    "supply-chain-risk": {
        "monitor": ["Disruption Live Map", "Risk Score Movers"],
        "diagnose": ["Concentration & Single-Source", "OTD Root Cause"],
        "predict": ["Disruption Forecast", "Tier-N Stress Test"],
        "outcomes": ["Mitigation Playbook", "Avoided Loss"],
    },
    "customer-360": {
        "monitor": ["Customer Health Today", "Revenue at Risk"],
        "diagnose": ["Segment Performance", "Funnel & Conversion"],
        "predict": ["Churn & Upsell Predict", "Next-Best-Action"],
        "outcomes": ["Campaign ROI", "Retention Wins"],
    },
    "esg-sustainability": {
        "monitor": ["Live Emissions Pulse", "Compliance Status"],
        "diagnose": ["Footprint Decomposition", "Material & Supplier ESG"],
        "predict": ["Pathway to Target", "Carbon Cost Forecast"],
        "outcomes": ["Initiative Tracker", "Reporting Pack"],
    },
}

# Solution-specific view names per Section 2 of the plan
SOLUTION_VIEW_NAMES: Dict[str, Dict[str, str]] = {
    "order-to-cash": {
        "monitor": "O2C Monitor", "diagnose": "O2C Diagnose",
        "predict": "O2C Predict", "outcomes": "O2C Act & Outcomes",
    },
    "demand-forecasting": {
        "monitor": "Demand Monitor", "diagnose": "Demand Diagnose",
        "predict": "Demand Predict", "outcomes": "Forecast Outcomes",
    },
    "inventory-optimization": {
        "monitor": "Inventory Monitor", "diagnose": "Inventory Diagnose",
        "predict": "Inventory Predict", "outcomes": "Inventory Outcomes",
    },
    "procurement-analytics": {
        "monitor": "Procurement Monitor", "diagnose": "Procurement Diagnose",
        "predict": "Procurement Predict", "outcomes": "Procurement Outcomes",
    },
    "production-quality": {
        "monitor": "Shop-floor Monitor", "diagnose": "Quality Diagnose",
        "predict": "Production Predict", "outcomes": "Production Outcomes",
    },
    "supply-chain-risk": {
        "monitor": "Risk Monitor", "diagnose": "Risk Diagnose",
        "predict": "Risk Predict", "outcomes": "Risk Outcomes",
    },
    "customer-360": {
        "monitor": "Customer Monitor", "diagnose": "Customer Diagnose",
        "predict": "Customer Predict", "outcomes": "Customer Outcomes",
    },
    "esg-sustainability": {
        "monitor": "ESG Monitor", "diagnose": "ESG Diagnose",
        "predict": "ESG Predict", "outcomes": "ESG Outcomes",
    },
}


def _solution_view_name(app_id: str, view_key: str) -> str:
    return (SOLUTION_VIEW_NAMES.get(app_id, {}).get(view_key)
            or f"{SOLUTION_PREFIXES.get(app_id, app_id)} {VIEW_LABELS[view_key]}")


def _solution_dashboard_titles(app_id: str, view_key: str) -> List[str]:
    return SOLUTION_DASHBOARD_TITLES.get(app_id, {}).get(view_key, [])


def _kpi_card_panels(prefix: str, kpis: List[Dict[str, Any]], y: int = 0) -> List[Dict[str, Any]]:
    panels: List[Dict[str, Any]] = []
    for i, kpi in enumerate(kpis):
        panels.append({
            "id": i + 1,
            "type": "kpi-card",
            "title": kpi["title"],
            "gridPos": {"x": (i % 4) * 6, "y": y + (i // 4) * 4, "w": 6, "h": 4},
            "datasource": {"type": "vdl", "uid": "vdl-default"},
            "targets": [{
                "refId": "A",
                "entity": f"{prefix}_KPI_Trend",
                "fields": ["value"],
                "filters": [{"field": "kpi", "operator": "eq", "value": kpi["metric"]}],
                "limit": 1,
            }],
            "options": {
                "unit": kpi.get("unit", ""),
                "target": kpi.get("target"),
                "valueField": "value",
            },
            "fieldConfig": {"defaults": {}, "overrides": []},
        })
    return panels


def _alert_panel(prefix: str, x: int = 0, y: int = 8, w: int = 12, h: int = 8) -> Dict[str, Any]:
    return {
        "id": 100,
        "type": "alert-list",
        "title": "Active Alerts",
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "vdl", "uid": "vdl-default"},
        "targets": [{"refId": "A", "entity": f"{prefix}_Alert", "limit": 50}],
        "options": {},
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


def _table_panel(panel_id: int, title: str, entity: str, columns: List[str],
                  x: int = 0, y: int = 8, w: int = 12, h: int = 10,
                  order_by: Optional[str] = None) -> Dict[str, Any]:
    target: Dict[str, Any] = {
        "refId": "A", "entity": entity, "fields": columns, "limit": 50,
    }
    if order_by:
        target["orderBy"] = order_by
    return {
        "id": panel_id, "type": "table", "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "vdl", "uid": "vdl-default"},
        "targets": [target],
        # Frontend TablePanel reads options.columns; pass the visible column
        # set explicitly so the order matches the seeder's intent.
        "options": {"columns": list(columns)},
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


def _bar_panel(panel_id: int, title: str, entity: str, group_by: str, value_field: str,
               x: int = 0, y: int = 8, w: int = 12, h: int = 8) -> Dict[str, Any]:
    # Fields MUST include the group_by column - otherwise the backend
    # returns rows that lack it and the bar chart's xKey resolves to
    # undefined.
    fields = [group_by, value_field] if group_by != value_field else [value_field]
    return {
        "id": panel_id, "type": "bar-chart", "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "vdl", "uid": "vdl-default"},
        "targets": [{
            "refId": "A", "entity": entity, "fields": fields,
            "groupBy": [group_by],
            "aggregation": {"function": "sum", "field": value_field},
            "limit": 200,
        }],
        "options": {
            "xKey": group_by,
            "yKey": "value",
            "color": "#3b82f6",
        },
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


def _line_panel(panel_id: int, title: str, entity: str, group_by: Optional[str] = None,
                 x: int = 0, y: int = 8, w: int = 12, h: int = 8,
                 value_field: str = "value") -> Dict[str, Any]:
    fields = [value_field]
    if group_by and group_by not in fields:
        fields.insert(0, group_by)
    target: Dict[str, Any] = {
        "refId": "A", "entity": entity, "fields": fields,
        "aggregation": {"function": "avg", "field": value_field},
        "limit": 5000,
    }
    if group_by:
        target["groupBy"] = [group_by]
    return {
        "id": panel_id, "type": "time-series", "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "vdl", "uid": "vdl-default"},
        "targets": [target],
        "options": {
            "drawStyle": "line",
            "fillOpacity": 0,
            "stacking": "none",
            "showLegend": True,
            "xKey": "timestamp",
        },
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


def _heatmap_panel(panel_id: int, title: str, entity: str, x_field: str, y_field: str,
                    x: int = 0, y: int = 8, w: int = 12, h: int = 10,
                    value_field: str = "value") -> Dict[str, Any]:
    fields = [x_field, y_field]
    if value_field not in fields:
        fields.append(value_field)
    return {
        "id": panel_id, "type": "heatmap", "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "vdl", "uid": "vdl-default"},
        "targets": [{
            "refId": "A", "entity": entity, "fields": fields,
            "groupBy": [x_field, y_field],
            "aggregation": {"function": "avg", "field": value_field},
            "limit": 1000,
        }],
        "options": {
            "xKey": x_field,
            "yKey": y_field,
            "valueKey": "value",
            "colorScheme": "blues",
            "cellGap": 1,
            "showTooltip": True,
        },
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


def _state_timeline_panel(panel_id: int, title: str, entity: str, group_by: str,
                           x: int = 0, y: int = 8, w: int = 24, h: int = 8) -> Dict[str, Any]:
    return {
        "id": panel_id, "type": "state-timeline", "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "vdl", "uid": "vdl-default"},
        "targets": [{
            "refId": "A", "entity": entity, "fields": ["value"],
            "groupBy": [group_by], "limit": 5000,
        }],
        "options": {
            "showValue": "auto",
            "rowHeight": 28,
        },
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


# Per-solution KPI catalogue used for KPI tiles and trend lines.
_SOLUTION_KPIS: Dict[str, List[Dict[str, Any]]] = {
    "O2C": [
        {"metric": "o2c_dso", "title": "DSO", "unit": "days", "target": 35},
        {"metric": "o2c_match_rate", "title": "Match Rate", "unit": "%", "target": 95},
        {"metric": "o2c_leakage_rate", "title": "Leakage", "unit": "%", "target": 0.5},
        {"metric": "o2c_open_ar", "title": "Open AR", "unit": "$"},
    ],
    "DF": [
        {"metric": "df_mape", "title": "MAPE", "unit": "%", "target": 15},
        {"metric": "df_bias", "title": "Bias", "unit": "%", "target": 3},
        {"metric": "df_stockout_rate", "title": "Stockout Rate", "unit": "%", "target": 2},
        {"metric": "df_promo_lift_accuracy", "title": "Promo Lift Acc.", "unit": "%"},
    ],
    "IO": [
        {"metric": "io_turns", "title": "Turns", "unit": "x", "target": 12},
        {"metric": "io_fill_rate", "title": "Fill Rate", "unit": "%", "target": 97},
        {"metric": "io_expiry_rate", "title": "Expiry %", "unit": "%", "target": 1},
        {"metric": "io_doh", "title": "DOH", "unit": "days"},
    ],
    "PA": [
        {"metric": "pa_maverick_rate", "title": "Maverick", "unit": "%", "target": 5},
        {"metric": "pa_stp_rate", "title": "STP Rate", "unit": "%", "target": 80},
        {"metric": "pa_price_variance", "title": "Price Variance", "unit": "%", "target": 3},
        {"metric": "pa_cycle_time", "title": "PR-PO Cycle", "unit": "days"},
    ],
    "PQ": [
        {"metric": "pq_oee", "title": "OEE", "unit": "%", "target": 85},
        {"metric": "pq_yield", "title": "Yield", "unit": "%", "target": 98},
        {"metric": "pq_first_pass", "title": "First Pass", "unit": "%", "target": 95},
        {"metric": "pq_downtime_minutes", "title": "Downtime", "unit": "min"},
    ],
    "SCR": [
        {"metric": "scr_risk_score", "title": "Risk Score", "unit": "", "target": 30},
        {"metric": "scr_otd_rate", "title": "OTD", "unit": "%", "target": 95},
        {"metric": "scr_early_warning_days", "title": "Early Warning", "unit": "days"},
    ],
    "C360": [
        {"metric": "c360_churn_rate", "title": "Churn Rate", "unit": "%", "target": 5},
        {"metric": "c360_wallet_share", "title": "Wallet Share", "unit": "%", "target": 60},
        {"metric": "c360_clv", "title": "CLV", "unit": "$"},
        {"metric": "c360_health_score", "title": "Health", "unit": ""},
    ],
    "ESG": [
        {"metric": "esg_co2_intensity", "title": "CO2 Intensity", "unit": "t/$"},
        {"metric": "esg_water_ratio", "title": "Water Ratio", "unit": "L/$", "target": 2},
        {"metric": "esg_recycled_pct", "title": "Recycled", "unit": "%", "target": 80},
        {"metric": "esg_renewable_pct", "title": "Renewable", "unit": "%"},
    ],
}


# ---------------------------------------------------------------------------
# Dashboard payload builders
# ---------------------------------------------------------------------------

def _solution_meta(app_id: str) -> Dict[str, Any]:
    prefix = SOLUTION_PREFIXES[app_id]
    return {"app_id": app_id, "prefix": prefix, "kpis": _SOLUTION_KPIS.get(prefix, [])}


def _build_monitor_dashboards(app_id: str) -> List[Dict[str, Any]]:
    meta = _solution_meta(app_id)
    prefix = meta["prefix"]
    kpis = meta["kpis"]
    titles = _solution_dashboard_titles(app_id, "monitor") or ["Snapshot", "Exception Queue"]
    primary = {
        "uid": _dashboard_uid(app_id, "monitor", "primary"),
        "title": titles[0],
        "description": f"Real-time KPIs and active alerts for {app_id}",
        "tags": ["four-views", "monitor", app_id],
        "panels": _kpi_card_panels(prefix, kpis, y=0) + [
            _alert_panel(prefix, x=0, y=8, w=12, h=10),
            _line_panel(101, "KPI Trend (7d)", f"{prefix}_KPI_Trend", group_by="kpi",
                         x=12, y=8, w=12, h=10),
        ],
    }
    secondary = {
        "uid": _dashboard_uid(app_id, "monitor", "exceptions"),
        "title": titles[1] if len(titles) > 1 else "Exception Queue",
        "description": "Items breaching SLA / requiring attention",
        "tags": ["four-views", "monitor", app_id],
        "panels": [
            _table_panel(1, "Top Risk Items", f"{prefix}_Anomaly_Score",
                         columns=["entity_id", "entity_type", "value", "timestamp"],
                         x=0, y=0, w=24, h=12),
            _line_panel(2, "Anomaly Score Trend", f"{prefix}_Anomaly_Score",
                         group_by="entity_type", x=0, y=12, w=24, h=8),
        ],
    }
    return [primary, secondary]


def _build_diagnose_dashboards(app_id: str) -> List[Dict[str, Any]]:
    prefix = SOLUTION_PREFIXES[app_id]
    titles = _solution_dashboard_titles(app_id, "diagnose") or ["Slice", "Drill-Down"]
    primary = {
        "uid": _dashboard_uid(app_id, "diagnose", "slice"),
        "title": titles[0],
        "description": "Cross-dimension breakdowns",
        "tags": ["four-views", "diagnose", app_id],
        "panels": [
            _bar_panel(1, "Cohort Breakdown", f"{prefix}_Cohort_Summary",
                       group_by="dimension_value", value_field="metric_value",
                       x=0, y=0, w=12, h=8),
            _heatmap_panel(2, "Dimension x Metric Heatmap", f"{prefix}_Cohort_Summary",
                           x_field="dimension", y_field="metric_name",
                           value_field="metric_value", x=12, y=0, w=12, h=8),
            _table_panel(3, "Top Cohorts", f"{prefix}_Cohort_Summary",
                         columns=["dimension", "dimension_value", "metric_name", "metric_value"],
                         x=0, y=8, w=24, h=10),
        ],
    }
    secondary = {
        "uid": _dashboard_uid(app_id, "diagnose", "drilldown"),
        "title": titles[1] if len(titles) > 1 else "Drill-Down",
        "description": "Drill into individual entities",
        "tags": ["four-views", "diagnose", app_id],
        "panels": [
            _line_panel(1, "Anomaly Trend", f"{prefix}_Anomaly_Score",
                         group_by="entity_type", x=0, y=0, w=24, h=10),
            _table_panel(2, "Recent Anomalies", f"{prefix}_Anomaly_Score",
                         columns=["entity_id", "entity_type", "value", "timestamp"],
                         x=0, y=10, w=24, h=10),
        ],
    }
    return [primary, secondary]


def _build_predict_dashboards(app_id: str) -> List[Dict[str, Any]]:
    prefix = SOLUTION_PREFIXES[app_id]
    titles = _solution_dashboard_titles(app_id, "predict") or ["Forecast", "Scenarios"]
    primary = {
        "uid": _dashboard_uid(app_id, "predict", "forecast"),
        "title": titles[0],
        "description": "13-week point + interval forecasts",
        "tags": ["four-views", "predict", app_id],
        "panels": [
            _line_panel(1, "KPI Forecast (13w)", f"{prefix}_KPI_Trend", group_by="kpi",
                         x=0, y=0, w=24, h=10),
            _table_panel(2, "Forecast Detail", f"{prefix}_Forecast_Result",
                         columns=["kpi_name", "horizon_period", "point_value", "lower_80", "upper_80", "model"],
                         order_by="created_at DESC", x=0, y=10, w=24, h=10),
        ],
    }
    secondary = {
        "uid": _dashboard_uid(app_id, "predict", "scenarios"),
        "title": titles[1] if len(titles) > 1 else "Scenarios",
        "description": "What-if scenario outputs",
        "tags": ["four-views", "predict", app_id],
        "panels": [
            _bar_panel(1, "Scenario Delta", f"{prefix}_Scenario_Result",
                       group_by="lever", value_field="delta_pct", x=0, y=0, w=12, h=8),
            _table_panel(2, "Scenario Detail", f"{prefix}_Scenario_Result",
                         columns=["name", "lever", "kpi_name", "baseline_value", "scenario_value", "delta_pct"],
                         x=12, y=0, w=12, h=8),
        ],
    }
    return [primary, secondary]


def _build_outcomes_dashboards(app_id: str) -> List[Dict[str, Any]]:
    prefix = SOLUTION_PREFIXES[app_id]
    titles = _solution_dashboard_titles(app_id, "outcomes") or ["Action Centre", "Value Realised"]
    primary = {
        "uid": _dashboard_uid(app_id, "outcomes", "actions"),
        "title": titles[0],
        "description": "Workflow actions and current status",
        "tags": ["four-views", "outcomes", app_id],
        "panels": [
            _bar_panel(1, "Actions by Type", f"{prefix}_Action_Log",
                       group_by="action_type", value_field="action_id",
                       x=0, y=0, w=12, h=8),
            _table_panel(2, "Recent Actions", f"{prefix}_Action_Log",
                         columns=["action_id", "action_type", "target_id", "status", "taken_at"],
                         order_by="taken_at DESC", x=12, y=0, w=12, h=8),
        ],
    }
    secondary = {
        "uid": _dashboard_uid(app_id, "outcomes", "value"),
        "title": titles[1] if len(titles) > 1 else "Value Realised",
        "description": "Before-vs-after KPI deltas + audit trail",
        "tags": ["four-views", "outcomes", app_id],
        "panels": [
            _bar_panel(1, "Delta by KPI", f"{prefix}_Outcome_Tracker",
                       group_by="kpi_name", value_field="delta_value",
                       x=0, y=0, w=12, h=8),
            _table_panel(2, "Audit Trail", f"{prefix}_Audit_Event",
                         columns=["event_id", "actor", "verb", "target", "event_ts"],
                         order_by="event_ts DESC", x=12, y=0, w=12, h=8),
            _table_panel(3, "Outcomes", f"{prefix}_Outcome_Tracker",
                         columns=["action_id", "kpi_name", "kpi_before", "kpi_after", "delta_value"],
                         x=0, y=8, w=24, h=8),
        ],
    }
    return [primary, secondary]


_DASHBOARD_BUILDERS = {
    "monitor": _build_monitor_dashboards,
    "diagnose": _build_diagnose_dashboards,
    "predict": _build_predict_dashboards,
    "outcomes": _build_outcomes_dashboards,
}


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------


def _has_stale_panel_targets(dashboard: Dict[str, Any]) -> bool:
    """
    Returns True if any panel in the saved dashboard has shape problems
    that the frontend can't render:

    * a target with ``aggregation`` as a string instead of a structured
      ``{function, field}`` object;
    * a panel missing the ``options`` field, which TablePanel /
      BarChartPanel / KPICardPanel etc. dereference unconditionally
      (e.g. ``options.columns`` -> ``Cannot read properties of undefined
      (reading 'columns')``).
    * a target whose ``fields`` does NOT include every column listed in
      ``groupBy`` - the backend returns rows missing those columns, so
      the bar/heatmap/line chart's xKey resolves to undefined and the
      panel renders empty.
    """
    for panel in dashboard.get("panels") or []:
        if "options" not in panel or panel.get("options") is None:
            return True
        for tgt in panel.get("targets") or []:
            agg = tgt.get("aggregation")
            if isinstance(agg, str):
                return True
            field_set = set(tgt.get("fields") or [])
            group_by = tgt.get("groupBy") or []
            if field_set and any(g not in field_set for g in group_by):
                return True
    return False


async def _ensure_dashboard(dashboard_service, payload: Dict[str, Any]) -> Optional[str]:
    uid = payload["uid"]
    try:
        existing = await dashboard_service.get(uid)
    except Exception:
        existing = None

    full = dict(payload)
    if "time" not in full:
        full["time"] = {"from": "now-7d", "to": "now"}
    if "refresh" not in full:
        full["refresh"] = "5m"
    if "variables" not in full:
        full["variables"] = []

    if existing:
        # Migrate stale dashboards in-place. We only rewrite the seeded ones
        # (their tags include "four-views"); user-edited dashboards with the
        # same uid would never collide because UIDs are deterministic hashes
        # only generated by this seeder.
        is_stale = _has_stale_panel_targets(existing) or "four-views" not in (existing.get("tags") or [])
        if not is_stale:
            return uid
        try:
            # version=0 in the payload tells DashboardService to skip the
            # optimistic-concurrency check and bump the version itself.
            full["version"] = 0
            await dashboard_service.update(uid, full, user="four-views-seed")
            seed_logger.info("Migrated stale four-views dashboard {} to new panel schema", uid)
            return uid
        except Exception as e:
            seed_logger.warning("Dashboard migration failed for {}: {}", uid, e)
            return uid  # keep linking even if migration fails

    try:
        full["version"] = 0
        await dashboard_service.create(full, user="four-views-seed")
        return uid
    except Exception as e:
        seed_logger.warning("Dashboard create failed for {}: {}", uid, e)
        return None


async def _ensure_view(view_service, app_id: str, view_key: str,
                        dashboard_uids: List[str]) -> Optional[str]:
    view_id = _view_uid(app_id, view_key)
    try:
        existing = await view_service.get(view_id)
    except Exception:
        existing = None
    if existing:
        return view_id

    tabs = [{
        "tabId": _stable_uid("tab", view_id, str(i)),
        "label": f"Tab {i+1}",
        "dashboardId": uid,
    } for i, uid in enumerate(dashboard_uids) if uid]

    if not tabs:
        seed_logger.warning("No dashboards for view {}/{}, skipping", app_id, view_key)
        return None

    payload = {
        "viewId": view_id,
        "name": _solution_view_name(app_id, view_key),
        "description": f"Auto-seeded {view_key} view for {app_id}",
        "tags": ["four-views", view_key, app_id],
        "tabs": tabs,
    }
    try:
        await view_service.create(payload, user="four-views-seed")
        return view_id
    except Exception as e:
        seed_logger.warning("View create failed for {}/{}: {}", app_id, view_key, e)
        return None


async def _ensure_solution_link(
    solution_service,
    app_id: str,
    view_ids_in_order: List[str],
) -> None:
    try:
        solution = await solution_service.get_by_app_id(app_id)
    except Exception:
        solution = None
    if solution is None:
        try:
            solution = await solution_service.create({
                "appId": app_id,
                "name": f"{SOLUTION_PREFIXES.get(app_id, app_id)} Solution",
                "description": f"Auto-created Solution row for {app_id}",
            }, user="four-views-seed")
        except Exception as e:
            seed_logger.warning("Could not create Solution row for {}: {}", app_id, e)
            return

    solution_id = solution.get("solutionId")
    existing_view_ids = {v.get("viewId") for v in (solution.get("views") or [])}
    for vid in view_ids_in_order:
        if not vid or vid in existing_view_ids:
            continue
        try:
            await solution_service.add_view(solution_id, vid)
        except Exception as e:
            seed_logger.debug("add_view skipped for {} -> {}: {}", solution_id, vid, e)


async def ensure_solution_views(
    dashboard_service: Any = None,
    view_service: Any = None,
    solution_service: Any = None,
    apps: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Idempotently seed dashboards / views / solution links for the
    Four-Views program. Safe to call on every backend startup.
    """
    if dashboard_service is None:
        try:
            from src.apis import dashboard_api
            dashboard_service = getattr(dashboard_api, "_dashboard_service", None)
        except Exception:
            dashboard_service = None
    if view_service is None:
        try:
            from src.apis import view_api
            view_service = getattr(view_api, "_view_service", None)
        except Exception:
            view_service = None
    if solution_service is None:
        try:
            from src.apis import solution_api
            solution_service = getattr(solution_api, "_solution_service", None)
        except Exception:
            solution_service = None
    missing = []
    if dashboard_service is None:
        missing.append("dashboard_service")
    if view_service is None:
        missing.append("view_service")
    if solution_service is None:
        missing.append("solution_service")
    if missing:
        seed_logger.warning(
            "Solution Four Views seed skipped - services not initialised: {}", missing
        )
        return {"status": "skipped", "reason": f"missing: {','.join(missing)}"}

    target_apps = apps or list(SOLUTION_PREFIXES.keys())
    seed_logger.info("Solution Four Views seed starting for {} apps", len(target_apps))
    summary: Dict[str, Any] = {"status": "ok", "apps": {}}

    for app_id in target_apps:
        per_app: Dict[str, Any] = {"dashboards": [], "views": []}
        view_ids: List[str] = []
        for view_key in VIEW_KEYS:
            builder = _DASHBOARD_BUILDERS[view_key]
            payloads = builder(app_id)
            uids: List[str] = []
            for p in payloads:
                uid = await _ensure_dashboard(dashboard_service, p)
                if uid:
                    uids.append(uid)
            per_app["dashboards"].extend(uids)
            view_id = await _ensure_view(view_service, app_id, view_key, uids)
            if view_id:
                per_app["views"].append(view_id)
                view_ids.append(view_id)
        await _ensure_solution_link(solution_service, app_id, view_ids)
        summary["apps"][app_id] = per_app

    seed_logger.info(
        "Solution Four Views seeding done: {} apps, {} views, {} dashboards",
        len(target_apps),
        sum(len(a["views"]) for a in summary["apps"].values()),
        sum(len(a["dashboards"]) for a in summary["apps"].values()),
    )
    return summary
