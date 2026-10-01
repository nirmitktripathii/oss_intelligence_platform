import { API_BASE } from '@/lib/api-client';

/**
 * Sign-in state for the agent. The API hands the browser a short-lived signed token in the URL
 * fragment after GitHub sign-in (`/alexa#token=...`; fragments are never sent to a server). It is
 * kept in sessionStorage so a reload keeps you signed in but closing the tab does not.
 */
const KEY = 'gitscout.auth.token';

export interface Me {
  signed_in: boolean;
  login: string | null;
  /** May run tools that change things (the server's allow-list says so). */
  can_write: boolean;
  /** The operator has configured GitHub sign-in on this backend. */
  sign_in_available: boolean;
}

export const SIGNED_OUT: Me = { signed_in: false, login: null, can_write: false, sign_in_available: false };

export function getToken(): string | null {
  try {
    return window.sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    window.sessionStorage.setItem(KEY, token);
  } catch {
    /* storage blocked: the token only lives for this page load */
    memoryToken = token;
  }
}

export function clearToken(): void {
  memoryToken = null;
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    /* nothing to clear */
  }
}

let memoryToken: string | null = null;

/** Headers that identify the signed-in user, or none for an anonymous caller. */
export function authHeaders(): Record<string, string> {
  const token = getToken() ?? memoryToken;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Pick up `#token=...` after the GitHub round trip, store it, and remove it from the address bar
 * so it is not left in history or copied with the link. Returns an error code from
 * `?auth_error=` when sign-in failed.
 */
export function captureSignIn(): { signedIn: boolean; error: string | null } {
  const url = new URL(window.location.href);
  const hash = new URLSearchParams(url.hash.replace(/^#/, ''));
  const token = hash.get('token');
  const error = url.searchParams.get('auth_error');
  if (!token && !error) return { signedIn: false, error: null };

  if (token) setToken(token);
  url.hash = '';
  url.searchParams.delete('auth_error');
  window.history.replaceState(null, '', url.pathname + url.search);
  return { signedIn: Boolean(token), error };
}

export async function fetchMe(signal?: AbortSignal): Promise<Me> {
  try {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders(), signal });
    if (!res.ok) return SIGNED_OUT;
    const me = (await res.json()) as Me;
    // An expired or invalid token reads as signed out: drop it so we stop sending it.
    if (!me.signed_in) clearToken();
    return me;
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    return SIGNED_OUT;
  }
}

export const signInUrl = `${API_BASE}/auth/github/login`;

export const AUTH_ERRORS: Record<string, string> = {
  state: 'Sign-in could not be verified. Please try again.',
  exchange: 'GitHub did not accept the sign-in. Please try again.',
  github: 'Could not reach GitHub. Please try again.',
  profile: 'GitHub did not return a profile. Please try again.',
};
