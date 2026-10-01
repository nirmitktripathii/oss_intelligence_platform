'use client';

import * as React from 'react';
import {
  AUTH_ERRORS,
  SIGNED_OUT,
  captureSignIn,
  clearToken,
  fetchMe,
  signInUrl,
  type Me,
} from '@/lib/auth-client';

/** Who is using the assistant, and whether they may approve actions that change things. */
export function useAuth() {
  const [me, setMe] = React.useState<Me>(SIGNED_OUT);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const ctl = new AbortController();
    const { error: code } = captureSignIn();
    if (code) setError(AUTH_ERRORS[code] ?? 'Sign-in failed. Please try again.');
    fetchMe(ctl.signal)
      .then(setMe)
      .catch(() => undefined)
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, []);

  const signIn = React.useCallback(() => {
    window.location.assign(signInUrl);
  }, []);

  const signOut = React.useCallback(() => {
    clearToken();
    setMe((m) => ({ ...SIGNED_OUT, sign_in_available: m.sign_in_available }));
  }, []);

  return { me, loading, error, dismissError: () => setError(null), signIn, signOut };
}
