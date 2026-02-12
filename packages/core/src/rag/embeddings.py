"""
Embeddings service using Ollama.

Uses nomic-embed-text model for high-quality embeddings with 768 dimensions.
"""

from typing import Any

import httpx
import structlog
from ollama import AsyncClient

from ..config import get_settings

logger = structlog.get_logger()


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass


class OllamaEmbeddings:
    """Embeddings service using Ollama's embedding models.

    Uses nomic-embed-text (768 dimensions) by default.

    Example:
        embeddings = OllamaEmbeddings()
        vector = await embeddings.embed("Hello world")
        vectors = await embeddings.embed_batch(["Hello", "World"])
    """

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
    ):
        """Initialize embeddings service.

        Args:
            model: Embedding model name. Defaults to config value.
            host: Ollama host URL. Defaults to config value.
        """
        settings = get_settings()
        self._model = model or settings.ollama_embedding_model
        self._host = host or settings.ollama_host
        self._client = AsyncClient(host=self._host)
        self._logger = logger.bind(model=self._model, service="embeddings")
        self._dimensions: int | None = None

    @property
    def model(self) -> str:
        """Get the embedding model name."""
        return self._model

    @property
    def dimensions(self) -> int:
        """Get the embedding dimensions (768 for nomic-embed-text)."""
        if self._dimensions is None:
            # nomic-embed-text produces 768-dimensional vectors
            self._dimensions = 768
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as list of floats.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")

        try:
            response = await self._client.embeddings(
                model=self._model,
                prompt=text,
            )

            embedding: list[float] = response.get("embedding", [])
            if not embedding:
                raise EmbeddingError(f"Empty embedding returned for text: {text[:50]}...")

            self._logger.debug(
                "generated_embedding",
                text_length=len(text),
                embedding_dim=len(embedding),
            )

            return embedding

        except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException) as e:
            self._logger.error("embedding_error", error=str(e), text_preview=text[:50])
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Processes texts in batches for efficiency.

        Args:
            texts: List of texts to embed.
            batch_size: Number of texts per batch.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        if not texts:
            return []

        # Filter empty texts and track indices
        valid_texts: list[tuple[int, str]] = [
            (i, t) for i, t in enumerate(texts) if t and t.strip()
        ]

        if not valid_texts:
            raise EmbeddingError("All texts are empty")

        embeddings: list[tuple[int, list[float]]] = []

        for batch_start in range(0, len(valid_texts), batch_size):
            batch = valid_texts[batch_start : batch_start + batch_size]

            for idx, text in batch:
                try:
                    embedding = await self.embed(text)
                    embeddings.append((idx, embedding))
                except EmbeddingError:
                    # Log and re-raise with context
                    self._logger.error(
                        "batch_embedding_failed",
                        index=idx,
                        batch_start=batch_start,
                    )
                    raise

        self._logger.info(
            "batch_embeddings_generated",
            total_texts=len(texts),
            valid_texts=len(valid_texts),
            batches=(len(valid_texts) + batch_size - 1) // batch_size,
        )

        # Sort by original index and return embeddings only
        embeddings.sort(key=lambda x: x[0])
        return [e for _, e in embeddings]

    async def similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts.

        Args:
            text1: First text.
            text2: Second text.

        Returns:
            Cosine similarity score between -1 and 1.
        """
        emb1 = await self.embed(text1)
        emb2 = await self.embed(text2)
        return self._cosine_similarity(emb1, emb2)

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions don't match: {len(vec1)} vs {len(vec2)}")

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    async def health_check(self) -> dict[str, Any]:
        """Check if embedding service is available.

        Returns:
            Health status dict with 'healthy' bool and 'model' name.
        """
        try:
            # Try to generate a test embedding
            test_embedding = await self.embed("health check")
            return {
                "healthy": True,
                "model": self._model,
                "dimensions": len(test_embedding),
            }
        except EmbeddingError as e:
            return {
                "healthy": False,
                "model": self._model,
                "error": str(e),
            }


# Singleton instance for convenience
_embeddings_instance: OllamaEmbeddings | None = None


def get_embeddings() -> OllamaEmbeddings:
    """Get singleton embeddings instance."""
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = OllamaEmbeddings()
    return _embeddings_instance
