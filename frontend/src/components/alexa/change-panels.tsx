'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { countChanges, type DiffLine } from '@/lib/diff';

const ROW: Record<DiffLine['kind'], string> = {
  add: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  del: 'bg-red-500/10 text-red-700 dark:text-red-300',
  ctx: 'text-muted-foreground',
  hunk: 'text-primary/80',
  meta: 'text-muted-foreground/70',
};
const MARK: Record<DiffLine['kind'], string> = { add: '+', del: '-', ctx: ' ', hunk: '', meta: '' };

/** A diff as the person will see it in a pull request: green added, red removed. */
export function DiffPanel({ title, lines, maxHeight = 'max-h-64' }: { title?: string; lines: DiffLine[]; maxHeight?: string }) {
  const { added, removed } = countChanges(lines);
  return (
    <figure className="overflow-hidden rounded border border-border bg-background/70" aria-label={title ?? 'Changes'}>
      <figcaption className="flex items-center justify-between gap-2 border-b border-border px-2 py-1 text-[11px]">
        <span className="min-w-0 truncate font-mono font-semibold text-foreground">{title ?? 'Changes'}</span>
        <span className="shrink-0 font-mono">
          <span className="text-emerald-600 dark:text-emerald-400">+{added}</span>{' '}
          <span className="text-red-600 dark:text-red-400">-{removed}</span>
        </span>
      </figcaption>
      <pre className={cn('overflow-auto py-1 font-mono text-[11px] leading-[1.45]', maxHeight)}>
        {lines.map((l, i) => (
          <div key={i} className={cn('flex whitespace-pre px-2', ROW[l.kind])}>
            <span className="w-3 shrink-0 select-none">{MARK[l.kind]}</span>
            <span>{l.text || ' '}</span>
          </div>
        ))}
      </pre>
    </figure>
  );
}

/** Terminal-style output, for test runs. */
export function TerminalPanel({
  title,
  text,
  ok,
  footer,
}: {
  title: string;
  text: string;
  ok?: boolean;
  footer?: string;
}) {
  return (
    <figure className="overflow-hidden rounded border border-border bg-zinc-950" aria-label={title}>
      <figcaption className="flex items-center justify-between gap-2 border-b border-zinc-800 px-2 py-1 font-mono text-[11px] text-zinc-400">
        <span className="min-w-0 truncate">
          <span className="text-zinc-500">$ </span>
          {title}
        </span>
        {ok !== undefined && (
          <span className={cn('shrink-0 font-semibold', ok ? 'text-emerald-400' : 'text-red-400')}>
            {ok ? 'passed' : 'failed'}
          </span>
        )}
      </figcaption>
      <pre className="max-h-56 overflow-auto whitespace-pre px-2 py-1.5 font-mono text-[11px] leading-[1.45] text-zinc-200">
        {text.trim() || '(no output)'}
      </pre>
      {footer && <div className="border-t border-zinc-800 px-2 py-1 font-mono text-[10px] text-zinc-500">{footer}</div>}
    </figure>
  );
}
