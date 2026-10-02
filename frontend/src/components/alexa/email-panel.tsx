'use client';

import * as React from 'react';
import { Check, Mail, Unlink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useEmailLink } from '@/hooks/use-email-link';

/**
 * The one address the assistant may email. Linking proves the mailbox: a six-digit code is sent to
 * the address and must be typed back, so nobody can point emails at an address that is not theirs.
 */
export function EmailPanel({ enabled }: { enabled: boolean }) {
  const mail = useEmailLink(enabled);
  const [address, setAddress] = React.useState('');
  const [code, setCode] = React.useState('');
  if (!enabled || mail.state === 'unavailable') return null;

  const inputClass =
    'h-7 min-w-0 flex-1 rounded-md border border-border bg-background px-2 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring';

  return (
    <div className="space-y-1.5 rounded-md border border-border bg-card/60 px-3 py-2 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Mail className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="font-semibold">Email me</span>
          {mail.state === 'linked' && (
            <span className="flex items-center gap-1 text-emerald-500">
              <Check className="h-3.5 w-3.5" />
              Emails go to {mail.maskedAddress}. You approve each one.
            </span>
          )}
          {mail.state === 'unlinked' && (
            <span className="text-muted-foreground">Confirm an address to let the assistant email you.</span>
          )}
          {mail.state === 'awaiting-code' && (
            <span className="text-muted-foreground">We sent a code to {mail.pendingFor}. It expires in 10 minutes.</span>
          )}
        </div>
        {mail.state === 'linked' && (
          <Button
            size="sm"
            variant="ghost"
            className="h-7 gap-1.5 text-xs text-muted-foreground"
            onClick={mail.unlink}
            disabled={mail.busy}
          >
            <Unlink className="h-3.5 w-3.5" />
            Unlink
          </Button>
        )}
      </div>

      {mail.state === 'unlinked' && (
        <form
          className="flex flex-wrap items-center gap-1.5"
          onSubmit={(e) => {
            e.preventDefault();
            void mail.sendCode(address);
          }}
        >
          <input
            type="email"
            required
            autoComplete="email"
            placeholder="you@example.com"
            aria-label="Email address"
            className={inputClass}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
          />
          <Button type="submit" size="sm" variant="outline" className="h-7 text-xs" disabled={mail.busy || !address.trim()}>
            Send code
          </Button>
        </form>
      )}

      {mail.state === 'awaiting-code' && (
        <form
          className="flex flex-wrap items-center gap-1.5"
          onSubmit={(e) => {
            e.preventDefault();
            void mail.confirm(code);
          }}
        >
          <input
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            placeholder="6-digit code"
            aria-label="Confirmation code"
            className={inputClass}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
          />
          <Button type="submit" size="sm" variant="outline" className="h-7 text-xs" disabled={mail.busy || code.length !== 6}>
            Confirm
          </Button>
          <Button type="button" size="sm" variant="ghost" className="h-7 text-xs text-muted-foreground" onClick={mail.cancel}>
            Use another address
          </Button>
        </form>
      )}

      {mail.error && (
        <p className="text-destructive" role="alert">
          {mail.error}{' '}
          <button type="button" className="underline" onClick={mail.dismissError}>
            Dismiss
          </button>
        </p>
      )}
    </div>
  );
}
