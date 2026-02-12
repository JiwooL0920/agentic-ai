"""Base Redis client with connection management and core operations."""

from __future__ import annotations

import builtins
from collections.abc import Mapping
from typing import Any

import redis.asyncio as aioredis
import structlog
from redis.asyncio.sentinel import Sentinel
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from ..config import get_settings

logger = structlog.get_logger()


class RedisClient:
    """
    Base async Redis client with Sentinel support and fallback to direct connection.

    Provides core operations:
    - Connection management (connect/disconnect)
    - Basic key-value operations (get/set/delete)
    - TTL management
    - Pipeline support for batch operations
    - JSON serialization helpers
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        password: str | None = None,
        master_name: str = "mymaster",
        socket_timeout: float = 5.0,
    ):
        settings = get_settings()
        self._host = host or settings.redis_host
        self._port = port or settings.redis_port
        self._password = password or settings.redis_password
        self._master_name = master_name
        self._socket_timeout = socket_timeout

        self._sentinel: Sentinel | None = None
        self._client: aioredis.Redis | None = None  # type: ignore[type-arg]
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    @property
    def client(self) -> aioredis.Redis:  # type: ignore[type-arg]
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    async def connect(self) -> None:
        """Connect to Redis Sentinel or fallback to direct connection."""
        if self._connected:
            return

        try:
            self._client = await self._connect_sentinel()
            logger.info("redis_sentinel_connected", master=self._master_name)
        except (RedisConnectionError, RedisError) as e:
            logger.warning("redis_sentinel_failed", error=str(e))
            self._client = await self._connect_direct()
            logger.info("redis_direct_connected")

        self._connected = True

    async def _connect_sentinel(self) -> aioredis.Redis:  # type: ignore[type-arg]
        """Attempt Sentinel connection."""
        sentinel_hosts = [(self._host, self._port)]
        self._sentinel = Sentinel(
            sentinel_hosts,
            socket_timeout=self._socket_timeout,
            password=self._password,
        )
        master = self._sentinel.master_for(
            self._master_name,
            socket_timeout=self._socket_timeout,
            decode_responses=True,
        )
        await master.ping()
        return master

    async def _connect_direct(self) -> aioredis.Redis:  # type: ignore[type-arg]
        """Fallback to direct Redis connection."""
        client = aioredis.Redis(
            host=self._host,
            port=self._port,
            password=self._password,
            decode_responses=True,
            socket_timeout=self._socket_timeout,
        )
        await client.ping()
        return client

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False
            logger.info("redis_disconnected")

    async def ping(self) -> bool:
        """Check if Redis is reachable."""
        try:
            await self.client.ping()
            return True
        except RedisError:
            return False

    async def get(self, key: str) -> str | None:
        """Get value by key."""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> None:
        """Set key-value with optional TTL."""
        if ttl:
            await self.client.setex(key, ttl, value)
        else:
            await self.client.set(key, value)

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns count of deleted keys."""
        if not keys:
            return 0
        return await self.client.delete(*keys)

    async def exists(self, *keys: str) -> int:
        """Check if keys exist. Returns count of existing keys."""
        if not keys:
            return 0
        return await self.client.exists(*keys)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set TTL on a key."""
        return await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """Get remaining TTL of a key. Returns -1 if no TTL, -2 if key doesn't exist."""
        return await self.client.ttl(key)

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern. Use sparingly in production."""
        return await self.client.keys(pattern)

    def pipeline(self) -> Any:
        """Create a pipeline for batch operations."""
        return self.client.pipeline()

    async def sadd(self, key: str, *values: str) -> int:
        """Add values to a set."""
        return await self.client.sadd(key, *values)

    async def srem(self, key: str, *values: str) -> int:
        """Remove values from a set."""
        return await self.client.srem(key, *values)

    async def smembers(self, key: str) -> builtins.set[str]:
        """Get all members of a set."""
        return await self.client.smembers(key)

    async def zadd(
        self,
        key: str,
        mapping: Mapping[str | bytes, bytes | float | int | str],
    ) -> int:
        """Add members to a sorted set with scores."""
        return await self.client.zadd(key, mapping)

    async def zremrangebyscore(
        self,
        key: str,
        min_score: float,
        max_score: float,
    ) -> int:
        """Remove members from sorted set by score range."""
        return await self.client.zremrangebyscore(key, min_score, max_score)

    async def zcard(self, key: str) -> int:
        """Get the number of members in a sorted set."""
        return await self.client.zcard(key)
