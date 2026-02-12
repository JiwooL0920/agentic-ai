'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { API_URL, getApiHeaders } from '@/lib/config';
import { notifySessionCreated } from '@/lib/session-events';
import type { Message } from '@/types/chat';

interface UseChatOptions {
  blueprint: string;
  initialSessionId?: string | null;
  onSessionCreated?: (sessionId: string) => void;
}

interface UseChatReturn {
  messages: Message[];
  input: string;
  setInput: (value: string) => void;
  isLoading: boolean;
  isHydrating: boolean;
  sessionId: string | null;
  handleSubmit: (e: React.FormEvent) => Promise<void>;
  handleCancel: () => Promise<void>;
  handleSuggestionClick: (text: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement>;
}

/**
 * Convert backend message format to frontend Message type.
 */
function convertBackendMessage(msg: {
  message_id?: string;
  role: string;
  content: string;
  agent?: string;
  rag_sources?: Array<{ filename?: string; score?: number; content?: string }>;
  documents_used?: number;
}): Message {
  return {
    id: msg.message_id || Date.now().toString(),
    role: msg.role as 'user' | 'assistant',
    content: msg.content,
    agent: msg.agent,
    ragSources: msg.rag_sources,
    documentsUsed: msg.documents_used,
  };
}

export function useChat({ blueprint, initialSessionId, onSessionCreated }: UseChatOptions): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isHydrating, setIsHydrating] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const hydratedSessionRef = useRef<string | null>(null);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Hydrate session when initialSessionId is provided
  useEffect(() => {
    // Reset state when navigating to fresh chat (no session ID)
    if (!initialSessionId) {
      setMessages([]);
      setSessionId(null);
      hydratedSessionRef.current = null;
      return;
    }

    // Skip if already hydrated this session
    if (hydratedSessionRef.current === initialSessionId) {
      return;
    }

    const hydrateSession = async () => {
      setIsHydrating(true);
      try {
        const response = await fetch(
          `${API_URL}/api/blueprints/${blueprint}/sessions/${initialSessionId}`,
          { headers: getApiHeaders() }
        );

        if (!response.ok) {
          console.error('Failed to fetch session:', response.status);
          return;
        }

        const data = await response.json();
        setSessionId(data.session_id);
        setMessages(data.messages.map(convertBackendMessage));
        hydratedSessionRef.current = initialSessionId;
      } catch (error) {
        console.error('Failed to hydrate session:', error);
      } finally {
        setIsHydrating(false);
      }
    };

    hydrateSession();
  }, [blueprint, initialSessionId]);

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

  const handleCancel = async () => {
    if (!sessionId) return;

    try {
      await fetch(
        `${API_URL}/api/blueprints/${blueprint}/sessions/${sessionId}/cancel`,
        {
          method: 'POST',
          headers: getApiHeaders(true),
        }
      );

      abortControllerRef.current?.abort();
      setIsLoading(false);
    } catch (error) {
      console.error('Failed to cancel request:', error);
      abortControllerRef.current?.abort();
      setIsLoading(false);
    }
  };

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

    try {
      const response = await fetch(
        `${API_URL}/api/blueprints/${blueprint}/chat/stream`,
        {
          method: 'POST',
          headers: getApiHeaders(true),
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

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
        ragSources: [],
        documentsUsed: 0,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine || trimmedLine.startsWith('event:')) {
              continue;
            }

            if (trimmedLine.startsWith('data: ')) {
              try {
                const jsonStr = trimmedLine.slice(6);
                if (!jsonStr) continue;

                const data = JSON.parse(jsonStr);

                if (data.type === 'metadata') {
                  assistantMessage.agent = data.agent;
                  if (data.session_id) {
                    setSessionId(data.session_id);
                    if (!initialSessionId) {
                      notifySessionCreated(data.session_id);
                      if (onSessionCreated) {
                        onSessionCreated(data.session_id);
                      }
                    }
                  }
                  // Update messages to show agent badge
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMessage.id ? { ...assistantMessage } : m
                    )
                  );
                } else if (data.type === 'content' && data.content) {
                  // Accumulate streaming content
                  assistantMessage.content += data.content;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMessage.id ? { ...assistantMessage } : m
                    )
                  );
                } else if (data.type === 'rag_sources' && data.sources) {
                  // Handle RAG sources
                  assistantMessage.ragSources = data.sources;
                  assistantMessage.documentsUsed = data.sources.length;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMessage.id ? { ...assistantMessage } : m
                    )
                  );
                }
              } catch (parseError) {
                if (parseError instanceof SyntaxError) {
                  console.warn('JSON parse error, skipping line:', trimmedLine);
                  continue;
                }
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
          `${API_URL}/api/blueprints/${blueprint}/chat`,
          {
            method: 'POST',
            headers: getApiHeaders(true),
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

  return {
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
  };
}
