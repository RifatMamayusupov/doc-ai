"""Redis client and utilities for caching and pub/sub."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from app.config import settings


class RedisClient:
    """
    Redis client for caching and pub/sub messaging.
    
    Used for:
    - WebSocket state across instances
    - Session caching
    - Rate limiting
    - Pub/sub for cross-instance communication
    """

    _instance: "RedisClient | None" = None
    _pool: redis.ConnectionPool | None = None
    _client: redis.Redis | None = None

    def __new__(cls) -> "RedisClient":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """Initialize Redis connection."""
        if self._client is not None:
            return

        self._pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=self._pool)

        # Test connection
        await self._client.ping()

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    @property
    def client(self) -> redis.Redis:
        """Get Redis client."""
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    # Cache operations
    async def get(self, key: str) -> str | None:
        """Get a value from cache."""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire: int | None = None,
    ) -> bool:
        """Set a value in cache."""
        return await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        """Delete a key."""
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self.client.exists(key) > 0

    # JSON helpers
    async def get_json(self, key: str) -> Any | None:
        """Get JSON data from cache."""
        data = await self.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        expire: int | None = None,
    ) -> bool:
        """Set JSON data in cache."""
        return await self.set(key, json.dumps(value), expire)

    # Rate limiting
    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded.
        
        Args:
            key: Rate limit key (e.g., "rate:user123")
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            (is_allowed, remaining_requests)
        """
        current = await self.client.get(key)

        if current is None:
            # First request in window
            await self.client.set(key, 1, ex=window_seconds)
            return True, max_requests - 1

        current_count = int(current)
        if current_count >= max_requests:
            return False, 0

        await self.client.incr(key)
        return True, max_requests - current_count - 1

    # Pub/Sub for cross-instance messaging
    async def publish(self, channel: str, message: dict) -> int:
        """Publish message to channel."""
        return await self.client.publish(channel, json.dumps(message))

    async def subscribe(self, *channels: str):
        """Subscribe to channels. Returns async generator."""
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub

    # WebSocket state
    async def add_ws_connection(
        self,
        user_id: str,
        connection_id: str,
        chat_id: str | None = None,
    ) -> None:
        """Track a WebSocket connection."""
        key = f"ws:user:{user_id}"
        await self.client.sadd(key, connection_id)
        await self.client.expire(key, 3600)  # 1 hour TTL

        if chat_id:
            chat_key = f"ws:chat:{chat_id}"
            await self.client.sadd(chat_key, connection_id)
            await self.client.expire(chat_key, 3600)

    async def remove_ws_connection(
        self,
        user_id: str,
        connection_id: str,
        chat_id: str | None = None,
    ) -> None:
        """Remove a WebSocket connection."""
        key = f"ws:user:{user_id}"
        await self.client.srem(key, connection_id)

        if chat_id:
            chat_key = f"ws:chat:{chat_id}"
            await self.client.srem(chat_key, connection_id)

    async def get_user_connections(self, user_id: str) -> set[str]:
        """Get all connection IDs for a user."""
        key = f"ws:user:{user_id}"
        return await self.client.smembers(key)

    async def get_chat_connections(self, chat_id: str) -> set[str]:
        """Get all connection IDs for a chat."""
        key = f"ws:chat:{chat_id}"
        return await self.client.smembers(key)


# Global instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency for getting Redis client."""
    return redis_client
