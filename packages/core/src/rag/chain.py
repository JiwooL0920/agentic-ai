"""
RAG Chain for context augmentation.

Builds context from retrieved documents and augments agent prompts
with relevant information.
"""

from dataclasses import dataclass, field
from typing import Any

import structlog

from ..config import get_settings
from .retriever import RAGRetriever, RetrievalResult, get_retriever

logger = structlog.get_logger()

# Default RAG prompt template
DEFAULT_RAG_TEMPLATE = """You have access to the following relevant context from the knowledge base:

<context>
{context}
</context>

Use this context to help answer the user's question. If the context doesn't contain relevant information, you can still answer based on your general knowledge, but mention that you couldn't find specific documentation on the topic.

User Question: {query}"""

# Compact template for shorter contexts
COMPACT_RAG_TEMPLATE = """Context:
{context}

Question: {query}"""


@dataclass
class RAGContext:
    """Context built from RAG retrieval.

    Attributes:
        context_text: Formatted context for prompt injection.
        documents: Source documents used.
        query: Original query.
        token_estimate: Approximate token count.
        scores: Similarity scores for each document.
    """

    context_text: str
    documents: list[Any]  # Document type from vector_store
    query: str
    token_estimate: int
    scores: list[float] = field(default_factory=list)

    @property
    def has_context(self) -> bool:
        """Check if context was found."""
        return len(self.documents) > 0


class RAGChain:
    """Chain for RAG context building and prompt augmentation.

    Handles:
    - Document retrieval based on query
    - Context formatting with token limits
    - Prompt template application
    - Source citation preparation

    Example:
        chain = RAGChain()
        await chain.initialize()

        # Build context for a query
        context = await chain.build_context(
            query="How do I configure Helm charts?",
            knowledge_scope=["kubernetes", "helm"],
            max_tokens=2000,
        )

        # Augment a prompt
        augmented_prompt = chain.augment_prompt(
            system_prompt="You are a Kubernetes expert.",
            query="How do I configure Helm charts?",
            context=context,
        )
    """

    def __init__(
        self,
        retriever: RAGRetriever | None = None,
        template: str = DEFAULT_RAG_TEMPLATE,
        max_context_tokens: int | None = None,
        chars_per_token: float = 4.0,
    ):
        """Initialize RAG chain.

        Args:
            retriever: RAG retriever (uses singleton if not provided).
            template: Prompt template with {context} and {query} placeholders.
            max_context_tokens: Maximum tokens for context (uses settings if not provided).
            chars_per_token: Approximate characters per token for estimation.
        """
        settings = get_settings()
        self._retriever = retriever
        self._template = template
        self._max_context_tokens = max_context_tokens if max_context_tokens is not None else settings.rag_max_context_tokens
        self._chars_per_token = chars_per_token
        self._logger = logger.bind(service="rag_chain")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize chain components."""
        if self._initialized:
            return

        if self._retriever is None:
            self._retriever = await get_retriever()

        self._initialized = True
        self._logger.info("chain_initialized")

    async def build_context(
        self,
        query: str,
        knowledge_scope: list[str] | None = None,
        max_tokens: int | None = None,
        k: int = 5,
        include_metadata: bool = True,
    ) -> RAGContext:
        """Build context from retrieved documents.

        Args:
            query: User query for retrieval.
            knowledge_scope: Scopes to filter documents.
            max_tokens: Maximum tokens for context (uses default if not provided).
            k: Number of documents to retrieve.
            include_metadata: Include source info in context.

        Returns:
            RAGContext with formatted context and metadata.
        """
        if not self._initialized:
            await self.initialize()

        if self._retriever is None:
            raise RuntimeError("Retriever not initialized")

        max_tokens = max_tokens or self._max_context_tokens
        max_chars = int(max_tokens * self._chars_per_token)

        # Retrieve relevant documents
        result: RetrievalResult = await self._retriever.retrieve(
            query=query,
            knowledge_scope=knowledge_scope,
            k=k,
        )

        if not result.documents:
            self._logger.info(
                "no_documents_found", 
                query=query[:100],
                knowledge_scope=knowledge_scope,
            )
            return RAGContext(
                context_text="",
                documents=[],
                query=query,
                token_estimate=0,
                scores=[],
            )

        # Build context with token limit
        context_parts: list[str] = []
        total_chars = 0
        included_docs: list[Any] = []
        included_scores: list[float] = []

        for doc, score in zip(result.documents, result.scores, strict=True):
            # Format document chunk
            doc_text = self._format_document(doc, score, include_metadata)
            doc_chars = len(doc_text)

            # Check if adding this doc exceeds limit
            if total_chars + doc_chars > max_chars:
                # Try to fit a truncated version
                remaining_chars = max_chars - total_chars
                if remaining_chars > 200:  # Only include if meaningful amount remains
                    truncated = doc_text[:remaining_chars] + "..."
                    context_parts.append(truncated)
                    included_docs.append(doc)
                    included_scores.append(score)
                break

            context_parts.append(doc_text)
            total_chars += doc_chars
            included_docs.append(doc)
            included_scores.append(score)

        context_text = "\n\n---\n\n".join(context_parts)
        token_estimate = int(len(context_text) / self._chars_per_token)

        self._logger.info(
            "context_built",
            documents_used=len(included_docs),
            total_retrieved=len(result.documents),
            token_estimate=token_estimate,
        )

        return RAGContext(
            context_text=context_text,
            documents=included_docs,
            query=query,
            token_estimate=token_estimate,
            scores=included_scores,
        )

    def _format_document(
        self,
        doc: Any,
        score: float,
        include_metadata: bool,
    ) -> str:
        """Format a single document for context."""
        parts: list[str] = []

        if include_metadata:
            # Add source info header
            source = doc.metadata.get("source", doc.metadata.get("filename", "Unknown"))
            parts.append(f"[Source: {source} | Relevance: {score:.2f}]")

        parts.append(doc.content)

        return "\n".join(parts)

    def augment_prompt(
        self,
        system_prompt: str,
        query: str,
        context: RAGContext,
        template: str | None = None,
    ) -> str:
        """Augment system prompt with RAG context.

        Args:
            system_prompt: Original system prompt.
            query: User query.
            context: RAG context from build_context.
            template: Custom template (uses instance default if not provided).

        Returns:
            Augmented system prompt.
        """
        if not context.has_context:
            # No context found, return original prompt
            return system_prompt

        template = template or self._template

        # Build RAG section
        rag_section = template.format(
            context=context.context_text,
            query=query,
        )

        # Combine with original system prompt
        augmented = f"{system_prompt}\n\n{rag_section}"

        self._logger.debug(
            "prompt_augmented",
            original_length=len(system_prompt),
            augmented_length=len(augmented),
        )

        return augmented

    def format_with_citations(
        self,
        response: str,
        context: RAGContext,
    ) -> str:
        """Add source citations to a response.

        Args:
            response: LLM response text.
            context: RAG context used for the response.

        Returns:
            Response with appended citations.
        """
        if not context.has_context:
            return response

        # Build citations
        citations: list[str] = []
        for i, doc in enumerate(context.documents, 1):
            source = doc.metadata.get("source", doc.metadata.get("filename", "Document"))
            citations.append(f"[{i}] {source}")

        citation_text = "\n\n---\nSources:\n" + "\n".join(citations)

        return response + citation_text

    async def invoke(
        self,
        query: str,
        system_prompt: str,
        knowledge_scope: list[str] | None = None,
        k: int = 5,
        max_tokens: int | None = None,
    ) -> tuple[str, RAGContext]:
        """Convenience method to build context and augment prompt in one call.

        Args:
            query: User query.
            system_prompt: Original system prompt.
            knowledge_scope: Scopes to filter documents.
            k: Number of documents to retrieve.
            max_tokens: Maximum context tokens.

        Returns:
            Tuple of (augmented_prompt, context).
        """
        context = await self.build_context(
            query=query,
            knowledge_scope=knowledge_scope,
            max_tokens=max_tokens,
            k=k,
        )

        augmented_prompt = self.augment_prompt(
            system_prompt=system_prompt,
            query=query,
            context=context,
        )

        return augmented_prompt, context


# Singleton instance
_chain_instance: RAGChain | None = None


async def get_rag_chain() -> RAGChain:
    """Get singleton RAG chain instance."""
    global _chain_instance
    if _chain_instance is None:
        _chain_instance = RAGChain()
        await _chain_instance.initialize()
    return _chain_instance
