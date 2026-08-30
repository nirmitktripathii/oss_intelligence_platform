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
        colorClass: 'text-purple-400 border-purple-500/30 bg-purple-500/10',
        borderClass: 'border-purple-500/40',
        bgClass: 'bg-purple-500/10',
        textClass: 'text-purple-400',
        hex: '#a855f7',
      };
    case 'data':
      return {
        label: 'Data & Infra',
        colorClass: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10',
        borderClass: 'border-cyan-500/40',
        bgClass: 'bg-cyan-500/10',
        textClass: 'text-cyan-400',
        hex: '#06b6d4',
      };
    case 'web':
      return {
        label: 'Web Ecosystem',
        colorClass: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
        borderClass: 'border-emerald-500/40',
        bgClass: 'bg-emerald-500/10',
        textClass: 'text-emerald-400',
        hex: '#10b981',
      };
    case 'cloud_devops':
      return {
        label: 'Cloud & DevOps',
        colorClass: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
        borderClass: 'border-blue-500/40',
        bgClass: 'bg-blue-500/10',
        textClass: 'text-blue-400',
        hex: '#3b82f6',
      };
    case 'security':
      return {
        label: 'Security',
        colorClass: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
        borderClass: 'border-rose-500/40',
        bgClass: 'bg-rose-500/10',
        textClass: 'text-rose-400',
        hex: '#f43f5e',
      };
    case 'systems':
      return {
        label: 'Systems & OS',
        colorClass: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
        borderClass: 'border-amber-500/40',
        bgClass: 'bg-amber-500/10',
        textClass: 'text-amber-400',
        hex: '#f59e0b',
      };
    default:
      return {
        label: String(domain).toUpperCase(),
        colorClass: 'text-slate-400 border-slate-500/30 bg-slate-500/10',
        borderClass: 'border-slate-500/40',
        bgClass: 'bg-slate-500/10',
        textClass: 'text-slate-400',
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
        badgeClass: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
        color: '#10b981',
      };
    case 'intermediate':
    case 'medium':
      return {
        label: 'Intermediate',
        badgeClass: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
        color: '#f59e0b',
      };
    case 'advanced':
    case 'hard':
      return {
        label: 'Advanced',
        badgeClass: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
        color: '#f43f5e',
      };
    default:
      return {
        label: 'General',
        badgeClass: 'bg-slate-500/15 text-slate-400 border-slate-500/30',
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
      badgeClass: 'bg-zinc-800/80 text-zinc-400 border-zinc-700/50',
      emoji: '🌱',
    };
  }
  if (hourlyRoiUsd >= 150) {
    return {
      tier: 'exceptional',
      label: `$${Math.round(hourlyRoiUsd)}/hr ROI`,
      badgeClass: 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.25)] animate-pulse-glow',
      emoji: '🔥',
    };
  }
  if (hourlyRoiUsd >= 75) {
    return {
      tier: 'great',
      label: `$${Math.round(hourlyRoiUsd)}/hr ROI`,
      badgeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.2)]',
      emoji: '⚡',
    };
  }
  return {
    tier: 'standard',
    label: `$${Math.round(hourlyRoiUsd)}/hr ROI`,
    badgeClass: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
    emoji: '⚖️',
  };
}
