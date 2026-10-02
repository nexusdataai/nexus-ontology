"""DataQueueManager protocol + factory.

NiFi-style queues between ReAct journey steps. Phase 0 of the AI
Engine Data Queues plan introduces the abstraction; the runner does
not yet route through it. Two implementations:

  * ``InMemoryQueueManager``         -- default, ``asyncio.Queue`` per
    (run_id, ConnectionDoc). Zero infra dependency; preserves today's
    sync run-to-quiescence semantics.

  * ``RedisStreamsQueueManager``     -- opt-in via
    ``DATA_QUEUE_BACKEND=redis`` env var (Phase 4). Adds durability,
    consumer groups, and back-pressure across crashes.

The protocol stays intentionally narrow: enqueue / dequeue / ack /
depth / is_full / drop_expired / snapshot / reset_run. Anything
NiFi-specific (prioritizers, fan-in strategies, expiry sweeps) is
layered on top of these primitives in subsequent phases.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from loguru import logger

from src.models.automation_models import ConnectionDoc

dq_logger = logger.bind(component="data-queue")


@dataclass
class QueueItem:
    """One payload dequeued from a queue.

    ``item_id`` is the producer-assigned id used for XACK in the Redis
    backend; for the InMemory backend it's a monotonic per-queue
    sequence number. Callers MUST call :meth:`DataQueueManager.ack`
    with this id once the consumer has processed the item.
    """

    item_id: str
    payload: Dict[str, Any]
    enqueued_at_ms: int
    producer_step: str
    relationship: str


@runtime_checkable
class DataQueueManager(Protocol):
    """Async protocol for the queue abstraction.

    Identity for a queue is the tuple (run_id, conn.from_step,
    conn.from_relationship, conn.to_step, conn.to_param). The
    implementation must scope queues per ``run_id`` so concurrent runs
    of the same journey do not bleed into each other.
    """

    async def enqueue(
        self, *, run_id: str, conn: ConnectionDoc, payload: Dict[str, Any],
    ) -> str:
        """Push ``payload`` onto the queue identified by ``conn``.

        Returns the producer-assigned ``item_id``. Blocking (or
        soft-blocking) back-pressure behaviour is layered in Phase 2;
        Phase 0 implementations enqueue unconditionally.
        """
        ...

    async def dequeue(
        self, *, run_id: str, conn: ConnectionDoc, consumer: str = "default",
        block_ms: int = 0,
    ) -> Optional[QueueItem]:
        """Pop the next item off the queue (or None on timeout).

        ``consumer`` is the consumer identity inside a consumer group
        (Redis Streams Phase 4). For InMemory it has no effect.
        ``block_ms`` is the soft wait when the queue is empty;
        ``0`` returns immediately.
        """
        ...

    async def ack(
        self, *, run_id: str, conn: ConnectionDoc, consumer: str, item_id: str,
    ) -> None:
        """Acknowledge that ``item_id`` was processed. No-op for the
        InMemory backend; Redis XACK in Phase 4."""
        ...

    async def depth(self, *, run_id: str, conn: ConnectionDoc) -> int:
        """Current pending depth (items enqueued but not yet acked)."""
        ...

    async def is_full(self, *, run_id: str, conn: ConnectionDoc) -> bool:
        """Whether the queue has hit its capacity threshold.

        Phase 0 always returns False; Phase 2 layers threshold checks
        on top of this hook.
        """
        ...

    async def drop_expired(self, *, run_id: str, conn: ConnectionDoc) -> int:
        """Drop items older than the per-queue ``expiry_seconds``.

        Phase 0 returns 0; Phase 5 implements the actual sweep.
        """
        ...

    async def snapshot(self, run_id: str) -> Dict[str, Any]:
        """Return a JSON-shaped inspection blob for diagnostics.

        Shape: ``{queue_key: {depth: int, pending: int}}``.
        """
        ...

    async def reset_run(self, run_id: str) -> None:
        """Purge every queue owned by ``run_id``. Called by the runner
        on STATUS_COMPLETED / STATUS_FAILED to release memory (or
        Redis keys in Phase 4)."""
        ...


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


_BACKEND_ENV = "DATA_QUEUE_BACKEND"
_DEFAULT_BACKEND = "in_memory"


def queue_key(*, run_id: str, conn: ConnectionDoc) -> str:
    """Stable string key identifying one queue. Used by the snapshot
    payload and as the Redis Stream key in Phase 4."""
    return (
        f"nexus:queue:{run_id}:"
        f"{conn.from_step}.{conn.from_relationship}->"
        f"{conn.to_step}.{conn.to_param}"
    )


def make_data_queue_manager(backend: Optional[str] = None) -> "DataQueueManager":
    """Construct a manager based on ``DATA_QUEUE_BACKEND`` (or the arg).

    ``in_memory`` (default) returns :class:`InMemoryQueueManager`.
    ``redis`` returns :class:`RedisStreamsQueueManager` -- imported
    lazily so the dependency is only resolved when the Redis backend
    is actually requested (Phase 4).
    """
    name = (backend or os.environ.get(_BACKEND_ENV) or _DEFAULT_BACKEND).lower().strip()
    if name == "in_memory":
        from .in_memory import InMemoryQueueManager
        return InMemoryQueueManager()
    if name == "redis":
        try:
            from .redis_streams import RedisQueueUnavailable, RedisStreamsQueueManager
            return RedisStreamsQueueManager()
        except (ImportError, ModuleNotFoundError) as e:
            dq_logger.warning(
                f"Redis backend requested but client missing ({e}); falling back to in-memory"
            )
        except Exception as e:
            # RedisQueueUnavailable plus any other constructor-time
            # exception from the Redis client (connection refused etc).
            dq_logger.warning(
                f"Redis backend requested but unreachable ({e}); falling back to in-memory"
            )
        from .in_memory import InMemoryQueueManager
        return InMemoryQueueManager()
    dq_logger.warning(f"Unknown DATA_QUEUE_BACKEND='{name}'; falling back to in-memory")
    from .in_memory import InMemoryQueueManager
    return InMemoryQueueManager()


__all__ = [
    "DataQueueManager",
    "QueueItem",
    "make_data_queue_manager",
    "queue_key",
]
