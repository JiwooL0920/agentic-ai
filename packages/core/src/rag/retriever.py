"""
RAG Retriever for semantic document search.

Combines embeddings with vector store to retrieve relevant documents
based on query similarity and knowledge scope filtering.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from ..config import get_settings
from .embeddings import OllamaEmbeddings, get_embeddings
from .vector_store import Document, PgVectorStore, SearchResult, get_vector_store

logger = structlog.get_logger()


@dataclass
class RetrievalResult:
    """Result from RAG retrieval.

    Attributes:
        documents: Retrieved documents.
        query: Original query text.
        scores: Similarity scores for each document.
    """

    documents: list[Document]
    query: str
    scores: list[float]

    @property
    def top_document(self) -> Document | None:
        """Get the most relevant document."""
        return self.documents[0] if self.documents else None

    @property
    def context(self) -> str:
        """Get concatenated document content as context."""
        return "\n\n---\n\n".join(doc.content for doc in self.documents)


class RAGRetriever:
    """Retriever for semantic document search.

    Combines:
    - Embedding generation (Ollama)
    - Vector similarity search (pgvector)
    - Knowledge scope filtering (agent-specific)

    Example:
        retriever = RAGRetriever()
        await retriever.initialize()

        # Retrieve for specific scopes
        results = await retriever.retrieve(
            query="How do I deploy to Kubernetes?",
            knowledge_scope=["kubernetes", "devops"],
            k=5,
        )

        # Use results
        context = results.context
        for doc, score in zip(results.documents, results.scores):
            print(f"[{score:.2f}] {doc.content[:100]}...")
    """

    def __init__(
        self,
        embeddings: OllamaEmbeddings | None = None,
        vector_store: PgVectorStore | None = None,
        default_k: int | None = None,
        min_score: float | None = None,
    ):
        """Initialize retriever.

        Args:
            embeddings: Embeddings service (uses singleton if not provided).
            vector_store: Vector store (uses singleton if not provided).
            default_k: Default number of results to retrieve (uses settings if not provided).
            min_score: Minimum similarity score threshold (uses settings if not provided).
        """
        settings = get_settings()
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._default_k = default_k if default_k is not None else settings.rag_default_k
        self._min_score = min_score if min_score is not None else settings.rag_min_score
        self._logger = logger.bind(service="rag_retriever")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize retriever components."""
        if self._initialized:
            return

        if self._embeddings is None:
            self._embeddings = get_embeddings()

        if self._vector_store is None:
            self._vector_store = await get_vector_store()

        self._initialized = True
        self._logger.info("retriever_initialized")

    async def retrieve(
        self,
        query: str,
        knowledge_scope: list[str] | None = None,
        k: int | None = None,
        min_score: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant documents for a query.

        Args:
            query: Search query text.
            knowledge_scope: List of scopes to filter by (matches agent config).
            k: Number of results to retrieve.
            min_score: Minimum similarity score.
            metadata_filter: Additional metadata filters.

        Returns:
            RetrievalResult with documents and scores.

        Raises:
            RuntimeError: If retriever is not initialized.
        """
        if not self._initialized:
            await self.initialize()

        if self._embeddings is None or self._vector_store is None:
            raise RuntimeError("Retriever not properly initialized")

        k = k or self._default_k
        min_score = min_score if min_score is not None else self._min_score

        self._logger.info(
            "retrieving_documents",
            query_preview=query[:100] if len(query) > 100 else query,
            knowledge_scope=knowledge_scope,
            k=k,
        )

        # Generate query embedding
        query_embedding = await self._embeddings.embed(query)

        # Search vector store
        search_results: list[SearchResult] = await self._vector_store.similarity_search(
            query_embedding=query_embedding,
            k=k,
            scopes=knowledge_scope,
            metadata_filter=metadata_filter,
            min_score=min_score,
        )

        documents = [r.document for r in search_results]
        scores = [r.score for r in search_results]

        self._logger.info(
            "retrieval_complete",
            results_count=len(documents),
            top_score=scores[0] if scores else 0,
        )

        return RetrievalResult(
            documents=documents,
            query=query,
            scores=scores,
        )

    async def retrieve_with_rerank(
        self,
        query: str,
        knowledge_scope: list[str] | None = None,
        k: int | None = None,
        initial_k_multiplier: int = 3,
    ) -> RetrievalResult:
        """Retrieve and re-rank documents for better relevance.

        Two-stage retrieval:
        1. Retrieve k * multiplier candidates
        2. Re-score using cross-encoder pattern (query-doc similarity)
        3. Return top k results

        Note: Currently uses embedding similarity for re-ranking.
        Can be extended to use a cross-encoder model for better results.

        Args:
            query: Search query text.
            knowledge_scope: Scopes to filter by.
            k: Final number of results.
            initial_k_multiplier: Multiplier for initial retrieval.

        Returns:
            RetrievalResult with re-ranked documents.
        """
        k = k or self._default_k

        # First pass: retrieve more candidates
        initial_k = k * initial_k_multiplier
        initial_result = await self.retrieve(
            query=query,
            knowledge_scope=knowledge_scope,
            k=initial_k,
            min_score=0.1,  # Lower threshold for initial retrieval
        )

        if len(initial_result.documents) <= k:
            return initial_result

        # Re-rank by computing similarity between query and each document
        # In a production system, you'd use a cross-encoder model here
        if self._embeddings is None:
            raise RuntimeError("Embeddings not initialized")

        reranked: list[tuple[Document, float]] = []

        for doc in initial_result.documents:
            # Compute direct similarity
            score = await self._embeddings.similarity(query, doc.content[:1000])
            reranked.append((doc, score))

        # Sort by re-ranked score
        reranked.sort(key=lambda x: x[1], reverse=True)

        # Take top k
        top_docs = [doc for doc, _ in reranked[:k]]
        top_scores = [score for _, score in reranked[:k]]

        self._logger.info(
            "reranking_complete",
            initial_count=len(initial_result.documents),
            final_count=len(top_docs),
        )

        return RetrievalResult(
            documents=top_docs,
            query=query,
            scores=top_scores,
        )

    async def health_check(self) -> dict[str, Any]:
        """Check retriever health.

        Returns:
            Health status dict.
        """
        status: dict[str, Any] = {"healthy": True, "components": {}}

        # Check embeddings
        if self._embeddings:
            emb_health = await self._embeddings.health_check()
            status["components"]["embeddings"] = emb_health
            if not emb_health.get("healthy"):
                status["healthy"] = False

        # Check vector store
        if self._vector_store:
            try:
                count = await self._vector_store.count()
                status["components"]["vector_store"] = {
                    "healthy": True,
                    "document_count": count,
                }
            except Exception as e:
                status["components"]["vector_store"] = {
                    "healthy": False,
                    "error": str(e),
                }
                status["healthy"] = False

        return status


# Singleton instance
_retriever_instance: RAGRetriever | None = None


async def get_retriever() -> RAGRetriever:
    """Get singleton retriever instance."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = RAGRetriever()
        await _retriever_instance.initialize()
    return _retriever_instance
