'use client';

import { Button } from '@/components/ui/button';
import { Send, X } from 'lucide-react';

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  isLoading: boolean;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement>;
}

export function ChatInput({
  input,
  setInput,
  isLoading,
  onSubmit,
  onCancel,
  onKeyDown,
  textareaRef,
}: ChatInputProps) {
  return (
    <div className="border-t border-border/50 bg-background/80 backdrop-blur-xl p-4">
      <form onSubmit={onSubmit} className="max-w-4xl mx-auto">
        <div className="relative flex items-end gap-2 p-2 rounded-2xl border border-border/50 bg-card shadow-lg shadow-black/5 focus-within:border-primary/50 focus-within:shadow-primary/5 transition-all">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask anything... (Shift+Enter for new line)"
            disabled={isLoading}
            rows={1}
            className="flex-1 resize-none bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 max-h-[200px]"
          />
          {isLoading ? (
            <Button
              type="button"
              onClick={onCancel}
              size="icon"
              variant="destructive"
              className="h-10 w-10 rounded-xl shadow-lg hover:shadow-xl transition-all"
            >
              <X className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="submit"
              disabled={!input.trim()}
              size="icon"
              className="h-10 w-10 rounded-xl bg-primary hover:bg-primary/90 shadow-lg shadow-primary/25 disabled:shadow-none transition-all"
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground text-center mt-2">
          AI responses may be inaccurate. Please verify important information.
        </p>
      </form>
    </div>
  );
}
