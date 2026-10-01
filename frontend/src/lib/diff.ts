/** Small, dependency-free diff helpers for showing the user what they are about to approve. */

export type DiffKind = 'add' | 'del' | 'ctx' | 'hunk' | 'meta';

export interface DiffLine {
  kind: DiffKind;
  text: string;
}

const CONTEXT = 2;

const splitLines = (text: string): string[] => text.replace(/\r\n/g, '\n').split('\n');

/**
 * The change `edit_file` will make: the exact old text replaced by the new text. Lines both
 * share at the start and end are trimmed to a little context, so a one-line fix does not show
 * as a whole function removed and re-added.
 */
export function textChange(oldText: string, newText: string): DiffLine[] {
  const a = splitLines(oldText);
  const b = splitLines(newText);

  let head = 0;
  while (head < a.length && head < b.length && a[head] === b[head]) head++;
  let tail = 0;
  while (tail < a.length - head && tail < b.length - head && a[a.length - 1 - tail] === b[b.length - 1 - tail]) tail++;

  const out: DiffLine[] = [];
  const ctxBefore = a.slice(Math.max(0, head - CONTEXT), head);
  if (head > ctxBefore.length) out.push({ kind: 'hunk', text: `... ${head - ctxBefore.length} unchanged line(s)` });
  for (const t of ctxBefore) out.push({ kind: 'ctx', text: t });
  for (const t of a.slice(head, a.length - tail)) out.push({ kind: 'del', text: t });
  for (const t of b.slice(head, b.length - tail)) out.push({ kind: 'add', text: t });
  const afterStart = a.length - tail;
  const ctxAfter = a.slice(afterStart, afterStart + CONTEXT);
  for (const t of ctxAfter) out.push({ kind: 'ctx', text: t });
  if (tail > ctxAfter.length) out.push({ kind: 'hunk', text: `... ${tail - ctxAfter.length} unchanged line(s)` });
  return out;
}

/** Classify the lines of a unified diff (`git diff`, or a patch the agent wants to apply). */
export function parseUnified(diff: string): DiffLine[] {
  const out: DiffLine[] = [];
  for (const line of splitLines(diff)) {
    if (line === '') continue;
    if (line.startsWith('@@')) out.push({ kind: 'hunk', text: line });
    else if (/^(diff --git|index |--- |\+\+\+ |new file|deleted file|similarity|rename )/.test(line)) {
      out.push({ kind: 'meta', text: line });
    } else if (line.startsWith('+')) out.push({ kind: 'add', text: line.slice(1) });
    else if (line.startsWith('-')) out.push({ kind: 'del', text: line.slice(1) });
    else if (line.startsWith('\\')) out.push({ kind: 'meta', text: line });
    else out.push({ kind: 'ctx', text: line.startsWith(' ') ? line.slice(1) : line });
  }
  return out;
}

/** Files named in a unified diff, in order, without duplicates. */
export function diffFiles(diff: string): string[] {
  const files: string[] = [];
  const pattern = /^\+\+\+ (?:b\/)?(.+?)(?:\t.*)?$/gm;
  let m: RegExpExecArray | null;
  while ((m = pattern.exec(diff)) !== null) {
    if (m[1] !== '/dev/null' && !files.includes(m[1])) files.push(m[1]);
  }
  return files;
}

export function countChanges(lines: DiffLine[]): { added: number; removed: number } {
  let added = 0;
  let removed = 0;
  for (const l of lines) {
    if (l.kind === 'add') added++;
    else if (l.kind === 'del') removed++;
  }
  return { added, removed };
}
