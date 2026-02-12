/**
 * Shared types for chat functionality.
 */

export interface RAGSource {
  filename?: string;
  score?: number;
  content?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent?: string;
  ragSources?: RAGSource[];
  documentsUsed?: number;
}
