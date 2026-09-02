'use client';

import * as React from 'react';
import { Slider } from '@/components/ui/slider';
import { getRoiTier } from '@/lib/utils';
import { Calculator, Coins, Clock } from 'lucide-react';

interface RoiCalculatorWidgetProps {
  bountyAmountUsd?: number;
  initialMinutes?: number;
}

export function RoiCalculatorWidget({
  bountyAmountUsd = 250,
  initialMinutes = 90,
}: RoiCalculatorWidgetProps) {
  const [minutes, setMinutes] = React.useState<number>(initialMinutes);

  if (!bountyAmountUsd || bountyAmountUsd <= 0) {
    return null;
  }

  const hours = minutes / 60;
  const effectiveHourlyRate = hours > 0 ? bountyAmountUsd / hours : 0;
  const roiTier = getRoiTier(effectiveHourlyRate);

  return (
    <div className="rounded-2xl border border-bounty-gold/30 bg-gradient-to-br from-bounty-gold/20 via-card/60 to-background p-5 font-mono text-xs text-foreground space-y-4 shadow-xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold text-foreground text-sm">
          <span className="flex items-center justify-center h-6 w-6 rounded-lg bg-bounty-gold/20 text-bounty-gold">
            <Calculator className="h-3.5 w-3.5" />
          </span>
          <span>Interactive Bounty ROI Simulator</span>
        </div>
        <span className={`px-3 py-1 rounded-lg border text-xs font-extrabold ${roiTier.badgeClass} shadow-sm`}>
          {roiTier.emoji} ${Math.round(effectiveHourlyRate)}/hr Rate
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 bg-background p-3.5 rounded-xl border border-border shadow-inner">
        <div>
          <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider block">
            Funded Bounty
          </span>
          <span className="text-lg font-extrabold text-bounty-gold flex items-center gap-1 pt-0.5">
            <Coins className="h-4 w-4 text-bounty-gold" />
            <span>${bountyAmountUsd} USD</span>
          </span>
        </div>
        <div>
          <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider block">
            Simulated Time
          </span>
          <span className="text-lg font-extrabold text-foreground flex items-center gap-1 pt-0.5">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span>{minutes < 60 ? `${minutes}m` : `${(minutes / 60).toFixed(1)}h`}</span>
          </span>
        </div>
      </div>

      <div className="space-y-2 pt-1">
        <div className="flex justify-between text-xs text-foreground font-semibold">
          <span>Personal Solve Time Slider:</span>
          <span className="text-primary font-bold">{minutes} minutes</span>
        </div>
        <Slider
          value={[minutes]}
          min={15}
          max={360}
          step={15}
          onValueChange={(val) => setMinutes(val[0])}
        />
        <div className="flex justify-between text-[10px] text-muted-foreground font-medium">
          <span>15m (Speedrun)</span>
          <span>1h</span>
          <span>3h</span>
          <span>6h (Deep Refactor)</span>
        </div>
      </div>
    </div>
  );
}
