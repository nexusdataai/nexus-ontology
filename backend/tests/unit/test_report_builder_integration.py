"""End-to-end smoke for ``JourneyReportBuilder.build`` against a
mocked executor + a real (bundled) schema.

Verifies: given 3 fake JobExecution rows under one journey_id and a
demand-forecasting schema, the builder produces an envelope with the
right summary KPI values, a populated section list, and the derived
fields the default schema relies on.
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock

import pytest

from src.services.journey_report_builder import (
    JourneyNotFound, JourneyReportBuilder,
)
from src.services.journey_report_catalog import ReportSchemaCatalog


SCHEMA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "enterprise-knowledge", "report-schemas",
)


def _make_executor(meta=None, jobs=None, transitions=None) -> MagicMock:
    """Build a mock executor exposing the minimum surface
    JourneyReportBuilder reads."""
    ex = MagicMock()
    ex._get_journey_pk.side_effect = lambda jid: f"JOURNEY#{jid}"
    ex.table = MagicMock()

    # get_item -> METADATA
    if meta is not None:
        ex.table.get_item.return_value = {"Item": {"Data": meta}}
    else:
        ex.table.get_item.return_value = {}

    # query -> JobExecution + JobTransition rows, depending on SK prefix.
    def _fake_query(**kwargs):
        sk_prefix = kwargs.get("ExpressionAttributeValues", {}).get(":sk", "")
        if sk_prefix == "JOB#":
            return {"Items": [
                {"EntityType": "JobExecution", "Data": j}
                for j in (jobs or [])
            ]}
        if sk_prefix == "JOBTXN#":
            return {"Items": [
                {"EntityType": "JobTransition", "Data": t}
                for t in (transitions or [])
            ]}
        return {"Items": []}

    ex.table.query.side_effect = _fake_query
    return ex


def test_404_when_metadata_missing() -> None:
    ex = _make_executor(meta=None)
    cat = ReportSchemaCatalog(schema_dir=SCHEMA_DIR); cat.reload()
    builder = JourneyReportBuilder(catalog=cat, executor=ex)
    with pytest.raises(JourneyNotFound):
        asyncio.run(builder.build("missing-id"))


def test_demand_forecasting_envelope_end_to_end() -> None:
    """A demand-forecasting journey with three completed jobs whose
    KPIs are slightly different across runs. The builder should pick
    up MAPE / stockout / forecasts via the YAML-declared rollups."""
    meta = {"title": "Weekly SKU Replenishment", "solutionId": "demand-forecasting"}
    jobs = [
        {
            "jobId": "JOB-001", "status": "completed",
            "metrics": {"durationSeconds": 30},
            "kpis": {
                "mape": 12, "bias": 1.0, "stockout_rate_pct": 3,
                "total_forecasts": 100, "total_base_qty": 1000,
                "total_forecast_qty": 1100, "alerts_count": 1,
                "sku_region_combos": 20, "forecast_horizon_weeks": 12,
                "override_count": 0,
                "alerts": [{"type": "demand_spike", "severity": "low"}],
            },
        },
        {
            "jobId": "JOB-002", "status": "completed",
            "metrics": {"durationSeconds": 25},
            "kpis": {
                "mape": 18, "bias": -2.0, "stockout_rate_pct": 6,
                "total_forecasts": 110, "total_base_qty": 1200,
                "total_forecast_qty": 1300, "alerts_count": 2,
                "sku_region_combos": 22, "forecast_horizon_weeks": 12,
                "override_count": 4,
                "alerts": [
                    {"type": "demand_spike", "severity": "high"},
                    {"type": "promotion_conflict", "severity": "medium"},
                ],
            },
        },
        {
            "jobId": "JOB-003", "status": "failed",
            "metrics": {"durationSeconds": 5},
            "kpis": {},
        },
    ]
    ex = _make_executor(meta=meta, jobs=jobs, transitions=[])
    cat = ReportSchemaCatalog(schema_dir=SCHEMA_DIR); cat.reload()
    builder = JourneyReportBuilder(catalog=cat, executor=ex)
    envelope = asyncio.run(builder.build("J-1"))

    assert envelope["solution_id"] == "demand-forecasting"
    assert envelope["title"] == "Demand Forecasting Report"
    assert envelope["journey_title"] == "Weekly SKU Replenishment"
    assert envelope["total_jobs"] == 3

    summary = {k["key"]: k for k in envelope["summary_kpis"]}
    # mape rollup=avg over JOB-001/002 (15), JOB-003 has empty kpis.
    assert summary["mape"]["value"] == pytest.approx(15.0)
    # MAPE threshold warn=15 critical=25 -> 15 is exactly warn boundary.
    assert summary["mape"]["status"] in {"warn", "ok"}
    # stockout_rate_pct rollup=avg of [3, 6] = 4.5.
    assert summary["stockout_rate_pct"]["value"] == pytest.approx(4.5)
    # total_forecast_qty rollup=sum of [1100, 1300] = 2400.
    assert summary["total_forecast_qty"]["value"] == 2400
    # alerts_count rollup=sum of [1, 2] = 3.
    assert summary["alerts_count"]["value"] == 3

    # Sections rendered.
    sec_ids = [s["id"] for s in envelope["sections"]]
    assert "volumes" in sec_ids
    assert "alerts" in sec_ids
    assert "performance" in sec_ids

    # Alerts section flattens all alerts across jobs and groups them.
    alerts_section = next(s for s in envelope["sections"] if s["id"] == "alerts")
    assert alerts_section["kind"] == "alerts_list"
    assert len(alerts_section["alerts"]) == 3
    groups = {g["key"]: g["count"] for g in alerts_section["groups"]}
    assert groups.get("demand_spike") == 2
    assert groups.get("promotion_conflict") == 1


def test_default_fallback_envelope_for_unknown_solution() -> None:
    """No solution_id at all => the builder uses the _default schema."""
    meta = {"title": "Random Journey"}
    jobs = [
        {
            "jobId": "JOB-001", "status": "completed",
            "metrics": {"durationSeconds": 10},
            "stepResults": {
                "s1": {"name": "Step 1", "tool": "find_x", "status": "completed"},
                "s2": {"name": "Step 2", "tool": "do_y", "status": "completed"},
            },
        },
    ]
    ex = _make_executor(meta=meta, jobs=jobs, transitions=[])
    cat = ReportSchemaCatalog(schema_dir=SCHEMA_DIR); cat.reload()
    builder = JourneyReportBuilder(catalog=cat, executor=ex)
    envelope = asyncio.run(builder.build("J-1"))
    assert envelope["title"] == "Journey Report"
    summary = {k["key"]: k for k in envelope["summary_kpis"]}
    assert summary["total_jobs"]["value"] == 1
    assert summary["completed_jobs"]["value"] == 1
    assert summary["failed_jobs"]["value"] == 0
    # Step breakdown section materialised.
    sb = next(s for s in envelope["sections"] if s["kind"] == "step_breakdown")
    step_ids = {st["step_id"] for st in sb["steps"]}
    assert step_ids == {"s1", "s2"}


def test_copilot_saved_uses_builder_yaml() -> None:
    """A Copilot-saved journey (solutionId=builder) renders the
    builder.yaml schema with steps_total/completed/failed cards."""
    meta = {"title": "Test Copilot Run", "solutionId": "builder"}
    jobs = [
        {
            "jobId": "JOB-001", "status": "completed",
            "metrics": {"durationSeconds": 8},
            "kpis": {
                "steps_total": 3, "steps_completed": 3, "steps_failed": 0,
                "tools_invoked": 2, "duration_seconds": 8,
            },
        },
    ]
    ex = _make_executor(meta=meta, jobs=jobs, transitions=[])
    cat = ReportSchemaCatalog(schema_dir=SCHEMA_DIR); cat.reload()
    builder = JourneyReportBuilder(catalog=cat, executor=ex)
    envelope = asyncio.run(builder.build("J-builder"))
    assert envelope["solution_id"] == "builder"
    assert envelope["title"] == "Copilot Saved Journey Report"
    summary = {k["key"]: k for k in envelope["summary_kpis"]}
    assert summary["steps_total"]["value"] == 3
    assert summary["steps_completed"]["value"] == 3
    assert summary["steps_failed"]["value"] == 0
