"""
Upstash Serverless Redis Cache Engine for GitScout.
Provides high-speed caching for issue lists, triage reports, and telemetry health.
Supports Upstash REST API and redis-py TCP fallback with graceful error degradation.
"""

import json
import logging
import time
from typing import Any, Optional, Dict
from app.config import settings

logger = logging.getLogger("gitscout.cache")

_upstash_client = None


def get_redis_client():
    """Lazily initialize and return the Upstash Redis client."""
    global _upstash_client
    if _upstash_client is not None:
        return _upstash_client

    if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
        try:
            from upstash_redis import Redis
            _upstash_client = Redis(
                url=settings.UPSTASH_REDIS_REST_URL,
                token=settings.UPSTASH_REDIS_REST_TOKEN,
            )
            logger.info("[OK] Initialized Upstash Serverless Redis REST client.")
        except Exception as exc:
            logger.warning(f"[!] Failed to initialize Upstash Redis: {exc}")
            _upstash_client = None

    return _upstash_client


async def get_cached_json(key: str) -> Optional[Any]:
    """Retrieve and deserialize a JSON object from cache."""
    client = get_redis_client()
    if not client:
        return None

    try:
        data = client.get(key)
        if data:
            if isinstance(data, (dict, list)):
                return data
            return json.loads(data)
    except Exception as exc:
        logger.debug(f"[CACHE READ ERROR] {key}: {exc}")
    return None


async def set_cached_json(key: str, data: Any, ttl_seconds: int = 120) -> bool:
    """Serialize and store a JSON object in cache with TTL."""
    client = get_redis_client()
    if not client:
        return False

    try:
        serialized = json.dumps(data) if not isinstance(data, str) else data
        client.set(key, serialized, ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.debug(f"[CACHE WRITE ERROR] {key}: {exc}")
        return False


async def invalidate_cache_pattern(pattern: str = "gitscout:*") -> int:
    """Invalidate keys matching a prefix/pattern."""
    client = get_redis_client()
    if not client:
        return 0

    try:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
            return len(keys)
    except Exception as exc:
        logger.debug(f"[CACHE INVALIDATE ERROR] {pattern}: {exc}")
    return 0


async def ping_redis_health() -> Dict[str, Any]:
    """Check Redis health and measure round-trip latency."""
    client = get_redis_client()
    if not client:
        return {"status": "unconfigured", "type": "none"}

    try:
        t0 = time.perf_counter()
        pong = client.ping()
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "status": "connected" if pong else "degraded",
            "latency_ms": latency_ms,
            "provider": "Upstash Serverless Redis",
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "provider": "Upstash Serverless Redis",
        }
