'use client';

import { Check, Send, Unlink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTelegram } from '@/hooks/use-telegram';

/**
 * Where the signed-in user's mission reports go. Linking is explicit: the button opens a one-time
 * Telegram link, and pressing Start there connects that chat to this account, nothing else.
 */
export function TelegramPanel({ enabled }: { enabled: boolean }) {
  const tg = useTelegram(enabled);
  if (!enabled || tg.state === 'unavailable') return null;

  return (
    <div className="space-y-1.5 rounded-md border border-border bg-card/60 px-3 py-2 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Send className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="font-semibold">Telegram reports</span>
          {tg.state === 'linked' && (
            <span className="flex items-center gap-1 text-emerald-500">
              <Check className="h-3.5 w-3.5" />
              Linked. Reports go to your chat.
            </span>
          )}
          {tg.state === 'unlinked' && (
            <span className="text-muted-foreground">Not linked. Link it to get a report when a mission finishes.</span>
          )}
          {tg.state === 'waiting' && (
            <span className="text-muted-foreground">Open Telegram and press Start. This updates by itself.</span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {tg.state === 'unlinked' && (
            <Button size="sm" variant="outline" className="h-7 gap-1.5 text-xs" onClick={tg.link} disabled={tg.busy}>
              <Send className="h-3.5 w-3.5" />
              Link Telegram
            </Button>
          )}
          {tg.state === 'waiting' && (
            <>
              {tg.linkUrl && (
                <a
                  href={tg.linkUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline underline-offset-2"
                >
                  Open Telegram again
                </a>
              )}
              <Button size="sm" variant="ghost" className="h-7 text-xs text-muted-foreground" onClick={tg.cancel}>
                Cancel
              </Button>
            </>
          )}
          {tg.state === 'linked' && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 gap-1.5 text-xs text-muted-foreground"
              onClick={tg.unlink}
              disabled={tg.busy}
            >
              <Unlink className="h-3.5 w-3.5" />
              Unlink
            </Button>
          )}
        </div>
      </div>
      {tg.error && (
        <p className="text-destructive" role="alert">
          {tg.error}{' '}
          <button type="button" className="underline" onClick={tg.dismissError}>
            Dismiss
          </button>
        </p>
      )}
    </div>
  );
}
