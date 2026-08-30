'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Terminal, RotateCcw, Sparkles } from 'lucide-react';

interface EmptyStateProps {
  onReset: () => void;
  searchQuery?: string;
}

export function EmptyState({ onReset, searchQuery }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 bg-zinc-950/40 p-12 text-center font-mono">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 mb-4">
        <Terminal className="h-6 w-6 text-emerald-400" />
      </div>
      <h3 className="text-sm font-semibold text-zinc-200">
        No matching open-source issues found
      </h3>
      <p className="text-xs text-zinc-400 max-w-sm mt-1 mb-5">
        {searchQuery
          ? `No live issues found matching "${searchQuery}". Try broadening your search or resetting filters.`
          : 'No issues currently match your active filters. Try adjusting domain, difficulty, or bounty requirements.'}
      </p>
      <Button
        variant="terminal"
        size="sm"
        onClick={onReset}
        className="gap-2 text-xs"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        Reset All Filters
      </Button>
    </div>
  );
}
