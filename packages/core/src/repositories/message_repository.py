"""
Message repository for chat history.

Handles CRUD operations for chat messages stored in ScyllaDB.
"""

import time
from datetime import UTC, datetime
from uuid import uuid4

import structlog

from ..config import get_settings
from .dynamodb_client import calculate_ttl, get_dynamodb_client
from .schema_evolution import SchemaEvolution
from .session_repository import SessionRepository

logger = structlog.get_logger()
settings = get_settings()


class MessageRepository:
    """
    Repository for chat messages using ScyllaDB Alternator.

    Table: {blueprint}-history
    PK: session_id (HASH)
    SK: timestamp (RANGE) - Unix epoch in milliseconds for time-series queries
    """

    def __init__(self, blueprint: str):
        self.blueprint = blueprint
        self.table_name = f"{blueprint}-history"
        self._dynamodb = get_dynamodb_client()

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent: str | None = None,
        metadata: dict | None = None,
        timestamp_ms: int | None = None,
    ) -> dict:
        """Save a single chat message.

        Args:
            session_id: Session identifier
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            agent: Optional agent name
            metadata: Optional metadata dict
            timestamp_ms: Optional Unix epoch milliseconds. If not provided,
                         uses current time. Pass explicit timestamps when saving
                         multiple messages to ensure correct ordering.

        Returns:
            The saved message dict including generated fields
        """
        message_id = uuid4().hex
        # Use Unix epoch milliseconds for sort key (Number type in DynamoDB)
        timestamp = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
        created_on = datetime.now(UTC).isoformat()

        message = {
            'session_id': session_id,
            'timestamp': timestamp,  # Sort key - Number (epoch ms)
            'created_on': created_on,  # Human-readable ISO timestamp
            'message_id': message_id,
            'role': role,  # 'user', 'assistant', 'system'
            'content': content,
            'expires_at': calculate_ttl(settings.history_ttl_days),
            'schema_version': 1,
        }

        if agent:
            message['agent'] = agent

        if metadata:
            message['metadata'] = metadata

        await self._dynamodb.put_item(self.table_name, message)

        logger.debug(
            "message_saved",
            session_id=session_id,
            message_id=message_id,
            role=role,
        )

        return message

    async def get_session_messages(
        self,
        session_id: str,
        limit: int | None = None,
        ascending: bool = True,
    ) -> list[dict]:
        """Get all messages for a session, ordered by timestamp.

        Note: ScyllaDB Alternator may not reliably honor ScanIndexForward,
        so we sort in Python to ensure correct ordering.
        """
        messages = await self._dynamodb.query(
            self.table_name,
            partition_key='session_id',
            partition_value=session_id,
            sort_ascending=ascending,
            limit=limit,
        )

        # Lazy migration: upgrade schema on read
        migrated = [SchemaEvolution.migrate_message(m) for m in messages]

        # Sort in Python to ensure correct order (ScyllaDB Alternator workaround)
        migrated.sort(key=lambda m: m.get('timestamp', 0), reverse=not ascending)

        return migrated

    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get the N most recent messages for a session."""
        # Query in descending order and reverse
        messages = await self._dynamodb.query(
            self.table_name,
            partition_key='session_id',
            partition_value=session_id,
            sort_ascending=False,
            limit=limit,
        )

        # Lazy migration and reverse to chronological order
        return [SchemaEvolution.migrate_message(m) for m in reversed(messages)]

    async def save_conversation_turn(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        bot_response: str,
        agent: str | None = None,
    ):
        """
        Save a complete conversation turn (user + assistant messages).

        Also updates session metadata.
        """
        # Generate timestamps with guaranteed ordering (user first, assistant second)
        base_timestamp = int(time.time() * 1000)
        user_timestamp = base_timestamp
        assistant_timestamp = base_timestamp + 1  # 1ms later ensures correct sort order

        # Save user message
        await self.save_message(
            session_id=session_id,
            role='user',
            content=user_message,
            timestamp_ms=user_timestamp,
        )

        # Save assistant response
        await self.save_message(
            session_id=session_id,
            role='assistant',
            content=bot_response,
            agent=agent,
            timestamp_ms=assistant_timestamp,
        )

        # Update session timestamps and count
        session_repo = SessionRepository(self.blueprint)
        await session_repo.touch_session(session_id, increment_messages=True)

        logger.info(
            "conversation_turn_saved",
            session_id=session_id,
            user_message_length=len(user_message),
            bot_response_length=len(bot_response),
        )
