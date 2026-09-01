'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';

export interface BountyStats {
  totalBountyPoolUsd: number;
  activeBountiesCount: number;
  avgHourlyRoi: number;
  highestBountyUsd: number;
}

export function useBounties() {
  // Seed with zeros, never fabricated figures — real telemetry replaces these on load.
  const [stats, setStats] = useState<BountyStats>({
    totalBountyPoolUsd: 0,
    activeBountiesCount: 0,
    avgHourlyRoi: 0,
    highestBountyUsd: 0,
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    async function loadBounties() {
      try {
        const res = await apiClient.getBounties();
        if (mounted && res) {
          const items = res.items || [];
          // Live backend returns total_bounty_usd / total / average_hourly_roi with
          // per-item `hourly_roi`; the offline fallback shape uses
          // total_payout_pool_usd / active_bounties_count. Accept either, then fall
          // back to computing from items so both modes render real numbers.
          const totalPool =
            res.total_bounty_usd ??
            res.total_payout_pool_usd ??
            items.reduce((sum: number, b: any) => sum + (b.bounty_amount_usd || 0), 0);
          const activeCount = res.total ?? res.active_bounties_count ?? items.length;
          const avgRoi =
            res.average_hourly_roi ??
            (items.length > 0
              ? items.reduce((sum: number, b: any) => sum + (b.hourly_roi ?? b.hourly_roi_usd ?? 0), 0) /
                items.length
              : 0);
          const highest =
            items.length > 0 ? Math.max(...items.map((b: any) => b.bounty_amount_usd || 0)) : 0;

          setStats({
            totalBountyPoolUsd: totalPool || 0,
            activeBountiesCount: activeCount || 0,
            avgHourlyRoi: Math.round(avgRoi) || 0,
            highestBountyUsd: highest || 0,
          });
        }
      } catch {
        // Leave zeros rather than inventing bounty telemetry the backend didn't return.
      } finally {
        if (mounted) setIsLoading(false);
      }
    }
    loadBounties();
    return () => {
      mounted = false;
    };
  }, []);

  return { stats, isLoading };
}
