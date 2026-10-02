"""Tests for the Phase-2 state-transition methods on
``JourneyExecutorBridge``: ``mark_awaiting_approval`` /
``reject_run`` / ``cancel_run`` + the JOBTXN# transition log.

These fixtures mock ``TransformationJobExecutor`` so the tests do
not need real AWS credentials. We assert:

1. ``mark_awaiting_approval`` flips ``Data.status`` to
   ``awaiting_step_approval`` and stashes ``Data.pendingStep`` on
   the JobExecution row via a single update_item call.
2. ``reject_run`` flips ``Data.status`` to ``rejected`` and
   increments the journey ``failed`` aggregate (rejected runs
   roll into the ``failed`` bucket for the card-grid counter).
3. ``cancel_run`` flips ``Data.status`` to ``cancelled``.
4. Each transition method emits a JOBTXN# row with the right
   from_state / to_state / step_id / reason fields.
5. ``start_job`` writes a ``pending -> in_progress`` JOBTXN row.
6. ``complete_run`` writes an ``in_progress -> completed`` JOBTXN row.
7. ``fail_run`` writes an ``in_progress -> failed`` JOBTXN row.
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
    ex.logs_bucket = "logs-bucket"
    ex.reports_bucket = "reports-bucket"
    ex.region_name = "us-east-1"
    # ``mark_awaiting_approval`` / ``reject_run`` / ``cancel_run`` go
    # through ``_set_overall_status`` which reads via
    # ``get_job_execution`` and writes via ``update_item``.
    ex.get_job_execution.return_value = {
        "stageId": "main",
        "executionNumber": 1,
        "stageOrder": 1,
    }
    return ex


def _put_items(ex: MagicMock) -> list:
    return [call.kwargs.get("Item") for call in ex.table.put_item.call_args_list]


def _last_transition(ex: MagicMock) -> dict:
    for item in reversed(_put_items(ex)):
        if item and item.get("EntityType") == "JobTransition":
            return item["Data"]
    raise AssertionError("no JobTransition row written")


def test_mark_awaiting_approval_flips_status_and_records_transition() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.mark_awaiting_approval(
        "J", "JOB-001-X", "s1",
        pending_payload={"step_id": "s1", "tool": "apply_promo_discount"},
    )
    # update_item flipped Data.status -> awaiting_step_approval and
    # stashed pendingStep alongside.
    ex.table.update_item.assert_called_once()
    update_kwargs = ex.table.update_item.call_args.kwargs
    values = update_kwargs["ExpressionAttributeValues"]
    assert values[":status"] == "awaiting_step_approval"
    # pendingStep was carried through as an extra :v* placeholder.
    assert any(
        isinstance(v, dict) and v.get("step_id") == "s1"
        for v in values.values()
    )
    # Transition recorded: in_progress -> awaiting_step_approval.
    txn = _last_transition(ex)
    assert txn["fromState"] == "in_progress"
    assert txn["toState"] == "awaiting_step_approval"
    assert txn["stepId"] == "s1"
    assert txn["ordinal"] == 1
    # And a LIVELOG line on the pausing step was written.
    livelog_items = [
        i for i in _put_items(ex)
        if i and i.get("PK", "").startswith("LIVELOG#")
    ]
    assert any(
        "Awaiting approval" in i.get("logs_json", "") for i in livelog_items
    )


def test_reject_run_flips_status_increments_failed_aggregate() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.reject_run("J", "JOB-001-X", step_id="s1", reason="too risky")
    values = ex.table.update_item.call_args.kwargs["ExpressionAttributeValues"]
    assert values[":status"] == "rejected"
    # update_journey_aggregates called with the 'failed' bucket so the
    # card-grid Failed counter reflects rejected runs.
    ex.update_journey_aggregates.assert_called_with("J", "main", "failed")
    txn = _last_transition(ex)
    assert txn["toState"] == "rejected"
    assert txn["reason"] == "too risky"


def test_cancel_run_flips_status() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.cancel_run("J", "JOB-001-X", reason="user pressed Cancel")
    values = ex.table.update_item.call_args.kwargs["ExpressionAttributeValues"]
    assert values[":status"] == "cancelled"
    ex.update_journey_aggregates.assert_called_with("J", "main", "failed")
    txn = _last_transition(ex)
    assert txn["toState"] == "cancelled"


def test_start_complete_fail_record_transitions() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.start_job("J", plan_steps=[{"id": "s1", "tool": "find_churning_customers"}])
    bridge.complete_run("J", "JOB-001-X", items_processed=1, items_total=1)
    txn = _last_transition(ex)
    assert txn["toState"] == "completed"
    # And fail_run also lands a transition row.
    ex2 = _make_executor()
    b2 = JourneyExecutorBridge(executor=ex2)
    b2.start_job("J", plan_steps=[{"id": "s1", "tool": "find_churning_customers"}])
    b2.fail_run("J", "JOB-001-X", error="something exploded")
    last = _last_transition(ex2)
    assert last["toState"] == "failed"
    assert last["reason"] == "something exploded"


def test_transition_ordinals_are_monotonic_per_job() -> None:
    ex = _make_executor()
    bridge = JourneyExecutorBridge(executor=ex)
    bridge.start_job("J", plan_steps=[{"id": "s1", "tool": "find_churning_customers"}])
    bridge.mark_awaiting_approval("J", "JOB-001-X", "s1", pending_payload={"step_id": "s1"})
    bridge.complete_run("J", "JOB-001-X")
    txn_rows = [
        i["Data"] for i in _put_items(ex)
        if i and i.get("EntityType") == "JobTransition"
    ]
    ordinals = [t["ordinal"] for t in txn_rows]
    assert ordinals == sorted(ordinals)
    # Three transitions total: start, pause, complete.
    assert len(ordinals) == 3
