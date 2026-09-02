'use client';

import * as React from 'react';
import { Issue } from '@/types/issue';
import { formatTimeMinutes, getRoiTier } from '@/lib/utils';
import { Coins, ArrowRight } from 'lucide-react';

interface IssueCompactProps {
  issues: Issue[];
  selectedIndex: number;
  onSelect: (issue: Issue) => void;
}

export function IssueCompact({ issues, selectedIndex, onSelect }: IssueCompactProps) {
  return (
    <div className="rounded-lg border border-border bg-background font-mono text-xs divide-y divide-border shadow-inner">
      {issues.map((issue, idx) => {
        const isSelected = idx === selectedIndex;
        const roiTier = getRoiTier(issue.hourlyRoiUsd);

        return (
          <div
            key={issue.id}
            onClick={() => onSelect(issue)}
            className={`flex items-center justify-between px-3 py-2 cursor-pointer transition-colors ${
              isSelected
                ? 'bg-primary/40 text-primary border-l-2 border-primary pl-2.5'
                : 'hover:bg-card/60 text-foreground'
            }`}
          >
            {/* Left: Indicator + Repo + Title */}
            <div className="flex items-center gap-2 truncate pr-4">
              <span className="text-muted-foreground shrink-0">
                {idx < 9 ? `0${idx + 1}` : idx + 1}.
              </span>
              <span className="text-muted-foreground shrink-0 font-semibold">
                {issue.repository.name}
                <span className="text-primary font-normal">#{issue.githubIssueNumber}</span>
              </span>
              <span className="text-foreground truncate">{issue.title}</span>
            </div>

            {/* Right: Bounty & ROI & Time */}
            <div className="flex items-center gap-3 shrink-0 text-[11px]">
              {issue.bounty && (
                <span className="text-bounty-gold font-bold flex items-center gap-0.5">
                  <Coins className="h-3 w-3" />
                  ${issue.bounty.amountUsd}
                </span>
              )}
              {issue.hourlyRoiUsd && issue.hourlyRoiUsd > 0 && (
                <span className="text-primary font-semibold">
                  ${Math.round(issue.hourlyRoiUsd)}/hr
                </span>
              )}
              <span className="text-muted-foreground">
                ~{formatTimeMinutes(issue.estimatedMinutesToSolve)}
              </span>
              <ArrowRight className="h-3 w-3 text-muted-foreground group-hover:text-primary" />
            </div>
          </div>
        );
      })}
    </div>
  );
}
