'use client';

import { useParams } from 'next/navigation';
import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import dynamic from 'next/dynamic';
import { ArrowLeft, Send, Loader2, Sparkles, MessageSquare, Code, FileQuestion, Lightbulb } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { AgentManager } from '@/components/agent-manager';

const SyntaxHighlighter = dynamic(
  () => import('react-syntax-highlighter').then((mod) => mod.Prism),
  { ssr: false, loading: () => <div className="animate-shimmer h-20 rounded-xl" /> }
);

import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent?: string;
}

const suggestions = [
  { icon: Code, text: 'Help me debug this error', color: 'text-blue-500' },
  { icon: FileQuestion, text: 'Explain how this code works', color: 'text-green-500' },
  { icon: Lightbulb, text: 'Suggest improvements for my code', color: 'text-yellow-500' },
  { icon: MessageSquare, text: 'Review my architecture decisions', color: 'text-purple-500' },
];

export default function ChatPage() {
  const params = useParams();
  const blueprint = params.blueprint as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastUserMessageRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

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

  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [input, adjustTextareaHeight]);

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

  const handleSuggestionClick = (text: string) => {
    setInput(text);
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

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
          <AgentManager blueprint={blueprint} sessionId={sessionId} />
        </div>
      </header>

      <ScrollArea className="flex-1" ref={scrollAreaRef}>
        <div className="max-w-4xl mx-auto px-4 py-6">
          {messages.length === 0 && mounted && (
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
                    onClick={() => handleSuggestionClick(s.text)}
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
                {message.agent && (
                  <Badge 
                    variant="outline" 
                    className="mb-2 text-xs bg-primary/10 text-primary border-primary/20"
                  >
                    {message.agent}
                  </Badge>
                )}
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

      <div className="border-t border-border/50 bg-background/80 backdrop-blur-xl p-4">
        <form
          onSubmit={handleSubmit}
          className="max-w-4xl mx-auto"
        >
          <div className="relative flex items-end gap-2 p-2 rounded-2xl border border-border/50 bg-card shadow-lg shadow-black/5 focus-within:border-primary/50 focus-within:shadow-primary/5 transition-all">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything... (Shift+Enter for new line)"
              disabled={isLoading}
              rows={1}
              className="flex-1 resize-none bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 max-h-[200px]"
            />
            <Button 
              type="submit" 
              disabled={isLoading || !input.trim()}
              size="icon"
              className="h-10 w-10 rounded-xl bg-primary hover:bg-primary/90 shadow-lg shadow-primary/25 disabled:shadow-none transition-all"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-2">
            AI responses may be inaccurate. Please verify important information.
          </p>
        </form>
      </div>
    </div>
  );
}
