"""Tests that ``JourneyExecutorBridge.complete_run`` writes the
auto-derived Copilot-saved KPI dict.

The bridge maps (items_processed, items_total) -> steps_completed /
steps_total / steps_failed on Data.kpis so the builder.yaml schema's
summary cards have data to render.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.control_plane.journey_executor_bridge import (
    JourneyExecutorBridge,
)


def _make_executor() -> MagicMock:
    ex = MagicMock()
    ex._get_journey_pk.side_effect = lambda jid: f"JOURNEY#{jid}"
    ex.table = MagicMock()
    ex.get_next_execution_number.return_value = 1
    ex.logs_bucket = "logs"
    ex.reports_bucket = "reports"
    ex.region_name = "us-east-1"
    ex.get_job_execution.return_value = {
        "stageId": "main", "executionNumber": 1, "stageOrder": 1,
        "startTime": "2026-05-17T20:00:00Z",
        "stepResults": {
            "s1": {"name": "find_churning_customers", "tool": "find_churning_customers",
                   "status": "completed"},
            "s2": {"name": "apply_promo_discount", "tool": "apply_promo_discount",
                   "status": "completed"},
        },
    }
    return ex


def test_complete_run_forwards_stage_kpis() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.complete_run("J-1", "JOB-001-X", items_processed=2, items_total=2)
    # complete_job was called WITH stage_kpis carrying the auto-derived
    # Copilot Saved KPIs.
    ex.complete_job.assert_called_once()
    kwargs = ex.complete_job.call_args.kwargs
    assert kwargs["items_processed"] == 2
    assert kwargs["items_total"] == 2
    kpis = kwargs["stage_kpis"]
    assert isinstance(kpis, dict)
    assert kpis["steps_total"] == 2
    assert kpis["steps_completed"] == 2
    assert kpis["steps_failed"] == 0
    # ``tools_invoked`` is derived from distinct tools across
    # stepResults; 2 distinct tools in the executor fixture.
    assert kpis.get("tools_invoked") == 2
    # ``duration_seconds`` is best-effort -- present when the
    # JobExecution has a parseable startTime.
    assert "duration_seconds" in kpis


def test_complete_run_falls_back_when_stage_kpis_unsupported() -> None:
    """If the executor's complete_job signature doesn't accept
    stage_kpis (old code path), the bridge transparently retries
    without the kwarg rather than blowing up the run completion."""
    ex = _make_executor()
    # First call: raise TypeError (simulating old signature); second
    # call: succeed without the kwarg.
    ex.complete_job.side_effect = [TypeError("unexpected kwarg"), None]
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.complete_run("J-1", "JOB-001-X", items_processed=1, items_total=2)
    # Two calls -- the first raised, the second was the fallback.
    assert ex.complete_job.call_count == 2
    second = ex.complete_job.call_args_list[1].kwargs
    assert "stage_kpis" not in second  # fallback dropped the kwarg


def test_complete_run_swallows_kpi_derive_errors() -> None:
    """If derive helper raises (e.g. JobExecution missing), the bridge
    still completes the job rather than hiding the user's run."""
    ex = _make_executor()
    ex.get_job_execution.side_effect = RuntimeError("ddb down")
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.complete_run("J-1", "JOB-001-X", items_processed=1, items_total=2)
    ex.complete_job.assert_called_once()
    # stage_kpis still includes the trivial counters even when
    # _derive_run_stats raised.
    kpis = ex.complete_job.call_args.kwargs.get("stage_kpis")
    assert kpis is not None
    assert kpis["steps_total"] == 2
    assert kpis["steps_completed"] == 1
    assert kpis["steps_failed"] == 1
