"""
Message repository for chat history.

Handles CRUD operations for chat messages stored in ScyllaDB.
"""

from typing import List, Optional
from datetime import datetime, timezone
from uuid import uuid4
import time

import structlog

from .dynamodb_client import get_dynamodb_client, calculate_ttl
from .session_repository import SessionRepository
from .schema_evolution import SchemaEvolution
from ..config import get_settings

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
        agent: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Save a single chat message."""
        message_id = uuid4().hex
        # Use Unix epoch milliseconds for sort key (Number type in DynamoDB)
        timestamp = int(time.time() * 1000)
        created_on = datetime.now(timezone.utc).isoformat()
        
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
        limit: Optional[int] = None,
        ascending: bool = True,
    ) -> List[dict]:
        """Get all messages for a session, ordered by timestamp."""
        messages = await self._dynamodb.query(
            self.table_name,
            partition_key='session_id',
            partition_value=session_id,
            sort_ascending=ascending,
            limit=limit,
        )
        
        # Lazy migration: upgrade schema on read
        return [SchemaEvolution.migrate_message(m) for m in messages]
    
    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[dict]:
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
        agent: Optional[str] = None,
    ):
        """
        Save a complete conversation turn (user + assistant messages).
        
        Also updates session metadata.
        """
        # Save user message
        await self.save_message(
            session_id=session_id,
            role='user',
            content=user_message,
        )
        
        # Save assistant response
        await self.save_message(
            session_id=session_id,
            role='assistant',
            content=bot_response,
            agent=agent,
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
