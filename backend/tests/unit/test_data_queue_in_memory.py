"""Unit tests for the Phase 0 InMemoryQueueManager + factory."""

from __future__ import annotations

import asyncio
import os
import time

import pytest

from src.models.automation_models import ConnectionDoc
from src.services.control_plane.data_queue import (
    DataQueueManager,
    QueueItem,
    make_data_queue_manager,
    queue_key,
)
from src.services.control_plane.data_queue.in_memory import InMemoryQueueManager


def _conn(*, src="s1", rel="success", dst="s2", param="x") -> ConnectionDoc:
    return ConnectionDoc(
        from_step=src,
        from_relationship=rel,
        to_step=dst,
        to_param=param,
    )


def test_queue_key_format_is_stable_and_unique_per_connection():
    a = queue_key(run_id="R1", conn=_conn(src="s1", rel="matched", dst="s2", param="customer_id"))
    b = queue_key(run_id="R1", conn=_conn(src="s1", rel="no_match", dst="s2", param="customer_id"))
    c = queue_key(run_id="R2", conn=_conn(src="s1", rel="matched", dst="s2", param="customer_id"))
    # Distinct relationship => distinct key. Distinct run_id => distinct key.
    assert a != b
    assert a != c
    assert "matched" in a and "customer_id" in a


def test_factory_returns_in_memory_when_env_unset_or_default(monkeypatch):
    monkeypatch.delenv("DATA_QUEUE_BACKEND", raising=False)
    mgr = make_data_queue_manager()
    assert isinstance(mgr, InMemoryQueueManager)
    assert isinstance(mgr, DataQueueManager)


def test_factory_falls_back_to_in_memory_on_unknown_backend(monkeypatch):
    monkeypatch.setenv("DATA_QUEUE_BACKEND", "made_up_thing")
    mgr = make_data_queue_manager()
    assert isinstance(mgr, InMemoryQueueManager)


@pytest.mark.asyncio
async def test_enqueue_dequeue_round_trip_preserves_payload():
    mgr = InMemoryQueueManager()
    conn = _conn()
    item_id = await mgr.enqueue(run_id="R1", conn=conn, payload={"customer_id": "ACC-1"})
    assert item_id.startswith("in-")

    item = await mgr.dequeue(run_id="R1", conn=conn)
    assert item is not None
    assert item.payload == {"customer_id": "ACC-1"}
    assert item.producer_step == "s1"
    assert item.relationship == "success"


@pytest.mark.asyncio
async def test_dequeue_returns_none_immediately_when_empty():
    mgr = InMemoryQueueManager()
    out = await mgr.dequeue(run_id="R1", conn=_conn())
    assert out is None


@pytest.mark.asyncio
async def test_dequeue_blocks_up_to_block_ms():
    mgr = InMemoryQueueManager()
    start = time.time()
    out = await mgr.dequeue(run_id="R1", conn=_conn(), block_ms=120)
    elapsed_ms = (time.time() - start) * 1000
    assert out is None
    # Allow some slack for scheduling jitter.
    assert elapsed_ms >= 100


@pytest.mark.asyncio
async def test_depth_counts_pending_until_ack():
    mgr = InMemoryQueueManager()
    conn = _conn()
    await mgr.enqueue(run_id="R1", conn=conn, payload={"x": 1})
    assert await mgr.depth(run_id="R1", conn=conn) == 1
    item = await mgr.dequeue(run_id="R1", conn=conn)
    # After dequeue, depth still 1 (pending until ack).
    assert await mgr.depth(run_id="R1", conn=conn) == 1
    await mgr.ack(run_id="R1", conn=conn, consumer="default", item_id=item.item_id)
    assert await mgr.depth(run_id="R1", conn=conn) == 0


@pytest.mark.asyncio
async def test_is_full_phase0_always_false():
    mgr = InMemoryQueueManager()
    for _ in range(100):
        await mgr.enqueue(run_id="R1", conn=_conn(), payload={"x": 1})
    assert await mgr.is_full(run_id="R1", conn=_conn()) is False


@pytest.mark.asyncio
async def test_snapshot_groups_by_queue_key():
    mgr = InMemoryQueueManager()
    c1 = _conn(src="s1", rel="matched", dst="s2", param="x")
    c2 = _conn(src="s1", rel="no_match", dst="s2", param="x")
    await mgr.enqueue(run_id="R1", conn=c1, payload={"a": 1})
    await mgr.enqueue(run_id="R1", conn=c1, payload={"a": 2})
    await mgr.enqueue(run_id="R1", conn=c2, payload={"b": 1})

    snap = await mgr.snapshot("R1")
    k1 = queue_key(run_id="R1", conn=c1)
    k2 = queue_key(run_id="R1", conn=c2)
    assert snap[k1]["depth"] == 2
    assert snap[k2]["depth"] == 1


@pytest.mark.asyncio
async def test_reset_run_purges_every_queue_for_that_run():
    mgr = InMemoryQueueManager()
    conn = _conn()
    await mgr.enqueue(run_id="R1", conn=conn, payload={"x": 1})
    await mgr.enqueue(run_id="R2", conn=conn, payload={"x": 2})

    await mgr.reset_run("R1")
    assert (await mgr.snapshot("R1")) == {}
    # Other runs untouched.
    snap2 = await mgr.snapshot("R2")
    assert next(iter(snap2.values()))["depth"] == 1


@pytest.mark.asyncio
async def test_distinct_run_ids_do_not_bleed():
    mgr = InMemoryQueueManager()
    conn = _conn()
    await mgr.enqueue(run_id="A", conn=conn, payload={"src": "A"})
    await mgr.enqueue(run_id="B", conn=conn, payload={"src": "B"})

    item_a = await mgr.dequeue(run_id="A", conn=conn)
    item_b = await mgr.dequeue(run_id="B", conn=conn)
    assert item_a.payload == {"src": "A"}
    assert item_b.payload == {"src": "B"}


@pytest.mark.asyncio
async def test_drop_expired_phase0_returns_zero():
    mgr = InMemoryQueueManager()
    assert await mgr.drop_expired(run_id="R1", conn=_conn()) == 0


# ---------------------------------------------------------------------------
# Phase 2 -- back-pressure thresholds + multi-producer fan-in
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_is_full_respects_max_object_count():
    mgr = InMemoryQueueManager()
    conn = ConnectionDoc(
        from_step="s1", from_relationship="success",
        to_step="s2", to_param="x", max_object_count=2,
    )
    assert await mgr.is_full(run_id="R1", conn=conn) is False
    await mgr.enqueue(run_id="R1", conn=conn, payload={"i": 1})
    assert await mgr.is_full(run_id="R1", conn=conn) is False
    await mgr.enqueue(run_id="R1", conn=conn, payload={"i": 2})
    # Depth == 2 hits max_object_count; producer back-pressures next enqueue.
    assert await mgr.is_full(run_id="R1", conn=conn) is True


@pytest.mark.asyncio
async def test_enqueue_back_pressures_until_drained():
    """Producer enqueue blocks while is_full=True and unblocks once the
    consumer drains the queue back under threshold."""
    mgr = InMemoryQueueManager()
    conn = ConnectionDoc(
        from_step="s1", from_relationship="success",
        to_step="s2", to_param="x", max_object_count=1,
    )
    await mgr.enqueue(run_id="R1", conn=conn, payload={"i": 1})
    # Second enqueue would block forever; schedule a drainer to unblock it.
    enq_task = asyncio.create_task(mgr.enqueue(run_id="R1", conn=conn, payload={"i": 2}))

    async def _drainer():
        await asyncio.sleep(0.05)
        item = await mgr.dequeue(run_id="R1", conn=conn)
        await mgr.ack(run_id="R1", conn=conn, consumer="c", item_id=item.item_id)

    await asyncio.gather(_drainer(), enq_task)
    # Both items should have flowed through.
    final_depth = await mgr.depth(run_id="R1", conn=conn)
    assert final_depth == 1  # second item is in the queue


@pytest.mark.asyncio
async def test_multi_producer_fan_in_merges_in_fifo_order():
    """Two ConnectionDocs feeding the same (to_step, to_param) port
    each push to the SAME underlying queue identity. Phase 2 InMemory
    backend uses ``queue_key`` which is per (from_step, from_rel,
    to_step, to_param) -- so multi-producer items land on separate
    queues today; the runner merges at the consumer-dispatch level.

    This test guards the simpler invariant: items within one
    ConnectionDoc stay FIFO.
    """
    mgr = InMemoryQueueManager()
    conn = ConnectionDoc(
        from_step="s1", from_relationship="success",
        to_step="s2", to_param="x", fan_in_strategy="merge_fifo",
    )
    await mgr.enqueue(run_id="R1", conn=conn, payload={"i": 1})
    await mgr.enqueue(run_id="R1", conn=conn, payload={"i": 2})
    await mgr.enqueue(run_id="R1", conn=conn, payload={"i": 3})

    out = []
    for _ in range(3):
        item = await mgr.dequeue(run_id="R1", conn=conn)
        out.append(item.payload["i"])
        await mgr.ack(run_id="R1", conn=conn, consumer="c", item_id=item.item_id)
    assert out == [1, 2, 3]


def test_validator_softens_duplicate_producer_when_fan_in_strategy_set():
    """validate_strict downgrades duplicate_input_producer from error
    to warning when at least one ConnectionDoc opts into a merge mode."""
    from src.models.automation_models import JourneyDoc, StageDoc, StepDoc

    j = JourneyDoc(
        use_case_id="merge.test",
        title="Merge test",
        solution_id="builder",
        stages=[StageDoc(
            stage_id="main", name="Main", order=1,
            steps=[
                StepDoc(step_id="p1", name="p1", order=1, tool="t1"),
                StepDoc(step_id="p2", name="p2", order=2, tool="t1"),
                StepDoc(step_id="c1", name="c1", order=3, tool="t2"),
            ],
            connections=[
                ConnectionDoc(from_step="p1", from_relationship="success",
                              to_step="c1", to_param="x",
                              fan_in_strategy="merge_fifo"),
                ConnectionDoc(from_step="p2", from_relationship="success",
                              to_step="c1", to_param="x",
                              fan_in_strategy="merge_fifo"),
            ],
        )],
    )
    report = j.validate_strict()
    error_codes = [iss.code for iss in report.errors]
    warning_codes = [iss.code for iss in report.warnings]
    assert "duplicate_input_producer" not in error_codes
    assert "multi_producer_fan_in" in warning_codes


# ---------------------------------------------------------------------------
# Phase 4 -- Redis backend factory fallback (the actual Redis client is
# integration-tested separately because it requires a running Redis).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Phase 5 -- prioritizer + expiry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drop_expired_removes_items_older_than_threshold():
    mgr = InMemoryQueueManager()
    conn = ConnectionDoc(
        from_step="s1", from_relationship="success",
        to_step="s2", to_param="x", expiry_seconds=1,
    )
    item_id_old = await mgr.enqueue(run_id="R1", conn=conn, payload={"i": "old"})
    # Backdate the item so the sweep treats it as expired.
    state = mgr._state("R1", conn)
    state.items[-1].enqueued_at_ms -= 5000  # 5 s in the past
    # And a fresh item that should survive.
    await mgr.enqueue(run_id="R1", conn=conn, payload={"i": "new"})

    dropped = await mgr.drop_expired(run_id="R1", conn=conn)
    assert dropped == 1
    survivor = await mgr.dequeue(run_id="R1", conn=conn)
    assert survivor.payload == {"i": "new"}


@pytest.mark.asyncio
async def test_drop_expired_returns_zero_when_no_expiry_set():
    mgr = InMemoryQueueManager()
    conn = ConnectionDoc(
        from_step="s1", from_relationship="success", to_step="s2", to_param="x",
    )
    await mgr.enqueue(run_id="R1", conn=conn, payload={"i": 1})
    state = mgr._state("R1", conn)
    state.items[-1].enqueued_at_ms -= 999_999  # ancient
    # Without expiry_seconds set, no sweep happens.
    dropped = await mgr.drop_expired(run_id="R1", conn=conn)
    assert dropped == 0


def test_validator_rejects_prioritizer_with_concurrent_consumers():
    from src.models.automation_models import JourneyDoc, StageDoc, StepDoc

    j = JourneyDoc(
        use_case_id="prio.conflict",
        title="Prio + concurrent",
        solution_id="builder",
        stages=[StageDoc(
            stage_id="main", name="Main", order=1,
            steps=[
                StepDoc(step_id="p", name="p", order=1, tool="t1"),
                StepDoc(step_id="c", name="c", order=2, tool="t2"),
            ],
            connections=[
                ConnectionDoc(
                    from_step="p", from_relationship="success",
                    to_step="c", to_param="x",
                    prioritizer="by_attribute", priority_path="urgency",
                    concurrent_consumers=4,
                ),
            ],
        )],
    )
    report = j.validate_strict()
    codes = [iss.code for iss in report.errors]
    assert "prioritizer_concurrent_conflict" in codes


def test_validator_rejects_by_attribute_without_priority_path():
    from src.models.automation_models import JourneyDoc, StageDoc, StepDoc

    j = JourneyDoc(
        use_case_id="prio.missing.path",
        title="No path",
        solution_id="builder",
        stages=[StageDoc(
            stage_id="main", name="Main", order=1,
            steps=[
                StepDoc(step_id="p", name="p", order=1, tool="t1"),
                StepDoc(step_id="c", name="c", order=2, tool="t2"),
            ],
            connections=[
                ConnectionDoc(
                    from_step="p", from_relationship="success",
                    to_step="c", to_param="x", prioritizer="by_attribute",
                ),
            ],
        )],
    )
    report = j.validate_strict()
    codes = [iss.code for iss in report.errors]
    assert "prioritizer_missing_path" in codes


def test_factory_falls_back_to_in_memory_when_redis_unreachable(monkeypatch):
    """When DATA_QUEUE_BACKEND=redis but no Redis is reachable, the
    factory must transparently return InMemoryQueueManager so the
    engine boots without depending on the queue backend's availability.
    """
    monkeypatch.setenv("DATA_QUEUE_BACKEND", "redis")
    # Point to an unreachable host (port 65535 reserved / unbound).
    monkeypatch.setenv("REDIS_URL", "redis://localhost:65535/0")
    mgr = make_data_queue_manager()
    assert isinstance(mgr, InMemoryQueueManager)


def test_validator_keeps_duplicate_producer_error_under_default_strategy():
    """Without fan_in_strategy override, the existing single-producer
    invariant still errors."""
    from src.models.automation_models import JourneyDoc, StageDoc, StepDoc

    j = JourneyDoc(
        use_case_id="default.test",
        title="Default test",
        solution_id="builder",
        stages=[StageDoc(
            stage_id="main", name="Main", order=1,
            steps=[
                StepDoc(step_id="p1", name="p1", order=1, tool="t1"),
                StepDoc(step_id="p2", name="p2", order=2, tool="t1"),
                StepDoc(step_id="c1", name="c1", order=3, tool="t2"),
            ],
            connections=[
                ConnectionDoc(from_step="p1", from_relationship="success",
                              to_step="c1", to_param="x"),
                ConnectionDoc(from_step="p2", from_relationship="success",
                              to_step="c1", to_param="x"),
            ],
        )],
    )
    report = j.validate_strict()
    error_codes = [iss.code for iss in report.errors]
    assert "duplicate_input_producer" in error_codes
