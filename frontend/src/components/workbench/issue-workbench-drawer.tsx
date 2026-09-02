'use client';

import * as React from 'react';
import { Issue } from '@/types/issue';
import { useTriage } from '@/hooks/use-triage';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { ProblemBreakdown } from './problem-breakdown';
import { FileLocalizer } from './file-localizer';
import { ReproSandbox } from './repro-sandbox';
import { FixChecklist } from './fix-checklist';
import { RoiCalculatorWidget } from './roi-calculator-widget';
import { ShareModal } from '@/components/modals/share-modal';
import { GraphifyModal } from '@/components/graph/graphify-modal';
import { getDomainInfo, getDifficultyInfo, getRoiTier, formatTimeMinutes } from '@/lib/utils';
import { useToast } from '@/components/ui/toast';
import {
  ExternalLink,
  Sparkles,
  Layers,
  Terminal,
  CheckSquare,
  Share2,
  Coins,
  Clock,
  GitBranch,
  Network,
  Copy,
  Check,
} from 'lucide-react';

interface IssueWorkbenchDrawerProps {
  issue: Issue | null;
  isOpen: boolean;
  onClose: () => void;
}

export function IssueWorkbenchDrawer({ issue, isOpen, onClose }: IssueWorkbenchDrawerProps) {
  const { report } = useTriage(issue?.id || null);
  const { toast } = useToast();
  const [activeTab, setActiveTab] = React.useState<'root_cause' | 'files' | 'repro' | 'fix'>('root_cause');
  const [isShareOpen, setIsShareOpen] = React.useState(false);
  const [isGraphOpen, setIsGraphOpen] = React.useState(false);
  const [targetGraphFile, setTargetGraphFile] = React.useState<string | undefined>(undefined);
  const [copiedBranch, setCopiedBranch] = React.useState(false);

  if (!issue) return null;

  const domainInfo = getDomainInfo(issue.domain);
  const diffInfo = getDifficultyInfo(issue.difficulty);
  const roiTier = getRoiTier(issue.hourlyRoiUsd);

  const handleOpenGraph = (file?: string) => {
    setTargetGraphFile(file);
    setIsGraphOpen(true);
  };

  const handleCopyBranch = async () => {
    const branchName = report?.branchingConvention || `fix/issue-${issue.githubIssueNumber}`;
    try {
      await navigator.clipboard.writeText(`git checkout -b ${branchName}`);
      setCopiedBranch(true);
      toast({
        title: 'Git Command Copied',
        description: `git checkout -b ${branchName}`,
        type: 'success',
      });
      setTimeout(() => setCopiedBranch(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <>
      <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <SheetContent
          side="right"
          className="font-mono text-foreground bg-background/98 border-l border-border/90 overflow-y-auto w-full sm:max-w-2xl md:max-w-3xl lg:max-w-4xl p-6 sm:p-8 backdrop-blur-2xl shadow-2xl space-y-6"
        >
          {/* Top Header Card */}
          <SheetHeader className="border-b border-border/80 pb-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pr-8">
              {/* Repository Breadcrumb & Issue ID */}
              <div className="flex items-center gap-2.5 truncate">
                <span className="flex items-center justify-center h-7 w-7 rounded-lg bg-card border border-border text-muted-foreground">
                  <GitBranch className="h-3.5 w-3.5 text-primary" />
                </span>
                <div className="flex items-center gap-1.5 text-sm">
                  <span className="text-muted-foreground font-medium">{issue.repository.owner}</span>
                  <span className="text-muted-foreground font-bold">/</span>
                  <span className="font-bold text-foreground">{issue.repository.name}</span>
                </div>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-primary/15 text-primary border border-primary/30 shadow-[0_0_12px_hsl(var(--primary)/0.2)]">
                  #{issue.githubIssueNumber}
                </span>
              </div>

              {/* Action Toolbar */}
              <div className="flex items-center gap-2 shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleOpenGraph()}
                  className="h-8 text-xs gap-1.5 text-accent border-accent/30 bg-accent/10 hover:bg-accent/20 transition-all"
                  title="Explore AST Knowledge Graph"
                >
                  <Network className="h-3.5 w-3.5 text-accent" />
                  <span className="hidden sm:inline">AST Graph</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs gap-1.5 text-foreground border-border bg-card/80 hover:bg-secondary transition-all"
                  onClick={() => setIsShareOpen(true)}
                  title="Share Blueprint"
                >
                  <Share2 className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="hidden sm:inline">Share</span>
                </Button>

                <a
                  href={issue.issueUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs gap-1.5 text-primary border-primary/40 bg-primary/10 hover:bg-primary/20 transition-all"
                  >
                    <span>GitHub</span>
                    <ExternalLink className="h-3 w-3" />
                  </Button>
                </a>
              </div>
            </div>

            {/* Issue Title */}
            <SheetTitle className="text-base sm:text-lg md:text-xl font-bold leading-snug text-foreground tracking-tight">
              {issue.title}
            </SheetTitle>

            {/* Telemetry & Metadata Badges */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {/* Domain Badge */}
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold ${domainInfo.borderClass} ${domainInfo.bgClass} ${domainInfo.textClass}`}
              >
                <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: domainInfo.hex }} />
                <span>{domainInfo.label}</span>
              </span>

              {/* Difficulty Badge */}
              <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border text-xs font-medium ${diffInfo.badgeClass}`}>
                <span>{diffInfo.label}</span>
              </span>

              {/* Estimated Solve Time */}
              <span className="inline-flex items-center gap-1.5 text-foreground bg-card/90 px-2.5 py-1 rounded-lg border border-border text-xs">
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                <span>~{formatTimeMinutes(issue.estimatedMinutesToSolve)} estimated</span>
              </span>

              {/* Funded Bounty Badge */}
              {issue.bounty && issue.bounty.isFunded && (
                <span className="inline-flex items-center gap-1.5 text-bounty-gold font-bold bg-bounty-gold/15 px-3 py-1 rounded-lg border border-bounty-gold/40 shadow-[0_0_12px_hsl(var(--bounty-gold)/0.2)] text-xs">
                  <Coins className="h-3.5 w-3.5 text-bounty-gold" />
                  <span>${issue.bounty.amountUsd} Bounty ({issue.bounty.source})</span>
                </span>
              )}

              {/* Hourly ROI Tier */}
              {issue.hourlyRoiUsd && issue.hourlyRoiUsd > 0 && (
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-bold text-xs ${roiTier.badgeClass}`}>
                  <span>{roiTier.emoji}</span>
                  <span>${Math.round(issue.hourlyRoiUsd)}/hr ROI</span>
                </span>
              )}
            </div>
          </SheetHeader>

          {/* Workbench Tabs Navigation */}
          <div className="space-y-5">
            <Tabs value={activeTab} onValueChange={(val: any) => setActiveTab(val)}>
              <TabsList className="grid w-full grid-cols-4 bg-card/90 border border-border p-1 rounded-xl text-xs h-11">
                <TabsTrigger
                  value="root_cause"
                  className="flex items-center justify-center gap-1.5 text-xs font-medium py-2 rounded-lg data-[state=active]:bg-secondary data-[state=active]:text-primary data-[state=active]:shadow-md transition-all"
                >
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  <span>Root Cause</span>
                </TabsTrigger>
                <TabsTrigger
                  value="files"
                  className="flex items-center justify-center gap-1.5 text-xs font-medium py-2 rounded-lg data-[state=active]:bg-secondary data-[state=active]:text-accent data-[state=active]:shadow-md transition-all"
                >
                  <Layers className="h-3.5 w-3.5 text-accent" />
                  <span>AST Files</span>
                </TabsTrigger>
                <TabsTrigger
                  value="repro"
                  className="flex items-center justify-center gap-1.5 text-xs font-medium py-2 rounded-lg data-[state=active]:bg-secondary data-[state=active]:text-accent data-[state=active]:shadow-md transition-all"
                >
                  <Terminal className="h-3.5 w-3.5 text-accent" />
                  <span>Repro</span>
                </TabsTrigger>
                <TabsTrigger
                  value="fix"
                  className="flex items-center justify-center gap-1.5 text-xs font-medium py-2 rounded-lg data-[state=active]:bg-secondary data-[state=active]:text-bounty-gold data-[state=active]:shadow-md transition-all"
                >
                  <CheckSquare className="h-3.5 w-3.5 text-bounty-gold" />
                  <span>Fix Plan</span>
                </TabsTrigger>
              </TabsList>

              {/* Tab 1: Root Cause & Diagnostics */}
              <TabsContent value="root_cause" className="pt-3">
                <ProblemBreakdown issue={issue} report={report} />
              </TabsContent>

              {/* Tab 2: AST Localized Files */}
              <TabsContent value="files" className="pt-3">
                <FileLocalizer
                  localizedFiles={report?.localizedFiles || []}
                  onOpenGraph={handleOpenGraph}
                />
              </TabsContent>

              {/* Tab 3: Minimal Repro Sandbox */}
              <TabsContent value="repro" className="pt-3">
                <ReproSandbox reproduction={report?.reproduction || null} />
              </TabsContent>

              {/* Tab 4: Fix Checklist */}
              <TabsContent value="fix" className="pt-3">
                <FixChecklist
                  issueId={issue.id}
                  fixBlueprint={report?.fixBlueprint || []}
                  suggestedPrTitle={report?.suggestedPrTitle}
                />
              </TabsContent>
            </Tabs>

            {/* Interactive Hourly ROI Simulator Widget */}
            {issue.bounty && issue.bounty.isFunded && (
              <div className="pt-2">
                <RoiCalculatorWidget
                  bountyAmountUsd={issue.bounty.amountUsd}
                  initialMinutes={issue.estimatedMinutesToSolve}
                />
              </div>
            )}
          </div>

          {/* Sticky Bottom Action Deck */}
          <div className="sticky bottom-0 z-20 -mx-6 -mb-6 sm:-mx-8 sm:-mb-8 border-t border-border/90 bg-background/95 p-4 sm:p-5 backdrop-blur-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xl">
            {/* Quick Branch Command */}
            <div className="flex items-center gap-2 text-xs text-muted-foreground truncate w-full sm:w-auto">
              <span className="text-muted-foreground font-semibold shrink-0">Branch:</span>
              <button
                onClick={handleCopyBranch}
                className="group flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-card border border-border hover:border-primary/50 transition-all truncate"
                title="Click to copy git checkout command"
              >
                <code className="text-primary font-bold truncate">
                  {report?.branchingConvention || `fix/issue-${issue.githubIssueNumber}`}
                </code>
                {copiedBranch ? (
                  <Check className="h-3 w-3 text-primary shrink-0" />
                ) : (
                  <Copy className="h-3 w-3 text-muted-foreground group-hover:text-primary shrink-0" />
                )}
              </button>
            </div>

            {/* Primary Action Buttons */}
            <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
              {issue.bounty && issue.bounty.sourceUrl && (
                <a
                  href={issue.bounty.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full sm:w-auto"
                >
                  <Button
                    variant="glow"
                    size="sm"
                    className="w-full sm:w-auto gap-1.5 text-xs font-bold bg-bounty-gold hover:bg-bounty-gold text-muted-foreground shadow-[0_0_15px_hsl(var(--bounty-gold)/0.3)]"
                  >
                    <Coins className="h-3.5 w-3.5" />
                    <span>Claim ${issue.bounty.amountUsd} on {issue.bounty.source}</span>
                  </Button>
                </a>
              )}
              <a
                href={issue.issueUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full sm:w-auto"
              >
                <Button
                  variant="terminal"
                  size="sm"
                  className="w-full sm:w-auto gap-2 text-xs font-bold text-primary-foreground bg-primary hover:bg-primary/90 shadow-[0_0_15px_hsl(var(--primary)/0.3)]"
                >
                  <span>Open on GitHub</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </Button>
              </a>
            </div>
          </div>
        </SheetContent>
      </Sheet>

      {/* Share Modal */}
      <ShareModal
        isOpen={isShareOpen}
        onClose={() => setIsShareOpen(false)}
        issue={issue}
      />

      {/* Graphify Knowledge Graph Modal */}
      <GraphifyModal
        isOpen={isGraphOpen}
        onClose={() => setIsGraphOpen(false)}
        targetFile={targetGraphFile}
      />
    </>
  );
}
