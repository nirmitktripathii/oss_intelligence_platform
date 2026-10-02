'use client';

import * as React from 'react';
import {
  TelegramError,
  fetchTelegramStatus,
  startTelegramLink,
  unlinkTelegram,
  type TelegramStatus,
} from '@/lib/telegram-client';

const POLL_MS = 3000;

export type TelegramState = 'unavailable' | 'unlinked' | 'waiting' | 'linked';

/**
 * The signed-in user's Telegram link. `link()` opens the one-time t.me link, then polls until the
 * server has seen the user press Start (or the link expires).
 */
export function useTelegram(enabled: boolean) {
  const [status, setStatus] = React.useState<TelegramStatus | null>(null);
  const [waitingUntil, setWaitingUntil] = React.useState<number | null>(null);
  const [linkUrl, setLinkUrl] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async (signal?: AbortSignal) => {
    try {
      setStatus(await fetchTelegramStatus(signal));
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setStatus(null);
    }
  }, []);

  React.useEffect(() => {
    if (!enabled) {
      setStatus(null);
      setWaitingUntil(null);
      setLinkUrl(null);
      return;
    }
    const ctl = new AbortController();
    void refresh(ctl.signal);
    return () => ctl.abort();
  }, [enabled, refresh]);

  // While waiting for Start: ask every few seconds, and give up when the code has expired.
  React.useEffect(() => {
    if (waitingUntil === null) return;
    if (status?.linked) {
      setWaitingUntil(null);
      setLinkUrl(null);
      return;
    }
    const timer = window.setInterval(() => {
      if (Date.now() > waitingUntil) {
        setWaitingUntil(null);
        setLinkUrl(null);
        setError('That link expired. Press Link Telegram to get a new one.');
      } else {
        void refresh();
      }
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [waitingUntil, status?.linked, refresh]);

  const link = React.useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const { url, expires_in } = await startTelegramLink();
      setLinkUrl(url);
      setWaitingUntil(Date.now() + expires_in * 1000);
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (err) {
      setError(err instanceof TelegramError ? err.message : 'Could not start linking.');
    } finally {
      setBusy(false);
    }
  }, []);

  const unlink = React.useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await unlinkTelegram();
      await refresh();
    } catch (err) {
      setError(err instanceof TelegramError ? err.message : 'Could not unlink.');
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  const cancel = React.useCallback(() => {
    setWaitingUntil(null);
    setLinkUrl(null);
  }, []);

  const state: TelegramState = !status?.configured
    ? 'unavailable'
    : status.linked
      ? 'linked'
      : waitingUntil !== null
        ? 'waiting'
        : 'unlinked';

  return { state, linkUrl, busy, error, link, unlink, cancel, dismissError: () => setError(null) };
}
