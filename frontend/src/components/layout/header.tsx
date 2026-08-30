'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Terminal, Bell, Zap, Command, Github, Network } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/theme/theme-toggle';
import { NotificationModal } from '@/components/modals/notification-modal';
import { PricingModal } from '@/components/modals/pricing-modal';
import { CommandMenu } from '@/components/layout/command-menu';
import { useBounties } from '@/hooks/use-bounties';
import { SITE_CONFIG } from '@/lib/constants';

interface HeaderProps {
  onOpenCommandMenu?: () => void;
}

export function Header({ onOpenCommandMenu }: HeaderProps) {
  const pathname = usePathname();
  const { stats } = useBounties();
  const [isNotificationOpen, setIsNotificationOpen] = React.useState(false);
  const [isPricingOpen, setIsPricingOpen] = React.useState(false);
  const [isCommandMenuOpen, setIsCommandMenuOpen] = React.useState(false);

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandMenuOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="container flex h-14 items-center justify-between font-mono">
          {/* Logo & Status Badge */}
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 group-hover:border-emerald-400 group-hover:bg-emerald-500/20 transition-all shadow-[0_0_10px_rgba(16,185,129,0.15)]">
                <Terminal className="h-4 w-4" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-bold tracking-tight text-foreground group-hover:text-emerald-400 transition-colors">
                    {SITE_CONFIG.name}
                  </span>
                  <span className="text-[10px] text-muted-foreground hidden sm:inline">TERMINAL</span>
                </div>
              </div>
            </Link>

            {/* Live Ticker Telemetry */}
            <div className="hidden lg:flex items-center gap-2 pl-3 border-l border-border text-[11px] text-muted-foreground">
              <div className="flex items-center gap-1.5 bg-muted/60 px-2 py-0.5 rounded border border-border/80">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-foreground font-medium">LIVE</span>
              </div>
              <span className="text-muted-foreground">
                Pool:{' '}
                <span className="text-amber-400 font-semibold">
                  ${stats.totalBountyPoolUsd.toLocaleString()}
                </span>
              </span>
              <span className="text-border">•</span>
              <span className="text-muted-foreground">
                Active:{' '}
                <span className="text-emerald-400 font-semibold">{stats.activeBountiesCount}</span>
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 text-xs">
            <Link href="/">
              <Button
                variant={pathname === '/' ? 'secondary' : 'ghost'}
                size="sm"
                className={`text-xs gap-1.5 ${
                  pathname === '/' ? 'text-emerald-400 font-bold bg-emerald-500/10 border border-emerald-500/30' : 'text-muted-foreground'
                }`}
              >
                <Terminal className="h-3.5 w-3.5" />
                Issue Terminal
              </Button>
            </Link>
            <Link href="/graph">
              <Button
                variant={pathname === '/graph' ? 'secondary' : 'ghost'}
                size="sm"
                className={`text-xs gap-1.5 ${
                  pathname === '/graph' ? 'text-purple-400 font-bold bg-purple-500/10 border border-purple-500/30' : 'text-muted-foreground'
                }`}
              >
                <Network className="h-3.5 w-3.5" />
                Knowledge Graph
              </Button>
            </Link>
            <Link href="/pricing">
              <Button
                variant={pathname === '/pricing' ? 'secondary' : 'ghost'}
                size="sm"
                className={`text-xs gap-1.5 ${
                  pathname === '/pricing' ? 'text-amber-400 font-bold bg-amber-500/10 border border-amber-500/30' : 'text-muted-foreground'
                }`}
              >
                <Zap className="h-3.5 w-3.5" />
                Pricing & ROI
              </Button>
            </Link>
            <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs gap-1.5 text-muted-foreground hover:text-foreground"
              >
                API Docs ↗
              </Button>
            </a>
          </nav>

          {/* Right Action Tools */}
          <div className="flex items-center gap-2">
            {/* Quick Command Menu Trigger */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (onOpenCommandMenu) onOpenCommandMenu();
                else setIsCommandMenuOpen(true);
              }}
              className="hidden sm:flex items-center gap-2 h-8 px-2.5 text-xs text-muted-foreground border-border bg-card/60 hover:text-foreground"
            >
              <Command className="h-3 w-3" />
              <span>Search</span>
              <kbd className="pointer-events-none inline-flex h-4 select-none items-center gap-0.5 rounded border border-border bg-muted px-1 text-[9px] font-mono text-muted-foreground">
                ⌘K
              </kbd>
            </Button>

            {/* Notifications Trigger */}
            <Button
              variant="outline"
              size="icon"
              onClick={() => setIsNotificationOpen(true)}
              className="h-8 w-8 border-zinc-800 bg-zinc-900/60 hover:border-zinc-700 text-zinc-400 hover:text-white"
              title="Configure Multi-Channel Alerts"
            >
              <Bell className="h-3.5 w-3.5" />
              <span className="sr-only">Notifications</span>
            </Button>

            {/* Pro Upgrade Button */}
            <Button
              variant="glow"
              size="sm"
              onClick={() => setIsPricingOpen(true)}
              className="h-8 gap-1.5 px-3 text-xs font-semibold"
            >
              <Zap className="h-3.5 w-3.5 fill-current" />
              <span className="hidden sm:inline">Pro Terminal</span>
            </Button>

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* GitHub Repo link */}
            <a
              href={SITE_CONFIG.links.github}
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:inline-flex"
            >
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-zinc-400 hover:text-zinc-100"
                title="GitHub Repository"
              >
                <Github className="h-4 w-4" />
                <span className="sr-only">GitHub</span>
              </Button>
            </a>
          </div>
        </div>
      </header>

      {/* Modals */}
      <NotificationModal
        isOpen={isNotificationOpen}
        onClose={() => setIsNotificationOpen(false)}
      />
      <PricingModal
        isOpen={isPricingOpen}
        onClose={() => setIsPricingOpen(false)}
      />
      <CommandMenu
        isOpen={isCommandMenuOpen}
        onClose={() => setIsCommandMenuOpen(false)}
        onOpenNotifications={() => setIsNotificationOpen(true)}
        onOpenPricing={() => setIsPricingOpen(true)}
      />
    </>
  );
}
