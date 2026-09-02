'use client';

import * as React from 'react';
import { FixStep } from '@/types/triage';
import { useLocalStorage } from '@/hooks/use-local-storage';
import { CodeBlock } from './code-block';
import { Button } from '@/components/ui/button';
import { CheckCircle2, Circle, Copy, Check, GitPullRequest, ShieldCheck, Terminal } from 'lucide-react';
import { useToast } from '@/components/ui/toast';

interface FixChecklistProps {
  issueId: string;
  fixBlueprint: FixStep[];
  suggestedPrTitle?: string;
}

export function FixChecklist({ issueId, fixBlueprint, suggestedPrTitle }: FixChecklistProps) {
  const safeBlueprint = React.useMemo(
    () => (Array.isArray(fixBlueprint) ? fixBlueprint : []),
    [fixBlueprint]
  );
  const { toast } = useToast();
  const [completedSteps, setCompletedSteps] = useLocalStorage<number[]>(
    `gitscout_checklist_${issueId}`,
    []
  );
  const [copiedTitle, setCopiedTitle] = React.useState(false);

  const toggleStep = (stepNumber: number) => {
    setCompletedSteps((prev) =>
      prev.includes(stepNumber) ? prev.filter((s) => s !== stepNumber) : [...prev, stepNumber]
    );
  };

  const handleCopyPrTitle = async () => {
    if (!suggestedPrTitle) return;
    try {
      await navigator.clipboard.writeText(suggestedPrTitle);
      setCopiedTitle(true);
      toast({
        title: 'PR Title Copied',
        description: suggestedPrTitle,
        type: 'success',
      });
      setTimeout(() => setCopiedTitle(false), 2000);
    } catch {
      // fallback
    }
  };

  const progressPercent =
    safeBlueprint.length > 0
      ? Math.round((completedSteps.length / safeBlueprint.length) * 100)
      : 0;

  return (
    <div className="space-y-4 font-mono text-xs text-foreground">
      {/* 1. Progress Bar Header */}
      <div className="rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/20 via-card/60 to-background p-4 sm:p-5 shadow-xl space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-foreground flex items-center gap-2">
            <span className="flex items-center justify-center h-6 w-6 rounded-lg bg-primary/20 text-primary">
              <GitPullRequest className="h-3.5 w-3.5" />
            </span>
            <span>PR Readiness Progress</span>
          </span>
          <span className="text-primary font-extrabold text-xs sm:text-sm">
            {completedSteps.length} of {safeBlueprint.length} Completed ({progressPercent}%)
          </span>
        </div>

        <div className="h-2.5 w-full rounded-full bg-card border border-border overflow-hidden p-0.5">
          <div
            className="h-full bg-gradient-to-r from-primary to-primary rounded-full transition-all duration-500 shadow-[0_0_10px_hsl(var(--primary)/0.5)]"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* 2. Conventional PR Title Banner */}
      {suggestedPrTitle && (
        <div className="flex items-center justify-between gap-3 bg-background p-3.5 rounded-2xl border border-border shadow-xl">
          <div className="truncate">
            <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider block">
              Conventional PR Title
            </span>
            <span className="text-xs sm:text-sm text-foreground font-bold truncate block">
              {suggestedPrTitle}
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyPrTitle}
            className="h-7 text-[11px] gap-1 text-foreground border-border bg-card hover:bg-secondary shrink-0"
          >
            {copiedTitle ? <Check className="h-3 w-3 text-primary" /> : <Copy className="h-3 w-3" />}
            <span>{copiedTitle ? 'Copied' : 'Copy Title'}</span>
          </Button>
        </div>
      )}

      {/* 3. Step-by-Step Checklist Cards */}
      <div className="space-y-3">
        {safeBlueprint.map((step) => {
          const isDone = completedSteps.includes(step.stepNumber);

          return (
            <div
              key={step.stepNumber}
              className={`rounded-2xl border p-4 sm:p-5 transition-all ${
                isDone
                  ? 'border-primary/40 bg-primary/10 opacity-90 shadow-sm'
                  : 'border-border bg-background/80 hover:border-border shadow-lg'
              }`}
            >
              <div className="flex items-start gap-3">
                <button
                  type="button"
                  onClick={() => toggleStep(step.stepNumber)}
                  className="mt-0.5 text-muted-foreground hover:text-primary transition-colors shrink-0"
                >
                  {isDone ? (
                    <CheckCircle2 className="h-5 w-5 text-primary" />
                  ) : (
                    <Circle className="h-5 w-5 text-muted-foreground hover:text-muted-foreground" />
                  )}
                </button>

                <div className="flex-1 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span
                      className={`text-xs sm:text-sm font-bold ${
                        isDone ? 'line-through text-muted-foreground' : 'text-foreground'
                      }`}
                    >
                      Step {step.stepNumber}: {step.title}
                    </span>

                    {step.guidelineRule && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-accent/10 text-accent border border-accent/30">
                        <ShieldCheck className="h-3 w-3" />
                        <span>{step.guidelineRule}</span>
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-foreground font-sans leading-relaxed">
                    {step.description}
                  </p>

                  {step.codeSnippet && (
                    <div className="pt-1">
                      <CodeBlock code={step.codeSnippet} language="typescript" />
                    </div>
                  )}

                  {step.validationCommand && (
                    <div className="flex items-center gap-2 bg-card/90 p-2.5 rounded-xl border border-border text-[11px] text-muted-foreground">
                      <Terminal className="h-3.5 w-3.5 text-primary shrink-0" />
                      <span className="font-semibold text-muted-foreground">Verify:</span>
                      <code className="text-primary font-bold truncate">
                        $ {step.validationCommand}
                      </code>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
