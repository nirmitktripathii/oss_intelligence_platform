import * as React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'destructive' | 'emerald' | 'purple' | 'cyan' | 'amber' | 'blue' | 'rose' | 'gold';
}

function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const baseStyles =
    'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-mono font-medium transition-colors focus:outline-none focus:ring-1 focus:ring-ring';

  const variants: Record<string, string> = {
    default: 'border-transparent bg-zinc-800 text-zinc-100',
    secondary: 'border-transparent bg-zinc-800 text-zinc-300',
    outline: 'border-zinc-700 text-zinc-300 bg-zinc-900/40',
    destructive: 'border-rose-500/30 bg-rose-500/10 text-rose-400',
    emerald: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
    purple: 'border-purple-500/30 bg-purple-500/10 text-purple-400',
    cyan: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400',
    amber: 'border-amber-500/30 bg-amber-500/10 text-amber-400',
    blue: 'border-blue-500/30 bg-blue-500/10 text-blue-400',
    rose: 'border-rose-500/30 bg-rose-500/10 text-rose-400',
    gold: 'border-amber-400/40 bg-amber-400/10 text-amber-300 shadow-[0_0_8px_rgba(251,191,36,0.2)]',
  };

  return <div className={cn(baseStyles, variants[variant], className)} {...props} />;
}

export { Badge };
