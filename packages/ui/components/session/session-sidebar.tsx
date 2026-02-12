'use client';

import { useState, useEffect, useCallback } from 'react';
import { PanelLeftClose, PanelLeft, Plus, Loader2 } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { SessionList } from './session-list';
import { useSessions } from '@/hooks/useSessions';

interface SessionSidebarProps {
  blueprint: string;
}

export function SessionSidebar({ blueprint }: SessionSidebarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  const {
    sessions,
    isLoading,
    activeSessionId,
    setActiveSession,
    createSession,
    pinSession,
    unpinSession,
    archiveSession,
  } = useSessions({ blueprint });

  useEffect(() => {
    const sessionParam = searchParams.get('session');
    if (sessionParam && sessionParam !== activeSessionId) {
      setActiveSession(sessionParam);
    }
  }, [searchParams, activeSessionId, setActiveSession]);

  const handleSelectSession = useCallback(
    (sessionId: string) => {
      setActiveSession(sessionId);
      router.push(`/${blueprint}?session=${sessionId}`);
    },
    [blueprint, router, setActiveSession]
  );

  const handleNewChat = useCallback(async () => {
    setIsCreating(true);
    try {
      const newSessionId = await createSession();
      handleSelectSession(newSessionId);
    } finally {
      setIsCreating(false);
    }
  }, [createSession, handleSelectSession]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault();
        setIsCollapsed((prev) => !prev);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        handleNewChat();
      }
    },
    [handleNewChat]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <aside
      className={cn(
        'flex flex-col border-r bg-muted/30 transition-all duration-300',
        isCollapsed ? 'w-12' : 'w-72'
      )}
    >
      <div className="flex items-center justify-between p-2 border-b">
        {!isCollapsed && (
          <Button
            variant="outline"
            size="sm"
            className="flex-1 mr-2"
            onClick={handleNewChat}
            disabled={isCreating}
          >
            {isCreating ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Plus className="h-4 w-4 mr-2" />
            )}
            New Chat
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="shrink-0"
        >
          {isCollapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </Button>
      </div>

      {!isCollapsed && (
        <>
          {isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <SessionList
              sessions={sessions}
              activeSessionId={activeSessionId}
              onSelectSession={handleSelectSession}
              onPinSession={pinSession}
              onUnpinSession={unpinSession}
              onArchiveSession={archiveSession}
            />
          )}
        </>
      )}
    </aside>
  );
}
