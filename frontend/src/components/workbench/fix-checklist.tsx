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
    <div className="space-y-4 font-mono text-xs text-zinc-300">
      {/* 1. Progress Bar Header */}
      <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-950/20 via-zinc-900/60 to-zinc-950 p-4 sm:p-5 shadow-xl space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-zinc-100 flex items-center gap-2">
            <span className="flex items-center justify-center h-6 w-6 rounded-lg bg-emerald-500/20 text-emerald-400">
              <GitPullRequest className="h-3.5 w-3.5" />
            </span>
            <span>PR Readiness Progress</span>
          </span>
          <span className="text-emerald-400 font-extrabold text-xs sm:text-sm">
            {completedSteps.length} of {safeBlueprint.length} Completed ({progressPercent}%)
          </span>
        </div>

        <div className="h-2.5 w-full rounded-full bg-zinc-900 border border-zinc-800 overflow-hidden p-0.5">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all duration-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* 2. Conventional PR Title Banner */}
      {suggestedPrTitle && (
        <div className="flex items-center justify-between gap-3 bg-zinc-950 p-3.5 rounded-2xl border border-zinc-800 shadow-xl">
          <div className="truncate">
            <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider block">
              Conventional PR Title
            </span>
            <span className="text-xs sm:text-sm text-zinc-100 font-bold truncate block">
              {suggestedPrTitle}
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyPrTitle}
            className="h-7 text-[11px] gap-1 text-zinc-300 border-zinc-700 bg-zinc-900 hover:bg-zinc-800 shrink-0"
          >
            {copiedTitle ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
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
                  ? 'border-emerald-500/40 bg-emerald-950/10 opacity-90 shadow-sm'
                  : 'border-zinc-800 bg-zinc-950/80 hover:border-zinc-700 shadow-lg'
              }`}
            >
              <div className="flex items-start gap-3">
                <button
                  type="button"
                  onClick={() => toggleStep(step.stepNumber)}
                  className="mt-0.5 text-zinc-500 hover:text-emerald-400 transition-colors shrink-0"
                >
                  {isDone ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                  ) : (
                    <Circle className="h-5 w-5 text-zinc-600 hover:text-zinc-400" />
                  )}
                </button>

                <div className="flex-1 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span
                      className={`text-xs sm:text-sm font-bold ${
                        isDone ? 'line-through text-zinc-500' : 'text-zinc-100'
                      }`}
                    >
                      Step {step.stepNumber}: {step.title}
                    </span>

                    {step.guidelineRule && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-300 border border-blue-500/30">
                        <ShieldCheck className="h-3 w-3" />
                        <span>{step.guidelineRule}</span>
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-zinc-300 font-sans leading-relaxed">
                    {step.description}
                  </p>

                  {step.codeSnippet && (
                    <div className="pt-1">
                      <CodeBlock code={step.codeSnippet} language="typescript" />
                    </div>
                  )}

                  {step.validationCommand && (
                    <div className="flex items-center gap-2 bg-zinc-900/90 p-2.5 rounded-xl border border-zinc-800 text-[11px] text-zinc-400">
                      <Terminal className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                      <span className="font-semibold text-zinc-500">Verify:</span>
                      <code className="text-emerald-400 font-bold truncate">
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
