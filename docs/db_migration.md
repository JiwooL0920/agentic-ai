# Database Schema Migration

This project uses **application-level schema versioning** for NoSQL schema evolution—a proven pattern used by Netflix, Stripe, Discord, and recommended by ScyllaDB.

## Why Application-Level Versioning?

| Kubernetes Jobs Approach | Schema Versioning (Our Approach) |
|--------------------------|----------------------------------|
| Extra infrastructure     | No extra infrastructure          |
| Must run before app      | Part of the app itself           |
| Separate deployment      | Single deployment                |
| Can fail/timeout         | No runtime failures              |
| Complex orchestration    | Simple code                      |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              SchemaEvolution                         │   │
│  │  - migrate_session() → lazy upgrade on READ          │   │
│  │  - migrate_message() → lazy upgrade on READ          │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│  ┌────────────────────────────────────────────────────┐    │
│  │  SessionRepository / MessageRepository              │    │
│  │  - get_* calls SchemaEvolution.migrate_*()          │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ↓
               ┌───────────────────────┐
               │      ScyllaDB         │
               │  (Alternator API)     │
               └───────────────────────┘
```

## How It Works

Every document stores a `schema_version` field:

```python
{
    "session_id": "abc-123",
    "schema_version": 1,  # Track version
    "user_id": "user-456",
    "title": "My Chat",
    ...
}
```

On **READ**, old documents are upgraded lazily:

```python
def migrate_session(session: dict) -> dict:
    version = session.get('schema_version', 1)
    
    if version < 2:
        session = _migrate_v1_to_v2(session)
    if version < 3:
        session = _migrate_v2_to_v3(session)
    
    session['schema_version'] = CURRENT_VERSION
    return session
```

## Key Files

| File | Purpose |
|------|---------|
| `packages/core/src/repositories/schema_evolution.py` | Schema versioning & lazy migrations |
| `packages/core/src/repositories/session_repository.py` | Session CRUD + schema migration on read |
| `packages/core/src/repositories/message_repository.py` | Message CRUD + schema migration on read |
| `scripts/create_scylla_tables.py` | One-time table creation (dev/initial setup) |

## Adding Schema Changes

When you need to evolve the schema:

### 1. Bump the version constant

```python
# In schema_evolution.py
SESSION_SCHEMA_VERSION = 2  # Was 1
```

### 2. Add the migration function

```python
@staticmethod
def _migrate_session_v1_to_v2(session: dict) -> dict:
    """
    v1 → v2 changes:
    - Renamed 'state' to 'session_state'
    - Added 'blueprint' field with default
    """
    if 'state' in session:
        session['session_state'] = session.pop('state')
    
    if 'blueprint' not in session:
        session['blueprint'] = 'devassist'
    
    return session
```

### 3. Chain it in the migrate function

```python
@staticmethod
def migrate_session(session: dict) -> dict:
    version = session.get('schema_version', 1)
    
    if version < 2:
        session = SchemaEvolution._migrate_session_v1_to_v2(session)
        version = 2
    
    # Future migrations chain here
    # if version < 3:
    #     session = SchemaEvolution._migrate_session_v2_to_v3(session)
    #     version = 3
    
    session['schema_version'] = SESSION_SCHEMA_VERSION
    return session
```

### 4. Deploy

Old documents upgrade automatically on next read. No migration scripts to run, no deployment order concerns.

## Best Practices

1. **Never remove fields immediately** - deprecate first, remove in a later version
2. **Always provide defaults** for new required fields
3. **Keep migrations idempotent** - safe to run multiple times
4. **Test migrations** with sample documents from each version
5. **Document changes** in the migration function docstring

## References

- [Discord's ScyllaDB Usage](https://discord.com/blog/how-discord-stores-trillions-of-messages) - Application-level schema versioning
- [Netflix Data Evolution](https://netflixtechblog.com/) - Schema versioning patterns
- [AWS DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-general.html) - Document versioning
- [ScyllaDB Schema Evolution](https://www.scylladb.com/2022/01/19/handling-schema-changes-in-nosql/) - Official guidance
