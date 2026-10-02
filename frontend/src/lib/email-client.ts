import { API_BASE } from '@/lib/api-base';
import { authHeaders } from '@/lib/auth-client';

/** The one email address the signed-in user confirmed, and the calls that link it. */
export interface EmailStatus {
  /** The operator has set up outgoing mail on this backend, so a confirmation code can be sent. */
  configured: boolean;
  linked: boolean;
  /** Masked, like a***e@example.com. The full address is never sent back. */
  address: string | null;
  linked_at: string | null;
}

export class EmailLinkError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = 'EmailLinkError';
  }
}

async function call<T>(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/email/${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(init.headers ?? {}) },
      signal,
    });
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    throw new EmailLinkError('Could not reach the server. Try again in a moment.');
  }
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = typeof body?.detail === 'string' ? body.detail : '';
    } catch {
      /* not JSON, or a validation error list */
    }
    if (res.status === 422 && !detail) detail = 'Enter one plain email address.';
    if (res.status === 429 && !detail) detail = 'Too many tries. Give it a minute.';
    throw new EmailLinkError(detail || `Request failed (${res.status}).`, res.status);
  }
  return (await res.json()) as T;
}

export const fetchEmailStatus = (signal?: AbortSignal) => call<EmailStatus>('status', {}, signal);
export const startEmailLink = (address: string) =>
  call<{ expires_in: number }>('link', { method: 'POST', body: JSON.stringify({ address }) });
export const confirmEmailLink = (code: string) =>
  call<EmailStatus>('confirm', { method: 'POST', body: JSON.stringify({ code }) });
export const unlinkEmail = () => call<{ was_linked: boolean }>('link', { method: 'DELETE' });
