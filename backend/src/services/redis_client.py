"""
Redis Client Utility

Async Redis connection pool with graceful fallback to in-memory when Redis is unavailable.
Used by simulator services to offload tabular data from the Python process heap.

Connection pools are tracked **per-event-loop**: ``redis.asyncio`` connections
are bound to the loop on which they were opened, so reusing a pool from a
different loop (e.g. journey stages that wrap each step in
``asyncio.new_event_loop()``) raises ``RuntimeError: Event loop is closed``
and silently turns every read into a cache miss. The per-loop cache below
keeps the FastAPI request loop pool stable while letting journey threads
get their own short-lived pool.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

redis_logger = logger.bind(component="redis-client")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_TTL = int(os.getenv("REDIS_SIMULATOR_TTL", "604800"))

# `_redis_pool` and `_redis_available` are kept as module globals for back-compat
# with diagnostics_api which reads `_redis_available` directly. `_redis_pool`
# is updated to point at the most-recently-used per-loop pool.
_redis_pool = None
_redis_available: Optional[bool] = None
_fallback_store: Dict[str, str] = {}

# Per-loop pool cache: id(loop) -> (pool, loop). The loop reference is kept
# so we can call ``loop.is_closed()`` during eviction.
_pools_by_loop: Dict[int, Tuple[Any, "asyncio.AbstractEventLoop"]] = {}


def _evict_closed_loops() -> None:
    """Drop pool entries whose loop has already been closed."""
    if not _pools_by_loop:
        return
    for lid in [k for k, (_, lp) in list(_pools_by_loop.items()) if lp.is_closed()]:
        _pools_by_loop.pop(lid, None)


async def get_redis():
    """Get or create the async Redis connection pool for the *current* loop.

    Returns None if Redis is permanently unavailable for this process or if
    we're not currently inside a running event loop.
    """
    global _redis_pool, _redis_available
    if _redis_available is False:
        return None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None

    _evict_closed_loops()

    cached = _pools_by_loop.get(id(loop))
    if cached is not None:
        pool, _lp = cached
        _redis_pool = pool
        return pool

    try:
        import redis.asyncio as aioredis
        pool = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            max_connections=20,
            socket_connect_timeout=3,
            socket_timeout=5,
        )
        await pool.ping()
        _pools_by_loop[id(loop)] = (pool, loop)
        _redis_pool = pool
        if _redis_available is None:
            redis_logger.info(f"Redis connected at {REDIS_URL}")
        _redis_available = True
        return pool
    except Exception as e:
        redis_logger.warning(f"Redis unavailable ({e}), falling back to in-memory store")
        _redis_available = False
        _redis_pool = None
        return None


async def redis_get(key: str) -> Optional[str]:
    """Get a value from Redis or fallback store."""
    r = await get_redis()
    if r:
        try:
            return await r.get(key)
        except Exception as e:
            redis_logger.warning(f"Redis GET failed for {key}: {e}")
    return _fallback_store.get(key)


async def redis_set(key: str, value: str, ttl: int = DEFAULT_TTL) -> bool:
    """Set a value in Redis or fallback store."""
    r = await get_redis()
    if r:
        try:
            await r.set(key, value, ex=ttl)
            return True
        except Exception as e:
            redis_logger.warning(f"Redis SET failed for {key}: {e}")
    _fallback_store[key] = value
    return True


async def redis_delete(key: str) -> bool:
    """Delete a key from Redis or fallback store."""
    r = await get_redis()
    if r:
        try:
            await r.delete(key)
            return True
        except Exception as e:
            redis_logger.warning(f"Redis DELETE failed for {key}: {e}")
    _fallback_store.pop(key, None)
    return True


async def redis_keys(pattern: str) -> List[str]:
    """Find keys matching a pattern."""
    r = await get_redis()
    if r:
        try:
            return [k async for k in r.scan_iter(match=pattern, count=1000)]
        except Exception as e:
            redis_logger.warning(f"Redis SCAN failed for {pattern}: {e}")
    return [k for k in _fallback_store if _matches_pattern(k, pattern)]


async def redis_flush_prefix(prefix: str) -> int:
    """Delete all keys with a given prefix."""
    keys = await redis_keys(f"{prefix}*")
    count = 0
    r = await get_redis()
    for key in keys:
        if r:
            try:
                await r.delete(key)
                count += 1
                continue
            except Exception:
                pass
        _fallback_store.pop(key, None)
        count += 1
    return count


async def get_json(key: str) -> Optional[Any]:
    """Get and JSON-decode a value."""
    raw = await redis_get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


async def set_json(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
    """JSON-encode and set a value."""
    return await redis_set(key, json.dumps(value, default=str), ttl)


async def redis_mget(keys: List[str]) -> List[Optional[str]]:
    """Batch get multiple keys in a single round-trip."""
    if not keys:
        return []
    r = await get_redis()
    if r:
        try:
            return await r.mget(keys)
        except Exception as e:
            redis_logger.warning(f"Redis MGET failed: {e}")
    return [_fallback_store.get(k) for k in keys]


async def redis_mset(mapping: Dict[str, str], ttl: int = DEFAULT_TTL) -> bool:
    """Batch set multiple keys in a single pipeline with TTL."""
    if not mapping:
        return True
    r = await get_redis()
    if r:
        try:
            pipe = r.pipeline()
            for k, v in mapping.items():
                pipe.set(k, v, ex=ttl)
            await pipe.execute()
            return True
        except Exception as e:
            redis_logger.warning(f"Redis MSET pipeline failed: {e}")
    _fallback_store.update(mapping)
    return True


async def is_available() -> bool:
    """Check if Redis is available."""
    r = await get_redis()
    return r is not None


def _matches_pattern(key: str, pattern: str) -> bool:
    """Simple glob pattern match for fallback store."""
    if pattern.endswith("*"):
        return key.startswith(pattern[:-1])
    return key == pattern
