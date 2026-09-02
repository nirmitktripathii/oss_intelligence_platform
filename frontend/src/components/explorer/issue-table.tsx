'use client';

import * as React from 'react';
import { Issue } from '@/types/issue';
import { Button } from '@/components/ui/button';
import { getDomainInfo, getDifficultyInfo, getRoiTier, formatTimeMinutes } from '@/lib/utils';
import { ArrowUpRight, Coins } from 'lucide-react';

interface IssueTableProps {
  issues: Issue[];
  selectedIndex: number;
  onSelect: (issue: Issue) => void;
}

export function IssueTable({ issues, selectedIndex, onSelect }: IssueTableProps) {
  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border bg-background/70 font-mono text-xs shadow-sm">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-border bg-card/80 text-[11px] text-muted-foreground uppercase tracking-wider">
            <th className="py-2.5 px-3 font-semibold">Ecosystem</th>
            <th className="py-2.5 px-3 font-semibold">Repository</th>
            <th className="py-2.5 px-4 font-semibold w-1/3">Issue Title & Diagnostics</th>
            <th className="py-2.5 px-3 font-semibold">Difficulty</th>
            <th className="py-2.5 px-3 font-semibold">Est. Time</th>
            <th className="py-2.5 px-3 font-semibold">Bounty ($)</th>
            <th className="py-2.5 px-3 font-semibold">Hourly ROI</th>
            <th className="py-2.5 px-3 text-right font-semibold">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {issues.map((issue, idx) => {
            const isSelected = idx === selectedIndex;
            const domainInfo = getDomainInfo(issue.domain);
            const diffInfo = getDifficultyInfo(issue.difficulty);
            const roiTier = getRoiTier(issue.hourlyRoiUsd);

            return (
              <tr
                key={issue.id}
                onClick={() => onSelect(issue)}
                className={`cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-primary/30 text-foreground ring-1 ring-inset ring-primary'
                    : 'hover:bg-card/60 text-foreground'
                }`}
              >
                {/* Domain */}
                <td className="py-3 px-3 whitespace-nowrap">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: domainInfo.hex }}
                    />
                    <span className="text-[11px] text-muted-foreground font-medium">
                      {domainInfo.label}
                    </span>
                  </div>
                </td>

                {/* Repo */}
                <td className="py-3 px-3 whitespace-nowrap">
                  <div className="flex flex-col">
                    <span className="font-semibold text-foreground">
                      {issue.repository.name}
                    </span>
                    <span className="text-[10px] text-primary">
                      #{issue.githubIssueNumber}
                    </span>
                  </div>
                </td>

                {/* Title & Body */}
                <td className="py-3 px-4">
                  <div className="flex flex-col space-y-0.5">
                    <span className="font-medium text-foreground line-clamp-1">
                      {issue.title}
                    </span>
                    <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                      <span>Stack:</span>
                      {issue.techStack.slice(0, 3).map((t) => (
                        <span key={t} className="text-muted-foreground">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </td>

                {/* Difficulty */}
                <td className="py-3 px-3 whitespace-nowrap">
                  <span className={`px-1.5 py-0.5 rounded border text-[10px] ${diffInfo.badgeClass}`}>
                    {diffInfo.label}
                  </span>
                </td>

                {/* Time to Solve */}
                <td className="py-3 px-3 whitespace-nowrap text-muted-foreground text-[11px]">
                  ~{formatTimeMinutes(issue.estimatedMinutesToSolve)}
                </td>

                {/* Bounty */}
                <td className="py-3 px-3 whitespace-nowrap">
                  {issue.bounty && issue.bounty.isFunded ? (
                    <span className="inline-flex items-center gap-1 rounded bg-bounty-gold/15 border border-bounty-gold/40 px-1.5 py-0.5 text-[11px] font-bold text-bounty-gold">
                      <Coins className="h-3 w-3" />
                      ${issue.bounty.amountUsd}
                    </span>
                  ) : (
                    <span className="text-[11px] text-muted-foreground">—</span>
                  )}
                </td>

                {/* Hourly ROI */}
                <td className="py-3 px-3 whitespace-nowrap">
                  {issue.hourlyRoiUsd && issue.hourlyRoiUsd > 0 ? (
                    <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-bold border ${roiTier.badgeClass}`}>
                      <span>{roiTier.emoji}</span>
                      <span>${Math.round(issue.hourlyRoiUsd)}/hr</span>
                    </span>
                  ) : (
                    <span className="text-[11px] text-muted-foreground">—</span>
                  )}
                </td>

                {/* Action */}
                <td className="py-3 px-3 text-right whitespace-nowrap">
                  <Button variant="terminal" size="xs" className="gap-1">
                    <span>Inspect</span>
                    <ArrowUpRight className="h-3 w-3" />
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
