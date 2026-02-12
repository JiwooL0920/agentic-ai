'use client';

import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { ArrowLeft, Sparkles, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgentManager } from '@/components/agent-manager';
import { SystemStats } from '@/components/system-stats';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { MessageList, ChatInput } from '@/components/chat';
import { useChat } from '@/hooks/useChat';

export default function ChatPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const blueprint = params.blueprint as string;
  const initialSessionId = searchParams.get('session');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleSessionCreated = useCallback(
    (newSessionId: string) => {
      router.replace(`/${blueprint}?session=${newSessionId}`, { scroll: false });
    },
    [blueprint, router]
  );

  const {
    messages,
    input,
    setInput,
    isLoading,
    isHydrating,
    sessionId,
    handleSubmit,
    handleCancel,
    handleSuggestionClick,
    handleKeyDown,
    textareaRef,
  } = useChat({ blueprint, initialSessionId, onSessionCreated: handleSessionCreated });

  return (
    <div className="flex flex-col h-screen bg-background">
      <header className="border-b border-border/50 px-4 py-3 bg-background/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link href="/">
              <Button variant="ghost" size="icon" className="hover:bg-primary/10">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div className="h-8 w-px bg-border" />
            <div>
              <h1 className="font-semibold text-lg capitalize flex items-center gap-2">
                {blueprint}
                <Sparkles className="h-4 w-4 text-primary" />
              </h1>
              <p className="text-xs text-muted-foreground">
                Multi-agent AI assistant
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <SystemStats />
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link href={`/${blueprint}/knowledge`}>
                    <Button variant="ghost" size="icon" className="hover:bg-primary/10">
                      <Database className="h-5 w-5" />
                    </Button>
                  </Link>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Manage Knowledge Base</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <AgentManager blueprint={blueprint} sessionId={sessionId} />
          </div>
        </div>
      </header>

      <MessageList
        messages={messages}
        isLoading={isLoading}
        isHydrating={isHydrating}
        mounted={mounted}
        blueprint={blueprint}
        onSuggestionClick={handleSuggestionClick}
      />

      <ChatInput
        input={input}
        setInput={setInput}
        isLoading={isLoading}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        onKeyDown={handleKeyDown}
        textareaRef={textareaRef}
      />
    </div>
  );
}
