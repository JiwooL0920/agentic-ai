'use client';

import { useEffect, useState, useCallback } from 'react';
import { BookOpen, Bot, User, Folder } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { KnowledgeConfig, getSession } from '@/lib/api/sessions';

interface KnowledgeScopeIndicatorProps {
  blueprint: string;
  sessionId: string | null;
}

export function KnowledgeScopeIndicator({ blueprint, sessionId }: KnowledgeScopeIndicatorProps) {
  const [config, setConfig] = useState<KnowledgeConfig | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchConfig = useCallback(async () => {
    if (!sessionId) {
      setConfig(null);
      return;
    }

    try {
      const session = await getSession(blueprint, sessionId);
      setConfig(session.knowledge_config);
    } catch (error) {
      console.error('Failed to fetch knowledge config:', error);
      setConfig(null);
    }
  }, [blueprint, sessionId]);

  useEffect(() => {
    if (mounted) {
      fetchConfig();
    }
  }, [mounted, fetchConfig]);

  useEffect(() => {
    const handleConfigUpdate = () => {
      fetchConfig();
    };

    window.addEventListener('knowledge-config-updated', handleConfigUpdate);
    return () => {
      window.removeEventListener('knowledge-config-updated', handleConfigUpdate);
    };
  }, [fetchConfig]);

  if (!mounted || !sessionId || !config) {
    return null;
  }

  const hasAnySources = config.include_agent_scopes || 
                        config.include_user_docs || 
                        config.active_scopes.length > 0;

  if (!hasAnySources) {
    return (
      <div className="border-b border-border/30 bg-muted/30 px-4 py-1.5">
        <div className="max-w-4xl mx-auto flex items-center gap-2 text-xs text-muted-foreground">
          <BookOpen className="h-3 w-3" />
          <span>No knowledge sources active</span>
        </div>
      </div>
    );
  }

  return (
    <div className="border-b border-border/30 bg-muted/30 px-4 py-1.5">
      <div className="max-w-4xl mx-auto flex items-center gap-2 text-xs">
        <BookOpen className="h-3 w-3 text-muted-foreground" />
        <span className="text-muted-foreground">Sources:</span>
        <div className="flex items-center gap-1.5 flex-wrap">
          {config.include_agent_scopes && (
            <Badge variant="secondary" className="h-5 text-[10px] px-1.5 gap-1">
              <Bot className="h-2.5 w-2.5" />
              Agent KB
            </Badge>
          )}
          {config.include_user_docs && (
            <Badge variant="secondary" className="h-5 text-[10px] px-1.5 gap-1">
              <User className="h-2.5 w-2.5" />
              My Docs
            </Badge>
          )}
          {config.active_scopes.map(scope => (
            <Badge 
              key={scope} 
              variant="outline" 
              className="h-5 text-[10px] px-1.5 gap-1 bg-background"
            >
              <Folder className="h-2.5 w-2.5" />
              {scope}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );
}
