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
      <div className="rounded-lg border border-border/80 bg-background/70 p-3 flex items-center justify-between">
        <div className="space-y-0.5">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">
            Indexed Live Issues
          </span>
          <span className="text-lg font-extrabold text-foreground">
            {totalIssuesCount}
          </span>
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-card border border-border text-primary">
          <Cpu className="h-4 w-4" />
        </div>
      </div>

      {/* Stat 2: Total Bounty Pool */}
      <div className="rounded-lg border border-border/80 bg-background/70 p-3 flex items-center justify-between">
        <div className="space-y-0.5">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">
            Total Bounty Pool
          </span>
          <span className="text-lg font-extrabold text-bounty-gold">
            ${stats.totalBountyPoolUsd.toLocaleString()}
          </span>
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-bounty-gold/10 border border-bounty-gold/30 text-bounty-gold">
          <Coins className="h-4 w-4" />
        </div>
      </div>

      {/* Stat 3: Avg Hourly ROI */}
      <div className="rounded-lg border border-border/80 bg-background/70 p-3 flex items-center justify-between">
        <div className="space-y-0.5">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">
            Avg Effective Rate
          </span>
          <span className="text-lg font-extrabold text-primary">
            ${stats.avgHourlyRoi}/hr
          </span>
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 border border-primary/30 text-primary">
          <Flame className="h-4 w-4" />
        </div>
      </div>

      {/* Stat 4: Active Funded Bounties */}
      <div className="rounded-lg border border-border/80 bg-background/70 p-3 flex items-center justify-between">
        <div className="space-y-0.5">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">
            Active Bounties
          </span>
          <span className="text-lg font-extrabold text-accent">
            {stats.activeBountiesCount.toLocaleString()}
          </span>
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent/10 border border-accent/30 text-accent">
          <Target className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}
