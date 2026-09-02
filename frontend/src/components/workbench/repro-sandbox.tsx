'use client';

import * as React from 'react';
import { ReproSnippet } from '@/types/triage';
import { CodeBlock } from './code-block';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/toast';
import { Terminal, Copy, Check, AlertOctagon, Play } from 'lucide-react';

interface ReproSandboxProps {
  reproduction: ReproSnippet | null;
}

export function ReproSandbox({ reproduction }: ReproSandboxProps) {
  const { toast } = useToast();
  const [copiedCmd, setCopiedCmd] = React.useState(false);
  const [copiedScript, setCopiedScript] = React.useState(false);

  if (!reproduction) {
    return (
      <div className="rounded-2xl border border-border bg-card/40 p-8 text-center text-xs text-muted-foreground font-mono space-y-2">
        <Terminal className="h-6 w-6 text-muted-foreground mx-auto" />
        <p>No automated reproduction script generated for this issue yet.</p>
      </div>
    );
  }

  const handleCopyCommand = async () => {
    try {
      await navigator.clipboard.writeText(reproduction.runCommand);
      setCopiedCmd(true);
      toast({
        title: 'Command Copied',
        description: reproduction.runCommand,
        type: 'success',
      });
      setTimeout(() => setCopiedCmd(false), 2000);
    } catch {
      // fallback
    }
  };

  const handleCopyScript = async () => {
    try {
      await navigator.clipboard.writeText(reproduction.code);
      setCopiedScript(true);
      toast({
        title: 'Repro Script Copied',
        description: 'Minimal reproduction script copied to clipboard.',
        type: 'success',
      });
      setTimeout(() => setCopiedScript(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs text-foreground">
      {/* 1. CLI Execution Command Card */}
      <div className="rounded-2xl border border-accent/30 bg-gradient-to-br from-accent/20 via-card/60 to-background p-4 sm:p-5 shadow-xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold text-foreground">
            <span className="flex items-center justify-center h-6 w-6 rounded-lg bg-accent/20 text-accent">
              <Terminal className="h-3.5 w-3.5" />
            </span>
            <span>CLI Test Execution Command</span>
          </div>
          <Badge variant="outline" className="text-[10px] text-accent border-accent/40 uppercase font-bold">
            {reproduction.language}
          </Badge>
        </div>

        <div className="flex items-center justify-between gap-3 bg-background p-3 rounded-xl border border-border shadow-inner">
          <code className="text-primary font-bold truncate flex-1 text-xs sm:text-sm">
            $ {reproduction.runCommand}
          </code>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyCommand}
            className="h-7 text-[11px] gap-1 text-foreground border-border bg-card hover:bg-secondary shrink-0"
          >
            {copiedCmd ? <Check className="h-3 w-3 text-primary" /> : <Copy className="h-3 w-3" />}
            <span>{copiedCmd ? 'Copied' : 'Copy'}</span>
          </Button>
        </div>
      </div>

      {/* 2. Minimal Bug Reproduction Script */}
      <div className="rounded-2xl border border-border bg-background p-4 sm:p-5 space-y-3 shadow-xl">
        <div className="flex items-center justify-between border-b border-border/80 pb-3">
          <div className="flex items-center gap-2 text-xs font-bold text-foreground">
            <span className="flex items-center justify-center h-6 w-6 rounded-lg bg-card border border-border text-muted-foreground">
              <Play className="h-3.5 w-3.5 text-primary" />
            </span>
            <span>Minimal Bug Reproduction Script</span>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyScript}
            className="h-7 text-[11px] gap-1 text-foreground border-border bg-card hover:bg-secondary shrink-0"
          >
            {copiedScript ? <Check className="h-3 w-3 text-primary" /> : <Copy className="h-3 w-3" />}
            <span>{copiedScript ? 'Copied Script' : 'Copy Script'}</span>
          </Button>
        </div>

        <CodeBlock
          code={reproduction.code}
          language={reproduction.language}
          filename={`repro.${reproduction.language === 'python' ? 'py' : reproduction.language === 'typescript' ? 'ts' : 'sh'}`}
        />
      </div>

      {/* 3. Expected Failure Callout */}
      {reproduction.expectedFailure && (
        <div className="rounded-2xl border border-destructive/30 bg-gradient-to-br from-destructive/20 via-card/60 to-background p-4 sm:p-5 shadow-xl space-y-2.5">
          <div className="flex items-center gap-2 text-destructive font-bold text-xs">
            <AlertOctagon className="h-4 w-4 shrink-0" />
            <span>Expected Failure / Error Assertion</span>
          </div>
          <div className="p-3 bg-background rounded-xl border border-border">
            <code className="text-destructive text-xs block leading-relaxed font-sans">
              {reproduction.expectedFailure}
            </code>
          </div>
        </div>
      )}
    </div>
  );
}
