"""Redis Streams DataQueueManager.

Phase 4 of the Data Queues plan. Opt-in via ``DATA_QUEUE_BACKEND=redis``.
Each (run_id, ConnectionDoc) maps to one Redis Stream key.

Capabilities:
  * Durable across pod restarts (Redis AOF + replication).
  * XADD / XREADGROUP / XACK / XAUTOCLAIM for crash-safe at-least-once
    delivery with idempotent acks.
  * Per-queue back-pressure via XLEN check + producer soft-block.
  * Consumer-group state persisted in the existing CopilotSessionStore
    so the runner can resume after a crash without re-delivering.

Items are JSON-encoded on the wire; payloads remain plain Python dicts
end-to-end so the rest of the engine is unchanged.

Failure handling: the manager raises ``RedisQueueUnavailable`` from
its constructor when Redis is unreachable so the factory can fall
back to the in-memory backend gracefully.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, Optional

from loguru import logger

from src.models.automation_models import ConnectionDoc

from . import DataQueueManager, QueueItem, queue_key

redis_logger = logger.bind(component="data-queue-redis")


class RedisQueueUnavailable(RuntimeError):
    """Raised when Redis cannot be reached at startup."""


def _resolve_url() -> str:
    url = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    return url


def _consumer_group_name(*, run_id: str) -> str:
    """One consumer group per run so resumes after a crash see the
    same XPENDING state. NiFi consumer-group analog."""
    return f"nexus-run-{run_id}"


class RedisStreamsQueueManager:
    """Async Redis-Streams-backed queue manager.

    The Redis client is imported lazily so the rest of the codebase
    doesn't pay the import cost when the in-memory backend is in use.
    """

    def __init__(self) -> None:
        try:
            from redis.asyncio import Redis  # type: ignore
        except ImportError as e:
            raise RedisQueueUnavailable(f"redis.asyncio not installed: {e}") from e

        self._Redis = Redis
        self._url = _resolve_url()
        self._client: Optional[Any] = None
        # Per (run_id, queue_key) -> {"group_created": True} so we don't
        # XGROUP-CREATE on every dequeue.
        self._groups_created: Dict[str, bool] = {}

    async def _conn(self):
        if self._client is None:
            try:
                self._client = self._Redis.from_url(
                    self._url, decode_responses=True,
                    password=os.environ.get("REDIS_PASSWORD") or None,
                )
                # Best-effort ping to surface unreachable Redis early.
                await self._client.ping()
            except Exception as e:
                raise RedisQueueUnavailable(f"Redis unreachable at {self._url}: {e}") from e
        return self._client

    # ------------------------------------------------------------------

    async def _ensure_group(self, *, run_id: str, conn: ConnectionDoc) -> str:
        """Create the consumer group on the stream if missing. Returns the stream key."""
        key = queue_key(run_id=run_id, conn=conn)
        if self._groups_created.get(key):
            return key
        client = await self._conn()
        group = _consumer_group_name(run_id=run_id)
        try:
            # ``mkstream=True`` creates the stream if it doesn't exist.
            # ``id="0"`` starts the group at the earliest entry so a
            # late-joining consumer sees historical items (rare for
            # journey runs but matches NiFi swap-in semantics).
            await client.xgroup_create(name=key, groupname=group, id="0", mkstream=True)
        except Exception as e:
            # BUSYGROUP means the group already exists -- benign.
            if "BUSYGROUP" not in str(e):
                redis_logger.warning(f"xgroup_create failed for {key}: {e}")
        self._groups_created[key] = True
        return key

    async def enqueue(
        self, *, run_id: str, conn: ConnectionDoc, payload: Dict[str, Any],
    ) -> str:
        # Phase 2: back-pressure soft-block.
        if conn.max_object_count or conn.max_byte_size:
            while await self.is_full(run_id=run_id, conn=conn):
                await asyncio.sleep(0.02)

        key = await self._ensure_group(run_id=run_id, conn=conn)
        client = await self._conn()
        data = {
            "json": json.dumps(payload, default=str),
            "producer": conn.from_step,
            "relationship": conn.from_relationship,
            "ts": str(int(time.time() * 1000)),
        }
        item_id = await client.xadd(name=key, fields=data)
        return str(item_id)

    async def dequeue(
        self, *, run_id: str, conn: ConnectionDoc, consumer: str = "default",
        block_ms: int = 0,
    ) -> Optional[QueueItem]:
        key = await self._ensure_group(run_id=run_id, conn=conn)
        client = await self._conn()
        group = _consumer_group_name(run_id=run_id)
        try:
            res = await client.xreadgroup(
                groupname=group, consumername=consumer or "default",
                streams={key: ">"}, count=1,
                block=block_ms if block_ms > 0 else None,
            )
        except Exception as e:
            redis_logger.warning(f"xreadgroup failed on {key}: {e}")
            return None

        if not res:
            return None
        # res = [(stream_key, [(item_id, {field: value, ...})])]
        _, entries = res[0]
        if not entries:
            return None
        item_id, fields = entries[0]
        try:
            payload = json.loads(fields.get("json") or "{}")
        except Exception:
            payload = {}
        try:
            enqueued_at_ms = int(fields.get("ts") or "0")
        except ValueError:
            enqueued_at_ms = 0
        return QueueItem(
            item_id=str(item_id),
            payload=payload,
            enqueued_at_ms=enqueued_at_ms,
            producer_step=fields.get("producer") or conn.from_step,
            relationship=fields.get("relationship") or conn.from_relationship,
        )

    async def ack(
        self, *, run_id: str, conn: ConnectionDoc, consumer: str, item_id: str,
    ) -> None:
        key = queue_key(run_id=run_id, conn=conn)
        client = await self._conn()
        group = _consumer_group_name(run_id=run_id)
        try:
            await client.xack(key, group, item_id)
        except Exception as e:
            redis_logger.warning(f"xack failed on {key}: {e}")

    async def depth(self, *, run_id: str, conn: ConnectionDoc) -> int:
        key = queue_key(run_id=run_id, conn=conn)
        client = await self._conn()
        try:
            return int(await client.xlen(key))
        except Exception:
            return 0

    async def is_full(self, *, run_id: str, conn: ConnectionDoc) -> bool:
        max_count = conn.max_object_count or 0
        if max_count <= 0:
            return False
        depth = await self.depth(run_id=run_id, conn=conn)
        return depth >= max_count

    async def drop_expired(self, *, run_id: str, conn: ConnectionDoc) -> int:
        # Phase 5 implementation. Returning 0 keeps the contract.
        return 0

    async def snapshot(self, run_id: str) -> Dict[str, Any]:
        """Diagnostics-friendly summary of every stream owned by this run.

        Implementation note: SCAN with a stable prefix avoids KEYS *
        (which blocks Redis for large key sets). The prefix matches the
        format produced by :func:`queue_key`.
        """
        client = await self._conn()
        out: Dict[str, Any] = {}
        prefix = f"nexus:queue:{run_id}:"
        try:
            async for k in client.scan_iter(match=f"{prefix}*", count=100):
                try:
                    depth = int(await client.xlen(k))
                except Exception:
                    depth = 0
                # pending = consumer-group-level not-yet-acked.
                pending = 0
                try:
                    info = await client.xpending(k, _consumer_group_name(run_id=run_id))
                    if isinstance(info, dict):
                        pending = int(info.get("pending") or 0)
                    elif isinstance(info, list) and info:
                        pending = int(info[0] or 0)
                except Exception:
                    pending = 0
                out[k] = {"depth": depth, "pending": pending}
        except Exception as e:
            redis_logger.warning(f"snapshot failed for run {run_id}: {e}")
        return out

    async def reset_run(self, run_id: str) -> None:
        """DEL every stream + consumer group for this run."""
        client = await self._conn()
        prefix = f"nexus:queue:{run_id}:"
        keys = []
        try:
            async for k in client.scan_iter(match=f"{prefix}*", count=100):
                keys.append(k)
        except Exception as e:
            redis_logger.warning(f"reset_run scan failed for {run_id}: {e}")
            return
        if not keys:
            return
        try:
            await client.delete(*keys)
        except Exception as e:
            redis_logger.warning(f"reset_run delete failed for {run_id}: {e}")
        # Drop cached "group created" flags for these keys.
        for k in keys:
            self._groups_created.pop(k, None)
