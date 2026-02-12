'use client';

import { MoreHorizontal, Pin, Archive, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { Session } from '@/hooks/useSessions';

interface SessionItemProps {
  session: Session;
  isActive: boolean;
  onClick: () => void;
  onPin: () => void;
  onUnpin: () => void;
  onArchive: () => void;
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function SessionItem({
  session,
  isActive,
  onClick,
  onPin,
  onUnpin,
  onArchive,
}: SessionItemProps) {
  const isPinned = session.session_state === 'pinned';
  const title = session.title || 'New conversation';

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      className={cn(
        'group flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer',
        'hover:bg-accent',
        isActive && 'bg-accent'
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          {isPinned && <Pin className="h-3 w-3 text-muted-foreground shrink-0" />}
          <span className="truncate font-medium">{title}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
          <span className="flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            {session.message_count}
          </span>
          <span>{formatRelativeTime(session.modified_on)}</span>
        </div>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 group-hover:opacity-100 shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          {isPinned ? (
            <DropdownMenuItem onClick={onUnpin}>
              <Pin className="h-4 w-4 mr-2" />
              Unpin
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem onClick={onPin}>
              <Pin className="h-4 w-4 mr-2" />
              Pin
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={onArchive} className="text-destructive">
            <Archive className="h-4 w-4 mr-2" />
            Archive
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
