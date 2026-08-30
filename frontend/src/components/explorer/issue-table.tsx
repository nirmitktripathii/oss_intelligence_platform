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
    <div className="w-full overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-950/70 font-mono text-xs shadow-sm">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/80 text-[11px] text-zinc-400 uppercase tracking-wider">
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
        <tbody className="divide-y divide-zinc-800/60">
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
                    ? 'bg-emerald-950/30 text-zinc-100 ring-1 ring-inset ring-emerald-500'
                    : 'hover:bg-zinc-900/60 text-zinc-300'
                }`}
              >
                {/* Domain */}
                <td className="py-3 px-3 whitespace-nowrap">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: domainInfo.hex }}
                    />
                    <span className="text-[11px] text-zinc-400 font-medium">
                      {domainInfo.label}
                    </span>
                  </div>
                </td>

                {/* Repo */}
                <td className="py-3 px-3 whitespace-nowrap">
                  <div className="flex flex-col">
                    <span className="font-semibold text-zinc-200">
                      {issue.repository.name}
                    </span>
                    <span className="text-[10px] text-emerald-400">
                      #{issue.githubIssueNumber}
                    </span>
                  </div>
                </td>

                {/* Title & Body */}
                <td className="py-3 px-4">
                  <div className="flex flex-col space-y-0.5">
                    <span className="font-medium text-zinc-100 line-clamp-1">
                      {issue.title}
                    </span>
                    <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                      <span>Stack:</span>
                      {issue.techStack.slice(0, 3).map((t) => (
                        <span key={t} className="text-zinc-400">
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
                <td className="py-3 px-3 whitespace-nowrap text-zinc-400 text-[11px]">
                  ~{formatTimeMinutes(issue.estimatedMinutesToSolve)}
                </td>

                {/* Bounty */}
                <td className="py-3 px-3 whitespace-nowrap">
                  {issue.bounty && issue.bounty.isFunded ? (
                    <span className="inline-flex items-center gap-1 rounded bg-amber-500/15 border border-amber-500/40 px-1.5 py-0.5 text-[11px] font-bold text-amber-300">
                      <Coins className="h-3 w-3" />
                      ${issue.bounty.amountUsd}
                    </span>
                  ) : (
                    <span className="text-[11px] text-zinc-500">—</span>
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
                    <span className="text-[11px] text-zinc-500">—</span>
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
