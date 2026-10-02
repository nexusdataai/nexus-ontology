"""
Control Plane Cache — thin async wrapper around redis_client.

Provides JSON-aware get/set with TTL and graceful fallback.
Key format: cp:{prefix}:{sha256_hex[:16]}
"""

import hashlib
import json
from typing import Any, Optional

from loguru import logger
from src.services.redis_client import get_json, set_json

_log = logger.bind(component="cp-cache")


def _make_key(prefix: str, raw: str) -> str:
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"cp:{prefix}:{h}"


async def get_cached(prefix: str, raw_key: str) -> Optional[Any]:
    key = _make_key(prefix, raw_key)
    try:
        return await get_json(key)
    except Exception as e:
        _log.debug(f"Cache miss/error for {key}: {e}")
        return None


async def set_cached(prefix: str, raw_key: str, value: Any, ttl_s: int = 300) -> None:
    key = _make_key(prefix, raw_key)
    try:
        await set_json(key, value, ttl=ttl_s)
    except Exception as e:
        _log.debug(f"Cache set failed for {key}: {e}")
