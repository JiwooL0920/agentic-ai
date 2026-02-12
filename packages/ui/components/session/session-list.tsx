'use client';

import { useMemo } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SessionItem } from './session-item';
import type { Session } from '@/hooks/useSessions';

interface SessionListProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onPinSession: (sessionId: string) => void;
  onUnpinSession: (sessionId: string) => void;
  onArchiveSession: (sessionId: string) => void;
}

interface GroupedSessions {
  pinned: Session[];
  today: Session[];
  yesterday: Session[];
  thisWeek: Session[];
  older: Session[];
}

function groupSessionsByDate(sessions: Session[]): GroupedSessions {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const groups: GroupedSessions = {
    pinned: [],
    today: [],
    yesterday: [],
    thisWeek: [],
    older: [],
  };

  for (const session of sessions) {
    if (session.session_state === 'pinned') {
      groups.pinned.push(session);
      continue;
    }

    const modified = new Date(session.modified_on);

    if (modified >= today) {
      groups.today.push(session);
    } else if (modified >= yesterday) {
      groups.yesterday.push(session);
    } else if (modified >= weekAgo) {
      groups.thisWeek.push(session);
    } else {
      groups.older.push(session);
    }
  }

  return groups;
}

interface SessionGroupProps {
  title: string;
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onPinSession: (sessionId: string) => void;
  onUnpinSession: (sessionId: string) => void;
  onArchiveSession: (sessionId: string) => void;
}

function SessionGroup({
  title,
  sessions,
  activeSessionId,
  onSelectSession,
  onPinSession,
  onUnpinSession,
  onArchiveSession,
}: SessionGroupProps) {
  if (sessions.length === 0) return null;

  return (
    <div className="mb-4">
      <h3 className="px-3 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
        {title}
      </h3>
      <div className="space-y-0.5">
        {sessions.map((session) => (
          <SessionItem
            key={session.session_id}
            session={session}
            isActive={activeSessionId === session.session_id}
            onClick={() => onSelectSession(session.session_id)}
            onPin={() => onPinSession(session.session_id)}
            onUnpin={() => onUnpinSession(session.session_id)}
            onArchive={() => onArchiveSession(session.session_id)}
          />
        ))}
      </div>
    </div>
  );
}

export function SessionList({
  sessions,
  activeSessionId,
  onSelectSession,
  onPinSession,
  onUnpinSession,
  onArchiveSession,
}: SessionListProps) {
  const grouped = useMemo(() => groupSessionsByDate(sessions), [sessions]);

  if (sessions.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <p className="text-sm text-muted-foreground text-center">
          No conversations yet.
          <br />
          Start a new chat to begin.
        </p>
      </div>
    );
  }

  const groupProps = {
    activeSessionId,
    onSelectSession,
    onPinSession,
    onUnpinSession,
    onArchiveSession,
  };

  return (
    <ScrollArea className="flex-1">
      <div className="p-2">
        <SessionGroup title="Pinned" sessions={grouped.pinned} {...groupProps} />
        <SessionGroup title="Today" sessions={grouped.today} {...groupProps} />
        <SessionGroup title="Yesterday" sessions={grouped.yesterday} {...groupProps} />
        <SessionGroup title="This Week" sessions={grouped.thisWeek} {...groupProps} />
        <SessionGroup title="Older" sessions={grouped.older} {...groupProps} />
      </div>
    </ScrollArea>
  );
}
