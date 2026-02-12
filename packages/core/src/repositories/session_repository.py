"""
Session repository for chat session management.

Handles CRUD operations for chat sessions stored in ScyllaDB.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

import structlog
from botocore.exceptions import BotoCoreError, ClientError
from redis.exceptions import RedisError

from ..cache.redis_client import get_redis_client
from ..config import get_settings
from .dynamodb_client import calculate_ttl, get_dynamodb_client
from .schema_evolution import DEFAULT_KNOWLEDGE_CONFIG, SchemaEvolution

logger = structlog.get_logger()
settings = get_settings()


class SessionState(StrEnum):
    """Session state enum."""

    ACTIVE = "active"
    PINNED = "pinned"
    UNPINNED = "unpinned"
    ARCHIVED = "archived"


class SessionRepository:
    """
    Repository for session management using ScyllaDB Alternator.

    Table: {blueprint}-sessions
    PK: session_id
    """

    def __init__(self, blueprint: str):
        self.blueprint = blueprint
        self.table_name = f"{blueprint}-sessions"
        self._dynamodb = get_dynamodb_client()

    async def create_session(
        self,
        user_id: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new chat session."""
        session_id = session_id or uuid4().hex
        now = datetime.now(UTC).isoformat()

        session = {
            'session_id': session_id,
            'user_id': user_id,
            'blueprint': self.blueprint,
            'session_state': SessionState.ACTIVE.value,
            'message_count': 0,
            'knowledge_config': DEFAULT_KNOWLEDGE_CONFIG.copy(),
            'created_on': now,
            'modified_on': now,
            'expires_at': calculate_ttl(settings.session_ttl_days),
            'schema_version': 2,
        }

        await self._dynamodb.put_item(self.table_name, session)

        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user_id,
            blueprint=self.blueprint,
        )

        return session

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session by ID."""
        # Try cache first
        try:
            redis = get_redis_client()
            if redis:
                cached = await redis.get_cached_session(session_id)
                if cached:
                    logger.debug("session_cache_hit", session_id=session_id)
                    return cached
        except RedisError as e:
            logger.warning("redis_cache_error", error=str(e))

        # Query ScyllaDB
        session = await self._dynamodb.get_item(
            self.table_name,
            key={'session_id': session_id},
        )

        # Cache for future requests and apply schema migration
        if session:
            # Lazy migration: upgrade schema on read
            session = SchemaEvolution.migrate_session(session)

            try:
                redis = get_redis_client()
                if redis:
                    await redis.cache_session(
                        session_id,
                        session,
                        ttl=settings.session_cache_ttl,
                    )
            except RedisError as e:
                logger.warning("redis_cache_error", error=str(e))

        return session

    async def get_user_sessions(
        self,
        user_id: str,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get all sessions for a user.

        Note: Since session_id is the partition key (not user_id), we use a scan
        operation with a filter. For production scale, consider adding a GSI on user_id.
        """
        # For now, use scan with filter (not optimal for scale but works for MVP)
        # TODO: Add GSI for user_id for better performance

        # Temporary implementation: scan all sessions and filter by user_id
        # This is acceptable for development/MVP with limited data
        async with self._dynamodb._session.client(**self._dynamodb._get_client_params()) as client:
            try:
                response = await client.scan(
                    TableName=self.table_name,
                    FilterExpression='user_id = :uid',
                    ExpressionAttributeValues={':uid': {'S': user_id}},
                )
                sessions = [self._dynamodb._deserialize_item(item) for item in response.get('Items', [])]
            except (ClientError, BotoCoreError) as e:
                logger.error("scan_error", table=self.table_name, error=str(e))
                # Return empty list on error rather than failing
                return []

        # Filter archived if needed
        if not include_archived:
            sessions = [
                s for s in sessions
                if s.get('session_state') != SessionState.ARCHIVED.value
            ]

        # Sort by modified_on (most recent first)
        sessions.sort(key=lambda x: x.get('modified_on', ''), reverse=True)

        # Separate pinned sessions to the top
        pinned = [s for s in sessions if s.get('session_state') == SessionState.PINNED.value]
        others = [s for s in sessions if s.get('session_state') != SessionState.PINNED.value]

        return pinned + others

    async def update_state(
        self,
        session_id: str,
        user_id: str,
        new_state: SessionState,
    ) -> bool:
        """Update session state (pin/unpin/archive)."""
        now = datetime.now(UTC).isoformat()

        success = await self._dynamodb.update_item(
            self.table_name,
            key={'session_id': session_id},
            updates={
                'session_state': new_state.value,
                'modified_on': now,
            },
        )

        if success:
            # Invalidate cache
            try:
                redis = get_redis_client()
                if redis:
                    await redis.invalidate_session(session_id)
                    await redis.invalidate_user_sessions(user_id, self.blueprint)
            except RedisError as e:
                logger.warning("redis_invalidate_error", error=str(e))

            logger.info(
                "session_state_updated",
                session_id=session_id,
                new_state=new_state.value,
            )

        return success

    async def update_title(self, session_id: str, title: str) -> bool:
        """Update session title (usually from first user message)."""
        now = datetime.now(UTC).isoformat()

        success = await self._dynamodb.update_item(
            self.table_name,
            key={'session_id': session_id},
            updates={
                'session_title': title,
                'modified_on': now,
            },
        )

        if success:
            # Invalidate cache
            try:
                redis = get_redis_client()
                if redis:
                    await redis.invalidate_session(session_id)
            except RedisError as e:
                logger.warning("redis_invalidate_error", error=str(e))

        return success

    async def update_knowledge_config(
        self,
        session_id: str,
        knowledge_config: dict[str, Any],
    ) -> bool:
        now = datetime.now(UTC).isoformat()

        success = await self._dynamodb.update_item(
            self.table_name,
            key={'session_id': session_id},
            updates={
                'knowledge_config': knowledge_config,
                'modified_on': now,
            },
        )

        if success:
            try:
                redis = get_redis_client()
                if redis:
                    await redis.invalidate_session(session_id)
            except RedisError as e:
                logger.warning("redis_invalidate_error", error=str(e))

            logger.info(
                "knowledge_config_updated",
                session_id=session_id,
                active_scopes=knowledge_config.get('active_scopes', []),
            )

        return success

    async def touch_session(self, session_id: str, increment_messages: bool = False) -> None:
        """Update session's modified_on timestamp and optionally increment message count."""
        now = datetime.now(UTC).isoformat()

        updates = {'modified_on': now}

        if increment_messages:
            # Get current session to increment
            session = await self.get_session(session_id)
            if session:
                current_count = session.get('message_count', 0)
                updates['message_count'] = current_count + 1

        await self._dynamodb.update_item(
            self.table_name,
            key={'session_id': session_id},
            updates=updates,
        )

        # Invalidate cache
        try:
            redis = get_redis_client()
            if redis:
                await redis.invalidate_session(session_id)
        except RedisError as e:
            logger.warning("redis_invalidate_error", error=str(e))
