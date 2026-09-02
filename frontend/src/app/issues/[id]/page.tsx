import { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { generateIssueMetadata } from '@/lib/seo-config';
import { IssueJsonLd } from '@/components/seo/json-ld';
import { ProblemBreakdown } from '@/components/workbench/problem-breakdown';
import { FileLocalizer } from '@/components/workbench/file-localizer';
import { ReproSandbox } from '@/components/workbench/repro-sandbox';
import { FixChecklist } from '@/components/workbench/fix-checklist';
import { RoiCalculatorWidget } from '@/components/workbench/roi-calculator-widget';
import { Button } from '@/components/ui/button';
import { getDomainInfo, getDifficultyInfo, getRoiTier, formatTimeMinutes } from '@/lib/utils';
import {
  ChevronLeft,
  ExternalLink,
  Coins,
  Clock,
  Star,
} from 'lucide-react';

interface IssuePageProps {
  params: { id: string };
}

export async function generateMetadata({ params }: IssuePageProps): Promise<Metadata> {
  const decodedId = decodeURIComponent(params.id);
  const issue = await apiClient.getIssue(decodedId);
  if (!issue) {
    return {
      title: 'Issue Not Found — GitScout Terminal',
    };
  }
  return generateIssueMetadata(issue);
}

export default async function IssueWorkbenchPage({ params }: IssuePageProps) {
  const decodedId = decodeURIComponent(params.id);
  const issue = await apiClient.getIssue(decodedId);

  if (!issue) {
    notFound();
  }

  const report = await apiClient.getTriage(issue.id);
  const domainInfo = getDomainInfo(issue.domain);
  const diffInfo = getDifficultyInfo(issue.difficulty);
  const roiTier = getRoiTier(issue.hourlyRoiUsd);

  return (
    <div className="container py-8 max-w-5xl space-y-6 font-mono text-foreground">
      {/* Schema.org Structured Data */}
      <IssueJsonLd issue={issue} />

      {/* Back Navigation Bar */}
      <div className="flex items-center justify-between">
        <Link href="/">
          <Button variant="outline" size="sm" className="gap-1.5 text-xs text-muted-foreground hover:text-foreground">
            <ChevronLeft className="h-4 w-4" />
            <span>Back to Issue Terminal</span>
          </Button>
        </Link>

        <div className="flex items-center gap-2">
          {issue.bounty && issue.bounty.sourceUrl && (
            <a
              href={issue.bounty.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="glow" size="sm" className="gap-1.5 text-xs">
                <Coins className="h-3.5 w-3.5" />
                <span>Claim ${issue.bounty.amountUsd} Bounty</span>
              </Button>
            </a>
          )}
          <a
            href={issue.issueUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="terminal" size="sm" className="gap-1.5 text-xs">
              <span>View on GitHub</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </Button>
          </a>
        </div>
      </div>

      {/* Main Header Banner */}
      <div className="rounded-xl border border-border bg-background/90 p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">{issue.repository.owner} /</span>
            <span className="font-bold text-foreground">{issue.repository.name}</span>
            <span className="text-primary font-bold">#{issue.githubIssueNumber}</span>
          </div>

          <div className="flex items-center gap-1">
            <Star className="h-3.5 w-3.5 text-bounty-gold fill-bounty-gold" />
            <span>{(issue.repository.stars / 1000).toFixed(1)}k stars</span>
          </div>
        </div>

        <h1 className="text-lg sm:text-xl font-bold text-foreground leading-snug">
          {issue.title}
        </h1>

        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
          <span className={`px-2 py-0.5 rounded border ${domainInfo.borderClass} ${domainInfo.bgClass} ${domainInfo.textClass} font-semibold`}>
            {domainInfo.label}
          </span>
          <span className={`px-2 py-0.5 rounded border ${diffInfo.badgeClass}`}>
            {diffInfo.label}
          </span>
          <span className="flex items-center gap-1 text-muted-foreground bg-card px-2 py-0.5 rounded border border-border">
            <Clock className="h-3 w-3 text-muted-foreground" />
            <span>Est. ~{formatTimeMinutes(issue.estimatedMinutesToSolve)}</span>
          </span>

          {issue.bounty && issue.bounty.isFunded && (
            <span className="flex items-center gap-1 text-bounty-gold font-bold bg-bounty-gold/15 px-2 py-0.5 rounded border border-bounty-gold/40">
              <Coins className="h-3.5 w-3.5" />
              <span>${issue.bounty.amountUsd} Bounty</span>
            </span>
          )}

          {issue.hourlyRoiUsd && issue.hourlyRoiUsd > 0 && (
            <span className={`flex items-center gap-1 px-2 py-0.5 rounded border font-bold ${roiTier.badgeClass}`}>
              <span>{roiTier.emoji}</span>
              <span>${Math.round(issue.hourlyRoiUsd)}/hr ROI</span>
            </span>
          )}
        </div>
      </div>

      {/* Grid of Triage Intelligence Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Root Cause + AST Files */}
        <div className="space-y-6">
          <ProblemBreakdown issue={issue} report={report} />
          <FileLocalizer localizedFiles={report?.localizedFiles || []} />
        </div>

        {/* Right Column: Repro Sandbox + Fix Checklist + ROI Widget */}
        <div className="space-y-6">
          <ReproSandbox reproduction={report?.reproduction || null} />
          <FixChecklist
            issueId={issue.id}
            fixBlueprint={report?.fixBlueprint || []}
            suggestedPrTitle={report?.suggestedPrTitle}
          />
          {issue.bounty && issue.bounty.isFunded && (
            <RoiCalculatorWidget
              bountyAmountUsd={issue.bounty.amountUsd}
              initialMinutes={issue.estimatedMinutesToSolve}
            />
          )}
        </div>
      </div>
    </div>
  );
}
