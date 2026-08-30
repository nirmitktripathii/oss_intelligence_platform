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
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 font-mono text-xs divide-y divide-zinc-900 shadow-inner">
      {issues.map((issue, idx) => {
        const isSelected = idx === selectedIndex;
        const roiTier = getRoiTier(issue.hourlyRoiUsd);

        return (
          <div
            key={issue.id}
            onClick={() => onSelect(issue)}
            className={`flex items-center justify-between px-3 py-2 cursor-pointer transition-colors ${
              isSelected
                ? 'bg-emerald-950/40 text-emerald-300 border-l-2 border-emerald-400 pl-2.5'
                : 'hover:bg-zinc-900/60 text-zinc-300'
            }`}
          >
            {/* Left: Indicator + Repo + Title */}
            <div className="flex items-center gap-2 truncate pr-4">
              <span className="text-zinc-600 shrink-0">
                {idx < 9 ? `0${idx + 1}` : idx + 1}.
              </span>
              <span className="text-zinc-400 shrink-0 font-semibold">
                {issue.repository.name}
                <span className="text-emerald-400 font-normal">#{issue.githubIssueNumber}</span>
              </span>
              <span className="text-zinc-200 truncate">{issue.title}</span>
            </div>

            {/* Right: Bounty & ROI & Time */}
            <div className="flex items-center gap-3 shrink-0 text-[11px]">
              {issue.bounty && (
                <span className="text-amber-300 font-bold flex items-center gap-0.5">
                  <Coins className="h-3 w-3" />
                  ${issue.bounty.amountUsd}
                </span>
              )}
              {issue.hourlyRoiUsd && issue.hourlyRoiUsd > 0 && (
                <span className="text-emerald-400 font-semibold">
                  ${Math.round(issue.hourlyRoiUsd)}/hr
                </span>
              )}
              <span className="text-zinc-500">
                ~{formatTimeMinutes(issue.estimatedMinutesToSolve)}
              </span>
              <ArrowRight className="h-3 w-3 text-zinc-600 group-hover:text-emerald-400" />
            </div>
          </div>
        );
      })}
    </div>
  );
}
