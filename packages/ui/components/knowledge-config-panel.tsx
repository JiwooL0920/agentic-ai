'use client';

import { useEffect, useState, useCallback } from 'react';
import { BookOpen, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  KnowledgeConfig,
  getSession,
  updateKnowledgeConfig,
} from '@/lib/api/sessions';
import { listScopes, ScopeInfo } from '@/lib/api/rag';

interface KnowledgeConfigPanelProps {
  blueprint: string;
  sessionId: string | null;
}

export function KnowledgeConfigPanel({ blueprint, sessionId }: KnowledgeConfigPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [scopeInfo, setScopeInfo] = useState<ScopeInfo | null>(null);
  const [config, setConfig] = useState<KnowledgeConfig>({
    active_scopes: [],
    include_agent_scopes: true,
    include_user_docs: true,
  });
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchData = useCallback(async () => {
    if (!sessionId) return;
    
    setIsLoading(true);
    try {
      const [sessionData, scopes] = await Promise.all([
        getSession(blueprint, sessionId),
        listScopes(),
      ]);
      
      setConfig(sessionData.knowledge_config || {
        active_scopes: [],
        include_agent_scopes: true,
        include_user_docs: true,
      });
      setScopeInfo(scopes);
    } catch (error) {
      console.error('Failed to fetch knowledge config:', error);
    } finally {
      setIsLoading(false);
    }
  }, [blueprint, sessionId]);

  useEffect(() => {
    if (isOpen && sessionId) {
      fetchData();
    }
  }, [isOpen, sessionId, fetchData]);

  const handleSave = async (newConfig: KnowledgeConfig) => {
    if (!sessionId) return;
    
    setIsSaving(true);
    try {
      await updateKnowledgeConfig(blueprint, sessionId, newConfig);
      setConfig(newConfig);
      window.dispatchEvent(new CustomEvent('knowledge-config-updated'));
    } catch (error) {
      console.error('Failed to update knowledge config:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const toggleAgentScopes = () => {
    const newConfig = { ...config, include_agent_scopes: !config.include_agent_scopes };
    setConfig(newConfig);
    handleSave(newConfig);
  };

  const toggleUserDocs = () => {
    const newConfig = { ...config, include_user_docs: !config.include_user_docs };
    setConfig(newConfig);
    handleSave(newConfig);
  };

  const toggleScope = (scope: string) => {
    const newScopes = config.active_scopes.includes(scope)
      ? config.active_scopes.filter(s => s !== scope)
      : [...config.active_scopes, scope];
    const newConfig = { ...config, active_scopes: newScopes };
    setConfig(newConfig);
    handleSave(newConfig);
  };

  const activeCount = (config.include_agent_scopes ? 1 : 0) + 
                      (config.include_user_docs ? 1 : 0) + 
                      config.active_scopes.length;

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" disabled className="hover:bg-primary/10">
        <BookOpen className="h-5 w-5" />
      </Button>
    );
  }

  if (!sessionId) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" disabled className="hover:bg-primary/10">
              <BookOpen className="h-5 w-5 text-muted-foreground" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Start a conversation to configure knowledge sources</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="hover:bg-primary/10 relative">
                <BookOpen className="h-5 w-5" />
                {activeCount > 0 && (
                  <Badge 
                    variant="secondary" 
                    className="absolute -top-1 -right-1 h-4 w-4 p-0 flex items-center justify-center text-[10px] bg-primary text-primary-foreground"
                  >
                    {activeCount}
                  </Badge>
                )}
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent>
            <p>Knowledge Sources</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Knowledge Sources
          </DialogTitle>
          <DialogDescription>
            Configure which knowledge sources this session uses for RAG
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <label className="text-sm font-medium">Agent Knowledge</label>
                  <p className="text-xs text-muted-foreground">
                    Use knowledge scopes defined by the agent
                  </p>
                </div>
                <Switch
                  checked={config.include_agent_scopes}
                  onCheckedChange={toggleAgentScopes}
                  disabled={isSaving}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <label className="text-sm font-medium">My Documents</label>
                  <p className="text-xs text-muted-foreground">
                    Include documents you&apos;ve uploaded
                  </p>
                </div>
                <Switch
                  checked={config.include_user_docs}
                  onCheckedChange={toggleUserDocs}
                  disabled={isSaving}
                />
              </div>
            </div>

            {scopeInfo && scopeInfo.scopes.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Additional Scopes</label>
                  {isSaving && <Loader2 className="h-3 w-3 animate-spin" />}
                </div>
                <ScrollArea className="h-[200px] rounded-md border p-3">
                  <div className="space-y-2">
                    {scopeInfo.scopes
                      .filter(scope => !scope.startsWith('user:'))
                      .map(scope => (
                        <div 
                          key={scope} 
                          className="flex items-center justify-between py-1.5"
                        >
                          <div className="flex items-center gap-2">
                            <Checkbox
                              id={`scope-${scope}`}
                              checked={config.active_scopes.includes(scope)}
                              onCheckedChange={() => toggleScope(scope)}
                              disabled={isSaving}
                            />
                            <label 
                              htmlFor={`scope-${scope}`}
                              className="text-sm cursor-pointer"
                            >
                              {scope}
                            </label>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {scopeInfo.counts[scope] || 0} docs
                          </Badge>
                        </div>
                      ))}
                    {scopeInfo.scopes.filter(s => !s.startsWith('user:')).length === 0 && (
                      <p className="text-sm text-muted-foreground py-4 text-center">
                        No additional scopes available
                      </p>
                    )}
                  </div>
                </ScrollArea>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
