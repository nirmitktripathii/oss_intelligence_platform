'use client';

import * as React from 'react';
import { Issue } from '@/types/issue';
import { Badge } from '@/components/ui/badge';
import { getDomainInfo, getDifficultyInfo, getRoiTier, formatTimeMinutes } from '@/lib/utils';
import { Star, Clock, Coins, ArrowUpRight } from 'lucide-react';

interface IssueCardProps {
  issue: Issue;
  isSelected?: boolean;
  onSelect: (issue: Issue) => void;
}

export function IssueCard({ issue, isSelected, onSelect }: IssueCardProps) {
  const domainInfo = getDomainInfo(issue.domain);
  const diffInfo = getDifficultyInfo(issue.difficulty);
  const roiTier = getRoiTier(issue.hourlyRoiUsd);

  return (
    <div
      onClick={() => onSelect(issue)}
      className={`group relative flex flex-col justify-between rounded-xl border p-4 font-mono transition-all cursor-pointer backdrop-blur-sm ${
        isSelected
          ? 'border-primary bg-card shadow-[0_0_20px_hsl(var(--primary)/0.2)] ring-1 ring-primary'
          : 'border-border/80 bg-card/70 hover:border-primary/60 hover:bg-card hover:shadow-md'
      }`}
    >
      {/* Top Bar: Domain Pill + Bounty / ROI Badge */}
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          {/* Domain tag */}
          <div className="flex items-center gap-1.5">
            <span
              className="h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: domainInfo.hex }}
            />
            <span className="text-[11px] font-semibold tracking-wide text-foreground/80">
              {domainInfo.label}
            </span>
          </div>

          {/* Bounty or ROI Badge */}
          {issue.bounty && issue.bounty.isFunded ? (
            <div className="flex items-center gap-1.5">
              <span className="inline-flex items-center gap-1 rounded-full border border-bounty-gold/40 bg-bounty-gold/10 px-2 py-0.5 text-[11px] font-bold text-bounty-gold shadow-[0_0_8px_hsl(var(--bounty-gold)/0.2)]">
                <Coins className="h-3 w-3" />
                <span>${issue.bounty.amountUsd}</span>
              </span>
              {issue.hourlyRoiUsd && issue.hourlyRoiUsd > 0 && (
                <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-bold ${roiTier.badgeClass}`}>
                  <span>{roiTier.emoji}</span>
                  <span>${Math.round(issue.hourlyRoiUsd)}/hr</span>
                </span>
              )}
            </div>
          ) : (
            <Badge variant="outline" className="text-[10px] text-muted-foreground border-border">
              Community Issue
            </Badge>
          )}
        </div>

        {/* Repo line: Icon, name, stars, date */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5 truncate">
            <span className="text-muted-foreground/70">{issue.repository.owner}/</span>
            <span className="font-semibold text-foreground">{issue.repository.name}</span>
            <span className="text-primary font-bold">#{issue.githubIssueNumber}</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground shrink-0">
            <Star className="h-3 w-3 text-bounty-gold fill-bounty-gold" />
            <span>{(issue.repository.stars / 1000).toFixed(1)}k</span>
          </div>
        </div>

        {/* Issue Title */}
        <h3 className="text-xs font-semibold leading-snug text-foreground group-hover:text-primary transition-colors line-clamp-2">
          {issue.title}
        </h3>

        {/* Short description excerpt */}
        <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
          {issue.body || 'No description provided.'}
        </p>

        {/* Tech Stack Pills */}
        <div className="flex flex-wrap gap-1 pt-1">
          {issue.techStack.slice(0, 4).map((tech) => (
            <span
              key={tech}
              className="rounded bg-muted border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground"
            >
              {tech}
            </span>
          ))}
          {issue.techStack.length > 4 && (
            <span className="text-[10px] text-muted-foreground/60 self-center">
              +{issue.techStack.length - 4}
            </span>
          )}
        </div>
      </div>

      {/* Card Footer: Difficulty + Estimated Time + Triage Trigger */}
      <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-[11px]">
        <div className="flex items-center gap-2">
          {/* Difficulty pill */}
          <span className={`rounded px-1.5 py-0.5 border text-[10px] ${diffInfo.badgeClass}`}>
            {diffInfo.label}
          </span>

          {/* Time estimate */}
          <span className="flex items-center gap-1 text-muted-foreground text-[10px]">
            <Clock className="h-3 w-3 text-muted-foreground/70" />
            <span>~{formatTimeMinutes(issue.estimatedMinutesToSolve)}</span>
          </span>
        </div>

        <div className="flex items-center gap-1 text-primary group-hover:translate-x-0.5 transition-transform font-semibold text-xs">
          <span>Inspect</span>
          <ArrowUpRight className="h-3.5 w-3.5" />
        </div>
      </div>
    </div>
  );
}
