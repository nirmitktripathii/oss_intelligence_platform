'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Issue } from '@/types/issue';
import { useToast } from '@/components/ui/toast';
import { Share2, Copy, Check, Twitter, ExternalLink, ShieldCheck } from 'lucide-react';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  issue: Issue | null;
}

export function ShareModal({ isOpen, onClose, issue }: ShareModalProps) {
  const { toast } = useToast();
  const [copiedLink, setCopiedLink] = React.useState(false);
  const [copiedBadge, setCopiedBadge] = React.useState(false);

  if (!issue) return null;

  const shareUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/issues/${encodeURIComponent(issue.id)}`
    : `https://gitscout.dev/issues/${encodeURIComponent(issue.id)}`;

  const badgeMarkdown = `[![GitScout Triage](https://img.shields.io/badge/GitScout-Triaged%20Issue-10b981?style=for-the-badge&logo=github)](${shareUrl})`;

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopiedLink(true);
      toast({ title: 'Link Copied', description: 'Workbench share link copied to clipboard.', type: 'success' });
      setTimeout(() => setCopiedLink(false), 2500);
    } catch {
      // fallback
    }
  };

  const handleCopyBadge = async () => {
    try {
      await navigator.clipboard.writeText(badgeMarkdown);
      setCopiedBadge(true);
      toast({ title: 'Badge Markdown Copied', description: 'Paste into your GitHub PR or README.', type: 'success' });
      setTimeout(() => setCopiedBadge(false), 2500);
    } catch {
      // fallback
    }
  };

  const tweetText = encodeURIComponent(
    `Check out this AI-triaged open-source issue on @gitscout_app: ${issue.title} (${issue.repository.name} #${issue.githubIssueNumber})${issue.bounty ? ` with $${issue.bounty.amountUsd} bounty!` : ''}\n\n${shareUrl}`
  );

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md border-border bg-background font-mono text-foreground">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/20 text-primary border border-primary/40">
              <Share2 className="h-4 w-4" />
            </div>
            <div>
              <DialogTitle className="text-sm font-semibold text-foreground">
                Share Issue Intelligence & Triage
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Export workbench link or embed verified Proof-of-Work badges in your pull request.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {/* Direct Link */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-muted-foreground">Direct Workbench URL</label>
            <div className="flex gap-2">
              <Input readOnly value={shareUrl} className="text-xs text-foreground font-mono bg-card/80 select-all" />
              <Button variant="outline" size="sm" onClick={handleCopyLink} className="gap-1 text-xs shrink-0">
                {copiedLink ? <Check className="h-3.5 w-3.5 text-primary" /> : <Copy className="h-3.5 w-3.5" />}
                {copiedLink ? 'Copied' : 'Copy'}
              </Button>
            </div>
          </div>

          {/* Social Share Buttons */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-muted-foreground">Social Broadcast</label>
            <div className="flex gap-2">
              <a
                href={`https://twitter.com/intent/tweet?text=${tweetText}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1"
              >
                <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs text-accent border-accent/30 hover:bg-accent/10">
                  <Twitter className="h-3.5 w-3.5" />
                  Post to X / Twitter
                </Button>
              </a>
              <a
                href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1"
              >
                <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs text-accent border-accent/30 hover:bg-accent/10">
                  <ExternalLink className="h-3.5 w-3.5" />
                  Share on LinkedIn
                </Button>
              </a>
            </div>
          </div>

          {/* GitHub Proof-of-Work Badge */}
          <div className="rounded border border-border bg-card/40 p-3 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-primary">
              <ShieldCheck className="h-4 w-4" />
              <span>Verified Proof-of-Work Badge</span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Include this badge in your PR description to prove the fix conforms to repository CONTRIBUTING guidelines.
            </p>
            <div className="flex items-center justify-between gap-2 bg-background p-2 rounded border border-border">
              <code className="text-[10px] text-muted-foreground truncate flex-1">{badgeMarkdown}</code>
              <Button variant="terminal" size="xs" onClick={handleCopyBadge} className="gap-1 shrink-0">
                {copiedBadge ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copiedBadge ? 'Copied' : 'Copy Badge'}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
