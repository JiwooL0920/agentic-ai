"""
Vector store using PostgreSQL with pgvector extension.

Provides document storage and similarity search with cosine distance.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import asyncpg
import structlog

from ..config import get_settings

logger = structlog.get_logger()

# Default embedding dimensions for nomic-embed-text
EMBEDDING_DIMENSIONS = 768


class VectorStoreError(Exception):
    """Raised when vector store operations fail."""

    pass


@dataclass
class Document:
    """Document with embedding for vector storage.

    Attributes:
        id: Unique document identifier.
        content: Document text content.
        embedding: Vector embedding (768 dimensions for nomic-embed-text).
        metadata: Additional document metadata (source, author, etc.).
        scope: Knowledge scope for filtering (e.g., "kubernetes", "python").
        created_at: Document creation timestamp.
        updated_at: Document last update timestamp.
    """

    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    scope: str = "default"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert document to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "scope": self.scope,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        """Create document from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data["content"],
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
            scope=data.get("scope", "default"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else None
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if data.get("updated_at")
                else None
            ),
        )


@dataclass
class SearchResult:
    """Result from similarity search.

    Attributes:
        document: The matched document.
        score: Similarity score (higher is more similar for cosine).
        distance: Vector distance (lower is more similar).
    """

    document: Document
    score: float
    distance: float


class PgVectorStore:
    """Vector store using PostgreSQL with pgvector.

    Uses cosine similarity for search and IVFFlat index for performance.

    Example:
        store = PgVectorStore()
        await store.initialize()

        # Add documents
        docs = [Document(content="Hello", embedding=[0.1, 0.2, ...])]
        await store.add_documents(docs)

        # Search
        results = await store.similarity_search(query_embedding, k=5, scope="python")
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        table_name: str = "documents",
    ):
        """Initialize vector store.

        Args:
            host: PostgreSQL host.
            port: PostgreSQL port.
            database: Database name.
            user: Database user.
            password: Database password.
            table_name: Name of documents table.
        """
        settings = get_settings()
        self._host = host or settings.postgres_host
        self._port = port or settings.postgres_port
        self._database = database or settings.postgres_db
        self._user = user or settings.postgres_user
        self._password = password or settings.postgres_password
        self._table_name = table_name
        self._pool: asyncpg.Pool | None = None
        self._logger = logger.bind(service="vector_store", table=table_name)

    async def initialize(self) -> None:
        """Initialize connection pool and create tables if needed."""
        try:
            self._pool = await asyncpg.create_pool(
                host=self._host,
                port=self._port,
                database=self._database,
                user=self._user,
                password=self._password,
                min_size=2,
                max_size=10,
            )
            self._logger.info("connection_pool_created")

            # Ensure pgvector extension and tables exist
            await self._ensure_schema()

        except asyncpg.PostgresError as e:
            self._logger.error("initialization_failed", error=str(e))
            raise VectorStoreError(f"Failed to initialize vector store: {e}") from e

    async def _ensure_schema(self) -> None:
        """Create pgvector extension and documents table if they don't exist."""
        if not self._pool:
            raise VectorStoreError("Connection pool not initialized")

        async with self._pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create documents table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    embedding vector({EMBEDDING_DIMENSIONS}),
                    metadata JSONB DEFAULT '{{}}',
                    scope VARCHAR(255) DEFAULT 'default',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Create indexes
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self._table_name}_scope
                ON {self._table_name} (scope)
            """)

            # Create IVFFlat index for similarity search
            # Using lists=100 is good for up to ~1M documents
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self._table_name}_embedding
                ON {self._table_name}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)

            self._logger.info("schema_ensured")

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._logger.info("connection_pool_closed")

    async def add_documents(self, documents: list[Document]) -> list[str]:
        """Add documents to the vector store.

        Args:
            documents: List of documents with embeddings.

        Returns:
            List of document IDs.

        Raises:
            VectorStoreError: If documents don't have embeddings or insert fails.
        """
        if not self._pool:
            raise VectorStoreError("Connection pool not initialized")

        if not documents:
            return []

        # Validate all documents have embeddings
        for doc in documents:
            if doc.embedding is None:
                raise VectorStoreError(f"Document {doc.id} is missing embedding")
            if len(doc.embedding) != EMBEDDING_DIMENSIONS:
                raise VectorStoreError(
                    f"Document {doc.id} has wrong embedding dimension: "
                    f"{len(doc.embedding)} (expected {EMBEDDING_DIMENSIONS})"
                )

        ids: list[str] = []
        async with self._pool.acquire() as conn:
            for doc in documents:
                embedding = doc.embedding
                if embedding is None:
                    continue
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

                result = await conn.fetchrow(
                    f"""
                    INSERT INTO {self._table_name}
                        (id, content, embedding, metadata, scope)
                    VALUES ($1, $2, $3::vector, $4, $5)
                    RETURNING id
                    """,
                    uuid.UUID(doc.id),
                    doc.content,
                    embedding_str,
                    json.dumps(doc.metadata),
                    doc.scope,
                )
                if result:
                    ids.append(str(result["id"]))

        self._logger.info("documents_added", count=len(ids))
        return ids

    async def similarity_search(
        self,
        query_embedding: list[float],
        k: int = 5,
        scope: str | None = None,
        scopes: list[str] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Search for similar documents using cosine similarity.

        Args:
            query_embedding: Query vector.
            k: Number of results to return.
            scope: Single scope to filter by.
            scopes: Multiple scopes to filter by (OR).
            metadata_filter: Filter by metadata fields.
            min_score: Minimum similarity score (0-1).

        Returns:
            List of search results ordered by similarity.
        """
        if not self._pool:
            raise VectorStoreError("Connection pool not initialized")

        if len(query_embedding) != EMBEDDING_DIMENSIONS:
            raise VectorStoreError(
                f"Query embedding has wrong dimension: "
                f"{len(query_embedding)} (expected {EMBEDDING_DIMENSIONS})"
            )

        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Build WHERE clause
        conditions = []
        params: list[Any] = [embedding_str, k]
        param_idx = 3

        # Scope filtering
        if scope:
            conditions.append(f"scope = ${param_idx}")
            params.append(scope)
            param_idx += 1
        elif scopes:
            placeholders = ", ".join(f"${param_idx + i}" for i in range(len(scopes)))
            conditions.append(f"scope IN ({placeholders})")
            params.extend(scopes)
            param_idx += len(scopes)

        # Metadata filtering (simple equality checks)
        if metadata_filter:
            for key, value in metadata_filter.items():
                conditions.append(f"metadata->>'{key}' = ${param_idx}")
                params.append(str(value))
                param_idx += 1

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Use cosine distance (1 - cosine_similarity)
        # Lower distance = more similar
        query = f"""
            SELECT
                id,
                content,
                metadata,
                scope,
                created_at,
                updated_at,
                1 - (embedding <=> $1::vector) AS similarity,
                embedding <=> $1::vector AS distance
            FROM {self._table_name}
            {where_clause}
            ORDER BY distance
            LIMIT $2
        """

        results: list[SearchResult] = []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            for row in rows:
                similarity = float(row["similarity"])

                # Filter by minimum score
                if similarity < min_score:
                    continue

                doc = Document(
                    id=str(row["id"]),
                    content=row["content"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    scope=row["scope"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

                results.append(
                    SearchResult(
                        document=doc,
                        score=similarity,
                        distance=float(row["distance"]),
                    )
                )

        self._logger.debug(
            "similarity_search_completed",
            k=k,
            scope=scope or scopes,
            results_count=len(results),
        )

        return results

    async def get_document(self, doc_id: str) -> Document | None:
        """Get a document by ID.

        Args:
            doc_id: Document ID.

        Returns:
            Document if found, None otherwise.
        """
        if not self._pool:
            raise VectorStoreError("Connection pool not initialized")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT id, content, metadata, scope, created_at, updated_at
                FROM {self._table_name}
                WHERE id = $1
                """,
                uuid.UUID(doc_id),
            )

            if not row:
                return None

            return Document(
                id=str(row["id"]),
                content=row["content"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                scope=row["scope"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def delete_documents(self, doc_ids: list[str]) -> int:
        """Delete documents by IDs.

        Args:
            doc_ids: List of document IDs to delete.

        Returns:
            Number of documents deleted.
        """
        if not self._pool:
            raise VectorStoreError("Connection pool not initialized")

        if not doc_ids:
            return 0

        uuids = [uuid.UUID(doc_id) for doc_id in doc_ids]

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"""
                DELETE FROM {self._table_name}
                WHERE id = ANY($1)
                """,
                uuids,
            )

            # Parse "DELETE N" response
            count = int(result.split()[-1]) if result else 0
            self._logger.info("documents_deleted", count=count)
            return count

    async def delete_by_scope(self, scope: str) -> int:
        """Delete all documents in a scope.

        Args:
            scope: Scope to delete.

        Returns:
            Number of documents deleted.
        """
        if not self._pool:
            raise VectorStoreError("Connection pool not initialized")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"""
                DELETE FROM {self._table_name}
                WHERE scope = $1
                """,
                scope,
            )

            count = int(result.split()[-1]) if result else 0
            self._logger.info("scope_deleted", scope=scope, count=count)
            return count

    async def list_scopes(self) -> list[str]:
        """List all unique scopes in the store.

        Returns:
            List of scope names.
        """
        if not self._pool:
            raise VectorStoreError("Connection pool not initialized")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT DISTINCT scope FROM {self._table_name}
                ORDER BY scope
                """
            )
            return [row["scope"] for row in rows]

    async def count(self, scope: str | None = None) -> int:
        """Count documents in the store.

        Args:
            scope: Optional scope to filter by.

        Returns:
            Document count.
        """
        if not self._pool:
            raise VectorStoreError("Connection pool not initialized")

        async with self._pool.acquire() as conn:
            if scope:
                row = await conn.fetchrow(
                    f"SELECT COUNT(*) FROM {self._table_name} WHERE scope = $1",
                    scope,
                )
            else:
                row = await conn.fetchrow(f"SELECT COUNT(*) FROM {self._table_name}")

            return row["count"] if row else 0

    async def list_documents(
        self, scope: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[Document]:
        """List documents from the store.

        Args:
            scope: Optional scope to filter by.
            limit: Maximum number of documents to return.
            offset: Number of documents to skip.

        Returns:
            List of documents.
        """
        if not self._pool:
            raise VectorStoreError("Connection pool not initialized")

        async with self._pool.acquire() as conn:
            if scope:
                query = f"""
                    SELECT id, content, scope, metadata, embedding
                    FROM {self._table_name}
                    WHERE scope = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                """
                rows = await conn.fetch(query, scope, limit, offset)
            else:
                query = f"""
                    SELECT id, content, scope, metadata, embedding
                    FROM {self._table_name}
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                """
                rows = await conn.fetch(query, limit, offset)

            documents = []
            for row in rows:
                # Convert UUID to string and parse JSON metadata
                metadata = row["metadata"]
                if isinstance(metadata, str):
                    import json
                    metadata = json.loads(metadata)

                doc = Document(
                    id=str(row["id"]),  # Convert UUID to string
                    content=row["content"],
                    scope=row["scope"],
                    metadata=metadata if isinstance(metadata, dict) else {},
                    embedding=row["embedding"],
                )
                documents.append(doc)

            return documents


# Singleton instance
_store_instance: PgVectorStore | None = None


async def get_vector_store() -> PgVectorStore:
    """Get singleton vector store instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = PgVectorStore()
        await _store_instance.initialize()
    return _store_instance
