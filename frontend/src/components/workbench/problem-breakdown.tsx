'use client';

import * as React from 'react';
import { TriageReport } from '@/types/triage';
import { Issue } from '@/types/issue';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toast';
import {
  Sparkles,
  CheckCircle2,
  Layers,
  FileText,
  GitBranch,
  ShieldCheck,
  Copy,
  Check,
  Cpu,
} from 'lucide-react';

interface ProblemBreakdownProps {
  issue: Issue;
  report: TriageReport | null;
}

export function ProblemBreakdown({ issue, report }: ProblemBreakdownProps) {
  const { toast } = useToast();
  const [copiedBranch, setCopiedBranch] = React.useState(false);
  const [copiedTitle, setCopiedTitle] = React.useState(false);

  const branchName = report?.branchingConvention || `fix/issue-${issue.githubIssueNumber}`;
  const prTitle = report?.suggestedPrTitle || `fix: resolve issue #${issue.githubIssueNumber}`;

  // Provenance: was this a real LLM enhancement, or the deterministic AST floor?
  const enhanced = Boolean(report?.llmEnhanced);
  const provider = report?.provider;
  const confidencePct = Math.round((report?.confidenceScore ?? 0) * 100);
  const groundedFiles = report?.groundedFiles ?? [];

  const handleCopy = async (text: string, type: 'branch' | 'title') => {
    try {
      await navigator.clipboard.writeText(text);
      if (type === 'branch') {
        setCopiedBranch(true);
        setTimeout(() => setCopiedBranch(false), 2000);
      } else {
        setCopiedTitle(true);
        setTimeout(() => setCopiedTitle(false), 2000);
      }
      toast({
        title: 'Copied to Clipboard',
        description: text,
        type: 'success',
      });
    } catch {
      // fallback
    }
  };

  // Safe guidelines normalization
  const guidelines: string[] = React.useMemo(() => {
    const raw: any = report?.contributingGuidelinesSummary;
    if (Array.isArray(raw)) {
      return raw;
    }
    if (typeof raw === 'string') {
      return raw
        .split('\n')
        .map((l: string) => l.replace(/^[-*#\s]+/, '').trim())
        .filter((l: string) => l.length > 3);
    }
    return [
      'Follow Conventional Commits specification for PR title and commit messages',
      'Add unit tests covering both positive and boundary failure conditions',
      'Pass all repository linters and typechecks before PR submission',
    ];
  }, [report?.contributingGuidelinesSummary]);

  // Real subsystems only — no fabricated defaults. Empty on the deterministic AST path.
  const subsystems: string[] = React.useMemo(() => {
    return Array.isArray(report?.affectedSubsystems) ? report.affectedSubsystems : [];
  }, [report?.affectedSubsystems]);

  return (
    <div className="space-y-4 font-mono text-xs text-foreground">
      {/* 1. AI Diagnostic & Root Cause Card */}
      <div className="rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/20 via-card/60 to-background p-5 shadow-xl space-y-3.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-foreground font-bold text-sm">
            <span className="flex items-center justify-center h-6 w-6 rounded-lg bg-primary/20 text-primary">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <span>AI Diagnostic & Root Cause Breakdown</span>
          </div>
          <Badge variant="emerald" className="text-[11px] font-bold px-2.5 py-0.5 shadow-sm shrink-0">
            {confidencePct}% Confidence
          </Badge>
        </div>

        {/* Provenance — honest about whether a real model ran or this is the deterministic floor */}
        <div className="flex items-center gap-1.5">
          <span
            className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${
              enhanced
                ? 'border-primary/40 bg-primary/10 text-primary'
                : 'border-border bg-card text-muted-foreground'
            }`}
          >
            {enhanced ? <Sparkles className="h-3 w-3" /> : <Cpu className="h-3 w-3" />}
            {enhanced ? `AI-enhanced${provider ? ` · ${provider}` : ''}` : 'Deterministic AST'}
          </span>
        </div>

        <p className="text-xs sm:text-sm text-foreground leading-relaxed font-sans font-normal tracking-wide">
          {report?.rootCauseAnalysis ||
            `Issue involves behavioral edge-case reported in '${issue.title}'. Automated triage isolated candidate source files and structural reproduction steps.`}
        </p>

        <div className="flex items-center gap-2 pt-1 border-t border-border/80 text-[11px] text-muted-foreground">
          <ShieldCheck className="h-3.5 w-3.5 text-primary shrink-0" />
          <span>
            {enhanced
              ? `Semantic analysis via ${provider ?? 'LLM'} over AST-localized candidate files`
              : 'Localized deterministically from stack traces & AST symbols'}
          </span>
        </div>

        {enhanced && groundedFiles.length > 0 && (
          <div className="flex items-start gap-2 text-[11px] text-primary/90">
            <FileText className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
            <span>
              Grounded in real source:{' '}
              <span className="font-semibold text-primary">{groundedFiles.join(', ')}</span>
            </span>
          </div>
        )}
      </div>

      {/* 2. Affected Subsystems & Blast Radius */}
      <div className="rounded-2xl border border-accent/30 bg-gradient-to-br from-accent/20 via-card/60 to-background p-5 shadow-xl space-y-3">
        <div className="flex items-center gap-2 text-foreground font-bold text-sm">
          <span className="flex items-center justify-center h-6 w-6 rounded-lg bg-accent/20 text-accent">
            <Layers className="h-3.5 w-3.5" />
          </span>
          <span>Affected Subsystems & Blast Radius</span>
        </div>

        {subsystems.length > 0 ? (
          <div className="flex flex-wrap gap-2 pt-1">
            {subsystems.map((sub) => (
              <span
                key={sub}
                className="inline-flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs text-accent font-semibold shadow-sm"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                <span>{sub}</span>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-[11px] text-muted-foreground pt-1 font-sans leading-relaxed">
            Subsystem mapping is produced by AI-enhanced triage. This report used deterministic AST
            localization — the localized files below trace the blast radius.
          </p>
        )}
      </div>

      {/* 3. Upstream CONTRIBUTING Guidelines */}
      <div className="rounded-2xl border border-accent/30 bg-gradient-to-br from-accent/20 via-card/60 to-background p-5 shadow-xl space-y-3.5">
        <div className="flex items-center gap-2 text-foreground font-bold text-sm">
          <span className="flex items-center justify-center h-6 w-6 rounded-lg bg-accent/20 text-accent">
            <FileText className="h-3.5 w-3.5" />
          </span>
          <span>Upstream CONTRIBUTING.md Guidelines</span>
        </div>

        <div className="space-y-2 pt-1">
          {guidelines.map((guide, i) => (
            <div
              key={i}
              className="flex items-start gap-2.5 p-2.5 rounded-xl bg-card/80 border border-border/80 text-xs text-foreground"
            >
              <CheckCircle2 className="h-4 w-4 text-accent shrink-0 mt-0.5" />
              <span className="leading-relaxed font-sans">{guide}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Recommended Branch & PR Formatting */}
      <div className="rounded-2xl border border-bounty-gold/30 bg-gradient-to-br from-bounty-gold/20 via-card/60 to-background p-5 shadow-xl space-y-3.5">
        <div className="flex items-center gap-2 text-foreground font-bold text-sm">
          <span className="flex items-center justify-center h-6 w-6 rounded-lg bg-bounty-gold/20 text-bounty-gold">
            <GitBranch className="h-3.5 w-3.5" />
          </span>
          <span>Recommended Branch & PR Formatting</span>
        </div>

        <div className="space-y-2.5 pt-1">
          {/* Branch Command Card */}
          <div className="flex items-center justify-between gap-3 bg-background p-3 rounded-xl border border-border shadow-inner">
            <div className="truncate">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider block font-bold">
                Git Checkout Branch
              </span>
              <code className="text-xs text-primary font-bold block truncate">
                git checkout -b {branchName}
              </code>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleCopy(`git checkout -b ${branchName}`, 'branch')}
              className="h-7 text-[11px] gap-1 text-foreground border-border bg-card hover:bg-secondary shrink-0"
            >
              {copiedBranch ? <Check className="h-3 w-3 text-primary" /> : <Copy className="h-3 w-3" />}
              <span>{copiedBranch ? 'Copied' : 'Copy'}</span>
            </Button>
          </div>

          {/* Suggested PR Title Card */}
          <div className="flex items-center justify-between gap-3 bg-background p-3 rounded-xl border border-border shadow-inner">
            <div className="truncate">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider block font-bold">
                Conventional PR Title
              </span>
              <code className="text-xs text-foreground font-bold block truncate">
                {prTitle}
              </code>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleCopy(prTitle, 'title')}
              className="h-7 text-[11px] gap-1 text-foreground border-border bg-card hover:bg-secondary shrink-0"
            >
              {copiedTitle ? <Check className="h-3 w-3 text-primary" /> : <Copy className="h-3 w-3" />}
              <span>{copiedTitle ? 'Copied' : 'Copy'}</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
