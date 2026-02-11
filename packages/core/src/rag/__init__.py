"""
RAG (Retrieval-Augmented Generation) module.

Provides document embedding, vector storage, and retrieval functionality
for augmenting agent responses with relevant context.
"""

from .chain import RAGChain, RAGContext, get_rag_chain
from .chunking import CodeChunker, MarkdownChunker, TextChunker, get_chunker
from .embeddings import OllamaEmbeddings, get_embeddings
from .retriever import RAGRetriever, RetrievalResult, get_retriever
from .vector_store import Document, PgVectorStore, SearchResult, get_vector_store

__all__ = [
    "OllamaEmbeddings",
    "get_embeddings",
    "PgVectorStore",
    "Document",
    "SearchResult",
    "get_vector_store",
    "TextChunker",
    "MarkdownChunker",
    "CodeChunker",
    "get_chunker",
    "RAGRetriever",
    "RetrievalResult",
    "get_retriever",
    "RAGChain",
    "RAGContext",
    "get_rag_chain",
]
