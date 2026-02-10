"""Cache layer for session state and temporary data.

This module provides a modular Redis caching system with:
- RedisClient: Base client with connection management and core operations
- SessionCache: Session metadata and context caching
- AgentStateCache: Active agent tracking per session
- RateLimiter: Sliding window rate limiting

For backward compatibility, RedisSentinelClient is still available as a facade
that composes all the above modules.
"""

from .agent_state_cache import AgentStateCache
from .base import RedisClient
from .rate_limiter import RateLimiter
from .redis_client import (
    RedisSentinelClient,
    close_redis,
    get_redis_client,
    init_redis,
)
from .session_cache import SessionCache

__all__ = [
    # New modular classes
    "RedisClient",
    "SessionCache",
    "AgentStateCache",
    "RateLimiter",
    # Backward compatible (facade + singleton management)
    "RedisSentinelClient",
    "get_redis_client",
    "init_redis",
    "close_redis",
]
