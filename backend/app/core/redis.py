"""
app/core/redis.py

Async Redis client used for:
  1. Task queue (via Celery broker — separate connection)
  2. Dashboard statistics caching (TTL-based)
  3. Rate limiting (sliding window counter)
  4. Storing refresh token blacklist

Why a singleton client?
  redis.asyncio.from_url() creates a connection pool internally.
  Re-creating it per-request would exhaust file descriptors.
  We create once at startup and reuse across the process lifetime.
"""
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return (or lazily create) the shared async Redis client.

    Used as a FastAPI dependency:
        redis: aioredis.Redis = Depends(get_redis)
    """
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("Redis connection pool initialised url=%s", settings.REDIS_URL)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis client on application shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")
