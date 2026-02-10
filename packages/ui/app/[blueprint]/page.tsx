'use client';

import { useParams } from 'next/navigation';
import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import dynamic from 'next/dynamic';
import { ArrowLeft, Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { AgentManager } from '@/components/agent-manager';

const SyntaxHighlighter = dynamic(
  () => import('react-syntax-highlighter').then((mod) => mod.Prism),
  { ssr: false, loading: () => <div className="animate-pulse bg-muted h-20 rounded" /> }
);

import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent?: string;
}

export default function ChatPage() {
  const params = useParams();
  const blueprint = params.blueprint as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastUserMessageRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

    try {
      const response = await fetch(
        `${apiUrl}/api/blueprints/${blueprint}/chat/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: userMessage.content,
            session_id: sessionId,
            stream: true,
          }),
          signal: abortControllerRef.current.signal,
        }
      );

      if (!response.ok) throw new Error('Failed to send message');

      const reader = response.body?.getReader();
      
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();

      let assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
      };

      setMessages((prev) => [...prev, assistantMessage]);

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === 'metadata') {
                  assistantMessage.agent = data.agent;
                  if (data.session_id) setSessionId(data.session_id);
                } else if (data.type === 'content') {
                  assistantMessage.content += data.content;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMessage.id ? { ...assistantMessage } : m
                    )
                  );
                }
              } catch (parseError) {
                if (parseError instanceof SyntaxError) continue;
                throw parseError;
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }
      
      try {
        const response = await fetch(
          `${apiUrl}/api/blueprints/${blueprint}/chat`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: userMessage.content,
              session_id: sessionId,
              stream: false,
            }),
            signal: abortControllerRef.current?.signal,
          }
        );

        if (response.ok) {
          const data = await response.json();
          setSessionId(data.session_id);
          setMessages((prev) => [
            ...prev,
            {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: data.response,
              agent: data.agent,
            },
          ]);
        }
      } catch (fallbackError) {
        if (fallbackError instanceof Error && fallbackError.name === 'AbortError') {
          return;
        }
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: 'Sorry, I encountered an error. Please try again.',
          },
        ]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="border-b px-4 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="font-semibold capitalize">{blueprint}</h1>
            <p className="text-sm text-muted-foreground">
              Chat with specialized AI agents
            </p>
          </div>
        </div>
        <AgentManager blueprint={blueprint} sessionId={sessionId} />
      </header>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground py-12">
              <p className="text-lg mb-2">Welcome to {blueprint}</p>
              <p className="text-sm">
                Ask any question and I'll route it to the best agent
              </p>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={message.id}
              ref={message.role === 'user' && index === messages.length - 1 ? lastUserMessageRef : null}
              className={`flex gap-3 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                    AI
                  </AvatarFallback>
                </Avatar>
              )}

              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted'
                }`}
              >
                {message.agent && (
                  <Badge variant="outline" className="mb-2 text-xs">
                    {message.agent}
                  </Badge>
                )}
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ node, inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match ? match[1] : '';
                        
                        return !inline && language ? (
                          <SyntaxHighlighter
                            style={vscDarkPlus}
                            language={language}
                            PreTag="div"
                            customStyle={{
                              margin: '1em 0',
                              borderRadius: '0.5rem',
                              fontSize: '0.875rem',
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
              </div>

              {message.role === 'user' && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-secondary">U</AvatarFallback>
                </Avatar>
              )}
            </div>
          ))}

          {isLoading && messages[messages.length - 1]?.role === 'user' && (
            <div className="flex gap-3 justify-start">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                  AI
                </AvatarFallback>
              </Avatar>
              <div className="bg-muted rounded-lg px-4 py-2">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            </div>
          )}
          
          {/* Invisible element at the bottom for auto-scroll */}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t p-4">
        <form
          onSubmit={handleSubmit}
          className="max-w-3xl mx-auto flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !input.trim()}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
