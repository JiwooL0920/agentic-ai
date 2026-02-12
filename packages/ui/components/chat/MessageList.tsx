'use client';

import { forwardRef, useState, useCallback, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Code, FileQuestion, Lightbulb, MessageSquare, Sparkles, BookOpen } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { RAGSources } from './RAGSources';
import type { Message } from '@/types/chat';

const SyntaxHighlighter = dynamic(
  () => import('react-syntax-highlighter').then((mod) => mod.Prism),
  { ssr: false, loading: () => <div className="animate-shimmer h-20 rounded-xl" /> }
);

import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';

const suggestions = [
  { icon: Code, text: 'Help me debug this error', color: 'text-blue-500' },
  { icon: FileQuestion, text: 'Explain how this code works', color: 'text-green-500' },
  { icon: Lightbulb, text: 'Suggest improvements for my code', color: 'text-yellow-500' },
  { icon: MessageSquare, text: 'Review my architecture decisions', color: 'text-purple-500' },
];

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  isHydrating?: boolean;
  mounted: boolean;
  blueprint: string;
  onSuggestionClick: (text: string) => void;
}

export const MessageList = forwardRef<HTMLDivElement, MessageListProps>(
  function MessageList({ messages, isLoading, isHydrating, mounted, blueprint, onSuggestionClick }, ref) {
    const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
    const scrollAreaRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const lastUserMessageRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = useCallback((smooth = true) => {
      const viewport = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
      if (viewport) {
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior: smooth ? 'smooth' : 'auto'
        });
      }
    }, []);

    const scrollToLastUserMessage = useCallback(() => {
      if (!lastUserMessageRef.current) return;

      const viewport = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
      if (viewport) {
        const messageTop = lastUserMessageRef.current.offsetTop;
        viewport.scrollTo({
          top: messageTop - 20,
          behavior: 'auto'
        });
      }
    }, []);

    useEffect(() => {
      if (messages.length > 0 && messages[messages.length - 1].role === 'user') {
        setTimeout(() => scrollToLastUserMessage(), 0);
      } else {
        scrollToBottom(true);
      }
    }, [messages, scrollToBottom, scrollToLastUserMessage]);

    const toggleSources = (messageId: string) => {
      setExpandedSources(prev => {
        const newSet = new Set(prev);
        if (newSet.has(messageId)) {
          newSet.delete(messageId);
        } else {
          newSet.add(messageId);
        }
        return newSet;
      });
    };

    return (
      <ScrollArea className="flex-1" ref={scrollAreaRef}>
        <div className="max-w-4xl mx-auto px-4 py-6">
          {mounted && isHydrating && (
            <div className="space-y-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className={`flex gap-4 ${i % 2 === 0 ? 'justify-end' : 'justify-start'}`}>
                  {i % 2 !== 0 && (
                    <div className="h-9 w-9 rounded-full bg-muted animate-pulse" />
                  )}
                  <div className={`rounded-2xl px-4 py-3 ${i % 2 === 0 ? 'bg-primary/10' : 'bg-muted'} animate-pulse`}>
                    <div className="h-4 w-48 bg-muted-foreground/20 rounded mb-2" />
                    <div className="h-4 w-32 bg-muted-foreground/20 rounded" />
                  </div>
                  {i % 2 === 0 && (
                    <div className="h-9 w-9 rounded-full bg-muted animate-pulse" />
                  )}
                </div>
              ))}
            </div>
          )}

          {messages.length === 0 && mounted && !isHydrating && (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center mb-6 shadow-lg shadow-primary/10">
                <Sparkles className="w-10 h-10 text-primary" />
              </div>
              <h2 className="text-2xl font-semibold mb-2">Welcome to {blueprint}</h2>
              <p className="text-muted-foreground mb-8 max-w-md">
                I&apos;ll route your questions to the best specialized agent. What would you like help with?
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => onSuggestionClick(s.text)}
                    className="flex items-center gap-3 p-4 rounded-xl border border-border/50 bg-card/50 hover:bg-card hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all text-left group"
                  >
                    <s.icon className={`w-5 h-5 ${s.color} group-hover:scale-110 transition-transform`} />
                    <span className="text-sm">{s.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {mounted && messages.map((message, index) => (
            <div
              key={message.id}
              ref={message.role === 'user' && index === messages.length - 1 ? lastUserMessageRef : null}
              className={`flex gap-4 mb-6 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <Avatar className="h-9 w-9 border-2 border-primary/20 shadow-lg shadow-primary/10">
                  <AvatarFallback className="bg-gradient-to-br from-primary to-purple-600 text-white text-xs font-medium">
                    AI
                  </AvatarFallback>
                </Avatar>
              )}

              <div
                className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'message-user rounded-br-md'
                    : 'message-assistant rounded-bl-md'
                }`}
              >
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  {message.agent && (
                    <Badge
                      variant="outline"
                      className="text-xs bg-primary/10 text-primary border-primary/20"
                    >
                      {message.agent}
                    </Badge>
                  )}
                  {(message.documentsUsed ?? 0) > 0 && (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Badge
                            variant="outline"
                            className="text-xs bg-blue-500/10 text-blue-600 border-blue-500/20 cursor-help"
                          >
                            <BookOpen className="h-3 w-3 mr-1" />
                            {message.documentsUsed} {message.documentsUsed === 1 ? 'source' : 'sources'}
                          </Badge>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Response augmented with knowledge base context</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </div>
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ inline, className, children, ...props }: { inline?: boolean; className?: string; children?: React.ReactNode }) {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match ? match[1] : '';

                        return !inline && language ? (
                          <SyntaxHighlighter
                            style={vscDarkPlus}
                            language={language}
                            PreTag="div"
                            customStyle={{
                              margin: '1em 0',
                              borderRadius: '0.75rem',
                              fontSize: '0.875rem',
                              border: '1px solid rgba(255,255,255,0.1)',
                            }}
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        );
                      },
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>

                {message.ragSources && message.ragSources.length > 0 && (
                  <RAGSources
                    sources={message.ragSources}
                    messageId={message.id}
                    isExpanded={expandedSources.has(message.id)}
                    onToggle={() => toggleSources(message.id)}
                  />
                )}
              </div>

              {message.role === 'user' && (
                <Avatar className="h-9 w-9 border-2 border-border shadow">
                  <AvatarFallback className="bg-secondary text-secondary-foreground font-medium">
                    U
                  </AvatarFallback>
                </Avatar>
              )}
            </div>
          ))}

          {mounted && isLoading && messages[messages.length - 1]?.role === 'user' && (
            <div className="flex gap-4 mb-6 justify-start">
              <Avatar className="h-9 w-9 border-2 border-primary/20 shadow-lg shadow-primary/10">
                <AvatarFallback className="bg-gradient-to-br from-primary to-purple-600 text-white text-xs font-medium">
                  AI
                </AvatarFallback>
              </Avatar>
              <div className="message-assistant rounded-2xl rounded-bl-md px-5 py-4">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-primary animate-typing-1" />
                  <span className="w-2 h-2 rounded-full bg-primary animate-typing-2" />
                  <span className="w-2 h-2 rounded-full bg-primary animate-typing-3" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
    );
  }
);
