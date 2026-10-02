// Kept apart from api-client so auth-client and api-client can both use it without importing each other.
export function resolveApiBase(rawUrl?: string): string {
  let url = (rawUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').trim();
  url = url.replace(/\/+$/, '');
  if (!url.endsWith('/api/v1')) {
    url = `${url}/api/v1`;
  }
  return url;
}

export const API_BASE = resolveApiBase();
