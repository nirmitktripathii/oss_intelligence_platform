'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { GraphCanvas } from './graph-canvas';
import { SAMPLE_GRAPH_DATA } from '@/lib/constants';
import { Network } from 'lucide-react';

interface GraphifyModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetFile?: string;
}

export function GraphifyModal({ isOpen, onClose, targetFile }: GraphifyModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-6xl w-[95vw] h-[85vh] p-0 border-zinc-800 bg-zinc-950 font-mono flex flex-col overflow-hidden">
        <DialogHeader className="p-4 pb-2 border-b border-zinc-800 shrink-0">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-purple-500/20 text-purple-400 border border-purple-500/40">
              <Network className="h-4 w-4" />
            </div>
            <div>
              <DialogTitle className="text-sm font-semibold text-zinc-100">
                Graphify Knowledge Graph & AST Blast Radius Visualizer
              </DialogTitle>
              <DialogDescription className="text-xs text-zinc-400">
                Interactive dependency paths, community clusters, and target function callers/callees.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 w-full h-full relative overflow-hidden">
          <GraphCanvas data={SAMPLE_GRAPH_DATA} initialTargetFile={targetFile} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
