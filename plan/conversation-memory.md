# Conversation Memory Feature

**Status:** Planned  
**Created:** 2025-02-12  
**Estimated Effort:** 6-7 hours

## Overview

Enable persistent conversation history with a collapsible sidebar showing previous sessions, organized by user (browser fingerprint until auth is implemented).

## Current State Assessment

### Backend (Already Well-Structured)

| Component | Status | Location |
|-----------|--------|----------|
| Session Storage | EXISTS | `SessionRepository` → ScyllaDB table `{blueprint}-sessions` |
| Message Storage | EXISTS | `MessageRepository` → ScyllaDB table `{blueprint}-history` |
| User Sessions API | EXISTS | `GET /api/blueprints/{blueprint}/sessions` |
| Session Detail API | EXISTS | `GET /api/blueprints/{blueprint}/sessions/{session_id}` |
| Session State (pin/archive) | EXISTS | `PATCH .../sessions/{session_id}/state` |
| Redis Caching | EXISTS | `SessionCache` with 5-min TTL for sidebar |
| User ID Handling | HARDCODED | Currently `user_id: str = "user"` (TODO: auth) |

### Frontend (Needs Work)

| Component | Status | Notes |
|-----------|--------|-------|
| Chat UI | EXISTS | `useChat` hook manages in-memory messages |
| Session Persistence | MISSING | `useChat` doesn't persist across page loads |
| Sidebar | MISSING | No session list component |
| Session Resume | MISSING | No API calls to load previous sessions |
| Layout | SIMPLE | Full-width single column, no sidebar slot |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| User Identity | Browser fingerprint UUID | Stored in localStorage until proper auth |
| Sidebar Behavior | Collapsible | Toggle with button/keyboard, saves space on mobile |
| Session Deletion | Soft delete (archive) | Move to archived state, can be restored |

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   SessionSidebar                    ChatPage                     │
│   ┌──────────────┐                  ┌────────────────────────┐  │
│   │ useSessions  │───selectSession──│ useChat(sessionId)     │  │
│   │              │                  │                        │  │
│   │ sessions[]   │                  │ loadSession() → hydrate│  │
│   │ activeId     │                  │ messages[]             │  │
│   └──────────────┘                  └────────────────────────┘  │
│          │                                     │                 │
│          │ GET /sessions                       │ GET /sessions/  │
│          │                                     │    {id}         │
│          ▼                                     ▼                 │
├─────────────────────────────────────────────────────────────────┤
│                        BACKEND                                   │
├─────────────────────────────────────────────────────────────────┤
│   SessionService                    MessageRepository            │
│   ┌────────────────┐                ┌────────────────────────┐  │
│   │ get_user_      │                │ get_session_messages() │  │
│   │   sessions()   │                │                        │  │
│   │                │                │ save_message()         │  │
│   └────────────────┘                └────────────────────────┘  │
│          │                                     │                 │
│          ▼                                     ▼                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                   ScyllaDB (DynamoDB API)                │   │
│   │   {blueprint}-sessions          {blueprint}-history      │   │
│   │   PK: session_id                PK: session_id           │   │
│   │                                 SK: timestamp            │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Frontend Layout Restructure

**Files to Create/Modify:**

| File | Action | Purpose |
|------|--------|---------|
| `packages/ui/app/[blueprint]/layout.tsx` | CREATE | Blueprint-level layout with sidebar slot |
| `packages/ui/components/session-sidebar.tsx` | CREATE | Collapsible sidebar container |
| `packages/ui/components/session-list.tsx` | CREATE | Session items with virtualized scroll |
| `packages/ui/components/session-item.tsx` | CREATE | Individual session row |
| `packages/ui/hooks/useSessions.ts` | CREATE | Session list data fetching |
| `packages/ui/lib/user-id.ts` | CREATE | Browser fingerprint UUID generator |
| `packages/ui/hooks/useChat.ts` | MODIFY | Add session hydration support |
| `packages/ui/app/[blueprint]/page.tsx` | MODIFY | Remove redundant layout, accept sessionId |

### Phase 2: Session Management

**New `useSessions` Hook Interface:**

```typescript
interface Session {
  session_id: string;
  title: string | null;
  session_state: 'active' | 'pinned' | 'archived';
  message_count: number;
  modified_on: string;
  created_on: string;
}

interface UseSessionsReturn {
  sessions: Session[];
  isLoading: boolean;
  error: Error | null;
  activeSessionId: string | null;
  setActiveSession: (id: string | null) => void;
  createSession: () => Promise<string>;
  pinSession: (id: string) => Promise<void>;
  archiveSession: (id: string) => Promise<void>;
  refresh: () => Promise<void>;
}
```

**Modify `useChat` Hook:**

- Add `initialSessionId?: string` prop
- On mount with `initialSessionId`: fetch `GET /sessions/{id}` → hydrate messages
- New return value: `isHydrated: boolean` (prevent flash of empty state)

### Phase 3: Backend Enhancements

**Archive Endpoint (Already Exists):**

```
PATCH /api/blueprints/{blueprint}/sessions/{session_id}/state
Body: {"state": "archived"}
```

**Add user_id header extraction (preparation for auth):**

```python
# packages/core/src/api/dependencies/auth.py
def get_current_user(x_user_id: str = Header(default="anonymous")) -> str:
    """Extract user ID from header. Placeholder for auth."""
    return x_user_id
```

### Phase 4: Component Hierarchy

```
app/[blueprint]/layout.tsx
├── SessionSidebar (collapsible, 280px)
│   ├── Header (New Chat button, collapse toggle)
│   ├── SessionList (scroll-area)
│   │   └── SessionItem[] (map sessions)
│   │       ├── Title (truncated)
│   │       ├── Preview (first message, 1 line)
│   │       ├── Timestamp (relative: "2h ago")
│   │       └── DropdownMenu (Pin, Archive)
│   └── Footer (archived sessions link)
└── children (ChatPage)
    └── page.tsx (existing, minimal changes)
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + B` | Toggle sidebar |
| `Cmd/Ctrl + N` | New chat |
| `Up/Down` in sidebar | Navigate sessions |
| `Enter` in sidebar | Open selected session |

## URL Structure

```
/devassist                    → New chat (no sessionId)
/devassist?session=abc123     → Resume session abc123
```

Using query param instead of path to avoid routing complexity.

## Implementation Order

| Step | Task | Time |
|------|------|------|
| 1 | `lib/user-id.ts` - Browser fingerprint | 5 min |
| 2 | `useSessions.ts` hook - Session list fetching | 45 min |
| 3 | `session-item.tsx` - Single session component | 30 min |
| 4 | `session-list.tsx` - List with scroll area | 30 min |
| 5 | `session-sidebar.tsx` - Container with collapse | 45 min |
| 6 | `layout.tsx` - Blueprint layout with sidebar | 30 min |
| 7 | Modify `useChat.ts` - Session hydration | 1 hour |
| 8 | Modify `page.tsx` - URL query handling | 30 min |
| 9 | Testing & polish | 1 hour |
| **Total** | | **~6-7 hours** |

## Dependencies

**shadcn/ui components to add:**

```bash
# Already have: button, dropdown-menu, scroll-area, tooltip
# May need:
npx shadcn@latest add sheet        # For mobile overlay
npx shadcn@latest add skeleton     # Loading states
```

## API Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/blueprints/{blueprint}/sessions` | List user sessions |
| GET | `/api/blueprints/{blueprint}/sessions/{id}` | Get session with messages |
| POST | `/api/blueprints/{blueprint}/sessions` | Create new session |
| PATCH | `/api/blueprints/{blueprint}/sessions/{id}/state` | Pin/archive session |
| PATCH | `/api/blueprints/{blueprint}/sessions/{id}/title` | Update session title |

## Future Enhancements

- [ ] Session search (full-text on titles/messages)
- [ ] GSI on `user_id` for O(1) session lookup (production scale)
- [ ] Proper authentication integration
- [ ] Cross-device session sync
- [ ] Session sharing/export
