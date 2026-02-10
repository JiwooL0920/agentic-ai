"""
Schema versioning for chat sessions and messages.

Best practice: Add schema_version to all documents and handle evolution at read time.
This allows zero-downtime schema changes.
"""

# Current schema versions
SESSION_SCHEMA_VERSION = 1
MESSAGE_SCHEMA_VERSION = 1


class SchemaEvolution:
    """Handle schema version migrations on read."""
    
    @staticmethod
    def migrate_session(session: dict) -> dict:
        """
        Migrate session document to current schema version.
        
        This is called on READ, not WRITE. Old documents are upgraded lazily.
        """
        version = session.get('schema_version', 1)
        
        # Apply migrations sequentially
        if version < 2:
            session = SchemaEvolution._migrate_session_v1_to_v2(session)
            version = 2
        
        # Future migrations would go here:
        # if version < 3:
        #     session = SchemaEvolution._migrate_session_v2_to_v3(session)
        #     version = 3
        
        session['schema_version'] = SESSION_SCHEMA_VERSION
        return session
    
    @staticmethod
    def _migrate_session_v1_to_v2(session: dict) -> dict:
        """
        Example migration: v1 → v2
        
        Changes:
        - Renamed 'state' to 'session_state'
        - Added 'blueprint' field
        """
        # Rename field
        if 'state' in session:
            session['session_state'] = session.pop('state')
        
        # Add missing field with default
        if 'blueprint' not in session:
            session['blueprint'] = 'devassist'
        
        return session
    
    @staticmethod
    def migrate_message(message: dict) -> dict:
        """
        Migrate message document to current schema version.
        """
        version = message.get('schema_version', 1)
        
        # Apply migrations sequentially
        # (no migrations yet, but structure is here)
        
        message['schema_version'] = MESSAGE_SCHEMA_VERSION
        return message
