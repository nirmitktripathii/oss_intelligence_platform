'use client';

import * as React from 'react';
import { GraphCanvas } from '@/components/graph/graph-canvas';
import { REPOSITORY_GRAPH_CATALOG } from '@/lib/graph-data';
import { Network, ArrowLeft, GitFork, Star, ShieldCheck, Sparkles, BookOpen, Layers, Terminal } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function GraphPage() {
  const [selectedRepoId, setSelectedRepoId] = React.useState<string>('gitscout');
  const activeRepo = REPOSITORY_GRAPH_CATALOG[selectedRepoId] || REPOSITORY_GRAPH_CATALOG.gitscout;

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] w-full overflow-hidden bg-zinc-950 font-mono text-zinc-100">
      {/* Top Header Bar: Repository Switcher & Telemetry HUD */}
      <div className="flex flex-wrap items-center justify-between border-b border-zinc-800 bg-zinc-950/95 px-4 py-2.5 z-30 gap-3 backdrop-blur-xl">
        {/* Left: Back & Title */}
        <div className="flex items-center gap-3">
          <Link href="/">
            <Button variant="outline" size="xs" className="gap-1 text-zinc-400 hover:text-white border-zinc-800 bg-zinc-900/60">
              <ArrowLeft className="h-3 w-3" />
              <span>Terminal</span>
            </Button>
          </Link>

          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-500/15 text-purple-400 border border-purple-500/30 shadow-[0_0_10px_rgba(168,85,247,0.15)]">
              <Network className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xs font-extrabold text-zinc-100 tracking-tight">
                  Graphify AST Architecture Explorer
                </h1>
                <span className="text-[10px] bg-purple-500/20 text-purple-300 px-1.5 py-0.2 rounded border border-purple-500/30 font-bold hidden sm:inline">
                  v2.4
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Center: Interactive Multi-Repository Switcher */}
        <div className="flex items-center gap-1.5 rounded-xl border border-zinc-800 bg-zinc-900/80 p-1 text-xs shadow-inner">
          <span className="text-[11px] text-zinc-400 px-2 font-semibold flex items-center gap-1 hidden md:flex">
            <GitFork className="h-3 w-3 text-emerald-400" />
            <span>Target Repo:</span>
          </span>
          {Object.values(REPOSITORY_GRAPH_CATALOG).map((repo) => (
            <button
              key={repo.id}
              onClick={() => setSelectedRepoId(repo.id)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                selectedRepoId === repo.id
                  ? 'bg-emerald-600 text-white font-bold shadow-md'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
              }`}
            >
              <span>{repo.name.split('/')[0]}</span>
              {repo.id === 'gitscout' && (
                <span className="text-[9px] bg-emerald-400/20 text-emerald-200 px-1 rounded uppercase font-bold">
                  Current Project
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Right: Architecture Summary Badges */}
        <div className="flex items-center gap-3 text-xs text-zinc-400">
          <div className="hidden lg:flex items-center gap-2 text-[11px] border-l border-zinc-800 pl-3">
            <span className="text-zinc-500">Modules:</span>
            <span className="font-bold text-zinc-200">{activeRepo.data.metadata.totalFiles} files</span>
            <span className="text-zinc-700">•</span>
            <span className="text-zinc-500">AST Nodes:</span>
            <span className="font-bold text-emerald-400">{activeRepo.data.nodes.length}</span>
            <span className="text-zinc-700">•</span>
            <span className="text-zinc-500">Connections:</span>
            <span className="font-bold text-cyan-400">{activeRepo.data.edges.length}</span>
          </div>

          <a href="https://gitscout-api.onrender.com/docs" target="_blank" rel="noreferrer">
            <Button variant="ghost" size="xs" className="text-zinc-400 hover:text-white gap-1 text-[11px]">
              <span>API Specs</span>
              <span className="text-emerald-400">↗</span>
            </Button>
          </a>
        </div>
      </div>

      {/* Graph Visualizer Canvas */}
      <div className="flex-1 w-full h-full relative overflow-hidden bg-zinc-950">
        <GraphCanvas
          key={selectedRepoId}
          data={activeRepo.data}
          currentRepoId={selectedRepoId}
          onSelectRepo={setSelectedRepoId}
        />
      </div>
    </div>
  );
}
