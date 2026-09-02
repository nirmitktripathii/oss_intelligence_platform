import * as React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'destructive' | 'emerald' | 'purple' | 'cyan' | 'amber' | 'blue' | 'rose' | 'gold';
}

function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const baseStyles =
    'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-mono font-medium transition-colors focus:outline-none focus:ring-1 focus:ring-ring';

  const variants: Record<string, string> = {
    default: 'border-transparent bg-secondary text-secondary-foreground',
    secondary: 'border-transparent bg-secondary text-muted-foreground',
    outline: 'border-border text-muted-foreground bg-card/40',
    destructive: 'border-destructive/30 bg-destructive/10 text-destructive',
    emerald: 'border-domain-web/30 bg-domain-web/10 text-domain-web',
    purple: 'border-domain-ai/30 bg-domain-ai/10 text-domain-ai',
    cyan: 'border-domain-data/30 bg-domain-data/10 text-domain-data',
    amber: 'border-domain-sys/30 bg-domain-sys/10 text-domain-sys',
    blue: 'border-domain-cloud/30 bg-domain-cloud/10 text-domain-cloud',
    rose: 'border-domain-sec/30 bg-domain-sec/10 text-domain-sec',
    gold: 'border-bounty-gold/40 bg-bounty-gold/10 text-bounty-gold shadow-[0_0_8px_hsl(var(--bounty-gold)/0.2)]',
  };

  return <div className={cn(baseStyles, variants[variant], className)} {...props} />;
}

export { Badge };
