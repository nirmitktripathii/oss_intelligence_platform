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
    <div className="flex flex-col h-[calc(100vh-3.5rem)] w-full overflow-hidden bg-background font-mono text-foreground">
      {/* Top Header Bar: Repository Switcher & Telemetry HUD */}
      <div className="flex flex-wrap items-center justify-between border-b border-border bg-background/95 px-4 py-2.5 z-30 gap-3 backdrop-blur-xl">
        {/* Left: Back & Title */}
        <div className="flex items-center gap-3">
          <Link href="/">
            <Button variant="outline" size="xs" className="gap-1 text-muted-foreground hover:text-foreground border-border bg-card/60">
              <ArrowLeft className="h-3 w-3" />
              <span>Terminal</span>
            </Button>
          </Link>

          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/15 text-accent border border-accent/30 shadow-[0_0_10px_hsl(var(--accent)/0.15)]">
              <Network className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xs font-extrabold text-foreground tracking-tight">
                  Graphify AST Architecture Explorer
                </h1>
                <span className="text-[10px] bg-accent/20 text-accent px-1.5 py-0.2 rounded border border-accent/30 font-bold hidden sm:inline">
                  v2.4
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Center: Interactive Multi-Repository Switcher */}
        <div className="flex items-center gap-1.5 rounded-xl border border-border bg-card/80 p-1 text-xs shadow-inner">
          <span className="text-[11px] text-muted-foreground px-2 font-semibold flex items-center gap-1 hidden md:flex">
            <GitFork className="h-3 w-3 text-primary" />
            <span>Target Repo:</span>
          </span>
          {Object.values(REPOSITORY_GRAPH_CATALOG).map((repo) => (
            <button
              key={repo.id}
              onClick={() => setSelectedRepoId(repo.id)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                selectedRepoId === repo.id
                  ? 'bg-primary text-primary-foreground font-bold shadow-md'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
              }`}
            >
              <span>{repo.name.split('/')[0]}</span>
              {repo.id === 'gitscout' && (
                <span className="text-[9px] bg-primary/20 text-primary px-1 rounded uppercase font-bold">
                  Current Project
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Right: Architecture Summary Badges */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <div className="hidden lg:flex items-center gap-2 text-[11px] border-l border-border pl-3">
            <span className="text-muted-foreground">Modules:</span>
            <span className="font-bold text-foreground">{activeRepo.data.metadata.totalFiles} files</span>
            <span className="text-muted-foreground">•</span>
            <span className="text-muted-foreground">AST Nodes:</span>
            <span className="font-bold text-primary">{activeRepo.data.nodes.length}</span>
            <span className="text-muted-foreground">•</span>
            <span className="text-muted-foreground">Connections:</span>
            <span className="font-bold text-accent">{activeRepo.data.edges.length}</span>
          </div>

          <a href="https://gitscout-api.onrender.com/docs" target="_blank" rel="noreferrer">
            <Button variant="ghost" size="xs" className="text-muted-foreground hover:text-foreground gap-1 text-[11px]">
              <span>API Specs</span>
              <span className="text-primary">↗</span>
            </Button>
          </a>
        </div>
      </div>

      {/* Graph Visualizer Canvas */}
      <div className="flex-1 w-full h-full relative overflow-hidden bg-background">
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
