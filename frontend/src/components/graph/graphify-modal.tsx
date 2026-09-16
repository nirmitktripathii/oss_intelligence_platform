'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { BlastRadiusMap } from './blast-radius-map';
import { LocalizedFile } from '@/types/triage';
import { Crosshair } from 'lucide-react';

interface GraphifyModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetFile?: string;
  localizedFiles?: LocalizedFile[];
  repoOwner?: string;
  repoName?: string;
  issueNumber?: number;
  isEnhanced?: boolean;
}

export function GraphifyModal({
  isOpen,
  onClose,
  targetFile,
  localizedFiles,
  repoOwner,
  repoName,
  issueNumber,
  isEnhanced,
}: GraphifyModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-6xl w-[95vw] h-[85vh] p-0 border-border bg-background font-mono flex flex-col overflow-hidden">
        <DialogHeader className="p-4 pb-2 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-accent/20 text-accent border border-accent/40">
              <Crosshair className="h-4 w-4" />
            </div>
            <div>
              <DialogTitle className="text-sm font-semibold text-foreground">
                Blast Radius — where this fix ripples outward
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Built from this issue&apos;s real localized files. The center is where to edit
                first; each ring outward is a wider impact zone.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 w-full h-full relative overflow-hidden">
          <BlastRadiusMap
            localizedFiles={localizedFiles || []}
            repoOwner={repoOwner}
            repoName={repoName}
            issueNumber={issueNumber}
            isEnhanced={isEnhanced}
            initialTargetFile={targetFile}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
