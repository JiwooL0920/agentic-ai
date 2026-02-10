# Chat History and Session Management Implementation Plan

## Executive Summary

This document outlines the adoption plan for implementing a production-grade chat history and session management system for the Agentic AI Platform. The design is based on the proven OneMesh architecture patterns, adapted for our Kubernetes-native stack (Kind cluster, ScyllaDB, Ollama).

**Key technology choice:** ScyllaDB with Alternator (DynamoDB-compatible API) - the same database Discord uses to store trillions of chat messages.

**Cross-validated against:** Industry best practices from AWS, Redis Labs, TanStack, SQLAlchemy 2.0, FastAPI production patterns, ScyllaDB case studies (Discord, Zillow), and 2025/2026 LLM architecture research.

---

## Table of Contents

1. [Architecture Comparison](#architecture-comparison)
2. [Industry Best Practices Validation](#industry-best-practices-validation)
3. [Storage Strategy Decision](#storage-strategy-decision)
4. [Implementation Phases](#implementation-phases)
5. [Database Schema Design](#database-schema-design)
6. [Backend Implementation](#backend-implementation)
7. [Frontend Implementation](#frontend-implementation)
8. [Infrastructure Changes](#infrastructure-changes)
9. [Context Window Management](#context-window-management)
10. [Production-Grade Scalability](#production-grade-scalability)
11. [Migration Path](#migration-path)

---

## Architecture Comparison

### OneMesh Reference Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│    React UI      │     │   FastAPI        │     │   DynamoDB       │
│  (TanStack Query)│────▶│   Backend        │────▶│   (Primary)      │
└──────────────────┘     └──────────────────┘     ├──────────────────┤
                                                  │   Snowflake      │
                                                  │   (Analytics)    │
                                                  └──────────────────┘
```

**Key Patterns:**
- Dual-write storage (DynamoDB + Snowflake)
- Three DynamoDB tables (chat_history, chat_history_objects, user_sessions)
- Session states (active, pinned, unpinned, archived)
- Sliding window context management
- TanStack Query for client-side caching

### Our Target Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│    Next.js UI    │     │   FastAPI        │     │  ScyllaDB        │
│  (TanStack Query)│────▶│   Backend        │────▶│  (Alternator)    │
│                  │     │                  │     │  (Chat History)  │
│                  │     │                  │     ├──────────────────┤
│                  │     │                  │────▶│  Redis Sentinel  │
│                  │     │                  │     │  (Cache/State)   │
└──────────────────┘     └──────────────────┘     ├──────────────────┤
                                                  │  PostgreSQL      │
                                                  │  (pgvector only) │
                                                  └──────────────────┘
```

**Architecture Rationale:**
1. **ScyllaDB with Alternator API** - DynamoDB-compatible, Kubernetes-native, Discord-proven at trillion-message scale
2. **Redis Sentinel for caching** - Session state, agent state, rate limiting (already deployed in cluster)
3. **PostgreSQL (pgvector) for RAG only** - Vector embeddings and document search
4. **Separation of concerns** - Chat data in ScyllaDB, embeddings in pgvector

**Why ScyllaDB over LocalStack DynamoDB:**
| Aspect | LocalStack DynamoDB | ScyllaDB |
|--------|---------------------|----------|
| Production use | Dev/test only | Discord, Zillow, Samsung |
| Kubernetes-native | ❌ Emulation layer | ✅ Official Scylla Operator |
| Performance | Simulated | Single-digit ms latency |
| Scaling | N/A | Horizontal (add nodes) |
| TTL support | ✅ | ✅ Native |
| API compatibility | DynamoDB | DynamoDB (Alternator) |

**Kind Cluster Services:**
- `scylla-client.scylla.svc.cluster.local:8000` - ScyllaDB Alternator (DynamoDB API)
- `redis-sentinel.redis-sentinel:6379` - Redis Sentinel cluster
- `postgres-rw.database.svc.cluster.local:5432` - CNPG PostgreSQL

---

## Industry Best Practices Validation

This section documents cross-validation of our plan against current industry standards (2025-2026) from authoritative sources.

### Source References

| Source | Domain | Key Validation |
|--------|--------|----------------|
| [Redis LLM Session Memory](https://redis.io/docs/latest/develop/ai/redisvl/user_guide/session_manager) | Session Management | StandardSessionManager pattern for role-based messages |
| [Factory.ai Context Compaction](https://www.factory.ai/news/compressing-context) | Context Window | Incremental summarization vs. full re-summarization |
| [mem0.ai LLM Chat History](https://mem0.ai/blog/llm-chat-history-summarization-guide-2025) | Memory Management | Semantic memory layers, ~90% token cost reduction |
| [SQLAlchemy 2.0 Async Patterns](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio) | Database Access | async_sessionmaker, connection pooling |
| [FastAPI Production Patterns 2025](https://orchestrator.dev/blog/2025-1-30-fastapi-production-patterns/) | API Architecture | Domain-driven structure, repository pattern |
| [TanStack Query v5](https://tanstack.com/query/v5/docs) | Frontend State | Optimistic updates with rollback |
| [AWS Database-per-Service](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-data-persistence/database-per-service.html) | Scalability | Microservices data patterns, CQRS |
| [DynamoDB TTL Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html) | Data Retention | Native TTL for automatic item expiration |

### Validated Architectural Decisions

#### 1. Session State Design ✅ VALIDATED

**Industry Standard (SparkCo AI, 2025):**
> "Maintain concise session states containing only essential elements (user context, preferences)"

**Our Implementation:** Aligns with storing minimal metadata in `conversations` table with full messages in separate `messages` table. Essential session state (title, state, timestamps) kept separate from message content.

#### 2. Centralized Database-Backed Storage ✅ VALIDATED

**Industry Standard (SparkCo AI, 2025):**
> "The 2025 consensus emphasizes centralized, database-backed session storage rather than stateless or client-side solutions"

**Our Implementation:** ScyllaDB (Alternator API) for chat history with Redis Sentinel for caching. Replaces current in-memory `AgentStateManager` with Redis-backed persistence. PostgreSQL (pgvector) remains for RAG/embeddings only.

#### 3. Sliding Window Context Management ✅ VALIDATED WITH IMPROVEMENT

**Industry Standard (Factory.ai, 2025):**
> "Rather than re-summarizing entire conversations per request, maintain a lightweight persistent conversation state with rolling summaries"

**Our Original Plan:** Re-summarize older messages on each request (OneMesh pattern).

**IMPROVEMENT NEEDED:** Adopt **incremental anchored summarization** pattern:
- Store `summarized_content` per message
- Only summarize newly dropped spans, not entire history
- Reduces linear cost growth as conversations lengthen

#### 4. Redis Sentinel Session Architecture ✅ VALIDATED

**Industry Standard (Redis Labs, 2025):**
> "Using Redis as a session store allows multiple application instances to access shared session data without losing state during crashes or restarts"

**Our Implementation:** Redis Sentinel (`redis-sentinel.redis-sentinel:6379`) for session caching with automatic failover. Enables horizontal scaling of FastAPI workers with shared state and high availability.

#### 5. DynamoDB for Chat History ✅ VALIDATED

**Industry Comparison:**
| Criteria | DynamoDB Advantage | PostgreSQL Advantage |
|----------|-------------------|---------------------|
| Chat access patterns | ✅ Key-value lookups | ❌ Overkill |
| Auto-scaling | ✅ Automatic | ❌ Manual |
| Latency at scale | ✅ Single-digit ms | ⚠️ Needs optimization |
| TTL/Expiration | ✅ Native support | ⚠️ Manual (pg_partman) |
| AWS production parity | ✅ Direct migration | ⚠️ Different service |
| Vector search | ❌ Separate service | ✅ pgvector |

**Validated Decision:** DynamoDB for chat history is optimal because:
- Chat history has simple access patterns (session_id → messages)
- Native TTL support for session expiration
- Matches OneMesh reference architecture exactly
- ScyllaDB Alternator provides DynamoDB-compatible API
- Kubernetes-native with Scylla Operator (production-grade)
- Proven at scale: Discord uses ScyllaDB for trillion+ chat messages
- Keep pgvector for RAG/embeddings (separate concern)

#### 6. TanStack Query Caching ✅ VALIDATED

**Industry Standard (TanStack v5 Docs):**
> "Optimistic updates with snapshot rollback using onMutate/onError/onSettled pattern"

**Our Implementation:** Correctly uses this pattern for session updates. Added improvement: persist optimistic updates to storage during mutations.

#### 7. FastAPI Repository Pattern ✅ VALIDATED

**Industry Standard (FastAPI Best Practices 2025):**
> "Organize code by business domain... separate business logic (service layer) from data access (repository layer)"

**Our Implementation:** Correctly separates `repositories/`, `services/`, and `api/routes/` directories.

### Identified Gaps and Improvements

| Gap | Industry Practice | Our Improvement |
|-----|------------------|-----------------|
| **Context re-summarization** | Incremental summarization | Store rolling summaries per message, only summarize new drops |
| **Connection pooling** | Pool size 20, pre_ping, recycle | Add explicit pool configuration to SQLAlchemy engine |
| **Data retention** | DynamoDB native TTL | Configure TTL on `expires_at` attribute for automatic expiration |
| **Rate limiting** | Redis-based rate limiting | Add API rate limiting middleware |
| **Observability** | Structured logging, metrics | Add latency tracking per operation |

---

## Storage Strategy Decision

### Recommendation: DynamoDB + Redis Sentinel

| Service | Purpose | Cluster Endpoint |
|---------|---------|------------------|
| **ScyllaDB (Alternator)** | Chat history, session metadata | `http://scylla-client.scylla.svc.cluster.local:8000` |
| **Redis Sentinel** | Session cache, agent state, rate limiting | `redis-sentinel.redis-sentinel:6379` |
| **PostgreSQL (pgvector)** | Vector embeddings, document search (RAG only) | `postgres-rw.database.svc.cluster.local:5432` |

### Why ScyllaDB for Chat History

| Factor | ScyllaDB (Alternator) | PostgreSQL |
|--------|----------------------|------------|
| **Terraform ready** | ✅ Tables already defined | ⚠️ Schema needs migration |
| **OneMesh pattern** | ✅ Exact match | ❌ Different architecture |
| **Access patterns** | ✅ Key-value (session_id) | ⚠️ Overkill for simple lookups |
| **TTL support** | ✅ Native `expires_at` | ⚠️ Manual pg_partman |
| **Production path** | ✅ Direct to AWS DynamoDB | ⚠️ Different service |
| **GSI for user queries** | ✅ Already configured | ⚠️ Needs index design |

### Storage Separation (Clean Architecture)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER SEPARATION                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CHAT DATA (DynamoDB)              VECTOR DATA (PostgreSQL)         │
│  ═══════════════════              ═════════════════════════         │
│                                                                     │
│  devassist-sessions                documents                        │
│  ├─ session_id (PK)                ├─ Ingested files metadata       │
│  ├─ user_id                        └─ agent_scope, source_type      │
│  ├─ session_title                                                   │
│  ├─ session_state                  document_chunks                  │
│  ├─ modified_on                    ├─ Chunked text content          │
│  └─ expires_at (TTL)               ├─ embedding vector(768)         │
│                                    └─ HNSW index for similarity     │
│  devassist-history                                                  │
│  ├─ session_id (PK)                                                 │
│  ├─ timestamp (SK)                 ┌─────────────────────────┐      │
│  ├─ user_id (GSI)                  │  CACHE LAYER (Redis)   │      │
│  ├─ role (user/assistant)          │  ═══════════════════   │      │
│  ├─ content                        │  • Session metadata    │      │
│  ├─ agent_name                     │  • Agent state         │      │
│  └─ expires_at (TTL)               │  • Rate limiting       │      │
│                                    └─────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

**Benefits of this separation:**
1. **Chat history** optimized for time-series access (DynamoDB)
2. **Embeddings** optimized for similarity search (pgvector)
3. **Session state** optimized for fast access (Redis)
4. **Each service does what it's best at**

---

## Implementation Phases

### Phase 1: Core Backend (Backend First)

**Goal:** Persistent chat history and session management APIs

| Task | Description | Priority |
|------|-------------|----------|
| 1.1 | Create ChatHistory repository (DynamoDB) | P0 |
| 1.2 | Create Session repository with CRUD | P0 |
| 1.3 | Add context formatting service | P0 |
| 1.4 | Update chat endpoints with persistence | P0 |
| 1.5 | Add session management endpoints | P0 |
| 1.6 | Redis caching layer for sessions | P1 |

### Phase 2: Frontend Session UI

**Goal:** Session drawer and history navigation

| Task | Description | Priority |
|------|-------------|----------|
| 2.1 | Add TanStack Query setup | P0 |
| 2.2 | Create SessionDrawer component | P0 |
| 2.3 | Implement session list with date grouping | P0 |
| 2.4 | Add session state management (pin/archive) | P1 |
| 2.5 | Session history loading and display | P0 |
| 2.6 | Optimistic updates and cache invalidation | P1 |

### Phase 3: Advanced Features

**Goal:** Context optimization and analytics

| Task | Description | Priority |
|------|-------------|----------|
| 3.1 | Sliding window context with summarization | P1 |
| 3.2 | Session expiration (TTL) | P2 |
| 3.3 | Agent state persistence (Redis) | P1 |
| 3.4 | Analytics event publishing (DynamoDB) | P2 |

---

## Database Schema Design

### DynamoDB Tables (Already in Terraform)

Your existing Terraform at `blueprints/devassist/terraform/main.tf` already defines the required tables:

**Table 1: `devassist-sessions` (User Sessions)**
```hcl
# Already defined in blueprints/devassist/terraform/main.tf
module "sessions" {
  source        = "../../../terraform/modules/dynamodb"
  table_name    = "${var.blueprint_name}-sessions"
  hash_key      = "session_id"
  ttl_attribute = "expires_at"
}
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `session_id` | String (PK) | UUID identifying the session |
| `user_id` | String | User identifier |
| `blueprint` | String | Blueprint name (devassist) |
| `session_title` | String | Title (first query summarized) |
| `session_state` | String | `active`, `pinned`, `unpinned`, `archived` |
| `modified_on` | String | ISO timestamp of last activity |
| `created_on` | String | ISO timestamp of creation |
| `message_count` | Number | Total messages in session |
| `expires_at` | Number | TTL epoch timestamp |

**Table 2: `devassist-history` (Chat Messages)**
```hcl
# Already defined in blueprints/devassist/terraform/main.tf
module "history" {
  source         = "../../../terraform/modules/dynamodb"
  table_name     = "${var.blueprint_name}-history"
  hash_key       = "session_id"
  range_key      = "timestamp"
  range_key_type = "N"
  ttl_attribute  = "expires_at"
  
  additional_attributes = [{ name = "user_id", type = "S" }]
  
  global_secondary_indexes = [{
    name     = "user-index"
    hash_key = "user_id"
  }]
}
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `session_id` | String (PK) | Session UUID |
| `timestamp` | Number (SK) | Unix timestamp (milliseconds) |
| `user_id` | String (GSI) | For querying user's messages |
| `message_id` | String | Unique message UUID |
| `role` | String | `user`, `assistant`, `system` |
| `content` | String | Message content |
| `agent_name` | String | Responding agent name |
| `search_results` | List | RAG search results (if any) |
| `suggestions` | List | Follow-up suggestions |
| `process_duration` | Number | Response time in ms |
| `expires_at` | Number | TTL epoch timestamp |

### Schema Comparison with OneMesh

| OneMesh Table | Our Table | Status |
|---------------|-----------|--------|
| `user_sessions` | `devassist-sessions` | ✅ Already in Terraform |
| `chat_history` | `devassist-history` | ✅ Already in Terraform |
| `chat_history_objects` | N/A | Query with session_id + timestamp range |

### Enhanced Terraform (Optional Additions)

To fully match OneMesh, consider adding a GSI for sorting sessions by modification time:

```hcl
# Enhancement to blueprints/devassist/terraform/main.tf

module "sessions" {
  source        = "../../../terraform/modules/dynamodb"
  table_name    = "${var.blueprint_name}-sessions"
  hash_key      = "user_id"           # Changed: user_id as PK
  range_key     = "session_id"        # Added: session_id as SK
  ttl_attribute = "expires_at"
  
  additional_attributes = [
    { name = "modified_on", type = "S" }
  ]
  
  global_secondary_indexes = [
    {
      name            = "user-modified-index"
      hash_key        = "user_id"
      range_key       = "modified_on"
      projection_type = "ALL"
    }
  ]
  
  tags = local.tags
}
```

**Note:** The current schema uses `session_id` as the primary key. For efficient "get all sessions for user sorted by date" queries (like OneMesh), consider the enhancement above. However, the existing schema works for MVP with a scan + filter.

---

## Backend Implementation

### Project Structure

```
packages/core/src/
├── repositories/               # NEW: Data access layer
│   ├── __init__.py
│   ├── base.py                # Abstract repository interface
│   ├── dynamodb_client.py     # DynamoDB client wrapper
│   ├── session_repository.py  # Session CRUD (DynamoDB)
│   └── message_repository.py  # Message CRUD (DynamoDB)
├── cache/                      # NEW: Cache layer
│   ├── __init__.py
│   └── redis_client.py        # Redis Sentinel client
├── services/                   # NEW: Business logic layer
│   ├── __init__.py
│   ├── chat_history_service.py
│   └── context_formatter.py   # Sliding window implementation
├── api/routes/
│   ├── chat.py               # MODIFY: Add persistence calls
│   └── sessions.py           # NEW: Session management endpoints
└── models/                    # NEW: Pydantic schemas
    ├── __init__.py
    ├── session.py
    └── message.py
```

### Key Backend Components

#### 1. DynamoDB Client Wrapper

```python
# packages/core/src/repositories/dynamodb_client.py

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import time

import aioboto3
import structlog
from botocore.config import Config

from ..config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class DynamoDBClient:
    """
    Async DynamoDB-compatible client for ScyllaDB Alternator.
    
    ScyllaDB's Alternator API provides DynamoDB compatibility,
    allowing us to use standard boto3/aioboto3 with minimal changes.
    
    Features:
    - Connection pooling via aioboto3
    - ScyllaDB Alternator endpoint configuration
    - Common operations (put, get, query, update)
    """
    
    def __init__(self):
        self._session = aioboto3.Session()
        self._config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            connect_timeout=5,
            read_timeout=30,
        )
    
    def _get_client_params(self) -> dict:
        """Get boto3 client parameters for ScyllaDB Alternator."""
        return {
            'service_name': 'dynamodb',
            'endpoint_url': settings.scylladb_endpoint,
            'region_name': settings.aws_region,
            'aws_access_key_id': settings.aws_access_key_id,
            'aws_secret_access_key': settings.aws_secret_access_key,
            'config': self._config,
        }
    
    async def put_item(
        self,
        table_name: str,
        item: Dict[str, Any],
    ) -> bool:
        """Put item into DynamoDB table."""
        async with self._session.client(**self._get_client_params()) as client:
            try:
                await client.put_item(
                    TableName=table_name,
                    Item=self._serialize_item(item),
                )
                return True
            except Exception as e:
                logger.error("dynamodb_put_error", table=table_name, error=str(e))
                raise
    
    async def get_item(
        self,
        table_name: str,
        key: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Get single item by key."""
        async with self._session.client(**self._get_client_params()) as client:
            response = await client.get_item(
                TableName=table_name,
                Key=self._serialize_item(key),
            )
            item = response.get('Item')
            return self._deserialize_item(item) if item else None
    
    async def query(
        self,
        table_name: str,
        partition_key: str,
        partition_value: str,
        index_name: Optional[str] = None,
        sort_ascending: bool = True,
        limit: Optional[int] = None,
        filter_expression: Optional[str] = None,
        filter_values: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query items by partition key.
        Matches OneMesh query_dynamodb_table pattern.
        """
        async with self._session.client(**self._get_client_params()) as client:
            params = {
                'TableName': table_name,
                'KeyConditionExpression': f'{partition_key} = :pk',
                'ExpressionAttributeValues': {':pk': {'S': partition_value}},
                'ScanIndexForward': sort_ascending,
            }
            
            if index_name:
                params['IndexName'] = index_name
            
            if limit:
                params['Limit'] = limit
            
            if filter_expression:
                params['FilterExpression'] = filter_expression
                if filter_values:
                    for k, v in filter_values.items():
                        params['ExpressionAttributeValues'][k] = self._serialize_value(v)
            
            response = await client.query(**params)
            return [self._deserialize_item(item) for item in response.get('Items', [])]
    
    async def update_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        update_data: Dict[str, Any],
    ) -> bool:
        """Update item attributes."""
        async with self._session.client(**self._get_client_params()) as client:
            update_expr_parts = []
            attr_names = {}
            attr_values = {}
            
            for i, (k, v) in enumerate(update_data.items()):
                update_expr_parts.append(f'#{k} = :v{i}')
                attr_names[f'#{k}'] = k
                attr_values[f':v{i}'] = self._serialize_value(v)
            
            await client.update_item(
                TableName=table_name,
                Key=self._serialize_item(key),
                UpdateExpression='SET ' + ', '.join(update_expr_parts),
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values,
            )
            return True
    
    def _serialize_item(self, item: Dict[str, Any]) -> Dict[str, Dict]:
        """Convert Python dict to DynamoDB format."""
        return {k: self._serialize_value(v) for k, v in item.items() if v is not None}
    
    def _serialize_value(self, value: Any) -> Dict:
        """Convert Python value to DynamoDB type."""
        if isinstance(value, str):
            return {'S': value}
        elif isinstance(value, bool):
            return {'BOOL': value}
        elif isinstance(value, (int, float)):
            return {'N': str(value)}
        elif isinstance(value, list):
            return {'L': [self._serialize_value(v) for v in value]}
        elif isinstance(value, dict):
            return {'M': self._serialize_item(value)}
        elif value is None:
            return {'NULL': True}
        else:
            return {'S': str(value)}
    
    def _deserialize_item(self, item: Dict[str, Dict]) -> Dict[str, Any]:
        """Convert DynamoDB format to Python dict."""
        return {k: self._deserialize_value(v) for k, v in item.items()}
    
    def _deserialize_value(self, value: Dict) -> Any:
        """Convert DynamoDB type to Python value."""
        if 'S' in value:
            return value['S']
        elif 'N' in value:
            n = value['N']
            return int(n) if '.' not in n else float(n)
        elif 'BOOL' in value:
            return value['BOOL']
        elif 'L' in value:
            return [self._deserialize_value(v) for v in value['L']]
        elif 'M' in value:
            return self._deserialize_item(value['M'])
        elif 'NULL' in value:
            return None
        return None


# Global singleton
_dynamodb_client = DynamoDBClient()


def get_dynamodb_client() -> DynamoDBClient:
    return _dynamodb_client
```

#### 2. Session Repository (DynamoDB Implementation)

```python
# packages/core/src/repositories/session_repository.py

from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
from enum import Enum
import time

import structlog

from ..config import get_settings
from ..cache.redis_client import get_redis_client
from .dynamodb_client import get_dynamodb_client

logger = structlog.get_logger()
settings = get_settings()


class SessionState(str, Enum):
    ACTIVE = "active"
    PINNED = "pinned"
    UNPINNED = "unpinned"
    ARCHIVED = "archived"


class SessionRepository:
    """
    Repository for session management using ScyllaDB Alternator.
    
    Implements OneMesh's user_sessions patterns with:
    - Redis Sentinel caching for frequently accessed sessions
    - DynamoDB for persistent storage
    - TTL support for automatic expiration
    """
    
    def __init__(self, blueprint: str = "devassist"):
        self.blueprint = blueprint
        self.table_name = f"{blueprint}-sessions"
        self._dynamodb = get_dynamodb_client()
        self._redis = get_redis_client()
    
    async def create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new chat session.
        Matches OneMesh session creation pattern.
        """
        now = datetime.now(timezone.utc)
        session_id = session_id or uuid4().hex
        
        # Calculate TTL (7 days from now)
        ttl_days = 7
        expires_at = int(time.time()) + (ttl_days * 24 * 60 * 60)
        
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "blueprint": self.blueprint,
            "session_state": SessionState.ACTIVE.value,
            "session_title": None,
            "created_on": now.isoformat(),
            "modified_on": now.isoformat(),
            "message_count": 0,
            "expires_at": expires_at,
        }
        
        await self._dynamodb.put_item(self.table_name, session)
        
        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user_id,
            blueprint=self.blueprint,
        )
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        # Check Redis cache first
        cached = await self._redis.get_cached_session(session_id)
        if cached:
            logger.debug("session_cache_hit", session_id=session_id)
            return cached
        
        # Query DynamoDB
        session = await self._dynamodb.get_item(
            self.table_name,
            {"session_id": session_id}
        )
        
        # Cache for future requests
        if session:
            await self._redis.cache_session(session_id, session)
        
        return session
    
    async def get_user_sessions(
        self,
        user_id: str,
        include_archived: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get sessions for a user, sorted by activity.
        
        Note: Current schema uses session_id as PK.
        For production, consider GSI on user_id + modified_on.
        """
        # Query all sessions and filter by user_id
        # TODO: Use GSI when available for better performance
        async with self._dynamodb._session.client(
            **self._dynamodb._get_client_params()
        ) as client:
            response = await client.scan(
                TableName=self.table_name,
                FilterExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': {'S': user_id}},
            )
        
        sessions = [
            self._dynamodb._deserialize_item(item) 
            for item in response.get('Items', [])
        ]
        
        # Filter archived if needed
        if not include_archived:
            sessions = [
                s for s in sessions 
                if s.get('session_state') != SessionState.ARCHIVED.value
            ]
        
        # Sort: pinned first, then by modified_on DESC
        def sort_key(s):
            is_pinned = 0 if s.get('session_state') == SessionState.PINNED.value else 1
            modified = s.get('modified_on', '')
            return (is_pinned, modified)
        
        sessions.sort(key=sort_key, reverse=True)
        
        return sessions[:limit]
    
    async def update_state(
        self,
        session_id: str,
        user_id: str,
        new_state: SessionState,
    ) -> bool:
        """
        Update session state (pin/unpin/archive).
        Implements soft-delete via 'archived' state.
        """
        now = datetime.now(timezone.utc)
        
        update_data = {
            "session_state": new_state.value,
            "modified_on": now.isoformat(),
        }
        
        # Track pinned timestamp for sorting
        if new_state == SessionState.PINNED:
            update_data["pinned_at"] = now.isoformat()
        
        await self._dynamodb.update_item(
            self.table_name,
            {"session_id": session_id},
            update_data,
        )
        
        # Invalidate cache
        await self._redis.invalidate_session(session_id)
        
        logger.info(
            "session_state_updated",
            session_id=session_id,
            new_state=new_state.value,
        )
        
        return True
    
    async def update_title(
        self,
        session_id: str,
        title: str,
    ) -> bool:
        """
        Update session title.
        Called after first message to set summarized title.
        """
        await self._dynamodb.update_item(
            self.table_name,
            {"session_id": session_id},
            {
                "session_title": title[:500],  # Truncate to max length
                "modified_on": datetime.now(timezone.utc).isoformat(),
            },
        )
        
        # Invalidate cache
        await self._redis.invalidate_session(session_id)
        
        return True
    
    async def touch_session(
        self,
        session_id: str,
        increment_count: bool = True,
    ):
        """Update modified_on timestamp (called on new messages)."""
        update_data = {
            "modified_on": datetime.now(timezone.utc).isoformat(),
        }
        
        # Note: DynamoDB doesn't support atomic increment in this simple update
        # For production, use UpdateExpression with ADD
        if increment_count:
            session = await self.get_session(session_id)
            if session:
                update_data["message_count"] = session.get("message_count", 0) + 1
        
        await self._dynamodb.update_item(
            self.table_name,
            {"session_id": session_id},
            update_data,
        )
        
        # Invalidate cache
        await self._redis.invalidate_session(session_id)
```

#### 3. Message Repository (DynamoDB Implementation)

```python
# packages/core/src/repositories/message_repository.py

from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
import time

import structlog

from ..config import get_settings
from .dynamodb_client import get_dynamodb_client
from .session_repository import SessionRepository

logger = structlog.get_logger()
settings = get_settings()


class MessageRepository:
    """
    Repository for chat messages using ScyllaDB Alternator.
    
    Table: {blueprint}-history
    PK: session_id
    SK: timestamp (for ordering)
    GSI: user_id (for user's message history)
    """
    
    def __init__(self, blueprint: str = "devassist"):
        self.blueprint = blueprint
        self.table_name = f"{blueprint}-history"
        self._dynamodb = get_dynamodb_client()
        self._session_repo = SessionRepository(blueprint)
    
    async def save_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        search_results: Optional[List] = None,
        suggestions: Optional[List[str]] = None,
        process_duration: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Save a chat message.
        Matches OneMesh save_message_to_table pattern.
        """
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp() * 1000)  # Milliseconds for SK
        
        # Calculate TTL (30 days)
        ttl_days = 30
        expires_at = int(time.time()) + (ttl_days * 24 * 60 * 60)
        
        message = {
            "session_id": session_id,
            "timestamp": timestamp,
            "message_id": uuid4().hex,
            "user_id": user_id,
            "role": role,
            "content": content,
            "created_on": now.isoformat(),
            "expires_at": expires_at,
        }
        
        if agent_name:
            message["agent_name"] = agent_name
        if search_results:
            message["search_results"] = search_results
        if suggestions:
            message["suggestions"] = suggestions
        if process_duration:
            message["process_duration"] = process_duration
        
        await self._dynamodb.put_item(self.table_name, message)
        
        # Update session's modified_on and message_count
        await self._session_repo.touch_session(session_id, increment_count=True)
        
        logger.info(
            "message_saved",
            session_id=session_id,
            role=role,
            message_id=message["message_id"],
        )
        
        return message
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        ascending: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a session, ordered by timestamp.
        """
        messages = await self._dynamodb.query(
            self.table_name,
            partition_key="session_id",
            partition_value=session_id,
            sort_ascending=ascending,
            limit=limit,
        )
        
        return messages
    
    async def get_recent_messages(
        self,
        session_id: str,
        count: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get most recent N messages (for context window)."""
        messages = await self.get_session_messages(
            session_id,
            limit=count,
            ascending=False,  # Most recent first
        )
        
        # Reverse to chronological order
        return list(reversed(messages))
    
    async def save_conversation_turn(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        bot_response: str,
        agent_name: Optional[str] = None,
        search_results: Optional[List] = None,
        suggestions: Optional[List[str]] = None,
        process_duration: Optional[int] = None,
        summarized_query: Optional[str] = None,
    ) -> tuple[Dict, Dict]:
        """
        Save a complete conversation turn (user + assistant).
        Matches OneMesh log_history pattern.
        """
        # Save user message
        user_msg = await self.save_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=user_message,
        )
        
        # Save assistant message
        bot_msg = await self.save_message(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=bot_response,
            agent_name=agent_name,
            search_results=search_results,
            suggestions=suggestions,
            process_duration=process_duration,
        )
        
        # Update session title if this is the first message
        if summarized_query:
            session = await self._session_repo.get_session(session_id)
            if session and not session.get("session_title"):
                await self._session_repo.update_title(session_id, summarized_query)
        
        return user_msg, bot_msg
```

#### 2. Context Formatter Service

```python
# packages/core/src/services/context_formatter.py

from typing import List, Dict, Optional
from ollama import AsyncClient

from ..models.message import Message

# Sliding window configuration (from OneMesh)
RECENT_MESSAGES_FULL = 5      # Keep last N messages in full detail
SUMMARY_WINDOW = 5            # Messages between N and 2N get summarized
MAX_CONTEXT_TOKENS = 4096     # Token budget for chat history


class ContextFormatter:
    """
    Formats chat history for LLM context using sliding window approach.
    
    Strategy (from OneMesh):
    1. Last `limit` messages: Include in full detail
    2. Messages `limit` to `2*limit`: Summarize via LLM
    3. Older messages: Discard
    
    This balances recency (most relevant) with context (conversation flow).
    """
    
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        recent_count: int = RECENT_MESSAGES_FULL,
        summary_count: int = SUMMARY_WINDOW,
    ):
        self.client = AsyncClient()
        self.model = model
        self.recent_count = recent_count
        self.summary_count = summary_count
    
    async def format_for_llm(
        self,
        messages: List[Message],
        current_query: str,
    ) -> str:
        """
        Format chat history for LLM prompt injection.
        
        Returns XML-structured context (OneMesh pattern):
        <CHAT_HISTORY_SUMMARY>...</CHAT_HISTORY_SUMMARY>
        <LAST_N_CONVERSATIONS>...</LAST_N_CONVERSATIONS>
        """
        if not messages:
            return ""
        
        # Split into windows
        recent = messages[-self.recent_count:]
        older = messages[-(self.recent_count + self.summary_count):-self.recent_count]
        
        # Format recent messages in full
        recent_formatted = self._format_messages_full(recent)
        
        # Summarize older messages if present
        summary = ""
        if older:
            summary = await self._summarize_messages(older)
        
        return f"""<CHAT_HISTORY_SUMMARY>
{summary}
</CHAT_HISTORY_SUMMARY>

<LAST_{self.recent_count}_CONVERSATIONS>
{recent_formatted}
</LAST_{self.recent_count}_CONVERSATIONS>"""
    
    def _format_messages_full(self, messages: List[Message]) -> str:
        """Format messages with full content."""
        formatted = []
        for msg in messages:
            formatted.append(f"""<message role="{msg.role}">{msg.content}</message>""")
        return "\n".join(formatted)
    
    async def _summarize_messages(self, messages: List[Message]) -> str:
        """Use LLM to summarize older messages."""
        messages_text = self._format_messages_full(messages)
        
        response = await self.client.chat(
            model=self.model,
            messages=[{
                "role": "user",
                "content": f"""Summarize this conversation history in 2-3 sentences, 
focusing on the key topics discussed and any decisions made:

{messages_text}"""
            }],
            options={"temperature": 0.3, "num_predict": 200},
        )
        
        return response.get("message", {}).get("content", "")
```

#### 3. API Endpoints (DynamoDB-backed)

```python
# packages/core/src/api/routes/sessions.py

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
import structlog

from ...repositories.session_repository import SessionRepository, SessionState
from ...repositories.message_repository import MessageRepository
from ...cache.redis_client import get_redis_client

router = APIRouter()
logger = structlog.get_logger()


class SessionListResponse(BaseModel):
    """Response for session list endpoint."""
    sessions: List[dict]
    total: int


class SessionDetailResponse(BaseModel):
    """Response for session detail with messages."""
    session_id: str
    blueprint: str
    title: Optional[str]
    session_state: str
    messages: List[dict]
    created_on: str
    modified_on: str


class UpdateSessionStateRequest(BaseModel):
    """Request to update session state."""
    state: str  # "pinned", "unpinned", "archived"


# Endpoint: Generate new session ID
@router.get("/sessions/new")
async def get_new_session_id():
    """Generate a new session UUID (matches OneMesh /feedback/session_id)."""
    return {"session_id": uuid4().hex}


# Endpoint: Get user's sessions
@router.get("/blueprints/{blueprint}/sessions")
async def get_user_sessions(
    blueprint: str,
    user_id: str = "user",  # TODO: Extract from auth
    include_archived: bool = False,
) -> SessionListResponse:
    """
    Get all sessions for a user, sorted by activity.
    Matches OneMesh /chat_history/get_chat_sessions.
    """
    redis = get_redis_client()
    
    # Check Redis cache first
    cached = await redis.get_cached_user_sessions(user_id, blueprint)
    if cached and not include_archived:
        return SessionListResponse(sessions=cached, total=len(cached))
    
    # Query DynamoDB
    session_repo = SessionRepository(blueprint)
    sessions = await session_repo.get_user_sessions(
        user_id=user_id,
        include_archived=include_archived,
    )
    
    # Cache for sidebar (5 minutes)
    if sessions and not include_archived:
        await redis.cache_user_sessions(user_id, blueprint, sessions)
    
    return SessionListResponse(sessions=sessions, total=len(sessions))


# Endpoint: Get session with messages
@router.get("/blueprints/{blueprint}/sessions/{session_id}")
async def get_session(
    blueprint: str,
    session_id: str,
) -> SessionDetailResponse:
    """
    Get session history for resuming a conversation.
    Matches OneMesh /chat_history/get_chat_history.
    """
    session_repo = SessionRepository(blueprint)
    message_repo = MessageRepository(blueprint)
    
    # Get session metadata
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get messages
    messages = await message_repo.get_session_messages(session_id)
    
    return SessionDetailResponse(
        session_id=session_id,
        blueprint=blueprint,
        title=session.get("session_title"),
        session_state=session.get("session_state", "active"),
        messages=messages,
        created_on=session.get("created_on", ""),
        modified_on=session.get("modified_on", ""),
    )


# Endpoint: Create new session
@router.post("/blueprints/{blueprint}/sessions")
async def create_session(
    blueprint: str,
    user_id: str = "user",  # TODO: Extract from auth
):
    """Create a new chat session."""
    session_repo = SessionRepository(blueprint)
    redis = get_redis_client()
    
    session = await session_repo.create_session(user_id=user_id)
    
    # Invalidate user's session list cache
    await redis.invalidate_user_sessions(user_id, blueprint)
    
    return {"session_id": session["session_id"]}


# Endpoint: Update session state
@router.patch("/blueprints/{blueprint}/sessions/{session_id}/state")
async def update_session_state(
    blueprint: str,
    session_id: str,
    body: UpdateSessionStateRequest,
    user_id: str = "user",  # TODO: Extract from auth
):
    """
    Update session state (pin/unpin/archive).
    Matches OneMesh /chat_history/{state_type}.
    """
    session_repo = SessionRepository(blueprint)
    redis = get_redis_client()
    
    try:
        new_state = SessionState(body.state)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid state: {body.state}. Must be one of: active, pinned, unpinned, archived"
        )
    
    success = await session_repo.update_state(
        session_id=session_id,
        user_id=user_id,
        new_state=new_state,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Invalidate user's session list cache
    await redis.invalidate_user_sessions(user_id, blueprint)
    
    return {"status": "updated", "new_state": new_state.value}


# Endpoint: Update session title
@router.patch("/blueprints/{blueprint}/sessions/{session_id}/title")
async def update_session_title(
    blueprint: str,
    session_id: str,
    title: str,
):
    """Update session title (typically auto-set from first query)."""
    session_repo = SessionRepository(blueprint)
    
    success = await session_repo.update_title(session_id, title)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "updated"}
```

#### 4. Modifying chat.py for Persistence

The existing `packages/core/src/api/routes/chat.py` needs to save conversation turns after streaming completes:

```python
# packages/core/src/api/routes/chat.py - Modifications

from ...repositories.session_repository import SessionRepository
from ...repositories.message_repository import MessageRepository
from ...cache.redis_client import get_redis_client


@router.post("/blueprints/{blueprint}/chat")
async def chat(
    request: Request,
    blueprint: str,
    body: ChatRequest,
) -> StreamingResponse:
    """
    Chat endpoint with message persistence.
    
    Flow:
    1. Create/get session in DynamoDB
    2. Format context with sliding window
    3. Stream response from Ollama
    4. After streaming completes: save conversation turn to DynamoDB
    """
    session_repo = SessionRepository(blueprint)
    message_repo = MessageRepository(blueprint)
    redis = get_redis_client()
    
    user_id = "user"  # TODO: Extract from auth
    
    # Ensure session exists (create if new)
    session = await session_repo.get_session(body.session_id)
    if not session:
        await session_repo.create_session(
            user_id=user_id,
            session_id=body.session_id,
        )
        # Set title from first message (truncated)
        title = body.message[:50] + "..." if len(body.message) > 50 else body.message
        await session_repo.update_title(body.session_id, title)
    
    # Get recent messages for context
    recent_messages = await message_repo.get_recent_messages(
        session_id=body.session_id,
        limit=20,
    )
    
    # Format context (sliding window + summarization)
    formatted_context = await format_context_for_ollama(
        recent_messages=recent_messages,
        new_message=body.message,
    )
    
    async def generate_and_persist():
        """
        Stream tokens from Ollama, then persist conversation turn.
        """
        accumulated_response = ""
        
        async for chunk in orchestrator.stream_response(
            message=body.message,
            context=formatted_context,
        ):
            accumulated_response += chunk
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        
        # After streaming completes: persist conversation turn
        try:
            await message_repo.save_conversation_turn(
                session_id=body.session_id,
                user_id=user_id,
                user_message=body.message,
                bot_response=accumulated_response,
            )
            
            # Update agent state in Redis (for multi-agent tracking)
            if body.agent:
                await redis.add_active_agent(body.session_id, body.agent)
            
            logger.info(
                "chat_turn_persisted",
                session_id=body.session_id,
                user_message_length=len(body.message),
                response_length=len(accumulated_response),
            )
        except Exception as e:
            # Log error but don't fail the stream
            logger.error("chat_persistence_error", error=str(e))
        
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(
        generate_and_persist(),
        media_type="text/event-stream",
    )
```

**Key changes from current implementation:**
1. Import repositories and redis client
2. Ensure session exists before processing
3. Load recent messages for context
4. Accumulate streamed response
5. After stream completes: call `save_conversation_turn()`
6. Track active agents in Redis

---

## Frontend Implementation

### Component Architecture

```
packages/ui/
├── app/
│   ├── [blueprint]/
│   │   ├── page.tsx           # MODIFY: Add session integration
│   │   └── session/
│   │       └── [sessionId]/
│   │           └── page.tsx   # NEW: Session resume page
│   └── layout.tsx             # MODIFY: Add SessionProvider
├── components/
│   ├── session-drawer.tsx     # NEW: Sidebar with session list
│   ├── session-list.tsx       # NEW: Grouped session list
│   ├── session-item.tsx       # NEW: Individual session row
│   └── chat-container.tsx     # NEW: Extracted chat logic
├── hooks/
│   ├── use-sessions.ts        # NEW: TanStack Query hooks
│   └── use-chat.ts            # NEW: Chat state management
├── lib/
│   ├── api.ts                 # NEW: API client functions
│   └── query-client.tsx       # NEW: TanStack Query provider
└── types/
    └── session.ts             # NEW: TypeScript interfaces
```

### Key Frontend Components

#### 1. Session Types

```typescript
// packages/ui/types/session.ts

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  agent?: string;
  created_at: string;
  suggestions?: string[];
  search_results?: any[];
}

export interface ChatSession {
  user: {
    message_id: string;
    message: string;
    created_on: string;
    selected_source?: string[];
  };
  bot?: {
    response: { type: string; content: any }[];
    text: string;
    search_results?: any[];
    suggestions?: string[];
    message_id: string;
    process_duration?: number;
    created_ts: string;
    summarized_query?: string;
  };
}

export type SessionState = 'active' | 'pinned' | 'unpinned' | 'archived';

export interface SessionListItem {
  session_id: string;
  session_title: string;
  session_state: SessionState;
  modified_on: string;
  message_count: number;
}

export interface SessionGroup {
  label: string;  // "Pinned", "Today", "Previous 7 days", etc.
  sessions: SessionListItem[];
}

export interface ChatHistory {
  session: ChatSession[];
  session_id: string;
}
```

#### 2. Session Hooks (TanStack Query v5 - Production Pattern)

**Industry Standard (TanStack Query v5 Docs):**
Optimistic updates with snapshot rollback using `onMutate/onError/onSettled` pattern.

```typescript
// packages/ui/hooks/use-sessions.ts

import { 
  useQuery, 
  useMutation, 
  useQueryClient,
  queryOptions,
} from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { 
  SessionListItem, 
  SessionState, 
  ChatSession,
  SessionListResponse,
} from '@/types/session';

/**
 * Query options factory for session list.
 * Enables reuse across hooks and prefetching.
 */
export const sessionListOptions = (blueprint: string, userId: string) =>
  queryOptions({
    queryKey: ['sessions', blueprint, userId] as const,
    queryFn: () => api.getSessions(blueprint, userId),
    staleTime: 30_000,  // 30 seconds
    gcTime: 5 * 60_000, // 5 minutes garbage collection
  });

/**
 * Fetch user sessions with proper caching.
 */
export function useSessions(blueprint: string, userId: string) {
  return useQuery(sessionListOptions(blueprint, userId));
}

/**
 * Fetch single session with messages.
 */
export function useSession(blueprint: string, sessionId: string) {
  return useQuery({
    queryKey: ['session', blueprint, sessionId] as const,
    queryFn: () => api.getSession(blueprint, sessionId),
    enabled: !!sessionId,
    staleTime: 60_000, // 1 minute - session data changes less frequently
  });
}

/**
 * Update session state with optimistic updates and rollback.
 * 
 * Pattern from TanStack Query v5 docs:
 * 1. onMutate: Cancel queries, snapshot previous data, apply optimistic update
 * 2. onError: Rollback to snapshot on failure
 * 3. onSettled: Always refetch to ensure consistency
 */
export function useUpdateSessionState(blueprint: string, userId: string) {
  const queryClient = useQueryClient();
  const queryKey = ['sessions', blueprint, userId] as const;
  
  return useMutation({
    mutationFn: ({ sessionId, state }: { sessionId: string; state: SessionState }) =>
      api.updateSessionState(blueprint, sessionId, state),
    
    // Optimistic update
    onMutate: async ({ sessionId, state }) => {
      // Cancel any outgoing refetches to prevent overwriting optimistic update
      await queryClient.cancelQueries({ queryKey });
      
      // Snapshot current data for rollback
      const previousSessions = queryClient.getQueryData<SessionListResponse>(queryKey);
      
      // Optimistically update the cache
      if (previousSessions) {
        queryClient.setQueryData<SessionListResponse>(queryKey, (old) => {
          if (!old) return old;
          
          return {
            ...old,
            sessions: old.sessions.map((session) =>
              session.session_id === sessionId
                ? { 
                    ...session, 
                    session_state: state,
                    // Update pinned_at for proper sorting
                    ...(state === 'pinned' && { pinned_at: new Date().toISOString() }),
                  }
                : session
            ).filter((session) => 
              // Remove archived from list immediately
              state !== 'archived' || session.session_id !== sessionId
            ),
          };
        });
      }
      
      // Return snapshot for rollback
      return { previousSessions };
    },
    
    // Rollback on error
    onError: (err, { sessionId }, context) => {
      console.error('Failed to update session state:', err);
      
      if (context?.previousSessions) {
        queryClient.setQueryData(queryKey, context.previousSessions);
      }
    },
    
    // Always refetch after error or success for consistency
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

/**
 * Log chat history after bot response completes.
 * Uses optimistic update for session list (title, timestamp).
 */
export function useLogHistory(blueprint: string, userId: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: {
      session_id: string;
      user: ChatSession['user'];
      bot: ChatSession['bot'];
      user_name: string;
      first_chat_object?: ChatSession;
    }) => api.logHistory(blueprint, data),
    
    onMutate: async ({ session_id, bot }) => {
      const queryKey = ['sessions', blueprint, userId] as const;
      
      await queryClient.cancelQueries({ queryKey });
      const previousSessions = queryClient.getQueryData<SessionListResponse>(queryKey);
      
      // Optimistically update session in list
      if (previousSessions) {
        queryClient.setQueryData<SessionListResponse>(queryKey, (old) => {
          if (!old) return old;
          
          return {
            ...old,
            sessions: old.sessions.map((session) =>
              session.session_id === session_id
                ? {
                    ...session,
                    // Update title from summarized query if available
                    session_title: bot?.summarized_query || session.session_title,
                    modified_on: new Date().toISOString(),
                    message_count: (session.message_count || 0) + 2, // user + bot
                  }
                : session
            ),
          };
        });
      }
      
      return { previousSessions };
    },
    
    onError: (err, _, context) => {
      console.error('Failed to log history:', err);
      const queryKey = ['sessions', blueprint, userId] as const;
      
      if (context?.previousSessions) {
        queryClient.setQueryData(queryKey, context.previousSessions);
      }
    },
    
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions', blueprint] });
    },
  });
}

/**
 * Prefetch sessions on hover (for session drawer).
 * Improves perceived performance.
 */
export function usePrefetchSessions(blueprint: string, userId: string) {
  const queryClient = useQueryClient();
  
  return () => {
    queryClient.prefetchQuery(sessionListOptions(blueprint, userId));
  };
}
```

#### 3. Session Drawer Component

```typescript
// packages/ui/components/session-drawer.tsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  PanelLeftOpen, 
  PanelLeftClose, 
  Plus, 
  Pin, 
  Archive, 
  MoreHorizontal 
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useSessions, useUpdateSessionState } from '@/hooks/use-sessions';
import { groupSessionsByDate } from '@/lib/session-utils';
import type { SessionListItem, SessionState } from '@/types/session';

interface SessionDrawerProps {
  blueprint: string;
  currentSessionId?: string;
  onNewChat: () => void;
}

export function SessionDrawer({ 
  blueprint, 
  currentSessionId,
  onNewChat 
}: SessionDrawerProps) {
  const [isOpen, setIsOpen] = useState(true);
  const router = useRouter();
  
  // TODO: Get userId from auth context
  const userId = 'user';
  
  const { data: sessions, isLoading } = useSessions(blueprint, userId);
  const updateState = useUpdateSessionState(blueprint);
  
  const groupedSessions = sessions ? groupSessionsByDate(sessions.sessions) : [];
  
  const handleSessionClick = (sessionId: string) => {
    router.push(`/${blueprint}/session/${sessionId}`);
  };
  
  const handleStateChange = (sessionId: string, state: SessionState) => {
    updateState.mutate({ sessionId, state });
  };
  
  if (!isOpen) {
    return (
      <Button 
        variant="ghost" 
        size="icon" 
        onClick={() => setIsOpen(true)}
        className="fixed left-4 top-4 z-50"
      >
        <PanelLeftOpen className="h-5 w-5" />
      </Button>
    );
  }
  
  return (
    <div className="w-64 border-r bg-muted/30 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <Button variant="outline" onClick={onNewChat} className="flex-1 mr-2">
          <Plus className="h-4 w-4 mr-2" />
          New Chat
        </Button>
        <Button variant="ghost" size="icon" onClick={() => setIsOpen(false)}>
          <PanelLeftClose className="h-5 w-5" />
        </Button>
      </div>
      
      {/* Session List */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-4">
          {groupedSessions.map((group) => (
            <div key={group.label}>
              <h3 className="px-2 py-1 text-xs font-medium text-muted-foreground uppercase">
                {group.label}
              </h3>
              <div className="space-y-1">
                {group.sessions.map((session) => (
                  <SessionItem
                    key={session.session_id}
                    session={session}
                    isActive={session.session_id === currentSessionId}
                    onClick={() => handleSessionClick(session.session_id)}
                    onPin={() => handleStateChange(session.session_id, 'pinned')}
                    onUnpin={() => handleStateChange(session.session_id, 'unpinned')}
                    onArchive={() => handleStateChange(session.session_id, 'archived')}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

// Session item with actions dropdown
function SessionItem({ 
  session, 
  isActive, 
  onClick,
  onPin,
  onUnpin,
  onArchive,
}: {
  session: SessionListItem;
  isActive: boolean;
  onClick: () => void;
  onPin: () => void;
  onUnpin: () => void;
  onArchive: () => void;
}) {
  return (
    <div
      className={`group flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer
        ${isActive ? 'bg-accent' : 'hover:bg-accent/50'}`}
      onClick={onClick}
    >
      <span className="flex-1 truncate text-sm">
        {session.session_title || 'New Chat'}
      </span>
      
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-6 w-6 opacity-0 group-hover:opacity-100"
            onClick={(e) => e.stopPropagation()}
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {session.session_state === 'pinned' ? (
            <DropdownMenuItem onClick={onUnpin}>
              <Pin className="h-4 w-4 mr-2" />
              Unpin
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem onClick={onPin}>
              <Pin className="h-4 w-4 mr-2" />
              Pin
            </DropdownMenuItem>
          )}
          <DropdownMenuItem onClick={onArchive} className="text-destructive">
            <Archive className="h-4 w-4 mr-2" />
            Remove
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
```

#### 4. Session Grouping Utility

```typescript
// packages/ui/lib/session-utils.ts

import { isToday, isWithinInterval, subDays } from 'date-fns';
import type { SessionListItem, SessionGroup } from '@/types/session';

/**
 * Group sessions by date for display in session drawer.
 * Order: Pinned → Today → Previous 7 days → Last 30 days → Older
 * 
 * Based on OneMesh groupSessionsByDate utility.
 */
export function groupSessionsByDate(sessions: SessionListItem[]): SessionGroup[] {
  const groups: Map<string, SessionListItem[]> = new Map();
  
  // Define group order
  const groupOrder = ['Pinned', 'Today', 'Previous 7 days', 'Last 30 days', 'Older'];
  groupOrder.forEach(label => groups.set(label, []));
  
  sessions.forEach((session) => {
    const sessionDate = new Date(session.modified_on);
    let label: string;
    
    if (session.session_state === 'pinned') {
      label = 'Pinned';
    } else if (isToday(sessionDate)) {
      label = 'Today';
    } else if (isWithinInterval(sessionDate, {
      start: subDays(new Date(), 7),
      end: subDays(new Date(), 1),
    })) {
      label = 'Previous 7 days';
    } else if (isWithinInterval(sessionDate, {
      start: subDays(new Date(), 30),
      end: subDays(new Date(), 1),
    })) {
      label = 'Last 30 days';
    } else {
      label = 'Older';
    }
    
    groups.get(label)!.push(session);
  });
  
  // Return only non-empty groups in order
  return groupOrder
    .filter(label => groups.get(label)!.length > 0)
    .map(label => ({
      label,
      sessions: groups.get(label)!,
    }));
}
```

---

## Infrastructure Changes

### 1. ScyllaDB Deployment (Kubernetes-Native)

**Why ScyllaDB:**
- Discord uses it for trillion+ chat messages
- Official Kubernetes Operator (production-grade)
- DynamoDB-compatible API (Alternator) - same boto3 code works
- Native TTL support for automatic data retention

**Step 1: Deploy Scylla Operator**

```bash
# Add Helm repository
helm repo add scylla https://scylla-operator-charts.storage.googleapis.com/stable
helm repo update

# Install operator
helm install scylla-operator scylla/scylla-operator \
  --namespace scylla-operator \
  --create-namespace \
  --set webhook.enabled=false  # Disable for Kind
```

**Step 2: Create ScyllaDB Cluster**

```yaml
# blueprints/devassist/scylla/cluster.yaml
apiVersion: scylla.scylladb.com/v1
kind: ScyllaCluster
metadata:
  name: scylla
  namespace: scylla
spec:
  version: 5.4.0
  agentVersion: 3.2.6
  developerMode: true  # For Kind (relaxed requirements)
  
  datacenter:
    name: dc1
    racks:
    - name: rack1
      members: 1  # Single node for dev
      storage:
        capacity: 10Gi
      resources:
        requests:
          cpu: 500m
          memory: 1Gi
        limits:
          cpu: 1
          memory: 2Gi
      
  # Enable Alternator (DynamoDB-compatible API)
  alternator:
    port: 8000
    writeIsolation: only_rmw_uses_lwt
```

```bash
# Apply cluster
kubectl create namespace scylla
kubectl apply -f blueprints/devassist/scylla/cluster.yaml

# Wait for ready
kubectl wait --for=condition=ready pod -l app=scylla -n scylla --timeout=600s
```

**Step 3: Create Tables via Alternator**

```python
# scripts/create_scylla_tables.py
import boto3

# Connect to ScyllaDB Alternator
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://scylla-client.scylla.svc.cluster.local:8000',
    region_name='us-east-1',
    aws_access_key_id='none',
    aws_secret_access_key='none',
)

# Sessions table
dynamodb.create_table(
    TableName='devassist-sessions',
    KeySchema=[
        {'AttributeName': 'session_id', 'KeyType': 'HASH'},
    ],
    AttributeDefinitions=[
        {'AttributeName': 'session_id', 'AttributeType': 'S'},
    ],
    BillingMode='PAY_PER_REQUEST',
)

# History table (with sort key for time-series)
dynamodb.create_table(
    TableName='devassist-history',
    KeySchema=[
        {'AttributeName': 'session_id', 'KeyType': 'HASH'},
        {'AttributeName': 'created_on', 'KeyType': 'RANGE'},
    ],
    AttributeDefinitions=[
        {'AttributeName': 'session_id', 'AttributeType': 'S'},
        {'AttributeName': 'created_on', 'AttributeType': 'S'},
    ],
    BillingMode='PAY_PER_REQUEST',
)

print("Tables created successfully!")
```

**Service endpoint:** `http://scylla-client.scylla.svc.cluster.local:8000`

**Tables created:**
- `devassist-sessions` - Session metadata
- `devassist-history` - Chat messages (time-series)

### 2. Redis Sentinel (Already Deployed) ✅

Redis Sentinel is already running in your Kind cluster:

```bash
# Verify Redis Sentinel is running
kubectl get pods -n redis-sentinel

# Expected output:
# redis-sentinel-node-0   Running
# redis-sentinel-node-1   Running
# redis-sentinel-node-2   Running
```

**Service endpoint:** `redis-sentinel.redis-sentinel:6379`

### 3. Configuration Updates Required

**Update `packages/core/src/config.py`:**

```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # ScyllaDB (Alternator - DynamoDB-compatible API)
    scylladb_endpoint: str = "http://scylla-client.scylla.svc.cluster.local:8000"
    aws_region: str = "us-east-1"  # Required by boto3, but ignored by Alternator
    aws_access_key_id: str = "none"  # Not used by Alternator
    aws_secret_access_key: str = "test"
    
    # Redis Sentinel (Kind cluster)
    redis_host: str = "redis-sentinel.redis-sentinel"  # K8s service
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # PostgreSQL (pgvector - for RAG only)
    postgres_host: str = "postgres-rw.database.svc.cluster.local"
    postgres_port: int = 5432
    postgres_db: str = "agentic"
    postgres_user: str = "postgres"
    postgres_password: str = ""
    
    # Session Management
    session_cache_ttl: int = 3600  # 1 hour
    session_ttl_days: int = 7
    history_ttl_days: int = 30
    context_window_recent: int = 5
    context_window_summary: int = 5
```

**Update `.env.example`:**

```bash
# ScyllaDB (Alternator - DynamoDB-compatible API)
SCYLLADB_ENDPOINT=http://scylla-client.scylla.svc.cluster.local:8000
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=none  # Not used by Alternator
AWS_SECRET_ACCESS_KEY=test

# Redis Sentinel
REDIS_HOST=redis-sentinel.redis-sentinel
REDIS_PORT=6379
REDIS_PASSWORD=

# PostgreSQL (pgvector - RAG only)
POSTGRES_HOST=postgres-rw.database.svc.cluster.local
POSTGRES_PORT=5432
POSTGRES_DB=agentic
POSTGRES_USER=postgres
POSTGRES_PASSWORD=

# Session Management
SESSION_CACHE_TTL=3600
SESSION_TTL_DAYS=7
HISTORY_TTL_DAYS=30

# For local development (override K8s endpoints)
# LOCALSTACK_ENDPOINT=http://localhost:4566
# REDIS_HOST=localhost
# POSTGRES_HOST=localhost
```

### 4. Application Startup Integration

```python
# packages/core/src/api/app.py

from contextlib import asynccontextmanager

from ..cache.redis_client import init_redis, close_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("starting_application")
    
    # Initialize Redis Sentinel connection
    await init_redis()
    
    # ... existing initialization ...
    
    yield
    
    # Cleanup
    await close_redis()
    logger.info("shutting_down_application")
```

### 5. Dependencies Required

Add to `packages/core/pyproject.toml`:

```toml
dependencies = [
    # ... existing dependencies ...
    "aioboto3>=12.0.0",       # Async DynamoDB client
    "redis>=5.0.0",           # Redis with Sentinel support
]
```

---

## Context Window Management

### OneMesh Pattern Summary

The OneMesh system uses a **sliding window approach** to manage chat context:

1. **Recent messages (last N):** Full content preserved
2. **Older messages (N to 2N):** Summarized via LLM  
3. **Oldest messages (> 2N):** Discarded

### Industry-Validated Improvement: Incremental Summarization

**Problem with OneMesh approach (Factory.ai, 2025):**
> "Naive on-the-fly compression has significant limitations: redundant re-summarization costs increase linearly with conversation length"

**Improved Strategy:**
Instead of re-summarizing all older messages on each request, we use **incremental anchored summarization**:

```
Conversation: [msg1, msg2, msg3, msg4, msg5, msg6, msg7, msg8, msg9, msg10]
                                                          │
                                                          ▼ NEW MESSAGE
                                                          
BEFORE (OneMesh - re-summarize all):
  - Summary(msg1-5) + Full(msg6-10) → expensive as convo grows
  
AFTER (Incremental - only summarize drops):
  - Persist summary at msg5 → stored in DB
  - On new message: Summary(msg5) + Summary(msg6 only) → merge
  - Full(msg7-10) → cheap, constant cost
```

### Production-Grade Context Formatter

```python
# packages/core/src/services/context_formatter.py

from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ollama import AsyncClient
import structlog

from ..models.message import Message
from ..repositories.message_repository import MessageRepository

logger = structlog.get_logger()

# Configuration (from industry benchmarks)
TMAX = 8192          # Trigger compression at this token count
TRETAINED = 4096     # Maximum tokens retained post-compression
RECENT_MESSAGES = 5  # Always keep last N messages in full


@dataclass
class ConversationState:
    """Persistent conversation state with rolling summary."""
    summary: str
    summary_anchor_id: str  # Message ID where summary ends
    total_tokens: int
    last_updated: datetime


class IncrementalContextFormatter:
    """
    Production-grade context formatter using incremental summarization.
    
    Based on Factory.ai's 2025 architecture:
    - Maintains persistent conversation state with rolling summaries
    - Only summarizes newly dropped spans (not entire history)
    - Avoids linear cost growth with conversation length
    
    References:
    - https://www.factory.ai/news/compressing-context
    - https://mem0.ai/blog/llm-chat-history-summarization-guide-2025
    """
    
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        message_repo: Optional[MessageRepository] = None,
        tmax: int = TMAX,
        tretained: int = TRETAINED,
    ):
        self.client = AsyncClient()
        self.model = model
        self.message_repo = message_repo
        self.tmax = tmax
        self.tretained = tretained
    
    async def format_for_llm(
        self,
        session_id: str,
        messages: List[Message],
        current_query: str,
    ) -> Tuple[str, Optional[ConversationState]]:
        """
        Format chat history with incremental summarization.
        
        Returns:
            Tuple of (formatted_context, updated_state_to_persist)
        """
        if not messages:
            return "", None
        
        # Estimate token count
        total_tokens = sum(self._estimate_tokens(m.content) for m in messages)
        
        # Get existing summary state from last summarized message
        existing_summary = await self._get_persisted_summary(session_id)
        
        # Determine if compression is needed
        if total_tokens < self.tmax:
            # No compression needed - return full context
            return self._format_full_context(messages, existing_summary), None
        
        # Compression needed - only summarize newly dropped messages
        recent = messages[-RECENT_MESSAGES:]
        to_summarize = messages[:-RECENT_MESSAGES]
        
        # Find messages that haven't been summarized yet
        if existing_summary and existing_summary.summary_anchor_id:
            new_to_summarize = [
                m for m in to_summarize 
                if m.id > existing_summary.summary_anchor_id
            ]
        else:
            new_to_summarize = to_summarize
        
        # Only summarize the new span (not entire history)
        if new_to_summarize:
            new_summary = await self._summarize_span(new_to_summarize)
            merged_summary = self._merge_summaries(
                existing_summary.summary if existing_summary else "",
                new_summary
            )
        else:
            merged_summary = existing_summary.summary if existing_summary else ""
        
        # Build new state to persist
        new_state = ConversationState(
            summary=merged_summary,
            summary_anchor_id=to_summarize[-1].id if to_summarize else None,
            total_tokens=self._estimate_tokens(merged_summary) + sum(
                self._estimate_tokens(m.content) for m in recent
            ),
            last_updated=datetime.utcnow(),
        )
        
        # Format context
        formatted = self._format_compressed_context(merged_summary, recent)
        
        return formatted, new_state
    
    async def _summarize_span(self, messages: List[Message]) -> str:
        """Summarize a span of messages (only newly dropped ones)."""
        messages_text = "\n".join(
            f"<{m.role}>{m.content}</{m.role}>" for m in messages
        )
        
        response = await self.client.chat(
            model=self.model,
            messages=[{
                "role": "user",
                "content": f"""Summarize this conversation segment concisely (2-3 sentences).
Focus on: key topics, decisions made, and important context for future questions.

{messages_text}"""
            }],
            options={"temperature": 0.3, "num_predict": 150},
        )
        
        return response.get("message", {}).get("content", "")
    
    def _merge_summaries(self, existing: str, new: str) -> str:
        """Merge existing summary with newly summarized content."""
        if not existing:
            return new
        if not new:
            return existing
        return f"{existing}\n\nMore recently: {new}"
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token average)."""
        return len(text) // 4
    
    def _format_full_context(
        self, 
        messages: List[Message], 
        summary: Optional[ConversationState]
    ) -> str:
        """Format context when no compression needed."""
        parts = []
        if summary and summary.summary:
            parts.append(f"<EARLIER_CONTEXT>\n{summary.summary}\n</EARLIER_CONTEXT>")
        
        msgs = "\n".join(
            f'<message role="{m.role}">{m.content}</message>' 
            for m in messages
        )
        parts.append(f"<RECENT_MESSAGES>\n{msgs}\n</RECENT_MESSAGES>")
        
        return "\n\n".join(parts)
    
    def _format_compressed_context(
        self, 
        summary: str, 
        recent: List[Message]
    ) -> str:
        """Format compressed context with summary and recent messages."""
        recent_msgs = "\n".join(
            f'<message role="{m.role}">{m.content}</message>' 
            for m in recent
        )
        
        return f"""<CONVERSATION_SUMMARY>
{summary}
</CONVERSATION_SUMMARY>

<LAST_{RECENT_MESSAGES}_MESSAGES>
{recent_msgs}
</LAST_{RECENT_MESSAGES}_MESSAGES>"""
    
    async def _get_persisted_summary(
        self, 
        session_id: str
    ) -> Optional[ConversationState]:
        """Retrieve persisted summary state from database."""
        if not self.message_repo:
            return None
        # Implementation: query conversations table for summary_state JSONB
        return None  # TODO: Implement with repository
```

### Integration with Orchestrator

```python
# Updated supervisor orchestrator integration

class SupervisorOrchestrator:
    def __init__(
        self, 
        agents, 
        context_formatter: IncrementalContextFormatter
    ):
        self.agents = agents
        self.context_formatter = context_formatter
    
    async def process_query_streaming(
        self,
        query: str,
        user_id: str,
        session_id: str,
        chat_history: List[Message] = None,
    ):
        # Format context with incremental summarization
        formatted_context, updated_state = await self.context_formatter.format_for_llm(
            session_id=session_id,
            messages=chat_history or [],
            current_query=query,
        )
        
        # Persist updated state if compression occurred
        if updated_state:
            await self._persist_conversation_state(session_id, updated_state)
        
        # Inject into agent prompts
        enhanced_query = f"""
{formatted_context}

<USER_QUERY>
{query}
</USER_QUERY>
"""
        # ... rest of processing
```

---

## Production-Grade Scalability

This section addresses scalability, maintainability, and performance concerns for production deployment.

### 1. PostgreSQL Connection Pooling (pgvector/RAG only)

**Note:** PostgreSQL is used **only for pgvector embeddings/RAG**, not for chat history. Chat data goes to DynamoDB.

```python
# packages/core/src/db/database.py

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncIterator

from ..config import get_settings

settings = get_settings()

# PostgreSQL connection for pgvector (RAG queries only)
# Reduced pool size since this is not for chat history
engine = create_async_engine(
    settings.postgres_url,
    echo=settings.debug,
    pool_size=10,                  # Smaller pool for RAG-only workload
    max_overflow=20,               # Additional connections under load
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_db() -> AsyncIterator[AsyncSession]:
    """
    Dependency for pgvector/RAG endpoints only.
    Chat history uses DynamoDB via separate repositories.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Storage responsibility:**
| Data Type | Storage | Reason |
|-----------|---------|--------|
| Chat sessions | ScyllaDB (Alternator) | Key-value access, TTL, K8s-native |
| Chat messages | ScyllaDB (Alternator) | Time-series, TTL, Discord-proven |
| Session cache | Redis Sentinel | Fast access, state management |
| Document embeddings | PostgreSQL (pgvector) | Vector similarity search |

### 2. Redis Sentinel Client

**Using Redis Sentinel deployed in Kind cluster at `redis-sentinel.redis-sentinel:6379`:**

```python
# packages/core/src/cache/redis_client.py

import json
from typing import Optional, List, Any, Dict

import redis.asyncio as aioredis
from redis.asyncio.sentinel import Sentinel
import structlog

from ..config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class RedisSentinelClient:
    """
    Redis Sentinel client for Kind cluster.
    
    Cluster endpoint: redis-sentinel.redis-sentinel:6379
    
    Features:
    - Automatic failover via Sentinel
    - Connection pooling
    - Pipeline for batch operations
    - Session and agent state caching
    """
    
    def __init__(self):
        self._sentinel: Optional[Sentinel] = None
        self._master: Optional[aioredis.Redis] = None
        self._master_name = "mymaster"  # Default Sentinel master name
    
    async def connect(self):
        """
        Initialize Redis Sentinel connection.
        
        Connects to Sentinel and gets master connection.
        """
        sentinel_hosts = [
            (settings.redis_host, settings.redis_port),
        ]
        
        self._sentinel = Sentinel(
            sentinel_hosts,
            socket_timeout=5.0,
            password=settings.redis_password,
        )
        
        # Get master connection
        self._master = self._sentinel.master_for(
            self._master_name,
            socket_timeout=5.0,
            decode_responses=True,
        )
        
        # Test connection
        await self._master.ping()
        
        logger.info(
            "redis_sentinel_connected",
            host=settings.redis_host,
            port=settings.redis_port,
            master=self._master_name,
        )
    
    async def disconnect(self):
        """Clean shutdown of connections."""
        if self._master:
            await self._master.close()
        logger.info("redis_sentinel_disconnected")
    
    @property
    def client(self) -> aioredis.Redis:
        if not self._master:
            raise RuntimeError("Redis Sentinel client not connected")
        return self._master
    
    # =========================================================================
    # Session Caching Operations
    # =========================================================================
    
    async def cache_session(
        self, 
        session_id: str, 
        data: Dict[str, Any], 
        ttl: int = 3600
    ):
        """
        Cache session metadata with TTL.
        Stores as JSON string for complex nested data.
        """
        key = f"session:{session_id}"
        # Serialize to JSON for nested structures
        await self.client.set(key, json.dumps(data), ex=ttl)
    
    async def get_cached_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached session."""
        key = f"session:{session_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def invalidate_session(self, session_id: str):
        """Remove session from cache."""
        await self.client.delete(f"session:{session_id}")
    
    # =========================================================================
    # Session List Caching (for sidebar)
    # =========================================================================
    
    async def cache_user_sessions(
        self,
        user_id: str,
        blueprint: str,
        sessions: List[Dict],
        ttl: int = 300,  # 5 minutes
    ):
        """Cache user's session list for quick sidebar loading."""
        key = f"user_sessions:{user_id}:{blueprint}"
        await self.client.set(key, json.dumps(sessions), ex=ttl)
    
    async def get_cached_user_sessions(
        self,
        user_id: str,
        blueprint: str,
    ) -> Optional[List[Dict]]:
        """Get cached session list."""
        key = f"user_sessions:{user_id}:{blueprint}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def invalidate_user_sessions(self, user_id: str, blueprint: str):
        """Invalidate user's session list cache."""
        await self.client.delete(f"user_sessions:{user_id}:{blueprint}")
    
    # =========================================================================
    # Batch Operations with Pipeline
    # =========================================================================
    
    async def cache_sessions_batch(
        self, 
        sessions: List[Dict],
        ttl: int = 3600
    ):
        """
        Batch cache multiple sessions using pipeline.
        Reduces network round trips from N to 1.
        """
        async with self.client.pipeline(transaction=True) as pipe:
            for session in sessions:
                key = f"session:{session['session_id']}"
                await pipe.set(key, json.dumps(session), ex=ttl)
            await pipe.execute()
    
    # =========================================================================
    # Agent State Management (replaces in-memory AgentStateManager)
    # =========================================================================
    
    async def set_agent_state(
        self,
        session_id: str,
        blueprint: str,
        disabled_agents: set,
    ):
        """
        Persist agent enabled/disabled state.
        Replaces in-memory AgentStateManager.
        """
        key = f"agent_state:{session_id}:{blueprint}"
        if disabled_agents:
            await self.client.delete(key)
            await self.client.sadd(key, *disabled_agents)
            await self.client.expire(key, 86400)  # 24 hours
        else:
            await self.client.delete(key)
    
    async def get_disabled_agents(
        self,
        session_id: str,
        blueprint: str,
    ) -> set:
        """Get disabled agents for session."""
        key = f"agent_state:{session_id}:{blueprint}"
        members = await self.client.smembers(key)
        return set(members) if members else set()
    
    async def enable_agent(
        self,
        session_id: str,
        blueprint: str,
        agent_name: str,
    ):
        """Enable a specific agent."""
        key = f"agent_state:{session_id}:{blueprint}"
        await self.client.srem(key, agent_name.lower())
    
    async def disable_agent(
        self,
        session_id: str,
        blueprint: str,
        agent_name: str,
    ):
        """Disable a specific agent."""
        key = f"agent_state:{session_id}:{blueprint}"
        await self.client.sadd(key, agent_name.lower())
        await self.client.expire(key, 86400)
    
    # =========================================================================
    # Rate Limiting
    # =========================================================================
    
    async def check_rate_limit(
        self,
        client_id: str,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """
        Check rate limit using sliding window.
        
        Returns:
            (allowed: bool, retry_after: int)
        """
        import time
        
        key = f"ratelimit:{client_id}"
        now = time.time()
        window_start = now - window_seconds
        
        async with self.client.pipeline(transaction=True) as pipe:
            # Remove old entries
            await pipe.zremrangebyscore(key, 0, window_start)
            # Count current requests
            await pipe.zcard(key)
            # Add current request
            await pipe.zadd(key, {str(now): now})
            await pipe.expire(key, window_seconds)
            results = await pipe.execute()
        
        current_count = results[1]
        
        if current_count >= max_requests:
            return False, window_seconds
        
        return True, 0
    
    # =========================================================================
    # Context Summary Caching (for incremental summarization)
    # =========================================================================
    
    async def cache_context_summary(
        self,
        session_id: str,
        summary: str,
        anchor_message_id: str,
        ttl: int = 86400,  # 24 hours
    ):
        """Cache conversation context summary."""
        key = f"context_summary:{session_id}"
        data = {
            "summary": summary,
            "anchor_message_id": anchor_message_id,
        }
        await self.client.set(key, json.dumps(data), ex=ttl)
    
    async def get_context_summary(
        self,
        session_id: str,
    ) -> Optional[Dict[str, str]]:
        """Get cached context summary."""
        key = f"context_summary:{session_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None


# Global singleton
_redis_client = RedisSentinelClient()


async def init_redis():
    """Initialize Redis on application startup."""
    await _redis_client.connect()


async def close_redis():
    """Close Redis on application shutdown."""
    await _redis_client.disconnect()


def get_redis_client() -> RedisSentinelClient:
    return _redis_client
```

### 3. DynamoDB TTL for Automatic Data Retention

**Native TTL support in DynamoDB** handles data retention automatically:

```python
# TTL is already configured in Terraform
# Tables: devassist-sessions (7 days), devassist-history (30 days)

# When saving items, include expires_at attribute:
import time

def calculate_ttl(days: int) -> int:
    """Calculate TTL as Unix epoch timestamp."""
    return int(time.time()) + (days * 24 * 60 * 60)

# Session item with 7-day TTL
session = {
    "session_id": "abc123",
    "user_id": "user@example.com",
    # ... other fields ...
    "expires_at": calculate_ttl(7),  # Auto-deleted after 7 days
}

# Message item with 30-day TTL
message = {
    "session_id": "abc123",
    "timestamp": 1706745600000,
    # ... other fields ...
    "expires_at": calculate_ttl(30),  # Auto-deleted after 30 days
}
```

**Benefits over PostgreSQL partitioning:**
- Zero maintenance - DynamoDB handles deletion automatically
- No manual cron jobs or pg_partman configuration
- Exact item-level expiration (not partition-level)
- AWS production parity

### 4. Rate Limiting Middleware

```python
# packages/core/src/api/middleware/rate_limit.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time

from ..cache.redis_client import get_redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-based rate limiting for API endpoints.
    Uses sliding window algorithm for fairness.
    """
    
    def __init__(
        self, 
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst = burst_size
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Identify client (user_id from auth or IP)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        allowed, retry_after = await self._check_rate_limit(client_id)
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)}
            )
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        # TODO: Extract from JWT when auth is implemented
        return request.client.host if request.client else "unknown"
    
    async def _check_rate_limit(self, client_id: str) -> tuple[bool, int]:
        """Sliding window rate limit check."""
        redis = get_redis_client()
        key = f"ratelimit:{client_id}"
        now = time.time()
        window = 60  # 1 minute window
        
        async with redis.client.pipeline(transaction=True) as pipe:
            # Remove old entries
            await pipe.zremrangebyscore(key, 0, now - window)
            # Count current requests
            await pipe.zcard(key)
            # Add current request
            await pipe.zadd(key, {str(now): now})
            await pipe.expire(key, window)
            results = await pipe.execute()
        
        current_count = results[1]
        
        if current_count >= self.rpm:
            return False, window
        
        return True, 0
```

### 5. Observability: Structured Logging and Metrics

```python
# packages/core/src/observability/logging.py

import structlog
from prometheus_client import Counter, Histogram

# Prometheus metrics
CHAT_REQUESTS = Counter(
    'chat_requests_total',
    'Total chat requests',
    ['blueprint', 'agent', 'status']
)

CHAT_LATENCY = Histogram(
    'chat_latency_seconds',
    'Chat request latency',
    ['blueprint', 'agent'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

SESSION_OPERATIONS = Counter(
    'session_operations_total',
    'Session management operations',
    ['operation', 'status']  # operation: create, load, pin, archive
)

CONTEXT_COMPRESSION = Histogram(
    'context_compression_ratio',
    'Ratio of compressed to original context size',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)


def configure_logging(environment: str = "development"):
    """Configure structured logging for production."""
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    if environment == "production":
        # JSON output for log aggregation (ELK, Datadog, etc.)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Human-readable for development
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### 6. Future Scalability: CQRS Pattern

**When to Consider (AWS Prescriptive Guidance):**
- Read/write ratio heavily skewed (many reads, few writes)
- Need different data models for reads vs writes
- Horizontal scaling of read operations independently

**Preparation in Current Design:**

```
Current (Phase 1-2):
┌─────────────────────────────────────────┐
│         PostgreSQL                       │
│  ┌───────────────┬───────────────┐      │
│  │ conversations │   messages    │      │
│  │  (read/write) │ (read/write)  │      │
│  └───────────────┴───────────────┘      │
└─────────────────────────────────────────┘

Future (Phase 4+ if needed):
┌─────────────────────────────────────────┐
│              WRITE PATH                  │
│  ┌───────────────────────────────────┐  │
│  │         PostgreSQL                 │  │
│  │  (source of truth, ACID)          │  │
│  └───────────────┬───────────────────┘  │
│                  │ Events                │
│                  ▼                       │
│  ┌───────────────────────────────────┐  │
│  │      Event Bus (Redis Streams)    │  │
│  └───────────────┬───────────────────┘  │
└──────────────────┼──────────────────────┘
                   │
┌──────────────────┼──────────────────────┐
│              READ PATH                   │
│                  ▼                       │
│  ┌───────────────────────────────────┐  │
│  │   DynamoDB (denormalized views)   │  │
│  │   - session_list_by_user          │  │
│  │   - recent_messages_by_session    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Preparation steps:**
1. Use repository pattern (abstracts storage)
2. Emit domain events on session/message changes
3. Design read models as projections

---

## Migration Path

### From Current State to Phase 1

1. **Deploy ScyllaDB:** Install Scylla Operator and create cluster in Kind
2. **Create repositories:** Abstract data access for sessions and messages  
3. **Update chat endpoint:** Add persistence after streaming completes
4. **Add session endpoints:** CRUD for sessions
5. **Test with existing UI:** Verify messages are persisted

### From Phase 1 to Phase 2

1. **Install TanStack Query:** Add to UI dependencies
2. **Create API client:** Typed fetch functions
3. **Build SessionDrawer:** Component with hooks
4. **Update page layout:** Add drawer to blueprint pages
5. **Add session routing:** `/[blueprint]/session/[sessionId]` page

### From Phase 2 to Phase 3

1. **Add context formatter:** Implement sliding window
2. **Integrate with orchestrator:** Use formatted context in prompts
3. **Add Redis caching:** Session metadata and agent state
4. **Implement TTL:** Automatic session expiration

---

## Summary

This plan adopts the proven OneMesh architecture patterns using **ScyllaDB (Alternator) + Redis Sentinel**, providing a Kubernetes-native solution proven at scale (Discord uses ScyllaDB for trillion+ chat messages).

### Architecture Mapping

| OneMesh | Our Implementation | Infrastructure |
|---------|-------------------|----------------|
| DynamoDB (primary) | ScyllaDB Alternator | `http://scylla-client.scylla.svc.cluster.local:8000` |
| Redis (cache) | Redis Sentinel | `redis-sentinel.redis-sentinel:6379` |
| Snowflake (analytics) | N/A (future) | - |
| AWS Lambda | FastAPI on Kind | Local pods |
| Bedrock agents | Ollama agents | `http://localhost:11434` |
| React frontend | Next.js frontend | `http://localhost:3000` |

### Key Architectural Decisions (Validated)

1. **ScyllaDB (Alternator) for chat history** - DynamoDB-compatible, K8s-native, Discord-proven
2. **Redis Sentinel for caching** - Session state, agent state, rate limiting (already deployed)
3. **PostgreSQL (pgvector) for RAG only** - Vector embeddings separate from chat data
4. **Incremental context summarization** - Only summarize newly dropped spans (Factory.ai pattern)
5. **TanStack Query v5** - Optimistic updates with rollback pattern
6. **Rate limiting** - Redis-based sliding window algorithm

### Production-Grade Features

| Feature | Implementation | Benefit |
|---------|---------------|---------|
| **Auto data retention** | ScyllaDB TTL | Zero-maintenance expiration |
| **High availability** | Redis Sentinel + Scylla Operator | Automatic failover |
| **Production path** | ScyllaDB (same in dev & prod) | No migration needed |
| **Incremental summarization** | Factory.ai pattern | ~90% token cost reduction |
| **Optimistic updates** | TanStack Query v5 | Instant UI feedback |
| **Pipeline batching** | Redis pipelines | Reduced network latency |

### Implementation Phases

| Phase | Goal | Infrastructure |
|-------|------|----------------|
| **Phase 0** | Deploy ScyllaDB Operator, verify cluster services | Scylla Operator + Helm |
| **Phase 1** | Backend (ScyllaDB repos, Redis client, endpoints) | ScyllaDB + Redis Sentinel |
| **Phase 2** | Frontend (session drawer, TanStack Query) | Next.js |
| **Phase 3** | Context optimization (incremental summarization) | Ollama |

### Prerequisites Checklist

```bash
# Verify all services are running
kubectl config use-context kind-dev-services-amer

# 1. Deploy ScyllaDB Operator
helm repo add scylla https://scylla-operator-charts.storage.googleapis.com/stable
helm install scylla-operator scylla/scylla-operator -n scylla-operator --create-namespace

# 2. Deploy ScyllaDB Cluster
kubectl apply -f blueprints/devassist/scylla/cluster.yaml
kubectl wait --for=condition=ready pod -l app=scylla -n scylla --timeout=300s

# 3. Verify Alternator endpoint
curl http://scylla-client.scylla.svc.cluster.local:8000/

# 4. Redis Sentinel
kubectl get pods -n redis-sentinel

# 4. PostgreSQL (pgvector - for RAG)
kubectl get pods -n database
```

---

## Appendix: References

### Industry Sources Consulted

1. **SparkCo AI (2025)** - Session State Persistence Best Practices
2. **Factory.ai (2025)** - Context Compaction for LLMs
3. **mem0.ai (2025)** - LLM Chat History Summarization Guide
4. **Redis Labs** - LLM Session Memory Documentation
5. **AWS DynamoDB** - TTL and Access Patterns
6. **TanStack Query v5** - Optimistic Updates Guide
7. **AWS Prescriptive Guidance** - DynamoDB for Chat Applications
8. **aioboto3** - Async DynamoDB Client Patterns
9. **FastAPI Best Practices 2025** - Production Patterns
