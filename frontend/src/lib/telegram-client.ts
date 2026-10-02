import { API_BASE } from '@/lib/api-base';
import { authHeaders } from '@/lib/auth-client';

/** Whether the signed-in user's mission reports can go to Telegram, and the calls that link one. */
export interface TelegramStatus {
  /** The operator has set up the bot and its webhook on this backend. */
  configured: boolean;
  linked: boolean;
  linked_at: string | null;
}

export interface TelegramLinkStart {
  /** t.me link; opening it and pressing Start links that Telegram chat to this account. */
  url: string;
  expires_in: number;
}

export class TelegramError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = 'TelegramError';
  }
}

async function call<T>(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/telegram/${path}`, {
      ...init,
      headers: { ...authHeaders(), ...(init.headers ?? {}) },
      signal,
    });
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    throw new TelegramError('Could not reach the server. Try again in a moment.');
  }
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = typeof body?.detail === 'string' ? body.detail : '';
    } catch {
      /* not JSON */
    }
    if (res.status === 429) throw new TelegramError('Too many tries. Give it a minute.', 429);
    throw new TelegramError(detail || `Request failed (${res.status}).`, res.status);
  }
  return (await res.json()) as T;
}

export const fetchTelegramStatus = (signal?: AbortSignal) => call<TelegramStatus>('status', {}, signal);
export const startTelegramLink = () => call<TelegramLinkStart>('link', { method: 'POST' });
export const unlinkTelegram = () => call<{ was_linked: boolean }>('link', { method: 'DELETE' });
