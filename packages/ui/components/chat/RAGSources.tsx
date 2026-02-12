'use client';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BookOpen, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import type { RAGSource } from '@/types/chat';

interface RAGSourcesProps {
  sources: RAGSource[];
  messageId: string;
  isExpanded: boolean;
  onToggle: () => void;
}

export function RAGSources({ sources, messageId, isExpanded, onToggle }: RAGSourcesProps) {
  if (!sources || sources.length === 0) return null;

  // Group sources by filename
  const grouped = sources.reduce((acc, source) => {
    const filename = source.filename || 'Unknown';
    if (!acc[filename]) {
      acc[filename] = [];
    }
    acc[filename].push(source);
    return acc;
  }, {} as Record<string, RAGSource[]>);

  const uniqueFiles = new Set(sources.map(s => s.filename));
  const fileCount = uniqueFiles.size;
  const chunkCount = sources.length;

  return (
    <div className="mt-3 pt-3 border-t border-border/50">
      <Button
        variant="ghost"
        size="sm"
        onClick={onToggle}
        className="w-full justify-between hover:bg-accent/50 mb-2"
      >
        <span className="flex items-center gap-2 text-xs font-medium">
          <BookOpen className="h-4 w-4" />
          View {fileCount} {fileCount === 1 ? 'File' : 'Files'} ({chunkCount} {chunkCount === 1 ? 'chunk' : 'chunks'})
        </span>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </Button>

      {isExpanded && (
        <div className="space-y-2 animate-in slide-in-from-top-2">
          {Object.entries(grouped).map(([filename, fileSources]) => {
            const bestScore = Math.max(...fileSources.map(s => s.score || 0));
            const avgScore = fileSources.reduce((sum, s) => sum + (s.score || 0), 0) / fileSources.length;
            const isWeakMatch = bestScore < 0.5;

            return (
              <div
                key={filename}
                className={`p-3 rounded-lg border transition-colors ${
                  isWeakMatch
                    ? 'bg-yellow-500/5 border-yellow-500/20 hover:bg-yellow-500/10'
                    : 'bg-muted/30 hover:bg-muted/50'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <ExternalLink className="h-3 w-3 flex-shrink-0 text-muted-foreground" />
                    <div className="flex-1 min-w-0">
                      <span className="text-xs font-medium truncate block">
                        {filename}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {fileSources.length} {fileSources.length === 1 ? 'chunk' : 'chunks'}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <Badge
                      variant="outline"
                      className={`text-xs ${isWeakMatch ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-700' : ''}`}
                    >
                      {Math.round(bestScore * 100)}% best
                    </Badge>
                    {fileSources.length > 1 && (
                      <span className="text-xs text-muted-foreground">
                        {Math.round(avgScore * 100)}% avg
                      </span>
                    )}
                  </div>
                </div>
                {isWeakMatch && (
                  <p className="text-xs text-yellow-700 dark:text-yellow-600 mb-2 flex items-start gap-1">
                    <span>⚠️</span>
                    <span>Weak match - consider uploading more relevant documents</span>
                  </p>
                )}
                {fileSources[0].content && (
                  <details className="text-xs text-muted-foreground mt-2">
                    <summary className="cursor-pointer hover:text-foreground">
                      Show content preview
                    </summary>
                    <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                      {fileSources.slice(0, 3).map((source, idx) => (
                        <p key={idx} className="line-clamp-2 pl-2 border-l-2 border-muted">
                          {source.content}
                        </p>
                      ))}
                      {fileSources.length > 3 && (
                        <p className="italic">+{fileSources.length - 3} more chunks...</p>
                      )}
                    </div>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
