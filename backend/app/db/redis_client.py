"""
Redis client for caching and task queue.
"""

import logging
import json
from typing import Any, Optional
from redis import Redis, ConnectionError as RedisConnectionError
from app.config import get_settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with convenience methods."""

    def __init__(self, url: str):
        """
        Initialize Redis client.

        Args:
            url: Redis connection URL (redis://...)
        """
        self.url = url
        try:
            self._client = Redis.from_url(url, decode_responses=True)
            # Test connection
            self._client.ping()
            logger.info(f"Successfully connected to Redis at {url}")
        except RedisConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        try:
            return self._client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    def set(
        self, key: str, value: str, ex: Optional[int] = None, nx: bool = False
    ) -> bool:
        """
        Set key to value.

        Args:
            key: Key name
            value: Value to store
            ex: Expiration time in seconds
            nx: Only set if key doesn't exist

        Returns:
            bool: True if successful
        """
        try:
            return self._client.set(key, value, ex=ex, nx=nx)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        try:
            return self._client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        try:
            return self._client.exists(*keys)
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return 0

    def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value by key."""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for key {key}: {e}")
        return None

    def set_json(
        self, key: str, value: dict, ex: Optional[int] = None, nx: bool = False
    ) -> bool:
        """Set JSON value."""
        try:
            json_str = json.dumps(value)
            return self.set(key, json_str, ex=ex, nx=nx)
        except (TypeError, json.JSONDecodeError) as e:
            logger.error(f"JSON encode error for key {key}: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        try:
            return self._client.incr(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        try:
            return self._client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    def flush_all(self):
        """Flush all keys (use with caution!)."""
        logger.warning("Flushing all Redis keys")
        self._client.flushall()

    @property
    def client(self) -> Redis:
        """Get underlying Redis client."""
        return self._client


# Global client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    Get or create Redis client singleton.

    Returns:
        RedisClient: Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        settings = get_settings()
        _redis_client = RedisClient(url=settings.redis_url)

    return _redis_client


def close_redis_client():
    """Close the global Redis client."""
    global _redis_client
    if _redis_client:
        _redis_client.client.close()
        _redis_client = None
