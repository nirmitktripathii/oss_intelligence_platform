import * as React from 'react';
import Link from 'next/link';
import { Terminal, Shield, Heart, Zap, Github, Twitter, MessageSquare } from 'lucide-react';
import { SITE_CONFIG } from '@/lib/constants';

export function Footer() {
  return (
    <footer className="w-full border-t border-zinc-800/80 bg-zinc-950 text-zinc-400 font-mono text-xs mt-auto">
      <div className="container py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 pb-8 border-b border-zinc-800/60">
          {/* Col 1: Brand & Status */}
          <div className="space-y-3 md:col-span-2">
            <div className="flex items-center gap-2 text-zinc-100 font-bold">
              <Terminal className="h-4 w-4 text-emerald-400" />
              <span>{SITE_CONFIG.name} / {SITE_CONFIG.terminalName}</span>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed max-w-md">
              {SITE_CONFIG.description}
            </p>
            <div className="flex items-center gap-2 pt-1">
              <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-900 border border-zinc-800 text-[11px] text-zinc-300">
                <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                <span>All Scraping & Dispatch Systems Operational</span>
              </div>
            </div>
          </div>

          {/* Col 2: Shortcuts */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">Terminal Hotkeys</h4>
            <ul className="space-y-1.5 text-[11px] text-zinc-400">
              <li className="flex items-center justify-between">
                <span>Focus Search Bar</span>
                <kbd className="px-1.5 py-0.5 rounded border border-zinc-700 bg-zinc-900 text-zinc-300">/</kbd>
              </li>
              <li className="flex items-center justify-between">
                <span>Next / Previous Issue</span>
                <kbd className="px-1.5 py-0.5 rounded border border-zinc-700 bg-zinc-900 text-zinc-300">J / K</kbd>
              </li>
              <li className="flex items-center justify-between">
                <span>Open Workbench</span>
                <kbd className="px-1.5 py-0.5 rounded border border-zinc-700 bg-zinc-900 text-zinc-300">Enter</kbd>
              </li>
              <li className="flex items-center justify-between">
                <span>Command Palette</span>
                <kbd className="px-1.5 py-0.5 rounded border border-zinc-700 bg-zinc-900 text-zinc-300">⌘K</kbd>
              </li>
            </ul>
          </div>

          {/* Col 3: Ecosystem */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">Platforms & Integrations</h4>
            <ul className="space-y-1 text-xs">
              <li>
                <Link href="/graph" className="hover:text-emerald-400 transition-colors">
                  Graphify AST Knowledge Graph
                </Link>
              </li>
              <li>
                <Link href="/pricing" className="hover:text-emerald-400 transition-colors">
                  Pro & Team Subscriptions
                </Link>
              </li>
              <li>
                <a
                  href="https://polar.sh"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-emerald-400 transition-colors"
                >
                  Polar.sh Bounty Network
                </a>
              </li>
              <li>
                <a
                  href="https://algora.io"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-emerald-400 transition-colors"
                >
                  Algora Bounty Engine
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-zinc-500">
          <div className="flex items-center gap-1">
            <span>Built for Open-Source Builders worldwide.</span>
            <span>Zero mock fallbacks. 100% genuine live issues.</span>
          </div>

          <div className="flex items-center gap-4 text-zinc-400">
            <a
              href={SITE_CONFIG.links.github}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-zinc-200 transition-colors flex items-center gap-1"
            >
              <Github className="h-3.5 w-3.5" />
              <span>GitHub</span>
            </a>
            <a
              href={SITE_CONFIG.links.discord}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-zinc-200 transition-colors flex items-center gap-1"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span>Discord</span>
            </a>
            <a
              href={SITE_CONFIG.links.twitter}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-zinc-200 transition-colors flex items-center gap-1"
            >
              <Twitter className="h-3.5 w-3.5" />
              <span>X / Twitter</span>
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
