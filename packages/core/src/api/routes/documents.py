"""Document management endpoints for RAG."""

import hashlib
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from ...rag import (
    Document,
    OllamaEmbeddings,
    PgVectorStore,
    get_chunker,
    get_embeddings,
    get_vector_store,
)

logger = structlog.get_logger()

router = APIRouter()


class DocumentResponse(BaseModel):
    """Response model for document operations."""

    id: str
    content_preview: str = Field(description="First 200 chars of content")
    scope: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_count: int = 0


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""

    documents: list[DocumentResponse]
    total_count: int
    scope: str | None = None


class DocumentSearchRequest(BaseModel):
    """Request model for document search."""

    query: str = Field(min_length=1, max_length=1000)
    scope: str | None = None
    scopes: list[str] | None = None
    k: int = Field(default=5, ge=1, le=50)
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)


class DocumentSearchResult(BaseModel):
    """Single search result."""

    id: str
    content: str
    score: float
    scope: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentSearchResponse(BaseModel):
    """Response model for document search."""

    results: list[DocumentSearchResult]
    query: str
    total_results: int


class DocumentDeleteResponse(BaseModel):
    """Response model for document deletion."""

    deleted_count: int
    message: str


@router.post("/documents", response_model=DocumentListResponse)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    scope: Annotated[str, Form()] = "default",
    chunk_size: Annotated[int, Form()] = 1000,
    chunk_overlap: Annotated[int, Form()] = 200,
) -> DocumentListResponse:
    """
    Upload and index a document for RAG.

    Supported file types:
    - Text (.txt)
    - Markdown (.md)
    - Python (.py)
    - JavaScript/TypeScript (.js, .ts, .tsx)

    The document will be:
    1. Chunked based on file type
    2. Embedded using nomic-embed-text
    3. Stored in pgvector for similarity search
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else "txt"
    allowed_extensions = {"txt", "md", "py", "js", "ts", "tsx", "jsx", "json", "yaml", "yml"}

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}",
        )

    content = await file.read()
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded text",
        ) from e

    if not text_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    content_hash = hashlib.sha256(content).hexdigest()

    chunker = get_chunker(file_ext, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = chunker.chunk(text_content)

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks generated from document",
        )

    logger.info(
        "document_chunked",
        filename=file.filename,
        chunk_count=len(chunks),
        file_type=file_ext,
    )

    embeddings: OllamaEmbeddings = get_embeddings()
    chunk_texts = [chunk.content for chunk in chunks]

    try:
        vectors = await embeddings.embed_batch(chunk_texts)
    except Exception as e:
        logger.error("embedding_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Embedding service unavailable: {e}",
        ) from e

    documents: list[Document] = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
        doc = Document(
            content=chunk.content,
            embedding=vector,
            scope=scope,
            metadata={
                "filename": file.filename,
                "file_type": file_ext,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "content_hash": content_hash,
                **chunk.metadata,
            },
        )
        documents.append(doc)

    store: PgVectorStore = await get_vector_store()

    try:
        doc_ids = await store.add_documents(documents)
    except Exception as e:
        logger.error("storage_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector store unavailable: {e}",
        ) from e

    logger.info(
        "document_indexed",
        filename=file.filename,
        scope=scope,
        documents_stored=len(doc_ids),
    )

    response_docs = [
        DocumentResponse(
            id=doc_id,
            content_preview=doc.content[:200],
            scope=doc.scope,
            metadata=doc.metadata,
            chunk_count=1,
        )
        for doc_id, doc in zip(doc_ids, documents, strict=True)
    ]

    return DocumentListResponse(
        documents=response_docs,
        total_count=len(response_docs),
        scope=scope,
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    scope: str | None = None,
    limit: int = 100,
) -> DocumentListResponse:
    """
    List documents in the vector store.

    Optionally filter by scope.
    """
    store: PgVectorStore = await get_vector_store()

    try:
        count = await store.count(scope=scope)
    except Exception as e:
        logger.error("list_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector store unavailable: {e}",
        ) from e

    return DocumentListResponse(
        documents=[],
        total_count=count,
        scope=scope,
    )


@router.get("/documents/scopes")
async def list_scopes() -> dict[str, Any]:
    """List all document scopes."""
    store: PgVectorStore = await get_vector_store()

    try:
        scopes = await store.list_scopes()
        scope_counts = {}
        for s in scopes:
            scope_counts[s] = await store.count(scope=s)
    except Exception as e:
        logger.error("list_scopes_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector store unavailable: {e}",
        ) from e

    return {
        "scopes": scopes,
        "counts": scope_counts,
        "total_documents": sum(scope_counts.values()),
    }


@router.post("/documents/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
) -> DocumentSearchResponse:
    """
    Search documents using semantic similarity.

    Returns documents ranked by relevance to the query.
    """
    embeddings: OllamaEmbeddings = get_embeddings()

    try:
        query_vector = await embeddings.embed(request.query)
    except Exception as e:
        logger.error("query_embedding_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Embedding service unavailable: {e}",
        ) from e

    store: PgVectorStore = await get_vector_store()

    try:
        results = await store.similarity_search(
            query_embedding=query_vector,
            k=request.k,
            scope=request.scope,
            scopes=request.scopes,
            min_score=request.min_score,
        )
    except Exception as e:
        logger.error("search_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector store unavailable: {e}",
        ) from e

    search_results = [
        DocumentSearchResult(
            id=r.document.id,
            content=r.document.content,
            score=r.score,
            scope=r.document.scope,
            metadata=r.document.metadata,
        )
        for r in results
    ]

    logger.info(
        "document_search",
        query_preview=request.query[:50],
        results_count=len(search_results),
    )

    return DocumentSearchResponse(
        results=search_results,
        query=request.query,
        total_results=len(search_results),
    )


@router.delete("/documents/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(doc_id: str) -> DocumentDeleteResponse:
    """Delete a specific document by ID."""
    store: PgVectorStore = await get_vector_store()

    try:
        deleted = await store.delete_documents([doc_id])
    except Exception as e:
        logger.error("delete_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector store unavailable: {e}",
        ) from e

    if deleted == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )

    return DocumentDeleteResponse(
        deleted_count=deleted,
        message=f"Deleted document {doc_id}",
    )


@router.delete("/documents/scope/{scope}", response_model=DocumentDeleteResponse)
async def delete_scope(scope: str) -> DocumentDeleteResponse:
    """Delete all documents in a scope."""
    store: PgVectorStore = await get_vector_store()

    try:
        deleted = await store.delete_by_scope(scope)
    except Exception as e:
        logger.error("delete_scope_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector store unavailable: {e}",
        ) from e

    return DocumentDeleteResponse(
        deleted_count=deleted,
        message=f"Deleted {deleted} documents from scope '{scope}'",
    )
