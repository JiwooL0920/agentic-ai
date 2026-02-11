# RAG Frontend User Guide

This guide explains how users can interact with the RAG (Retrieval-Augmented Generation) system through the UI.

## Features

### 1. **Document Management** (`/[blueprint]/knowledge`)

Upload and manage documents that will be used to augment AI responses with relevant context.

#### Upload Documents

- **Drag & Drop**: Simply drag files into the upload area
- **File Browser**: Click "browse" to select files from your computer
- **Supported Formats**:
  - Text: `.txt`, `.md`
  - Code: `.py`, `.js`, `.ts`, `.tsx`, `.jsx`
  - Config: `.json`, `.yaml`, `.yml`

#### Document Processing

When you upload a document:
1. The file is chunked based on its type (code-aware chunking for `.py`/`.js`, markdown-aware for `.md`)
2. Each chunk is converted to a vector embedding using `nomic-embed-text`
3. Embeddings are stored in PostgreSQL with pgvector for fast similarity search
4. Documents are organized by **scope** for better organization

#### Scope Management

Scopes organize documents into logical groups (e.g., "kubernetes", "python", "terraform"):

- **View Scopes**: See all scopes with document counts
- **Switch Scopes**: Click tabs to view different scopes
- **Upload to Scope**: Documents are uploaded to the currently selected scope
- **Delete Scope**: Remove all documents in a scope (cannot be undone)

#### Semantic Search

Test your knowledge base with natural language queries:

1. Enter a question (e.g., "How do I configure Kubernetes deployments?")
2. View top matching document chunks with relevance scores
3. See source filenames and preview content

### 2. **Enhanced Chat Interface** (`/[blueprint]`)

Chat interface now shows when RAG context is being used.

#### Knowledge Base Button

- **Location**: Top right of chat header (database icon)
- **Function**: Quick access to document management
- **Tooltip**: "Manage Knowledge Base"

#### RAG Indicators in Messages

When an agent uses RAG context, you'll see:

1. **Sources Badge**: Shows number of documents used (e.g., "3 sources")
   - Appears next to the agent name badge
   - Blue color indicates RAG augmentation
   - Hover for tooltip: "Response augmented with knowledge base context"

2. **Source Citations**: Listed below the message
   - Shows up to 3 source filenames
   - Displays relevance match percentage
   - If more than 3 sources, shows "+X more sources"

#### Example Message with RAG

```
┌─────────────────────────────────────────┐
│ AI Assistant                            │
│ [kubernetes]  [📚 3 sources]            │
│                                         │
│ To configure a Kubernetes deployment,   │
│ you need to create a YAML file with...  │
│                                         │
│ ────────────────────────────────────    │
│ Sources:                                │
│ 🔗 k8s-deployment.yaml (85% match)      │
│ 🔗 kubernetes-guide.md (78% match)      │
│ 🔗 best-practices.md (72% match)        │
└─────────────────────────────────────────┘
```

## How RAG Works

### Automatic Context Retrieval

When you chat with an agent that has a `knowledge_scope` configured:

1. **You send a message**: "How do I deploy with Helm?"
2. **RAG retrieval happens**:
   - Your message is converted to an embedding
   - Similar document chunks are found using vector similarity search
   - Top 5 most relevant chunks are retrieved
3. **Context augmentation**:
   - Retrieved context is added to the agent's prompt
   - Agent generates response using both its knowledge AND your documents
4. **Response with citations**:
   - Agent's response is shown with source badges
   - You can see which documents influenced the response

### When RAG is Used

RAG is **automatically enabled** when:
- ✅ Agent has `knowledge_scope` configured in YAML (e.g., `knowledge_scope: ["kubernetes", "helm"]`)
- ✅ Documents exist in those scopes
- ✅ `RAG_ENABLED = True` in backend (default)

RAG is **NOT used** when:
- ❌ Agent has no `knowledge_scope` configured
- ❌ No documents uploaded to the specified scopes
- ❌ RAG retrieval fails (graceful fallback to regular response)

## Best Practices

### Organizing Documents

1. **Use Meaningful Scopes**
   - Group related documents (e.g., "kubernetes", "python", "api-docs")
   - Match scope names to agent `knowledge_scope` in YAML configs

2. **Upload Quality Content**
   - Well-structured documentation works best
   - Code files with comments are more useful than raw code
   - Markdown with headers helps chunking

3. **Keep Documents Updated**
   - Delete outdated documents
   - Re-upload updated versions (old chunks remain until deleted)

### Configuring Agents for RAG

Edit agent YAML files in `blueprints/{blueprint}/agents/`:

```yaml
name: Kubernetes Expert
agent_id: kubernetes
description: Expert in Kubernetes deployments
model: qwen2.5:32b
knowledge_scope:  # ← Add this!
  - kubernetes
  - helm
  - devops
system_prompt: |
  You are a Kubernetes expert. Use the provided documentation
  to give accurate, up-to-date answers.
```

## Troubleshooting

### "No sources" shown in chat

**Possible causes:**
- Agent doesn't have `knowledge_scope` configured
- No documents uploaded to the specified scopes
- Query doesn't match any documents (similarity score too low)

**Solutions:**
1. Check agent YAML has `knowledge_scope` field
2. Upload documents to the correct scope
3. Try more specific queries

### Upload fails

**Common issues:**
- Unsupported file type → Check supported extensions
- File is empty → Verify file has content
- File not UTF-8 encoded → Convert to UTF-8

### Search returns no results

**Possible causes:**
- No documents in selected scope
- Query too vague or unrelated to uploaded content

**Solutions:**
- Verify documents are uploaded (check scope counts)
- Try more specific search terms
- Use keywords from your uploaded documents

## Technical Details

### Embedding Model
- **Model**: `nomic-embed-text` via Ollama
- **Dimensions**: 768-dimensional vectors
- **Local**: All embeddings happen locally (no external API calls)

### Vector Store
- **Database**: PostgreSQL with pgvector extension
- **Index**: HNSW for fast approximate nearest neighbor search
- **Distance**: Cosine similarity

### Chunking Strategy
- **Code files** (`.py`, `.js`, `.ts`): Function/class-aware chunking
- **Markdown** (`.md`): Header-aware chunking
- **Text files** (`.txt`): Semantic sentence-based chunking
- **Default**: 1000 chars with 200 char overlap

### Context Limits
- **Max context tokens**: 4000 tokens (~16,000 characters)
- **Default retrieval**: Top 5 documents
- **Min relevance score**: 0.3 (30% similarity)

## API Endpoints

For programmatic access, the RAG system exposes REST APIs:

```bash
# Upload document
POST /api/documents
Content-Type: multipart/form-data

# List documents
GET /api/documents?scope=kubernetes

# Search documents
POST /api/documents/search
{"query": "How to deploy?", "scope": "kubernetes", "k": 5}

# Delete document
DELETE /api/documents/{doc_id}

# Delete scope
DELETE /api/documents/scope/{scope}
```

See `/docs` (FastAPI Swagger UI) for full API documentation.

## Next Steps

1. **Upload your first document**: Go to Knowledge Base page
2. **Configure agent scopes**: Edit agent YAML files
3. **Test retrieval**: Use semantic search to verify documents are indexed
4. **Chat with context**: Ask questions and see RAG in action!

---

For issues or questions, check the backend logs for RAG-related events:
- `rag_context_applied`: RAG context successfully retrieved
- `rag_retrieval_failed`: RAG retrieval error (falls back to regular response)
- `document_indexed`: Document successfully uploaded and chunked
