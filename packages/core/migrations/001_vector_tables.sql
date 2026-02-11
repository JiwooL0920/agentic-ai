-- Migration 001: Vector tables for RAG pipeline
-- Requires: PostgreSQL 15+ with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table for RAG storage
-- Uses 768 dimensions for nomic-embed-text embeddings
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Document content
    content TEXT NOT NULL,
    
    -- Vector embedding (768 dimensions for nomic-embed-text)
    embedding vector(768),
    
    -- Metadata as JSONB for flexible querying
    -- Can include: source, author, filename, chunk_index, etc.
    metadata JSONB DEFAULT '{}',
    
    -- Knowledge scope for filtering by agent
    -- Matches agent's knowledge_scope config (e.g., "kubernetes", "python")
    scope VARCHAR(255) NOT NULL DEFAULT 'default',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for scope filtering (most common filter)
CREATE INDEX IF NOT EXISTS idx_documents_scope 
ON documents (scope);

-- Index for metadata JSONB queries
CREATE INDEX IF NOT EXISTS idx_documents_metadata 
ON documents USING GIN (metadata);

-- IVFFlat index for fast cosine similarity search
-- lists=100 is good for up to ~1M documents
-- Increase lists for larger datasets (sqrt(n) is a good heuristic)
CREATE INDEX IF NOT EXISTS idx_documents_embedding 
ON documents 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Trigger to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Document chunks table for tracking chunked documents
-- Helps with document management and re-chunking
CREATE TABLE IF NOT EXISTS document_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Original document info
    filename VARCHAR(512) NOT NULL,
    content_hash VARCHAR(64) NOT NULL, -- SHA-256 of original content
    file_type VARCHAR(50) NOT NULL,    -- 'text', 'markdown', 'code', 'pdf'
    
    -- Processing info
    chunk_count INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER,
    
    -- Scope for filtering
    scope VARCHAR(255) NOT NULL DEFAULT 'default',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicate uploads
    CONSTRAINT unique_source_hash UNIQUE (content_hash, scope)
);

-- Link chunks back to their source documents
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS source_id UUID REFERENCES document_sources(id) ON DELETE CASCADE;

-- Index for finding chunks by source
CREATE INDEX IF NOT EXISTS idx_documents_source_id 
ON documents (source_id);

-- Index for source document queries
CREATE INDEX IF NOT EXISTS idx_document_sources_scope 
ON document_sources (scope);

CREATE INDEX IF NOT EXISTS idx_document_sources_filename 
ON document_sources (filename);

-- Apply updated_at trigger to sources table too
DROP TRIGGER IF EXISTS update_document_sources_updated_at ON document_sources;
CREATE TRIGGER update_document_sources_updated_at
    BEFORE UPDATE ON document_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE documents IS 'Vector storage for RAG document chunks';
COMMENT ON TABLE document_sources IS 'Tracks original documents that have been chunked';
COMMENT ON COLUMN documents.embedding IS 'nomic-embed-text produces 768-dimensional vectors';
COMMENT ON COLUMN documents.scope IS 'Matches agent knowledge_scope for filtering';
COMMENT ON COLUMN documents.metadata IS 'Flexible metadata: source, author, chunk_index, language, etc.';
