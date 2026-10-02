'use client';

import * as React from 'react';
import type { LiveStep } from '@/hooks/use-agent-session';
import type { MissionStep } from '@/types/agent';
import { parseUnified, textChange, type DiffLine } from '@/lib/diff';
import { DiffPanel } from '@/components/alexa/change-panels';

/** "gitci.edit_file" -> "edit_file" */
export const baseTool = (tool: string): string => tool.slice(tool.indexOf('.') + 1);

const str = (v: unknown): string => (typeof v === 'string' ? v : '');

const capped = (text: string, limit: number): string => (text.length <= limit ? text : `${text.slice(0, limit - 1).trimEnd()}…`);

/** The Telegram message `send_report` will send. Mirrors the server's template and length caps. */
export function reportText(title: string, summary: string, prUrl: string): string {
  const parts = ['Developer Mission Control report', capped(title.trim(), 120) || '(no title)'];
  if (summary.trim()) parts.push(capped(summary.trim(), 1200));
  if (prUrl.trim()) parts.push(`Draft pull request: ${prUrl.trim()}`);
  return parts.join('\n\n');
}

/** Every edit made so far in this conversation turn, as one diff: what a commit would contain. */
export function pendingChanges(history: MissionStep[], before: number): DiffLine[] {
  const lines: DiffLine[] = [];
  for (const s of history) {
    if (s.index >= before || s.status !== 'done') continue;
    const tool = baseTool(s.tool);
    if (tool === 'edit_file') {
      lines.push({ kind: 'meta', text: str(s.arguments.path) });
      lines.push(...textChange(str(s.arguments.old), str(s.arguments.new)));
    } else if (tool === 'apply_patch') {
      lines.push(...parseUnified(str(s.arguments.diff)));
    }
  }
  return lines;
}

function findArg(history: MissionStep[], tool: string, key: string, before: number): string {
  for (let i = history.length - 1; i >= 0; i--) {
    const s = history[i];
    if (s.index < before && s.status === 'done' && baseTool(s.tool) === tool) return str(s.arguments[key]);
  }
  return '';
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2 text-xs">
      <span className="w-14 shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 break-words font-medium text-foreground">{children}</span>
    </div>
  );
}

/**
 * What the person is being asked to approve, in plain terms: the repository, the branch, the
 * exact change as a diff. The raw arguments stay one click away so nothing is hidden.
 */
export function ApprovalPreview({ step, history }: { step: LiveStep; history: MissionStep[] }) {
  const tool = baseTool(step.tool);
  const a = step.arguments;
  const changes = pendingChanges(history, step.index);

  let body: React.ReactNode = null;
  switch (tool) {
    case 'sandbox_clone':
      body = (
        <>
          <Row label="Clone">{str(a.repo_url)}</Row>
          {str(a.branch) && <Row label="Resume">your saved work on {str(a.branch)}</Row>}
          <p className="text-[11px] text-muted-foreground">Into a throwaway copy on the server. Nothing is changed on GitHub.</p>
        </>
      );
      break;
    case 'delete_saved_work':
      body = (
        <>
          <Row label="Repo">{str(a.repo_url).replace('https://github.com/', '')}</Row>
          <Row label="Branch">{str(a.branch)}</Row>
          <p className="text-[11px] text-muted-foreground">
            Permanently deletes your saved, unfinished work on this branch to free space. Anything already pushed to GitHub stays there.
          </p>
        </>
      );
      break;
    case 'destroy_sandbox':
      body = a.discard ? (
        <p className="text-[11px] text-muted-foreground">
          Deletes the sandbox <span className="font-semibold">without saving</span> its unfinished work.
        </p>
      ) : null;
      break;
    case 'create_branch':
      body = <Row label="Branch">{str(a.name)}</Row>;
      break;
    case 'edit_file':
      body = (
        <DiffPanel title={str(a.path)} lines={textChange(str(a.old), str(a.new))} />
      );
      break;
    case 'apply_patch':
      body = <DiffPanel title="Patch" lines={parseUnified(str(a.diff))} />;
      break;
    case 'run_tests':
      body = (
        <>
          <Row label="Command">
            <code className="font-mono">{str(a.command) || 'pytest -q'}</code>
          </Row>
          <p className="text-[11px] text-muted-foreground">Runs the repository&apos;s own tests on the server, with a time limit.</p>
        </>
      );
      break;
    case 'commit_changes':
      body = (
        <>
          <Row label="Message">{str(a.message)}</Row>
          {changes.length > 0 ? (
            <DiffPanel title="Changes in this commit" lines={changes} />
          ) : (
            <p className="text-[11px] text-muted-foreground">Commits whatever is changed in the sandbox.</p>
          )}
        </>
      );
      break;
    case 'draft_pr': {
      const repo = findArg(history, 'sandbox_clone', 'repo_url', step.index).replace('https://github.com/', '');
      const branch =
        findArg(history, 'create_branch', 'name', step.index) || findArg(history, 'sandbox_clone', 'branch', step.index);
      body = (
        <>
          {repo && <Row label="Repo">{repo}</Row>}
          {branch && <Row label="Branch">{branch}</Row>}
          <Row label="Title">{str(a.title)}</Row>
          {str(a.body) && <Row label="Text">{str(a.body)}</Row>}
          <p className="text-[11px] text-muted-foreground">
            Pushes the branch and opens a <span className="font-semibold">draft</span> pull request. The main branch is not changed.
          </p>
          {changes.length > 0 && <DiffPanel title="Changes in this pull request" lines={changes} />}
        </>
      );
      break;
    }
    case 'send_report':
      body = (
        <>
          <Row label="To">Your linked Telegram chat</Row>
          <pre className="whitespace-pre-wrap break-words rounded border border-border bg-background/70 p-2 text-[11px] leading-relaxed text-foreground">
            {reportText(str(a.title), str(a.summary), str(a.pr_url))}
          </pre>
          <p className="text-[11px] text-muted-foreground">Plain text. It goes to the chat you linked to your account; the assistant cannot choose another.</p>
        </>
      );
      break;
    case 'send_email':
      body = (
        <>
          <Row label="To">The email address you confirmed</Row>
          <Row label="Subject">{capped(str(a.subject).trim(), 150) || '(no subject)'}</Row>
          <pre className="whitespace-pre-wrap break-words rounded border border-border bg-background/70 p-2 text-[11px] leading-relaxed text-foreground">
            {capped(str(a.body).trim(), 4000) || '(empty)'}
          </pre>
          <p className="text-[11px] text-muted-foreground">
            Plain text, one recipient. A short note saying an AI wrote it is added at the end. It goes to the address you
            confirmed; the assistant cannot choose another.
          </p>
        </>
      );
      break;
    default:
      body = null;
  }

  return (
    <div className="space-y-2">
      {body}
      <details className="text-[11px] text-muted-foreground">
        <summary className="cursor-pointer select-none hover:text-foreground">Exact arguments</summary>
        <pre className="mt-1 overflow-x-auto rounded border border-border bg-background/70 p-2">
          {JSON.stringify(step.arguments, null, 2)}
        </pre>
      </details>
    </div>
  );
}
