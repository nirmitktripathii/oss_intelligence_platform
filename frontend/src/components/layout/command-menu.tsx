'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import {
  Dialog,
  DialogContent,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { DOMAINS } from '@/lib/constants';
import {
  Terminal,
  Search,
  Zap,
  Bell,
  Moon,
  Sun,
  Laptop,
  Network,
  Sparkles,
  Database,
  Globe,
  Cloud,
  ShieldAlert,
  Cpu,
  ArrowRight,
} from 'lucide-react';

interface CommandMenuProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectDomain?: (domain: string) => void;
  onOpenNotifications?: () => void;
  onOpenPricing?: () => void;
}

export function CommandMenu({
  isOpen,
  onClose,
  onSelectDomain,
  onOpenNotifications,
  onOpenPricing,
}: CommandMenuProps) {
  const router = useRouter();
  const { setTheme } = useTheme();
  const [query, setQuery] = React.useState('');

  const getDomainIcon = (iconName: string) => {
    switch (iconName) {
      case 'Sparkles':
        return <Sparkles className="h-4 w-4 text-purple-400" />;
      case 'Database':
        return <Database className="h-4 w-4 text-cyan-400" />;
      case 'Globe':
        return <Globe className="h-4 w-4 text-emerald-400" />;
      case 'Cloud':
        return <Cloud className="h-4 w-4 text-blue-400" />;
      case 'ShieldAlert':
        return <ShieldAlert className="h-4 w-4 text-rose-400" />;
      case 'Cpu':
        return <Cpu className="h-4 w-4 text-amber-400" />;
      default:
        return <Terminal className="h-4 w-4 text-zinc-400" />;
    }
  };

  const filteredDomains = DOMAINS.filter(
    (d) =>
      d.label.toLowerCase().includes(query.toLowerCase()) ||
      d.description.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl border-zinc-800 bg-zinc-950 p-0 font-mono text-zinc-100 overflow-hidden shadow-2xl">
        <div className="flex items-center border-b border-zinc-800 px-3">
          <Search className="h-4 w-4 text-zinc-500 mr-2 shrink-0" />
          <Input
            placeholder="Type a command or search domains..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-12 border-0 bg-transparent text-sm focus-visible:ring-0 focus-visible:ring-offset-0 px-0"
            autoFocus
          />
          <kbd className="pointer-events-none rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 text-[10px] text-zinc-400">
            ESC
          </kbd>
        </div>

        <div className="max-h-80 overflow-y-auto p-2 space-y-4 text-xs">
          {/* Section 1: Navigation & Actions */}
          <div className="space-y-1">
            <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider px-2">
              Quick Navigation
            </span>
            <button
              onClick={() => {
                router.push('/');
                onClose();
              }}
              className="w-full flex items-center justify-between px-2.5 py-2 rounded-md hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors"
            >
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4 text-emerald-400" />
                <span>Go to Main Issue Terminal</span>
              </div>
              <ArrowRight className="h-3 w-3 text-zinc-600" />
            </button>

            <button
              onClick={() => {
                router.push('/graph');
                onClose();
              }}
              className="w-full flex items-center justify-between px-2.5 py-2 rounded-md hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors"
            >
              <div className="flex items-center gap-2">
                <Network className="h-4 w-4 text-purple-400" />
                <span>Open Graphify AST Knowledge Graph</span>
              </div>
              <ArrowRight className="h-3 w-3 text-zinc-600" />
            </button>

            <button
              onClick={() => {
                onClose();
                onOpenPricing?.();
              }}
              className="w-full flex items-center justify-between px-2.5 py-2 rounded-md hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors"
            >
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-400" />
                <span>Upgrade to Pro Terminal</span>
              </div>
              <ArrowRight className="h-3 w-3 text-zinc-600" />
            </button>

            <button
              onClick={() => {
                onClose();
                onOpenNotifications?.();
              }}
              className="w-full flex items-center justify-between px-2.5 py-2 rounded-md hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors"
            >
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4 text-blue-400" />
                <span>Configure Push Alert Channels</span>
              </div>
              <ArrowRight className="h-3 w-3 text-zinc-600" />
            </button>
          </div>

          {/* Section 2: Jump to Domain */}
          {filteredDomains.length > 0 && (
            <div className="space-y-1">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider px-2">
                Filter by Ecosystem
              </span>
              {filteredDomains.map((dom) => (
                <button
                  key={dom.id}
                  onClick={() => {
                    onSelectDomain?.(dom.id);
                    onClose();
                  }}
                  className="w-full flex items-center justify-between px-2.5 py-2 rounded-md hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    {getDomainIcon(dom.icon)}
                    <div className="text-left">
                      <p className="font-medium text-zinc-200">{dom.label}</p>
                      <p className="text-[10px] text-zinc-500">{dom.description}</p>
                    </div>
                  </div>
                  <kbd className="text-[10px] text-zinc-600 border border-zinc-800 rounded px-1.5 py-0.5">
                    Filter
                  </kbd>
                </button>
              ))}
            </div>
          )}

          {/* Section 3: Theme Switcher */}
          <div className="space-y-1 border-t border-zinc-800/80 pt-2">
            <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider px-2">
              Theme Mode
            </span>
            <div className="grid grid-cols-3 gap-1 px-1">
              <button
                onClick={() => {
                  setTheme('dark');
                  onClose();
                }}
                className="flex items-center justify-center gap-1.5 py-1.5 rounded border border-zinc-800 hover:bg-zinc-900 text-zinc-300"
              >
                <Moon className="h-3 w-3 text-emerald-400" />
                <span>Dark</span>
              </button>
              <button
                onClick={() => {
                  setTheme('light');
                  onClose();
                }}
                className="flex items-center justify-center gap-1.5 py-1.5 rounded border border-zinc-800 hover:bg-zinc-900 text-zinc-300"
              >
                <Sun className="h-3 w-3 text-amber-400" />
                <span>Light</span>
              </button>
              <button
                onClick={() => {
                  setTheme('system');
                  onClose();
                }}
                className="flex items-center justify-center gap-1.5 py-1.5 rounded border border-zinc-800 hover:bg-zinc-900 text-zinc-300"
              >
                <Laptop className="h-3 w-3 text-blue-400" />
                <span>System</span>
              </button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
