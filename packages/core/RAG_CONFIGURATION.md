# RAG Configuration Guide

All RAG (Retrieval-Augmented Generation) settings are configurable via environment variables.

## Configuration Settings

### Location
- **File**: `packages/core/.env`
- **Class**: `packages/core/src/config.py` → `Settings`
- **Environment Variables**: Set in `.env` or as system environment variables

### Available Settings

```bash
# RAG (Retrieval-Augmented Generation)
RAG_ENABLED=true           # Enable/disable RAG globally
RAG_MIN_SCORE=0.5          # Minimum similarity score (0.0-1.0)
RAG_DEFAULT_K=5            # Number of documents to retrieve per query
RAG_MAX_CONTEXT_TOKENS=4000  # Maximum tokens for RAG context
RAG_CHUNK_SIZE=1000        # Default chunk size for documents
RAG_CHUNK_OVERLAP=200      # Overlap between chunks
```

## Setting Details

### `RAG_ENABLED`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Master switch for RAG functionality
- **Impact**: When `false`, agents will not use knowledge base even if `knowledge_scope` is configured

**Use Case**: Disable RAG for testing or if you want agents to rely only on their base knowledge.

### `RAG_MIN_SCORE`
- **Type**: Float (0.0 to 1.0)
- **Default**: `0.5` (50% similarity)
- **Description**: Minimum cosine similarity score for retrieved documents
- **Impact**: Higher = more strict filtering, fewer but more relevant results

**Recommended Values**:
- **0.7-1.0**: Very strict (only high-quality matches)
- **0.5-0.7**: Balanced (recommended for production)
- **0.3-0.5**: Permissive (may include weak matches)
- **<0.3**: Very permissive (not recommended - lots of noise)

**Example**:
```bash
RAG_MIN_SCORE=0.7  # Only show matches with 70%+ relevance
```

**When to Adjust**:
- **Increase** (0.6-0.7): Users complain about irrelevant results
- **Decrease** (0.4-0.5): Users complain about not finding documents that should match

### `RAG_DEFAULT_K`
- **Type**: Integer
- **Default**: `5`
- **Description**: Number of top documents to retrieve per query
- **Impact**: More documents = more context but slower responses and higher token usage

**Recommended Values**:
- **3**: Fast, minimal context
- **5**: Balanced (recommended)
- **10**: Comprehensive, but may hit token limits

**Trade-offs**:
```
k=3:  Fast, ~1200 tokens, may miss relevant context
k=5:  Balanced, ~2000 tokens, good coverage
k=10: Comprehensive, ~4000 tokens, may exceed limits
```

### `RAG_MAX_CONTEXT_TOKENS`
- **Type**: Integer
- **Default**: `4000`
- **Description**: Maximum tokens allocated to RAG context in prompts
- **Impact**: Limits how much retrieved content can be injected

**Calculation**:
- Assumes ~4 characters per token
- 4000 tokens ≈ 16,000 characters of context

**When to Adjust**:
- **Increase** (6000-8000): Using models with large context windows (32K+)
- **Decrease** (2000-3000): Using smaller models or want faster responses

**Warning**: Must fit within model's total context window along with system prompt and conversation history.

### `RAG_CHUNK_SIZE`
- **Type**: Integer
- **Default**: `1000`
- **Description**: Target size for document chunks (in characters)
- **Impact**: Larger chunks = more context per chunk but fewer chunks per document

**Recommended Values**:
- **500**: Small chunks, precise matching, more chunks
- **1000**: Balanced (recommended)
- **2000**: Large chunks, more context per match

**Trade-offs**:
```
Small (500):  Precise matching, more specific results, more chunks to manage
Medium (1000): Balanced precision and context
Large (2000):  Broader context, fewer chunks, may include irrelevant info
```

### `RAG_CHUNK_OVERLAP`
- **Type**: Integer
- **Default**: `200`
- **Description**: Number of characters to overlap between consecutive chunks
- **Impact**: Prevents splitting important context across chunk boundaries

**Recommended Values**:
- **100**: Minimal overlap (faster, more chunks)
- **200**: Balanced (recommended, ~20% of chunk_size)
- **400**: High overlap (better context preservation)

**Why Overlap Matters**:
```
Without overlap (0):
  Chunk 1: "...machine learning models."
  Chunk 2: "To deploy a model, you need..."
  Problem: Context break! Lost connection between chunks.

With overlap (200):
  Chunk 1: "...machine learning models. To deploy a model..."
  Chunk 2: "machine learning models. To deploy a model, you need..."
  Benefit: Smooth transition, no context loss.
```

## Configuration Examples

### Strict/Production Setup
```bash
RAG_ENABLED=true
RAG_MIN_SCORE=0.7          # Only high-quality matches
RAG_DEFAULT_K=3            # Fewer documents for faster responses
RAG_MAX_CONTEXT_TOKENS=3000
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=150
```

### Permissive/Development Setup
```bash
RAG_ENABLED=true
RAG_MIN_SCORE=0.4          # More lenient matching
RAG_DEFAULT_K=10           # Comprehensive retrieval
RAG_MAX_CONTEXT_TOKENS=6000
RAG_CHUNK_SIZE=1500
RAG_CHUNK_OVERLAP=300
```

### Disable RAG
```bash
RAG_ENABLED=false          # Turn off RAG completely
```

## Testing Your Configuration

### 1. Check Current Settings
```bash
curl http://localhost:8001/health | jq
# Settings are loaded at startup - check logs
```

### 2. Test Document Upload
```bash
# Uses RAG_CHUNK_SIZE and RAG_CHUNK_OVERLAP
curl -X POST http://localhost:8001/api/documents \
  -F "file=@test.md" \
  -F "scope=test"
```

### 3. Test Semantic Search
```bash
# Uses RAG_MIN_SCORE and RAG_DEFAULT_K
curl -X POST http://localhost:8001/api/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "kubernetes", "scope": "test"}'
```

### 4. Check RAG in Agent Responses

Look for these log entries:
```
rag_context_applied: documents_used=X, token_estimate=Y
retrieval_complete: results_count=X, top_score=Y
```

If `results_count=0` and you expected matches → **Increase RAG_MIN_SCORE**  
If too many weak matches → **Decrease RAG_MIN_SCORE**

## Performance Tuning

### Fast Responses (Latency-Optimized)
```bash
RAG_MIN_SCORE=0.6
RAG_DEFAULT_K=3
RAG_MAX_CONTEXT_TOKENS=2000
RAG_CHUNK_SIZE=800
```

### Quality Responses (Accuracy-Optimized)
```bash
RAG_MIN_SCORE=0.7
RAG_DEFAULT_K=10
RAG_MAX_CONTEXT_TOKENS=6000
RAG_CHUNK_SIZE=1500
```

### Balanced (Recommended)
```bash
RAG_MIN_SCORE=0.5
RAG_DEFAULT_K=5
RAG_MAX_CONTEXT_TOKENS=4000
RAG_CHUNK_SIZE=1000
```

## Monitoring

Watch backend logs for:
- `rag_context_applied`: RAG successfully provided context
- `no_documents_found`: Query didn't match any documents (may need to lower MIN_SCORE)
- `rag_retrieval_failed`: Error in RAG pipeline (check PostgreSQL, Ollama)

## Hot Reload

**Changes take effect**: On next request (no restart needed with `--reload`)  
**Cached values**: Settings are cached with `@lru_cache` - restart server to pick up changes

**Quick Restart**:
```bash
make dev-backend  # Restarts with new settings
```

---

**Configuration follows industry best practices**:
- Environment variables for all tunable parameters
- Sensible defaults for production use
- Clear documentation of trade-offs
- Easy to tune for different use cases
