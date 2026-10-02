"""In-memory DataQueueManager implementation.

Default backend. Each queue is an ``asyncio.Queue`` keyed by the
(run_id, ConnectionDoc) tuple. State is lost on process restart -- if
durability matters, switch to the Redis backend in Phase 4.

The implementation deliberately tracks the same per-queue metadata
the Redis backend will need later (depth, capacity, pending items by
item_id) so the runner integration in Phase 1 sees a stable shape
regardless of backend.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Optional

from loguru import logger

from src.models.automation_models import ConnectionDoc

from . import DataQueueManager, QueueItem, queue_key

inmem_logger = logger.bind(component="data-queue-inmem")


@dataclass
class _QueueState:
    """Per-queue state for the InMemory backend."""

    items: Deque[QueueItem] = field(default_factory=deque)
    # Items that have been dequeued but not yet acked. The Redis
    # backend will use XPENDING + XAUTOCLAIM here; the in-memory
    # backend just stores them so ``depth`` can include pending
    # work for the diagnostics view.
    pending: Dict[str, QueueItem] = field(default_factory=dict)
    seq: int = 0


class InMemoryQueueManager:
    """Async, single-process queue manager backed by ``asyncio.Queue``.

    Suitable for the default sync run-to-quiescence path the runner
    uses today. Thread-safe within a single asyncio event loop; not
    safe across processes (use the Redis backend for that).
    """

    def __init__(self) -> None:
        # run_id -> queue_key -> _QueueState
        self._queues: Dict[str, Dict[str, _QueueState]] = {}
        # Default capacity. Phase 2 threads max_object_count from the
        # ConnectionDoc through enqueue/is_full; for Phase 0 the queue
        # is effectively unbounded.
        self._default_capacity: int = 0  # 0 == unbounded

    def _state(self, run_id: str, conn: ConnectionDoc) -> _QueueState:
        per_run = self._queues.setdefault(run_id, {})
        key = queue_key(run_id=run_id, conn=conn)
        if key not in per_run:
            per_run[key] = _QueueState()
        return per_run[key]

    async def enqueue(
        self, *, run_id: str, conn: ConnectionDoc, payload: Dict[str, Any],
    ) -> str:
        # Phase 2: soft back-pressure. When the queue is at capacity,
        # yield to the event loop until the consumer drains. Caps
        # ``max_object_count`` and ``max_byte_size`` are read off the
        # ConnectionDoc; either being None means unbounded.
        if conn.max_object_count or conn.max_byte_size:
            while await self.is_full(run_id=run_id, conn=conn):
                await asyncio.sleep(0.01)

        state = self._state(run_id, conn)
        state.seq += 1
        item = QueueItem(
            item_id=f"in-{state.seq}",
            payload=dict(payload),
            enqueued_at_ms=int(time.time() * 1000),
            producer_step=conn.from_step,
            relationship=conn.from_relationship,
        )
        state.items.append(item)
        return item.item_id

    async def dequeue(
        self, *, run_id: str, conn: ConnectionDoc, consumer: str = "default",
        block_ms: int = 0,
    ) -> Optional[QueueItem]:
        state = self._state(run_id, conn)
        if state.items:
            item = state.items.popleft()
            state.pending[item.item_id] = item
            return item

        if block_ms <= 0:
            return None

        # Soft-block until something arrives or the timeout fires.
        end = time.time() + (block_ms / 1000.0)
        while time.time() < end:
            await asyncio.sleep(min(0.05, max(0.0, end - time.time())))
            if state.items:
                item = state.items.popleft()
                state.pending[item.item_id] = item
                return item
        return None

    async def ack(
        self, *, run_id: str, conn: ConnectionDoc, consumer: str, item_id: str,
    ) -> None:
        state = self._state(run_id, conn)
        state.pending.pop(item_id, None)

    async def depth(self, *, run_id: str, conn: ConnectionDoc) -> int:
        state = self._state(run_id, conn)
        return len(state.items) + len(state.pending)

    async def is_full(self, *, run_id: str, conn: ConnectionDoc) -> bool:
        """Phase 2: enforce per-queue ``max_object_count`` and
        ``max_byte_size`` thresholds from the ConnectionDoc.

        When EITHER threshold is set and currently violated, the
        producer's :meth:`enqueue` loop yields until the consumer
        drains it back below the cap. Both thresholds None means the
        queue is unbounded (Phase 0 semantics).
        """
        max_count = conn.max_object_count or 0
        max_bytes = conn.max_byte_size or 0
        if max_count <= 0 and max_bytes <= 0:
            return False

        state = self._state(run_id, conn)
        depth = len(state.items) + len(state.pending)
        if max_count > 0 and depth >= max_count:
            return True
        if max_bytes > 0:
            # Byte size is approximated by the JSON-encoded length of each
            # payload; cheap-ish since the payloads are dicts the runner
            # has already serialised once for the session blob anyway.
            import json as _json
            total = 0
            for it in list(state.items) + list(state.pending.values()):
                try:
                    total += len(_json.dumps(it.payload, default=str))
                except Exception:
                    total += 1024
                if total >= max_bytes:
                    return True
        return False

    async def drop_expired(self, *, run_id: str, conn: ConnectionDoc) -> int:
        """Phase 5 -- drop items older than ``expiry_seconds``.

        Walks the queue's items deque AND the pending dict and removes
        any item whose ``enqueued_at_ms`` is older than the threshold.
        Returns the number of items dropped (for diagnostics).
        """
        expiry = conn.expiry_seconds or 0
        if expiry <= 0:
            return 0
        state = self._state(run_id, conn)
        cutoff_ms = int(time.time() * 1000) - (expiry * 1000)
        before = len(state.items) + len(state.pending)
        state.items = deque(it for it in state.items if it.enqueued_at_ms >= cutoff_ms)
        state.pending = {
            item_id: it for item_id, it in state.pending.items()
            if it.enqueued_at_ms >= cutoff_ms
        }
        after = len(state.items) + len(state.pending)
        return max(0, before - after)

    async def snapshot(self, run_id: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        per_run = self._queues.get(run_id) or {}
        for key, state in per_run.items():
            out[key] = {
                "depth": len(state.items),
                "pending": len(state.pending),
                "seq": state.seq,
            }
        return out

    async def reset_run(self, run_id: str) -> None:
        self._queues.pop(run_id, None)
