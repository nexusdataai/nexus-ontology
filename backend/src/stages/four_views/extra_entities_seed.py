"""
Seed solution-specific result entities the FourViewsProcessor doesn't write.

The FourViewsProcessor produces a generic set of archetypes per solution
(``Action_Log``, ``Forecast_Result``, ``Scenario_Result``, ``Outcome_Tracker``,
``Audit_Event``, ``Cohort_Summary``, ``Alert``, ``KPI_Trend``,
``Anomaly_Score``). The catalogue declares additional solution-specific
entities (``C360_Campaign_ROI``, ``PA_Match_Result``, ``PQ_Yield_Loss``,
etc.) that have a mapping rule but no producer - so dashboards that point
at them stay empty and the Virtual Data Diagnostic flags them as
``source_table_present: fail``.

This module fills the gap with deterministic plausible synthetic rows
derived from each entity's declared ``columns`` schema. Idempotent: skips
any entity that already has rows in the simulator.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.services.solution_entity_catalogue import CATALOGUE, SOLUTION_PREFIXES

extra_logger = logger.bind(component="extra-entities-seed")


# Entities the FourViewsProcessor already writes; we skip them here.
PROCESSOR_WRITTEN_ARCHETYPES = {
    "Action_Log", "Forecast_Result", "Scenario_Result",
    "Outcome_Tracker", "Audit_Event", "Cohort_Summary",
    "Alert", "KPI_Trend", "Anomaly_Score",
}


def _is_processor_archetype(virtual_entity: str) -> bool:
    """Return True if FourViewsProcessor already writes ``virtual_entity``."""
    for archetype in PROCESSOR_WRITTEN_ARCHETYPES:
        if virtual_entity.endswith("_" + archetype):
            return True
    return False


def _isoformat(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Column-name driven value synthesis.
# ---------------------------------------------------------------------------

def _synth_value(column: str, rng: random.Random, prefix: str, idx: int) -> Any:
    """Pick a plausible value based on column name conventions."""
    c = column.lower()
    now = _now()

    if c.endswith("_id") or c == "id":
        # Tag the id with the prefix for traceability.
        token = c[:-3] if c.endswith("_id") else c
        return f"{prefix}-{token.upper()}-{idx:03d}"
    if c == "value" or c.endswith("_value"):
        return round(rng.uniform(10.0, 1000.0), 3)
    if c == "timestamp":
        return int(now.timestamp() * 1000)
    if c.endswith("_at") or c.endswith("_ts") or c == "event_ts" or c == "rolled_up_at":
        return _isoformat(now - timedelta(minutes=rng.randint(1, 600)))
    if c.endswith("_pct"):
        return round(rng.uniform(0.0, 1.0) * 100, 2)
    if c == "probability" or c.endswith("_probability"):
        return round(rng.uniform(0.05, 0.45), 3)
    if c.endswith("_qty"):
        return rng.randint(0, 5000)
    if c.endswith("_amount") or c == "spend" or c.endswith("_amount_usd"):
        return round(rng.uniform(1000.0, 250_000.0), 2)
    if c.endswith("_count") or c == "count":
        return rng.randint(1, 500)
    if c == "currency":
        return "USD"
    if c == "status":
        return rng.choice(["open", "in_progress", "resolved", "closed"])
    if c == "severity":
        return rng.choice(["low", "medium", "high"])
    if c == "stage":
        return rng.choice(["Prospect", "Qualified", "Proposal", "Negotiation", "Won"])
    if c == "region":
        return rng.choice(["North", "South", "East", "West", "Central"])
    if c == "category":
        return rng.choice(["Beverages", "Snacks", "Dairy", "Frozen", "Personal Care"])
    if c == "model":
        return rng.choice(["linear_seasonal_v1", "ensemble_v2", "lstm_v3"])
    if c == "kpi" or c == "kpi_name" or c == "metric_name":
        return rng.choice([f"{prefix.lower()}_kpi_{i}" for i in range(1, 6)])
    if c == "horizon_period":
        target = now + timedelta(weeks=rng.randint(1, 12))
        return target.strftime("%Y-W%U")
    if c == "month" or c == "period":
        target = now - timedelta(days=rng.randint(1, 365))
        return target.strftime("%Y-%m")
    if c.endswith("_pct"):
        return round(rng.uniform(0.0, 100.0), 2)
    if c == "dimension":
        return rng.choice(["region", "segment", "channel"])
    if c == "dimension_value":
        return rng.choice(["North", "Enterprise", "Direct", "Wholesale"])
    if c == "lever":
        return rng.choice(["aggressive", "conservative", "baseline"])
    if c == "verb":
        return rng.choice(["create", "update", "execute", "approve"])
    if c == "actor":
        return rng.choice(["system", "user:alice", "user:bob", "agent"])
    if c == "payload":
        return rng.choice(["campaign:launch", "rule:apply", "task:complete"])
    if c == "target":
        return f"{prefix}-T-{rng.randint(1, 999):03d}"
    if c == "name" or c == "title":
        return f"{prefix} item {idx + 1}"
    if c == "notes" or c == "message" or c == "reason":
        return f"Auto-generated demo row {idx + 1} for {prefix}"
    if c == "root_cause":
        return rng.choice(["material_defect", "tooling_wear", "operator_error", "spec_drift"])
    if c == "match_status":
        return rng.choice(["matched", "price_variance", "qty_variance", "missing_gr"])
    if c == "recommended_action":
        return rng.choice(["engage_csm", "send_promo", "schedule_qbr", "monitor"])
    if c == "expected_uplift_usd" or c == "expected_revenue_loss" or c == "expected_impact_usd":
        return round(rng.uniform(5_000.0, 250_000.0), 2)
    if c == "delta_value" or c == "delta":
        return round(rng.uniform(-100.0, 100.0), 3)
    if c == "lift_pct" or c == "uplift_units":
        if c == "lift_pct":
            return round(rng.uniform(-3.0, 25.0), 2)
        return rng.randint(50, 5000)
    if c == "attributed_revenue":
        return round(rng.uniform(5_000.0, 200_000.0), 2)
    if c == "active_vendor_count":
        return rng.randint(1, 4)
    if c == "doh":
        return rng.randint(2, 60)
    if c == "expiry_30d_qty":
        return rng.randint(0, 800)
    if c == "leakage_pct":
        return round(rng.uniform(0.5, 18.0), 2)
    if c == "leakage_amount":
        return round(rng.uniform(5_000.0, 90_000.0), 2)
    if c == "predicted_failure_date" or c == "predicted_yield_pct":
        if c == "predicted_failure_date":
            return _isoformat(now + timedelta(days=rng.randint(7, 90)))
        return round(rng.uniform(85.0, 99.0), 2)
    if c == "loss_pct":
        return round(rng.uniform(0.5, 12.0), 2)
    if c == "lower_80" or c == "upper_80":
        v = rng.uniform(50.0, 100.0)
        return round(v if c == "upper_80" else v - rng.uniform(5.0, 30.0), 3)
    if c == "point_value":
        return round(rng.uniform(40.0, 120.0), 3)
    if c == "spend":
        return round(rng.uniform(5_000.0, 250_000.0), 2)
    if c == "realised_revenue":
        return round(rng.uniform(5_000.0, 400_000.0), 2)
    if c == "roi_pct":
        return round(rng.uniform(-15.0, 60.0), 2)
    if c == "churn_probability":
        return round(rng.uniform(0.05, 0.45), 3)
    if c == "scenario_value" or c == "baseline_value":
        return round(rng.uniform(40.0, 130.0), 3)
    if c == "delta_pct":
        return round(rng.uniform(-15.0, 25.0), 2)
    if c == "scenario_id":
        return f"SC-{prefix}-{idx:03d}"
    if c == "outcome_id":
        return str(uuid.uuid4())
    if c == "kpi_before" or c == "kpi_after":
        return round(rng.uniform(40.0, 110.0), 3)
    if c == "measured_at":
        return _isoformat(now)
    # Fallback: a string token derived from the column name.
    return f"{column}-{idx+1}"


def _entities_for_prefix(prefix: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Catalogue entries that belong to ``prefix`` AND we should seed.

    Skips:
      - storage=MIMIR (handled via the metric pipeline)
      - archetype names already produced by FourViewsProcessor
    """
    out: List[Tuple[str, Dict[str, Any]]] = []
    for name, spec in CATALOGUE.items():
        if not name.startswith(f"{prefix}_"):
            continue
        if spec.get("storage") == "MIMIR":
            continue
        if _is_processor_archetype(name):
            continue
        out.append((name, spec))
    return out


def _generate_rows_for(virtual_entity: str, spec: Dict[str, Any],
                       prefix: str, count: int = 12) -> List[Dict[str, Any]]:
    """Build ``count`` synthetic rows shaped by the catalogue's column list."""
    columns = [c[0] for c in spec.get("columns") or []]
    if not columns:
        # Catalogue declared no columns - emit a tiny stub row so the
        # table at least registers in the simulator.
        return [{"id": f"{prefix}-{virtual_entity}-001", "created_at": _isoformat(_now())}]

    rng = random.Random(hash(virtual_entity) & 0xFFFFFFFF)
    rows: List[Dict[str, Any]] = []
    for i in range(count):
        row: Dict[str, Any] = {}
        for col in columns:
            row[col] = _synth_value(col, rng, prefix, i)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def _table_already_populated(sim: Any, schema: str, table: str) -> bool:
    if sim is None:
        return False
    try:
        if hasattr(sim, "_get_table_row_count"):
            count = await sim._get_table_row_count(schema, table)
            if count and count > 0:
                return True
        if hasattr(sim, "_get_table_data"):
            rows = await sim._get_table_data(schema, table)
            if rows:
                return True
    except Exception:
        return False
    return False


async def seed_extra_entities(
    prefix: str,
    sink: Any,
    sim: Any,
    schema: str = "external_sources",
    rows_per_entity: int = 12,
) -> Dict[str, int]:
    """For each catalogue entity matching ``prefix`` that is not already
    populated, generate ``rows_per_entity`` synthetic rows and write them
    via ``ResultSink.write_rows``.

    Returns ``{ virtual_entity: rows_written }``; empty dict if nothing
    needed seeding.
    """
    written: Dict[str, int] = {}
    candidates = _entities_for_prefix(prefix)
    for ve, spec in candidates:
        if await _table_already_populated(sim, schema, ve):
            continue
        rows = _generate_rows_for(ve, spec, prefix, count=rows_per_entity)
        try:
            await sink.write_rows(ve, rows, virtual_entity=ve)
            written[ve] = len(rows)
        except Exception as e:
            extra_logger.warning("seed_extra_entities {} failed: {}", ve, e)
    if written:
        extra_logger.info("Seeded {} extra entities for {}: {}",
                          len(written), prefix, list(written.keys()))
    return written


async def seed_all_extra_entities(
    sink: Any,
    sim: Any,
    rows_per_entity: int = 12,
) -> Dict[str, Dict[str, int]]:
    """Run ``seed_extra_entities`` for every solution prefix."""
    summary: Dict[str, Dict[str, int]] = {}
    for prefix in SOLUTION_PREFIXES.values():
        summary[prefix] = await seed_extra_entities(prefix, sink, sim,
                                                    rows_per_entity=rows_per_entity)
    return summary
