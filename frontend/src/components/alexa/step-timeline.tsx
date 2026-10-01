'use client';

import * as React from 'react';
import { Check, CircleDashed, Loader2, ShieldQuestion, X, Ban } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LiveStep } from '@/hooks/use-agent-session';

const ICON: Record<LiveStep['state'], React.ReactNode> = {
  planned: <CircleDashed className="h-3.5 w-3.5 text-muted-foreground" />,
  running: <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />,
  done: <Check className="h-3.5 w-3.5 text-primary" />,
  failed: <X className="h-3.5 w-3.5 text-destructive" />,
  awaiting: <ShieldQuestion className="h-3.5 w-3.5 text-bounty-gold" />,
  rejected: <Ban className="h-3.5 w-3.5 text-muted-foreground" />,
};

const LABEL: Record<LiveStep['state'], string> = {
  planned: 'queued',
  running: 'running',
  done: 'done',
  failed: 'failed',
  awaiting: 'needs your OK',
  rejected: 'declined',
};

function summarize(args: Record<string, unknown>): string {
  const text = JSON.stringify(args);
  return text.length > 160 ? `${text.slice(0, 157)}...` : text;
}

/** The planner's tool calls as they happen: what it chose, why, and how each one ended. */
export function StepTimeline({ steps, thinking }: { steps: LiveStep[]; thinking: boolean }) {
  if (steps.length === 0 && !thinking) return null;
  return (
    <ol className="space-y-2" aria-label="What the assistant did">
      {steps.map((s) => (
        <li key={s.index} className="flex gap-2.5 text-xs">
          <span className="mt-0.5 shrink-0">{ICON[s.state]}</span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2">
              <span className="font-semibold text-foreground">{s.tool}</span>
              <span
                className={cn(
                  'text-[10px] uppercase tracking-wide',
                  s.state === 'awaiting' ? 'text-bounty-gold' : 'text-muted-foreground',
                )}
              >
                {LABEL[s.state]}
              </span>
            </div>
            {s.thought && <p className="text-muted-foreground">{s.thought}</p>}
            {Object.keys(s.arguments).length > 0 && (
              <p className="truncate font-mono text-[11px] text-muted-foreground/80" title={JSON.stringify(s.arguments)}>
                {summarize(s.arguments)}
              </p>
            )}
            {s.error && <p className="text-destructive">{s.error}</p>}
          </div>
        </li>
      ))}
      {thinking && !steps.some((s) => s.state === 'running' || s.state === 'awaiting') && (
        <li className="flex items-center gap-2.5 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          Thinking...
        </li>
      )}
    </ol>
  );
}
