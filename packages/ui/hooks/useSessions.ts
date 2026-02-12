'use client';

import { useState, useCallback, useEffect } from 'react';
import { API_URL, getApiHeaders } from '@/lib/config';
import { subscribeToSessionEvents } from '@/lib/session-events';

export interface Session {
  session_id: string;
  title: string | null;
  session_state: 'active' | 'pinned' | 'archived';
  message_count: number;
  modified_on: string;
  created_on: string;
}

interface UseSessionsOptions {
  blueprint: string;
  includeArchived?: boolean;
}

interface UseSessionsReturn {
  sessions: Session[];
  isLoading: boolean;
  error: Error | null;
  activeSessionId: string | null;
  setActiveSession: (id: string | null) => void;
  createSession: () => Promise<string>;
  pinSession: (id: string) => Promise<void>;
  unpinSession: (id: string) => Promise<void>;
  archiveSession: (id: string) => Promise<void>;
  refresh: () => Promise<void>;
}

export function useSessions({
  blueprint,
  includeArchived = false,
}: UseSessionsOptions): UseSessionsReturn {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        include_archived: String(includeArchived),
      });

      const response = await fetch(
        `${API_URL}/api/blueprints/${blueprint}/sessions?${params}`,
        { headers: getApiHeaders() }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.statusText}`);
      }

      const data = await response.json();
      setSessions(data.sessions);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [blueprint, includeArchived]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Subscribe to session events for cross-component updates
  useEffect(() => {
    const unsubscribe = subscribeToSessionEvents((event) => {
      if (
        event.type === 'session-created' ||
        event.type === 'session-updated' ||
        event.type === 'session-refresh'
      ) {
        fetchSessions();
      }
    });
    return unsubscribe;
  }, [fetchSessions]);

  const createSession = useCallback(async (): Promise<string> => {
    const response = await fetch(
      `${API_URL}/api/blueprints/${blueprint}/sessions`,
      {
        method: 'POST',
        headers: getApiHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to create session');
    }

    const data = await response.json();
    await fetchSessions();
    return data.session_id;
  }, [blueprint, fetchSessions]);

  const updateSessionState = useCallback(
    async (sessionId: string, state: string) => {
      const response = await fetch(
        `${API_URL}/api/blueprints/${blueprint}/sessions/${sessionId}/state`,
        {
          method: 'PATCH',
          headers: getApiHeaders(true),
          body: JSON.stringify({ state }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update session state: ${response.statusText}`);
      }

      await fetchSessions();
    },
    [blueprint, fetchSessions]
  );

  const pinSession = useCallback(
    (id: string) => updateSessionState(id, 'pinned'),
    [updateSessionState]
  );

  const unpinSession = useCallback(
    (id: string) => updateSessionState(id, 'active'),
    [updateSessionState]
  );

  const archiveSession = useCallback(
    (id: string) => updateSessionState(id, 'archived'),
    [updateSessionState]
  );

  return {
    sessions,
    isLoading,
    error,
    activeSessionId,
    setActiveSession: setActiveSessionId,
    createSession,
    pinSession,
    unpinSession,
    archiveSession,
    refresh: fetchSessions,
  };
}
