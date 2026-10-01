import * as React from 'react';

/**
 * Renders the small markdown subset the planner emits (headings, lists, fenced code, bold,
 * inline code, links). Builds React elements only, never HTML strings, because the text comes
 * from a model that has read untrusted issue content. Links are limited to http(s).
 */

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)\s]+\))/g;

function inline(text: string, keyBase: string): React.ReactNode[] {
  return text.split(INLINE).map((part, i) => {
    const key = `${keyBase}-${i}`;
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={key} className="text-foreground font-semibold">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code key={key} className="rounded bg-muted px-1 py-0.5 text-[0.85em] text-primary">
          {part.slice(1, -1)}
        </code>
      );
    }
    const link = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(part);
    if (link && /^https?:\/\//i.test(link[2])) {
      return (
        <a
          key={key}
          href={link[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent underline underline-offset-2 hover:text-primary"
        >
          {link[1]}
        </a>
      );
    }
    return part;
  });
}

export function MiniMarkdown({ source }: { source: string }) {
  const lines = source.replace(/\r\n/g, '\n').split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const key = `b${i}`;

    if (line.trimStart().startsWith('```')) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trimStart().startsWith('```')) code.push(lines[i++]);
      i++; // closing fence
      blocks.push(
        <pre key={key} className="overflow-x-auto rounded-md border border-border bg-background/70 p-3 text-xs">
          <code>{code.join('\n')}</code>
        </pre>,
      );
      continue;
    }

    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    if (heading) {
      blocks.push(
        <h4 key={key} className="pt-1 text-sm font-bold text-foreground">
          {inline(heading[2], key)}
        </h4>,
      );
      i++;
      continue;
    }

    if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const items: React.ReactNode[] = [];
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
        items.push(<li key={`${key}-${i}`}>{inline(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, ''), `${key}-${i}`)}</li>);
        i++;
      }
      const Tag = ordered ? 'ol' : 'ul';
      blocks.push(
        <Tag key={key} className={`space-y-1 pl-5 ${ordered ? 'list-decimal' : 'list-disc'} marker:text-muted-foreground`}>
          {items}
        </Tag>,
      );
      continue;
    }

    if (line.trim() === '') {
      i++;
      continue;
    }

    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].trimStart().startsWith('```') &&
      !/^(#{1,4})\s+/.test(lines[i]) &&
      !/^\s*([-*]|\d+\.)\s+/.test(lines[i])
    ) {
      para.push(lines[i++]);
    }
    blocks.push(<p key={key}>{inline(para.join(' '), key)}</p>);
  }

  return <div className="space-y-2 text-sm leading-relaxed text-muted-foreground">{blocks}</div>;
}
