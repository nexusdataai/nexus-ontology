"""
Copilot Session Store.

Phase 4.1 (data-organization spec) makes Redis the default backing store
for Copilot journey sessions - matching the spec's characterization of
Copilot as a "pure transient program". A key TTL (COPILOT_SESSION_TTL,
default 24h) enforces the ephemeral semantics; sessions still survive
pod restarts and load-balanced multi-replica traffic within that
window.

Legacy PostgreSQL and in-memory backends remain available via the
``COPILOT_SESSION_STORE`` env var (``redis`` | ``pg`` | ``memory``,
default ``redis``). ``USE_REDIS_COPILOT_SESSIONS=false`` restores the
old PG default for rollback.

Redis layout:

    copilot:sess:{session_id}   JSON string, TTL = COPILOT_SESSION_TTL
    copilot:sess:index          Sorted set, score = epoch seconds,
                                member = session_id (for list_recent)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from loguru import logger

ss_logger = logger.bind(component="copilot-session-store")


_DEFAULT_TTL = int(os.getenv("COPILOT_SESSION_TTL", "86400"))  # 24h


def _resolve_backend() -> str:
    """Return one of ``redis`` | ``pg`` | ``memory``.

    Priority:
      1. ``COPILOT_SESSION_STORE`` env var (explicit override).
      2. ``USE_REDIS_COPILOT_SESSIONS=false`` -> ``pg`` (Phase 4 rollback flag).
      3. Default -> ``redis``.
    """
    explicit = os.getenv("COPILOT_SESSION_STORE", "").strip().lower()
    if explicit in ("redis", "pg", "memory"):
        return explicit
    if os.getenv("USE_REDIS_COPILOT_SESSIONS", "true").strip().lower() == "false":
        return "pg"
    return "redis"


class CopilotSessionStore:
    """Session store with Redis (default), PostgreSQL, or in-memory backend."""

    _CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS copilot_sessions (
            session_id TEXT PRIMARY KEY,
            data JSONB NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """

    _REDIS_KEY = "copilot:sess:{sid}"
    _REDIS_INDEX = "copilot:sess:index"

    def __init__(self) -> None:
        self._mem: Dict[str, Dict[str, Any]] = {}
        self._engine = None
        self._use_pg = False
        self._use_redis = False
        self._ttl_secs = _DEFAULT_TTL

    async def initialize(self) -> None:
        backend = _resolve_backend()
        if backend == "redis":
            try:
                from src.services import redis_client
                r = await redis_client.get_redis()
                if r is None:
                    raise RuntimeError("redis client unavailable")
                # Simple ping to confirm connectivity.
                await r.ping()
                self._use_redis = True
                ss_logger.info(
                    "Copilot session store initialized with Redis (TTL={}s)",
                    self._ttl_secs,
                )
                return
            except Exception as e:
                ss_logger.warning(f"Redis session store init failed ({e}); trying PG fallback")
                backend = "pg"

        if backend == "pg":
            try:
                from sqlalchemy import create_engine, text
                host = os.getenv("FDW_PG_HOST", "")
                port = os.getenv("FDW_PG_PORT", "5432")
                db = os.getenv("FDW_PG_DATABASE", "")
                user = os.getenv("FDW_PG_USER", "")
                pw = os.getenv("FDW_PG_PASSWORD", "")
                if not host or not db:
                    ss_logger.info("FDW_PG_HOST/DB not set; using in-memory session store")
                    return
                url = f"postgresql://{user}:{pw}@{host}:{port}/{db}"
                engine = create_engine(url, pool_size=2, max_overflow=2)
                with engine.connect() as conn:
                    conn.execute(text(self._CREATE_SQL))
                    conn.commit()
                self._engine = engine
                self._use_pg = True
                ss_logger.info("Copilot session store initialized with PostgreSQL")
                return
            except Exception as e:
                ss_logger.warning(f"PostgreSQL session store init failed ({e}); using in-memory fallback")

        ss_logger.info("Copilot session store using in-memory backend")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def save(self, session_id: str, data: Dict[str, Any]) -> None:
        if self._use_redis:
            try:
                import asyncio
                asyncio.get_event_loop().create_task(self._redis_save(session_id, data))
                self._mem[session_id] = data  # local hot cache
                return
            except Exception as e:
                ss_logger.warning(f"Redis save failed for {session_id}: {e}; mirroring to memory")
                self._mem[session_id] = data
                return

        if not self._use_pg or not self._engine:
            self._mem[session_id] = data
            return
        try:
            from sqlalchemy import text
            with self._engine.connect() as conn:
                conn.execute(
                    text(
                        "INSERT INTO copilot_sessions (session_id, data, updated_at) "
                        "VALUES (:sid, cast(:data as jsonb), NOW()) "
                        "ON CONFLICT (session_id) DO UPDATE "
                        "SET data = cast(:data as jsonb), updated_at = NOW()"
                    ),
                    {"sid": session_id, "data": json.dumps(data, default=str)},
                )
                conn.commit()
        except Exception as e:
            ss_logger.warning(f"PG save failed for {session_id}: {e}; mirroring to memory")
            self._mem[session_id] = data

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self._use_redis:
            cached = self._mem.get(session_id)
            if cached is not None:
                return cached
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Called from an async context - use existing loop.
                    future = asyncio.ensure_future(self._redis_load(session_id))
                    if not future.done():
                        # Fall back to memory when called synchronously from within a running loop;
                        # callers should prefer aload() below when they need a hard fetch.
                        return None
                    return future.result()
                return loop.run_until_complete(self._redis_load(session_id))
            except Exception as e:
                ss_logger.debug(f"Redis load failed for {session_id}: {e}; falling back to memory")
                return self._mem.get(session_id)

        if self._use_pg and self._engine:
            try:
                from sqlalchemy import text
                with self._engine.connect() as conn:
                    row = conn.execute(
                        text("SELECT data FROM copilot_sessions WHERE session_id = :sid"),
                        {"sid": session_id},
                    ).fetchone()
                    if row:
                        data = row.data
                        return data if isinstance(data, dict) else json.loads(data)
            except Exception as e:
                ss_logger.warning(f"PG load failed for {session_id}: {e}; falling back to memory")
        return self._mem.get(session_id)

    def delete(self, session_id: str) -> None:
        self._mem.pop(session_id, None)
        if self._use_redis:
            try:
                import asyncio
                asyncio.get_event_loop().create_task(self._redis_delete(session_id))
            except Exception as e:
                ss_logger.debug(f"Redis delete failed for {session_id}: {e}")
            return
        if self._use_pg and self._engine:
            try:
                from sqlalchemy import text
                with self._engine.connect() as conn:
                    conn.execute(
                        text("DELETE FROM copilot_sessions WHERE session_id = :sid"),
                        {"sid": session_id},
                    )
                    conn.commit()
            except Exception as e:
                ss_logger.warning(f"PG delete failed for {session_id}: {e}")

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self._use_redis:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Best-effort fallback for sync callers inside a running loop.
                    return list(self._mem.values())[-limit:]
                return loop.run_until_complete(self._redis_list_recent(limit))
            except Exception as e:
                ss_logger.debug(f"Redis list_recent failed: {e}")
                return list(self._mem.values())[-limit:]

        if self._use_pg and self._engine:
            try:
                from sqlalchemy import text
                with self._engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            "SELECT session_id, data, updated_at "
                            "FROM copilot_sessions ORDER BY updated_at DESC LIMIT :n"
                        ),
                        {"n": limit},
                    ).fetchall()
                    out: List[Dict[str, Any]] = []
                    for r in rows:
                        data = r.data if isinstance(r.data, dict) else json.loads(r.data)
                        data["_updated_at"] = r.updated_at.isoformat() if r.updated_at else None
                        out.append(data)
                    return out
            except Exception as e:
                ss_logger.warning(f"PG list failed: {e}")
        return list(self._mem.values())[-limit:]

    # ------------------------------------------------------------------
    # Redis helpers (async internals)
    # ------------------------------------------------------------------

    async def _redis_save(self, session_id: str, data: Dict[str, Any]) -> None:
        from src.services import redis_client
        r = await redis_client.get_redis()
        if r is None:
            return
        key = self._REDIS_KEY.format(sid=session_id)
        blob = json.dumps(data, default=str)
        await r.set(key, blob, ex=self._ttl_secs)
        await r.zadd(self._REDIS_INDEX, {session_id: time.time()})
        # Cap the index size so it doesn't grow unbounded.
        await r.zremrangebyrank(self._REDIS_INDEX, 0, -5001)

    async def _redis_load(self, session_id: str) -> Optional[Dict[str, Any]]:
        from src.services import redis_client
        r = await redis_client.get_redis()
        if r is None:
            return None
        key = self._REDIS_KEY.format(sid=session_id)
        blob = await r.get(key)
        if not blob:
            return None
        if isinstance(blob, bytes):
            blob = blob.decode("utf-8")
        try:
            data = json.loads(blob)
            self._mem[session_id] = data
            return data
        except Exception:
            return None

    async def _redis_delete(self, session_id: str) -> None:
        from src.services import redis_client
        r = await redis_client.get_redis()
        if r is None:
            return
        await r.delete(self._REDIS_KEY.format(sid=session_id))
        await r.zrem(self._REDIS_INDEX, session_id)

    async def _redis_list_recent(self, limit: int) -> List[Dict[str, Any]]:
        from src.services import redis_client
        r = await redis_client.get_redis()
        if r is None:
            return []
        # newest first
        ids = await r.zrevrange(self._REDIS_INDEX, 0, max(0, limit - 1))
        out: List[Dict[str, Any]] = []
        for sid in ids or []:
            if isinstance(sid, bytes):
                sid = sid.decode("utf-8")
            data = await self._redis_load(sid)
            if data:
                data.setdefault("_updated_at", None)
                out.append(data)
        return out

    def count_by_status(self, lookback: int = 200) -> Dict[str, Any]:
        """Aggregate the most recent N sessions by ``status`` and return:

            {
              "by_status": {"planning": 0, "planned": 3, ...},
              "total_recent": 47,
              "stuck_awaiting_approval_24h": 0,
              "mode": "pg" | "memory",
            }

        ``stuck_awaiting_approval_24h`` counts sessions that have been
        sitting in ``awaiting_step_approval`` for more than 24 hours -
        a signal that a high-risk step never got Approved/Rejected and
        the journey is silently abandoned.
        """
        from datetime import datetime, timezone, timedelta

        sessions = self.list_recent(limit=lookback)
        by_status: Dict[str, int] = {}
        stuck = 0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        for s in sessions:
            status = str(s.get("status") or "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            if status == "awaiting_step_approval":
                ts_raw = s.get("_updated_at") or s.get("created_at")
                if isinstance(ts_raw, str):
                    try:
                        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        if ts < cutoff:
                            stuck += 1
                    except Exception:
                        pass

        return {
            "by_status": by_status,
            "total_recent": len(sessions),
            "stuck_awaiting_approval_24h": stuck,
            "mode": "pg" if self._use_pg else "memory",
        }
