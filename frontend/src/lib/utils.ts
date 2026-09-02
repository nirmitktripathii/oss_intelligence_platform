import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Domain, Difficulty } from '@/types/issue';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatTimeMinutes(minutes: number): string {
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = (minutes / 60).toFixed(1).replace(/\.0$/, '');
  return `${hours}h`;
}

export function formatDateRelative(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return 'recently';
  }
}

export function getDomainInfo(domain: Domain | string): { label: string; colorClass: string; borderClass: string; bgClass: string; textClass: string; hex: string } {
  switch (domain) {
    case 'ai_ml':
      return {
        label: 'AI / ML',
        colorClass: 'text-domain-ai border-domain-ai/30 bg-domain-ai/10',
        borderClass: 'border-domain-ai/40',
        bgClass: 'bg-domain-ai/10',
        textClass: 'text-domain-ai',
        hex: '#a855f7',
      };
    case 'data':
      return {
        label: 'Data & Infra',
        colorClass: 'text-domain-data border-domain-data/30 bg-domain-data/10',
        borderClass: 'border-domain-data/40',
        bgClass: 'bg-domain-data/10',
        textClass: 'text-domain-data',
        hex: '#06b6d4',
      };
    case 'web':
      return {
        label: 'Web Ecosystem',
        colorClass: 'text-domain-web border-domain-web/30 bg-domain-web/10',
        borderClass: 'border-domain-web/40',
        bgClass: 'bg-domain-web/10',
        textClass: 'text-domain-web',
        hex: '#10b981',
      };
    case 'cloud_devops':
      return {
        label: 'Cloud & DevOps',
        colorClass: 'text-domain-cloud border-domain-cloud/30 bg-domain-cloud/10',
        borderClass: 'border-domain-cloud/40',
        bgClass: 'bg-domain-cloud/10',
        textClass: 'text-domain-cloud',
        hex: '#3b82f6',
      };
    case 'security':
      return {
        label: 'Security',
        colorClass: 'text-domain-sec border-domain-sec/30 bg-domain-sec/10',
        borderClass: 'border-domain-sec/40',
        bgClass: 'bg-domain-sec/10',
        textClass: 'text-domain-sec',
        hex: '#f43f5e',
      };
    case 'systems':
      return {
        label: 'Systems & OS',
        colorClass: 'text-domain-sys border-domain-sys/30 bg-domain-sys/10',
        borderClass: 'border-domain-sys/40',
        bgClass: 'bg-domain-sys/10',
        textClass: 'text-domain-sys',
        hex: '#f59e0b',
      };
    default:
      return {
        label: String(domain).toUpperCase(),
        colorClass: 'text-muted-foreground border-border bg-muted/40',
        borderClass: 'border-border',
        bgClass: 'bg-muted/40',
        textClass: 'text-muted-foreground',
        hex: '#64748b',
      };
  }
}

export function getDifficultyInfo(difficulty: Difficulty | string): { label: string; badgeClass: string; color: string } {
  switch (difficulty) {
    case 'good_first_issue':
    case 'easy':
      return {
        label: 'Good First Issue',
        badgeClass: 'bg-primary/15 text-primary border-primary/30',
        color: '#10b981',
      };
    case 'intermediate':
    case 'medium':
      return {
        label: 'Intermediate',
        badgeClass: 'bg-bounty-gold/15 text-bounty-gold border-bounty-gold/30',
        color: '#f59e0b',
      };
    case 'advanced':
    case 'hard':
      return {
        label: 'Advanced',
        badgeClass: 'bg-destructive/15 text-destructive border-destructive/30',
        color: '#f43f5e',
      };
    default:
      return {
        label: 'General',
        badgeClass: 'bg-muted/40 text-muted-foreground border-border',
        color: '#64748b',
      };
  }
}

export function getRoiTier(hourlyRoiUsd: number | undefined): {
  tier: 'exceptional' | 'great' | 'standard' | 'none';
  label: string;
  badgeClass: string;
  emoji: string;
} {
  if (!hourlyRoiUsd || hourlyRoiUsd <= 0) {
    return {
      tier: 'none',
      label: 'Community Issue',
      badgeClass: 'bg-secondary/80 text-muted-foreground border-border',
      emoji: '🌱',
    };
  }
  if (hourlyRoiUsd >= 150) {
    return {
      tier: 'exceptional',
      label: `$${Math.round(hourlyRoiUsd)}/hr ROI`,
      badgeClass: 'bg-bounty-gold/20 text-bounty-gold border-bounty-gold/40 shadow-[0_0_12px_hsl(var(--bounty-gold)/0.25)] animate-pulse-glow',
      emoji: '🔥',
    };
  }
  if (hourlyRoiUsd >= 75) {
    return {
      tier: 'great',
      label: `$${Math.round(hourlyRoiUsd)}/hr ROI`,
      badgeClass: 'bg-primary/20 text-primary border-primary/40 shadow-[0_0_8px_hsl(var(--primary)/0.2)]',
      emoji: '⚡',
    };
  }
  return {
    tier: 'standard',
    label: `$${Math.round(hourlyRoiUsd)}/hr ROI`,
    badgeClass: 'bg-accent/15 text-accent border-accent/30',
    emoji: '⚖️',
  };
}
