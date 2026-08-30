'use client';

import * as React from 'react';
import { CommunityCluster } from '@/types/graph';
import { Network } from 'lucide-react';

interface GraphLegendProps {
  communities: Record<number, CommunityCluster>;
  selectedCommunity: number | 'all';
  onSelectCommunity: (id: number | 'all') => void;
}

export function GraphLegend({
  communities,
  selectedCommunity,
  onSelectCommunity,
}: GraphLegendProps) {
  const communityList = Object.values(communities);

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/90 p-3 font-mono text-xs text-zinc-300 space-y-3 backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2">
        <span className="font-semibold text-zinc-200 flex items-center gap-1.5 text-xs">
          <Network className="h-3.5 w-3.5 text-purple-400" />
          <span>AST Community Clusters</span>
        </span>
        <button
          type="button"
          onClick={() => onSelectCommunity('all')}
          className={`text-[10px] px-1.5 py-0.5 rounded border transition-colors ${
            selectedCommunity === 'all'
              ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300 font-bold'
              : 'border-zinc-800 text-zinc-500 hover:text-zinc-300'
          }`}
        >
          All Clusters
        </button>
      </div>

      {/* Cluster List */}
      <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
        {communityList.map((comm) => {
          const isSelected = selectedCommunity === comm.id;
          return (
            <button
              key={comm.id}
              type="button"
              onClick={() => onSelectCommunity(isSelected ? 'all' : comm.id)}
              className={`w-full flex items-center justify-between p-1.5 rounded text-left transition-all ${
                isSelected
                  ? 'bg-zinc-900 border border-zinc-700 text-zinc-100 shadow-sm'
                  : 'hover:bg-zinc-900/60 text-zinc-400'
              }`}
            >
              <div className="flex items-center gap-2 truncate">
                <span
                  className="h-2.5 w-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: comm.color }}
                />
                <span className="text-[11px] truncate font-medium">{comm.name}</span>
              </div>
              <span className="text-[10px] text-zinc-500 shrink-0">
                {comm.nodeCount} nodes
              </span>
            </button>
          );
        })}
      </div>

      {/* Symbol Indicators */}
      <div className="border-t border-zinc-800/80 pt-2 space-y-1 text-[10px] text-zinc-400">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400 border border-emerald-300 ring-2 ring-emerald-500/30"></span>
          <span>Target AST Symbol / Localized File</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-amber-400"></span>
          <span>God Node (High Centrality Hub)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-emerald-500"></div>
          <span>Extracted AST Reference (Solid)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 border-t border-dashed border-zinc-500"></div>
          <span>Inferred Heuristic Blast Radius</span>
        </div>
      </div>
    </div>
  );
}
