"""
Redis async cache service.
Provides typed get/set helpers with automatic JSON serialisation.
"""
import json
from typing import Any, Optional
import redis.asyncio as aioredis
from backend.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    try:
        redis = await get_redis()
        value = await redis.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as e:
        logger.warning("cache_get_error", key=key, error=str(e))
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    try:
        redis = await get_redis()
        await redis.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning("cache_set_error", key=key, error=str(e))
        return False


async def cache_delete(key: str) -> None:
    try:
        redis = await get_redis()
        await redis.delete(key)
    except Exception as e:
        logger.warning("cache_delete_error", key=key, error=str(e))


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a glob pattern."""
    try:
        redis = await get_redis()
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
    except Exception as e:
        logger.warning("cache_delete_pattern_error", pattern=pattern, error=str(e))