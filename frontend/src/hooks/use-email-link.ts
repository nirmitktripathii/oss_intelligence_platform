'use client';

import * as React from 'react';
import {
  EmailLinkError,
  confirmEmailLink,
  fetchEmailStatus,
  startEmailLink,
  unlinkEmail,
  type EmailStatus,
} from '@/lib/email-client';

export type EmailLinkState = 'unavailable' | 'unlinked' | 'awaiting-code' | 'linked';

/**
 * The signed-in user's confirmed email address. `sendCode(address)` mails a six-digit code to it;
 * `confirm(code)` links the address once the code is typed back. The address is only ever shown
 * masked, as the server returns it.
 */
export function useEmailLink(enabled: boolean) {
  const [status, setStatus] = React.useState<EmailStatus | null>(null);
  const [pendingFor, setPendingFor] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async (signal?: AbortSignal) => {
    try {
      setStatus(await fetchEmailStatus(signal));
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setStatus(null);
    }
  }, []);

  React.useEffect(() => {
    if (!enabled) {
      setStatus(null);
      setPendingFor(null);
      return;
    }
    const ctl = new AbortController();
    void refresh(ctl.signal);
    return () => ctl.abort();
  }, [enabled, refresh]);

  const sendCode = React.useCallback(async (address: string) => {
    setBusy(true);
    setError(null);
    try {
      await startEmailLink(address.trim());
      setPendingFor(address.trim());
    } catch (err) {
      setError(err instanceof EmailLinkError ? err.message : 'Could not send the code.');
    } finally {
      setBusy(false);
    }
  }, []);

  const confirm = React.useCallback(async (code: string) => {
    setBusy(true);
    setError(null);
    try {
      setStatus(await confirmEmailLink(code.trim()));
      setPendingFor(null);
    } catch (err) {
      setError(err instanceof EmailLinkError ? err.message : 'Could not confirm the code.');
    } finally {
      setBusy(false);
    }
  }, []);

  const unlink = React.useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await unlinkEmail();
      await refresh();
    } catch (err) {
      setError(err instanceof EmailLinkError ? err.message : 'Could not unlink.');
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  const cancel = React.useCallback(() => {
    setPendingFor(null);
    setError(null);
  }, []);

  const state: EmailLinkState = !status?.configured
    ? 'unavailable'
    : status.linked
      ? 'linked'
      : pendingFor !== null
        ? 'awaiting-code'
        : 'unlinked';

  return {
    state,
    maskedAddress: status?.address ?? null,
    pendingFor,
    busy,
    error,
    sendCode,
    confirm,
    unlink,
    cancel,
    dismissError: () => setError(null),
  };
}
