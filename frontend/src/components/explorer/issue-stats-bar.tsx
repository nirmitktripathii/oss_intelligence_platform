'use client';

import * as React from 'react';
import { useBounties } from '@/hooks/use-bounties';
import { Coins, Flame, Target, Cpu } from 'lucide-react';

interface IssueStatsBarProps {
  totalIssuesCount?: number;
}

export function IssueStatsBar({ totalIssuesCount = 54 }: IssueStatsBarProps) {
  const { stats } = useBounties();

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 font-mono text-xs">
      {/* Stat 1: Total Open Issues */}
      <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/70 p-3 flex items-center justify-between">
        <div className="space-y-0.5">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider block">
            Indexed Live Issues
          </span>
          <span className="text-lg font-extrabold text-zinc-100">
            {totalIssuesCount}
          </span>
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-zinc-900 border border-zinc-800 text-emerald-400">
          <Cpu className="h-4 w-4" />
        </div>
      </div>

      {/* Stat 2: Total Bounty Pool */}
      <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/70 p-3 flex items-center justify-between">
        <div className="space-y-0.5">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider block">
            Total Bounty Pool
          </span>
          <span className="text-lg font-extrabold text-amber-300">
            ${stats.totalBountyPoolUsd.toLocaleString()}
          </span>
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-400">
          <Coins className="h-4 w-4" />
        </div>
      </div>

      {/* Stat 3: Avg Hourly ROI */}
      <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/70 p-3 flex items-center justify-between">
        <div className="space-y-0.5">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider block">
            Avg Effective Rate
          </span>
          <span className="text-lg font-extrabold text-emerald-400">
            ${stats.avgHourlyRoi}/hr
          </span>
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
          <Flame className="h-4 w-4" />
        </div>
      </div>

      {/* Stat 4: Active Funded Bounties */}
      <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/70 p-3 flex items-center justify-between">
        <div className="space-y-0.5">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider block">
            Active Bounties
          </span>
          <span className="text-lg font-extrabold text-purple-400">
            {stats.activeBountiesCount.toLocaleString()}
          </span>
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-purple-500/10 border border-purple-500/30 text-purple-400">
          <Target className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}
