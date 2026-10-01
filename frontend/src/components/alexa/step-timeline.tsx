'use client';

import * as React from 'react';
import { Check, CircleDashed, Loader2, ShieldQuestion, X, Ban } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LiveStep } from '@/hooks/use-agent-session';
import type { MissionStep } from '@/types/agent';
import { DiffPanel, TerminalPanel } from '@/components/alexa/change-panels';
import { baseTool } from '@/components/alexa/approval-preview';
import { parseUnified, textChange } from '@/lib/diff';

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

const text = (v: unknown): string => (typeof v === 'string' ? v : '');

/** What a finished step produced, shown as a diff, a terminal, or a link, when that is more useful than JSON. */
function StepOutput({ step }: { step: MissionStep }) {
  if (step.status !== 'done') return null;
  const tool = baseTool(step.tool);
  const r = (step.result && typeof step.result === 'object' ? step.result : {}) as Record<string, unknown>;

  if (tool === 'run_tests' && typeof r.output_tail === 'string') {
    const footer = [r.exit_code != null ? `exit ${r.exit_code}` : null, r.timed_out ? 'timed out' : null, r.seconds != null ? `${r.seconds}s` : null]
      .filter(Boolean)
      .join(' · ');
    return <TerminalPanel title={text(r.command) || 'tests'} text={r.output_tail} ok={r.passed === true} footer={footer} />;
  }
  if (tool === 'show_diff' && typeof r.diff === 'string') {
    return <DiffPanel title="Current changes" lines={parseUnified(r.diff)} />;
  }
  if (tool === 'edit_file') {
    return (
      <details className="text-[11px] text-muted-foreground">
        <summary className="cursor-pointer select-none hover:text-foreground">Show the change</summary>
        <div className="mt-1">
          <DiffPanel title={text(step.arguments.path)} lines={textChange(text(step.arguments.old), text(step.arguments.new))} />
        </div>
      </details>
    );
  }
  if (tool === 'draft_pr' && typeof r.url === 'string' && /^https:\/\/github\.com\//.test(r.url)) {
    return (
      <a href={r.url} target="_blank" rel="noopener noreferrer" className="inline-block text-[11px] font-semibold text-primary hover:underline">
        Open draft pull request #{String(r.number ?? '')} on GitHub
      </a>
    );
  }
  return null;
}

/** The planner's tool calls as they happen: what it chose, why, and how each one ended. */
export function StepTimeline({
  steps,
  thinking,
  results,
}: {
  steps: LiveStep[];
  thinking: boolean;
  /** The mission's own steps, which carry each tool's result once the mission is back from the server. */
  results?: MissionStep[];
}) {
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
            {results?.find((r) => r.index === s.index) && (
              <div className="mt-1.5">
                <StepOutput step={results.find((r) => r.index === s.index) as MissionStep} />
              </div>
            )}
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
