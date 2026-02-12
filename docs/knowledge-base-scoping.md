# Knowledge Base Scoping

This document covers the Knowledge Base Scoping feature, which allows users to configure which knowledge sources are active for each chat session.

---

## Table of Contents

- [User Guide](#user-guide)
  - [Overview](#overview)
  - [Getting Started](#getting-started)
  - [Configuration Options](#configuration-options)
  - [Visual Indicators](#visual-indicators)
- [Developer Documentation](#developer-documentation)
  - [Architecture Overview](#architecture-overview)
  - [Frontend Components](#frontend-components)
  - [Backend API](#backend-api)
  - [Data Models](#data-models)
  - [Event System](#event-system)
  - [Testing](#testing)

---

# User Guide

## Overview

Knowledge Base Scoping lets you control which knowledge sources the AI assistant uses when answering your questions. By default, sessions use:

- **Agent Knowledge** - Built-in knowledge scopes defined by the agent
- **My Documents** - Documents you've personally uploaded

You can toggle these on/off and add additional scopes as needed.

## Getting Started

### Step 1: Start a Conversation

The Knowledge Sources configuration is **session-specific**. You must first send a message to create a session.

1. Navigate to a blueprint (e.g., `http://localhost:3000/devassist`)
2. Send any message in the chat input
3. Once the session is created, the Knowledge Sources button becomes enabled

### Step 2: Open Knowledge Sources Panel

Look for the **BookOpen icon** (📖) in the header area. When a session exists:

- The button shows a **badge** with the count of active sources
- Click the button to open the configuration dialog

### Step 3: Configure Your Sources

The dialog presents three sections:

| Section | Description |
|---------|-------------|
| **Agent Knowledge** | Toggle ON/OFF to include/exclude agent-defined knowledge scopes |
| **My Documents** | Toggle ON/OFF to include/exclude your uploaded documents |
| **Additional Scopes** | Checkboxes to select specific knowledge scopes (if available) |

Changes are saved **automatically** when you toggle any option.

## Configuration Options

### Agent Knowledge (Default: ON)

When enabled, the AI uses knowledge scopes that the blueprint's agents are configured to access. This typically includes:

- Technical documentation
- Best practices
- Domain-specific knowledge

### My Documents (Default: ON)

When enabled, the AI includes documents you've uploaded to your personal document space. This allows personalized context based on your own files.

### Additional Scopes

If your organization has configured shared knowledge scopes, they appear as checkboxes. Each scope shows:

- **Scope name** - Identifier for the knowledge collection
- **Document count** - Number of documents in that scope

## Visual Indicators

### Header Badge

The Knowledge Sources button displays a badge showing the count of active sources:

```
[📖 2]  →  2 sources active (Agent KB + My Docs)
[📖 3]  →  3 sources active (Agent KB + My Docs + 1 custom scope)
```

### Indicator Bar

Below the header, a thin indicator bar shows which sources are active:

```
📖 Sources: [🤖 Agent KB] [👤 My Docs] [📁 kubernetes-docs]
```

If no sources are active:

```
📖 No knowledge sources active
```

---

# Developer Documentation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [KnowledgeConfigPanel]  ←→  [KnowledgeScopeIndicator]          │
│         │                              │                         │
│         │ (Dialog with toggles)        │ (Badge bar display)    │
│         │                              │                         │
│         └──────────┬───────────────────┘                        │
│                    │                                             │
│                    │  CustomEvent: 'knowledge-config-updated'   │
│                    │                                             │
│         ┌──────────▼───────────┐                                │
│         │   sessions.ts API    │                                │
│         └──────────┬───────────┘                                │
│                    │                                             │
└────────────────────┼────────────────────────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────────────────────────┐
│                         Backend                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [sessions.py routes]                                            │
│         │                                                        │
│         │  GET  /api/blueprints/{bp}/sessions/{id}              │
│         │  PATCH /api/blueprints/{bp}/sessions/{id}/knowledge   │
│         │                                                        │
│         ▼                                                        │
│  [SessionService]                                                │
│         │                                                        │
│         ▼                                                        │
│  [SessionRepository] → DynamoDB/ScyllaDB                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Frontend Components

### KnowledgeConfigPanel

**Location:** `packages/ui/components/knowledge-config-panel.tsx`

The main dialog component for configuring knowledge sources.

```typescript
interface KnowledgeConfigPanelProps {
  blueprint: string;      // Current blueprint name
  sessionId: string | null; // Current session ID (null = no session yet)
}
```

**Key Features:**

- Shows disabled state with tooltip when no session exists
- Fetches current config and available scopes on dialog open
- Auto-saves changes immediately on toggle
- Emits `knowledge-config-updated` event after successful save
- Displays loading states during fetch/save operations

**Usage:**

```tsx
import { KnowledgeConfigPanel } from '@/components/knowledge-config-panel';

<KnowledgeConfigPanel 
  blueprint={blueprint} 
  sessionId={sessionId} 
/>
```

### KnowledgeScopeIndicator

**Location:** `packages/ui/components/knowledge-scope-indicator.tsx`

A thin indicator bar showing active knowledge sources.

```typescript
interface KnowledgeScopeIndicatorProps {
  blueprint: string;
  sessionId: string | null;
}
```

**Key Features:**

- Renders nothing when no session exists
- Shows "No knowledge sources active" when all sources disabled
- Displays badges for each active source type
- Listens for `knowledge-config-updated` event to refresh

**Usage:**

```tsx
import { KnowledgeScopeIndicator } from '@/components/knowledge-scope-indicator';

<KnowledgeScopeIndicator 
  blueprint={blueprint} 
  sessionId={sessionId} 
/>
```

### API Client

**Location:** `packages/ui/lib/api/sessions.ts`

```typescript
// Types
interface KnowledgeConfig {
  active_scopes: string[];       // List of explicitly selected scope IDs
  include_agent_scopes: boolean; // Whether to include agent-defined scopes
  include_user_docs: boolean;    // Whether to include user's documents
}

// Functions
async function getSession(blueprint: string, sessionId: string): Promise<SessionDetailResponse>
async function updateKnowledgeConfig(blueprint: string, sessionId: string, config: KnowledgeConfig): Promise<UpdateKnowledgeConfigResponse>
```

## Backend API

### Get Session Details

```http
GET /api/blueprints/{blueprint}/sessions/{session_id}
```

**Response:**

```json
{
  "session_id": "uuid",
  "blueprint": "devassist",
  "user_id": "user123",
  "created_at": "2024-01-15T10:30:00Z",
  "last_activity_at": "2024-01-15T11:45:00Z",
  "messages": [...],
  "knowledge_config": {
    "active_scopes": [],
    "include_agent_scopes": true,
    "include_user_docs": true
  }
}
```

### Update Knowledge Config

```http
PATCH /api/blueprints/{blueprint}/sessions/{session_id}/knowledge
Content-Type: application/json

{
  "knowledge_config": {
    "active_scopes": ["kubernetes-docs", "terraform-modules"],
    "include_agent_scopes": true,
    "include_user_docs": false
  }
}
```

**Response:**

```json
{
  "status": "updated",
  "knowledge_config": {
    "active_scopes": ["kubernetes-docs", "terraform-modules"],
    "include_agent_scopes": true,
    "include_user_docs": false
  }
}
```

### List Available Scopes

```http
GET /api/rag/scopes
```

**Response:**

```json
{
  "scopes": ["kubernetes-docs", "terraform-modules", "user:abc123"],
  "counts": {
    "kubernetes-docs": 150,
    "terraform-modules": 75,
    "user:abc123": 12
  }
}
```

## Data Models

### Backend (Python/Pydantic)

**Location:** `packages/core/src/schemas/sessions.py`

```python
class KnowledgeConfig(BaseModel):
    active_scopes: list[str] = Field(default_factory=list)
    include_agent_scopes: bool = True
    include_user_docs: bool = True

class UpdateKnowledgeConfigRequest(BaseModel):
    knowledge_config: KnowledgeConfig

class SessionDetailResponse(BaseModel):
    session_id: str
    blueprint: str
    user_id: str
    created_at: datetime
    last_activity_at: datetime
    messages: list[MessageResponse]
    knowledge_config: KnowledgeConfig
```

### Frontend (TypeScript)

**Location:** `packages/ui/lib/api/sessions.ts`

```typescript
export interface KnowledgeConfig {
  active_scopes: string[];
  include_agent_scopes: boolean;
  include_user_docs: boolean;
}

export interface SessionDetailResponse {
  session_id: string;
  blueprint: string;
  user_id: string;
  created_at: string;
  last_activity_at: string;
  messages: Array<{...}>;
  knowledge_config: KnowledgeConfig;
}
```

## Event System

Components communicate via browser CustomEvents:

### knowledge-config-updated

Fired when knowledge configuration is successfully saved.

**Emitter:** `KnowledgeConfigPanel` (after successful API call)

```typescript
window.dispatchEvent(new CustomEvent('knowledge-config-updated'));
```

**Listener:** `KnowledgeScopeIndicator`

```typescript
useEffect(() => {
  const handleConfigUpdate = () => {
    fetchConfig(); // Refresh display
  };

  window.addEventListener('knowledge-config-updated', handleConfigUpdate);
  return () => {
    window.removeEventListener('knowledge-config-updated', handleConfigUpdate);
  };
}, [fetchConfig]);
```

## Testing

### E2E Tests

**Location:** `packages/ui/tests/e2e/knowledge-config.spec.ts`

**Test Coverage:**

| Test | Description |
|------|-------------|
| Button disabled without session | Verifies button is disabled when no session exists |
| Tooltip shown on hover | Shows help text for disabled button |
| Button enabled with session | Button becomes active after session creation |
| Badge shows active count | Displays correct count of active sources |
| Dialog opens on click | Configuration dialog appears |
| Agent Knowledge toggle | Can toggle agent scopes on/off |
| My Documents toggle | Can toggle user docs on/off |
| Indicator bar display | Shows active sources below header |
| Indicator updates on toggle | Real-time update when config changes |
| Badge count updates | Count reflects configuration changes |
| Session persists config | Config preserved across page refresh |
| Multiple sessions isolated | Each session has independent config |

**Run Tests:**

```bash
cd packages/ui

# With dev server running
SKIP_WEB_SERVER=1 npx playwright test tests/e2e/knowledge-config.spec.ts

# Start server and run tests
npx playwright test tests/e2e/knowledge-config.spec.ts
```

### Unit Test Considerations

For unit testing components:

```typescript
// Mock the API calls
jest.mock('@/lib/api/sessions', () => ({
  getSession: jest.fn(),
  updateKnowledgeConfig: jest.fn(),
}));

// Mock the RAG scopes API
jest.mock('@/lib/api/rag', () => ({
  listScopes: jest.fn().mockResolvedValue({
    scopes: ['scope1', 'scope2'],
    counts: { scope1: 10, scope2: 20 },
  }),
}));
```

---

## Troubleshooting

### Button stays disabled after sending message

**Cause:** Session might not be created properly, or `sessionId` prop isn't updating.

**Solution:** Check browser console for API errors. Verify the session creation endpoint returns a valid session ID.

### Changes not persisting

**Cause:** API call might be failing silently.

**Solution:** Open browser DevTools Network tab, check PATCH request response. Verify backend is running and accessible.

### Indicator not updating

**Cause:** Event listener might not be registered.

**Solution:** Verify `KnowledgeScopeIndicator` is mounted and the `knowledge-config-updated` event is being dispatched.

---

## Future Enhancements

- [ ] Scope search/filter for large scope lists
- [ ] Scope descriptions and metadata display
- [ ] Bulk enable/disable all scopes
- [ ] Scope usage analytics
- [ ] Default configuration at blueprint level
