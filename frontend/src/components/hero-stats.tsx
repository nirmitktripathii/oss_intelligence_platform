'use client';

import * as React from 'react';
import { Activity, DollarSign, Target, Zap } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

interface StatCard {
  label: string;
  value: string;
  change: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bg: string;
}

/**
 * Hero metrics strip.
 *
 * The first two cards show REAL telemetry fetched from the live backend
 * (open-issue count from /health, funded bounty pool from /bounties). When the
 * backend is unreachable, api-client returns its labeled offline fallback and
 * `db_connected` is false, so the cards render a "demo" badge instead of
 * pretending the numbers are live.
 *
 * The last two cards describe real product capabilities (AST-assisted
 * localization, multi-channel alerts) with honest labels rather than the
 * fabricated precision/latency figures they replaced.
 */
export function HeroStats() {
  const [issuesCount, setIssuesCount] = React.useState<number | null>(null);
  const [bountyPool, setBountyPool] = React.useState<number | null>(null);
  const [isLive, setIsLive] = React.useState<boolean>(false);
  const [loaded, setLoaded] = React.useState<boolean>(false);

  React.useEffect(() => {
    let cancelled = false;

    (async () => {
      const [health, bounties] = await Promise.all([
        apiClient.getHealth(),
        apiClient.getBounties().catch(() => null),
      ]);
      if (cancelled) return;

      setIsLive(Boolean(health.db_connected));
      setIssuesCount(typeof health.issues_count === 'number' ? health.issues_count : null);
      // Live /bounties returns `total_bounty_usd`; the offline fallback shape
      // uses `total_payout_pool_usd`. Accept either so the card is correct in
      // both modes.
      const pool =
        bounties && typeof bounties.total_bounty_usd === 'number'
          ? bounties.total_bounty_usd
          : bounties && typeof bounties.total_payout_pool_usd === 'number'
            ? bounties.total_payout_pool_usd
            : null;
      setBountyPool(pool);
      setLoaded(true);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const fmt = (n: number) => Math.round(n).toLocaleString('en-US');
  const liveBadge = !loaded ? 'syncing…' : isLive ? 'live' : 'demo';
  const dataColor = !loaded || isLive ? undefined : 'text-bounty-gold';

  const stats: StatCard[] = [
    {
      label: 'Open Issues Tracked',
      value: issuesCount == null ? '—' : fmt(issuesCount),
      change: liveBadge,
      icon: Activity,
      color: dataColor ?? 'text-primary',
      bg: 'bg-primary/10 border-primary/20',
    },
    {
      label: 'Funded Bounty Pool',
      value: bountyPool == null ? '—' : `$${fmt(bountyPool)}`,
      change: !loaded ? 'syncing…' : isLive ? 'Polar · Algora' : 'demo',
      icon: DollarSign,
      color: dataColor ?? 'text-bounty-gold',
      bg: 'bg-bounty-gold/10 border-bounty-gold/20',
    },
    {
      label: 'AST Localization',
      value: 'AI-Assisted',
      change: 'Graphify',
      icon: Target,
      color: 'text-accent',
      bg: 'bg-accent/10 border-accent/20',
    },
    {
      label: 'Push Alerts',
      value: 'Multi-Channel',
      change: 'Telegram · Discord',
      icon: Zap,
      color: 'text-accent',
      bg: 'bg-accent/10 border-accent/20',
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
      {stats.map((stat, i) => {
        const Icon = stat.icon;
        return (
          <div
            key={i}
            className={`rounded-xl border p-3.5 flex flex-col justify-between ${stat.bg} backdrop-blur-sm transition-all hover:scale-[1.02]`}
          >
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
              <span className="text-[11px] font-semibold">{stat.label}</span>
              <Icon className={`h-4 w-4 ${stat.color}`} />
            </div>
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-lg sm:text-xl font-extrabold text-foreground">{stat.value}</span>
              <span className={`text-[10px] font-bold ${stat.color}`}>{stat.change}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
