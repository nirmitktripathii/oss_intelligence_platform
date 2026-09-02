'use client';

import * as React from 'react';
import { LocalizedFile } from '@/types/triage';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CodeBlock } from './code-block';
import { FileCode, Network, ChevronRight, Hash, Compass } from 'lucide-react';

interface FileLocalizerProps {
  localizedFiles: LocalizedFile[];
  onOpenGraph?: (targetFile?: string) => void;
}

export function FileLocalizer({ localizedFiles, onOpenGraph }: FileLocalizerProps) {
  const safeFiles = React.useMemo(
    () => (Array.isArray(localizedFiles) ? localizedFiles : []),
    [localizedFiles]
  );
  const [selectedFile, setSelectedFile] = React.useState<LocalizedFile | null>(
    safeFiles[0] || null
  );

  React.useEffect(() => {
    if (safeFiles.length > 0 && !selectedFile) {
      setSelectedFile(safeFiles[0]);
    }
  }, [safeFiles, selectedFile]);

  return (
    <div className="space-y-4 font-mono text-xs text-foreground">
      {/* 1. Blast Radius & Graph Action Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3.5 rounded-2xl border border-accent/30 bg-gradient-to-br from-accent/30 via-card/70 to-background p-4 sm:p-5 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-accent font-bold text-sm">
            <span className="flex items-center justify-center h-6 w-6 rounded-lg bg-accent/20 text-accent">
              <Network className="h-3.5 w-3.5" />
            </span>
            <span>Graphify AST Knowledge Graph Integration</span>
          </div>
          <p className="text-xs text-muted-foreground font-sans leading-relaxed">
            Trace caller/callee AST relationships, topological clusters, and calculate blast radius across the repository.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onOpenGraph?.(selectedFile?.filePath)}
          className="border-accent/50 text-accent bg-accent/10 hover:bg-accent/20 gap-2 shrink-0 text-xs font-semibold shadow-[0_0_12px_hsl(var(--accent)/0.2)]"
        >
          <Compass className="h-3.5 w-3.5 text-accent" />
          <span>Launch AST Graph</span>
        </Button>
      </div>

      {/* 2. Pinpointed Source Files List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
            <FileCode className="h-3.5 w-3.5 text-primary" />
            <span>Pinpointed Source Files ({safeFiles.length})</span>
          </h4>
          <span className="text-[11px] text-muted-foreground">Click a file to inspect AST trace</span>
        </div>

        <div className="space-y-2.5">
          {safeFiles.map((file) => {
            const isSelected = selectedFile?.filePath === file.filePath;
            const confidencePercent = Math.round(file.confidence * 100);

            return (
              <div
                key={file.filePath}
                onClick={() => setSelectedFile(file)}
                className={`rounded-xl border p-3.5 cursor-pointer transition-all ${
                  isSelected
                    ? 'border-primary/60 bg-primary/15 shadow-[0_0_15px_hsl(var(--primary)/0.15)] ring-1 ring-primary/50'
                    : 'border-border bg-card/60 hover:border-border hover:bg-card'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 truncate">
                    <span className={`p-1.5 rounded-lg border ${isSelected ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border bg-background text-muted-foreground'}`}>
                      <FileCode className="h-4 w-4" />
                    </span>
                    <div className="truncate">
                      <span className="font-bold text-xs text-foreground block truncate">
                        {file.filePath}
                      </span>
                      {file.lineRange && (
                        <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                          <Hash className="h-3 w-3 text-muted-foreground" />
                          <span>Lines: {Array.isArray(file.lineRange) ? `${file.lineRange[0]}-${file.lineRange[1]}` : file.lineRange}</span>
                        </span>
                      )}
                    </div>
                  </div>

                  <Badge
                    variant={confidencePercent >= 90 ? 'emerald' : confidencePercent >= 75 ? 'amber' : 'outline'}
                    className="text-[10px] font-bold px-2 py-0.5 shrink-0"
                  >
                    {confidencePercent}% match
                  </Badge>
                </div>

                <p className="mt-2 text-xs text-muted-foreground font-sans leading-relaxed pl-8">
                  {file.reason || 'Stack trace signature and heuristic pattern matched core handler route.'}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Selected File AST Code Snippet Preview */}
      {selectedFile && (
        <div className="rounded-2xl border border-border bg-background p-4 space-y-3 shadow-xl">
          <div className="flex items-center justify-between border-b border-border/80 pb-2.5">
            <span className="font-bold text-xs text-foreground flex items-center gap-1.5 truncate">
              <span className="h-2 w-2 rounded-full bg-primary" />
              <span>Preview: {selectedFile.filePath}</span>
            </span>
            <button
              onClick={() => onOpenGraph?.(selectedFile.filePath)}
              className="text-[11px] text-accent hover:text-accent font-semibold flex items-center gap-1"
            >
              <span>View in Graph</span>
              <ChevronRight className="h-3 w-3" />
            </button>
          </div>

          <CodeBlock
            code={selectedFile.diffSnippet || `# Target File: ${selectedFile.filePath}\n# Confidence: ${Math.round(selectedFile.confidence * 100)}%\n\ndef execute_handler(request):\n    # Isolated execution flow\n    pass`}
            language="typescript"
            filename={selectedFile.filePath}
          />
        </div>
      )}
    </div>
  );
}
