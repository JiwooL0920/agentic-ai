#!/usr/bin/env python3
"""
Initialize DynamoDB tables in ScyllaDB Alternator.

This script creates the required tables for chat session management:
- devassist-sessions: User session metadata
- devassist-history: Chat message history

Run this once after deploying ScyllaDB to initialize the schema.
"""

import asyncio
import logging
import sys
from pathlib import Path

import aioboto3
import structlog
from botocore.config import Config

logger = structlog.get_logger()


class DynamoDBTableInitializer:
    """Initialize DynamoDB-compatible tables in ScyllaDB Alternator."""

    def __init__(self, endpoint_url: str, region: str = "us-east-1", access_key: str = "cassandra", secret_key: str = "cassandra"):
        self.endpoint_url = endpoint_url
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self._session = aioboto3.Session()
        self._config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            connect_timeout=10,
            read_timeout=30,
        )

    async def create_sessions_table(self, blueprint: str = "devassist"):
        """
        Create sessions table.
        
        Schema:
        - PK: session_id (String)
        - Attributes: user_id, blueprint, session_title, session_state, 
                     message_count, created_on, modified_on, expires_at
        """
        table_name = f"{blueprint}-sessions"
        
        async with self._session.client(
            'dynamodb',
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=self._config,
        ) as client:
            try:
                await client.create_table(
                    TableName=table_name,
                    KeySchema=[
                        {'AttributeName': 'session_id', 'KeyType': 'HASH'},
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'session_id', 'AttributeType': 'S'},
                    ],
                    BillingMode='PAY_PER_REQUEST',
                )
                logger.info(f"✅ Created table: {table_name}")
                
                # Enable TTL
                try:
                    await client.update_time_to_live(
                        TableName=table_name,
                        TimeToLiveSpecification={
                            'Enabled': True,
                            'AttributeName': 'expires_at'
                        }
                    )
                    logger.info(f"✅ Enabled TTL on {table_name}")
                except Exception as e:
                    logger.warning(f"⚠️  TTL configuration skipped: {e}")
                
            except client.exceptions.ResourceInUseException:
                logger.info(f"✅ Table already exists: {table_name}")
            except Exception as e:
                logger.error(f"❌ Failed to create {table_name}: {e}")
                raise

    async def create_history_table(self, blueprint: str = "devassist"):
        """
        Create history table.
        
        Schema:
        - PK: session_id (String)
        - SK: created_on (String) - ISO timestamp for time-series queries
        - GSI: user_id (for querying user's message history)
        """
        table_name = f"{blueprint}-history"
        
        async with self._session.client(
            'dynamodb',
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=self._config,
        ) as client:
            try:
                await client.create_table(
                    TableName=table_name,
                    KeySchema=[
                        {'AttributeName': 'session_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_on', 'KeyType': 'RANGE'},
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'session_id', 'AttributeType': 'S'},
                        {'AttributeName': 'created_on', 'AttributeType': 'S'},
                        {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    ],
                    GlobalSecondaryIndexes=[
                        {
                            'IndexName': 'user-index',
                            'KeySchema': [
                                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            ],
                            'Projection': {'ProjectionType': 'ALL'},
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST',
                )
                logger.info(f"✅ Created table: {table_name}")
                
                # Enable TTL
                try:
                    await client.update_time_to_live(
                        TableName=table_name,
                        TimeToLiveSpecification={
                            'Enabled': True,
                            'AttributeName': 'expires_at'
                        }
                    )
                    logger.info(f"✅ Enabled TTL on {table_name}")
                except Exception as e:
                    logger.warning(f"⚠️  TTL configuration skipped: {e}")
                
            except client.exceptions.ResourceInUseException:
                logger.info(f"✅ Table already exists: {table_name}")
            except Exception as e:
                logger.error(f"❌ Failed to create {table_name}: {e}")
                raise

    async def list_tables(self):
        """List all tables."""
        async with self._session.client(
            'dynamodb',
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=self._config,
        ) as client:
            response = await client.list_tables()
            return response.get('TableNames', [])

    async def describe_table(self, table_name: str):
        """Describe table schema."""
        async with self._session.client(
            'dynamodb',
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=self._config,
        ) as client:
            response = await client.describe_table(TableName=table_name)
            return response['Table']


async def main():
    """Main initialization routine."""
    # LocalStack DynamoDB endpoint (inside cluster)
    # For local access from outside cluster, use port-forward:
    # kubectl port-forward -n localstack svc/localstack 4566:4566
    
    endpoint_url = "http://localstack.localstack.svc.cluster.local:4566"
    
    logger.info("🚀 Initializing DynamoDB tables in LocalStack")
    logger.info(f"   Endpoint: {endpoint_url}")
    
    initializer = DynamoDBTableInitializer(endpoint_url, access_key="test", secret_key="test")
    
    try:
        # Create tables
        await initializer.create_sessions_table(blueprint="devassist")
        await initializer.create_history_table(blueprint="devassist")
        
        # List all tables
        logger.info("\n📋 Existing tables:")
        tables = await initializer.list_tables()
        for table in sorted(tables):
            logger.info(f"   - {table}")
        
        logger.info("\n✅ Initialization complete!")
        
    except Exception as e:
        logger.error(f"\n❌ Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    
    asyncio.run(main())
