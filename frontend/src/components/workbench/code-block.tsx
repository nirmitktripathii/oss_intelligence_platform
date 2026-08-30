'use client';

import * as React from 'react';
import { Copy, Check } from 'lucide-react';
import { useToast } from '@/components/ui/toast';

interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  showLineNumbers?: boolean;
}

export function CodeBlock({
  code,
  language = 'bash',
  filename,
  showLineNumbers = true,
}: CodeBlockProps) {
  const { toast } = useToast();
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      toast({ title: 'Code Copied', description: 'Snippet copied to clipboard.', type: 'success' });
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  const lines = code.split('\n');

  return (
    <div className="relative my-2 rounded-xl border border-zinc-800 bg-zinc-950 font-mono text-xs overflow-hidden shadow-xl">
      {/* Mac-style Window Titlebar */}
      <div className="flex items-center justify-between border-b border-zinc-800/80 bg-zinc-900/80 px-3.5 py-2 text-[11px] text-zinc-400">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-green-500/80" />
          </div>
          <span className="font-bold text-zinc-300 pl-1">
            {filename || language.toUpperCase()}
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-300 hover:text-emerald-400 hover:bg-zinc-700 transition-all text-[10px]"
        >
          {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {/* Code Area */}
      <div className="overflow-x-auto p-4 text-zinc-200 leading-relaxed font-mono">
        <pre className="flex text-xs">
          {showLineNumbers && (
            <div className="select-none pr-4 text-right text-zinc-600 font-mono select-none">
              {lines.map((_, i) => (
                <div key={i}>{i + 1}</div>
              ))}
            </div>
          )}
          <code className="flex-1 whitespace-pre">{code}</code>
        </pre>
      </div>
    </div>
  );
}
