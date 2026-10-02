"""Unit tests for ``JourneyExecutorBridge``.

The bridge writes Copilot-engine runs into the same DDB shape that the
regular Journeys API consumes. We mock the underlying
``TransformationJobExecutor`` (its ``table``, ``get_next_execution_number``,
``update_step_status``, ``complete_job`` and ``fail_job``) so the tests
do not need real AWS credentials.

What we verify here:

1. ``ensure_metadata`` issues a single conditional put_item per journey
   (idempotent + cached after first call).
2. ``start_job`` writes a JobExecution row with PK / SK in the exact
   shape ``journey_api`` queries, ``Data.stepResults`` pre-populated
   with one entry per planned step, and ``Data.source == copilot_saved``.
3. ``mark_step_in_progress/completed/failed`` delegate to the
   executor's ``update_step_status`` and survive an underlying raise.
4. ``write_step_log`` produces a LIVELOG put_item with the exact JSON
   shape ``BaseStage._write_live_logs_to_dynamo`` produces, so the
   existing Layer-1 fast path on
   ``/jobs/{job_id}/logs?step_name=...`` reads it unchanged.
5. ``complete_run`` / ``fail_run`` route to the right executor method.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.services.control_plane.journey_executor_bridge import (
    JourneyExecutorBridge,
)


def _make_executor() -> MagicMock:
    """Mock that mimics the surface of ``TransformationJobExecutor``
    the bridge actually touches."""
    ex = MagicMock()
    ex._get_journey_pk.side_effect = lambda jid: f"JOURNEY#{jid}"
    ex.table = MagicMock()
    ex.get_next_execution_number.return_value = 1
    ex.logs_bucket = "logs-bucket"
    ex.reports_bucket = "reports-bucket"
    ex.region_name = "us-east-1"
    return ex


def test_ensure_metadata_writes_once_and_caches() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)

    assert bridge.ensure_metadata("builder.testjourney", title="Test J") is True
    # Second call should NOT issue another put_item (cached).
    assert bridge.ensure_metadata("builder.testjourney", title="Test J") is True
    assert ex.table.put_item.call_count == 1

    item = ex.table.put_item.call_args.kwargs.get("Item") or ex.table.put_item.call_args[1]["Item"]
    assert item["PK"] == "JOURNEY#builder.testjourney"
    assert item["SK"] == "METADATA"
    assert item["EntityType"] == "Journey"
    assert item["Data"]["source"] == "copilot_saved"
    assert item["Data"]["aggregates"] == {
        "totalJobs": 0, "completedJobs": 0, "failedJobs": 0,
    }


def test_ensure_metadata_swallows_conditional_check_failed() -> None:
    ex = _make_executor()
    ex.table.put_item.side_effect = Exception(
        "ConditionalCheckFailedException: already exists"
    )
    bridge = JourneyExecutorBridge(executor=ex)
    # Should still return True (existing METADATA is the happy path)
    # AND still cache, so a second call does not retry.
    assert bridge.ensure_metadata("builder.x") is True
    assert bridge.ensure_metadata("builder.x") is True
    assert ex.table.put_item.call_count == 1


def _job_execution_put_item(ex: MagicMock) -> dict:
    """Helper -- ``start_job`` now writes both the JobExecution row
    AND a JOBTXN# transition row. Locate the JobExecution put_item
    by SK prefix."""
    for call in ex.table.put_item.call_args_list:
        item = call.kwargs.get("Item") or call.args[0].get("Item") if call.args else None
        if item is None and call.kwargs:
            item = call.kwargs.get("Item")
        if item and item.get("EntityType") == "JobExecution":
            return item
    raise AssertionError("no JobExecution put_item found")


def _last_put_item_matching(ex: MagicMock, entity_type: str) -> dict:
    for call in reversed(ex.table.put_item.call_args_list):
        item = call.kwargs.get("Item")
        if item and item.get("EntityType") == entity_type:
            return item
    raise AssertionError(f"no put_item with EntityType={entity_type}")


def test_start_job_writes_job_execution_with_step_results() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    plan = [
        {"id": "s1", "name": "Find churners", "tool": "find_churning_customers"},
        {"id": "s2", "name": "Apply promo", "tool": "apply_promo_discount"},
    ]
    job_id = bridge.start_job("builder.testjourney", plan_steps=plan)
    assert job_id is not None
    assert job_id.startswith("JOB-001-")
    item = _job_execution_put_item(ex)
    assert item["PK"] == "JOURNEY#builder.testjourney"
    assert item["SK"].startswith("JOB#01#main#001#")
    assert item["EntityType"] == "JobExecution"
    assert item["Data"]["jobId"] == job_id
    assert item["Data"]["stageId"] == "main"
    assert item["Data"]["status"] == "in_progress"
    assert set(item["Data"]["stepResults"].keys()) == {"s1", "s2"}
    assert item["Data"]["stepResults"]["s1"]["tool"] == "find_churning_customers"
    assert item["Data"]["source"] == "copilot_saved"
    # GSI1 used by /jobs handler must be present so the list query
    # behaves identically to regular Journeys.
    assert item["GSI1PK"] == "STAGE#builder.testjourney#main"
    # Phase-2: start_job also records a pending -> in_progress transition.
    txn = _last_put_item_matching(ex, "JobTransition")
    assert txn["SK"].startswith(f"JOBTXN#{job_id}#")
    assert txn["Data"]["fromState"] == "pending"
    assert txn["Data"]["toState"] == "in_progress"


def test_mark_step_helpers_delegate_to_executor() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.mark_step_in_progress("J", "JOB-001-X", "s1", 0)
    ex.update_step_status.assert_called_with("J", "JOB-001-X", "s1", "in_progress", 0)
    bridge.mark_step_completed("J", "JOB-001-X", "s1", 0, duration_ms=123, result_preview="ok")
    assert ex.update_step_status.call_args_list[-1][0] == ("J", "JOB-001-X", "s1", "completed", 0)
    bridge.mark_step_failed("J", "JOB-001-X", "s2", 1, error="boom")
    assert ex.update_step_status.call_args_list[-1][0] == ("J", "JOB-001-X", "s2", "failed", 1)


def test_mark_step_helpers_swallow_executor_failure() -> None:
    ex = _make_executor()
    ex.update_step_status.side_effect = RuntimeError("ddb out to lunch")
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.mark_step_in_progress("J", "JOB-001-X", "s1", 0)  # must not raise


def test_write_step_log_writes_livelog_with_base_stage_shape() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.write_step_log("J", "JOB-001-X", "s1",
                          level="info", message="hi", details={"k": "v"},
                          source="tool")
    item = ex.table.put_item.call_args.kwargs.get("Item") or ex.table.put_item.call_args[1]["Item"]
    assert item["PK"] == "LIVELOG#JOB-001-X"
    assert item["SK"] == "s1"
    assert item["log_count"] == 1
    parsed = json.loads(item["logs_json"])
    assert parsed[0]["message"] == "hi"
    assert parsed[0]["level"] == "INFO"
    assert parsed[0]["step_id"] == "s1"
    assert parsed[0]["details"] == {"k": "v"}
    assert "timestamp" in parsed[0]
    assert item["ttl"] > 0  # rolling TTL like BaseStage


def test_write_step_log_rate_limits_after_threshold() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    # Drop the threshold so the test stays fast.
    bridge._emit_truncate_threshold = 3
    for i in range(10):
        bridge.write_step_log("J", "JOB-001-X", "s1",
                              level="INFO", message=f"line {i}",
                              source="custom_code")
    # 3 normal entries + 1 truncation marker -> 4 LIVELOG put_items
    # then all subsequent calls are dropped.
    assert ex.table.put_item.call_count == 4
    last_item = ex.table.put_item.call_args.kwargs.get("Item") or ex.table.put_item.call_args[1]["Item"]
    last_log = json.loads(last_item["logs_json"])[-1]
    assert "truncated" in last_log["message"].lower()


def test_complete_run_and_fail_run_route_correctly() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.complete_run("J", "JOB-001-X", items_processed=2, items_total=2)
    # complete_job is now called with the auto-derived Copilot Saved
    # stage_kpis attached -- match positional + the kwargs we care
    # about rather than the full call signature.
    assert ex.complete_job.called
    kwargs = ex.complete_job.call_args.kwargs
    assert kwargs["items_processed"] == 2
    assert kwargs["items_total"] == 2
    assert isinstance(kwargs.get("stage_kpis"), dict)
    bridge.fail_run("J", "JOB-001-X", error="kaboom")
    ex.fail_job.assert_called_with("J", "JOB-001-X", "kaboom")


def test_no_op_when_executor_is_none() -> None:
    bridge = JourneyExecutorBridge(executor=None)
    assert bridge.ensure_metadata("J") is False
    assert bridge.start_job("J", plan_steps=[]) is None
    bridge.mark_step_in_progress("J", "X", "s1", 0)
    bridge.write_step_log("J", "X", "s1", message="hi")
    bridge.complete_run("J", "X")
    bridge.fail_run("J", "X", "boom")
