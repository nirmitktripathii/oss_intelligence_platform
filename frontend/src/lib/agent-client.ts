import { API_BASE } from '@/lib/api-client';
import { authHeaders } from '@/lib/auth-client';
import type { AgentEvent, Mission } from '@/types/agent';

/** Error the UI can show as-is; `status` 503 means the agent is not configured on this backend. */
export class AgentError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = 'AgentError';
  }
}

const EVENT_NAMES = new Set([
  'mission_started',
  'thinking',
  'step',
  'tool_start',
  'tool_done',
  'mission',
  'error',
]);

/** Parse one SSE frame ("event: x\ndata: {...}") into a typed event, or null if it is not ours. */
export function parseFrame(frame: string): AgentEvent | null {
  let event = '';
  const data: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) data.push(line.slice(5).trim());
  }
  if (!EVENT_NAMES.has(event) || data.length === 0) return null;
  try {
    return { event, data: JSON.parse(data.join('\n')) } as AgentEvent;
  } catch {
    return null;
  }
}

async function failure(res: Response): Promise<AgentError> {
  let detail = '';
  try {
    const body = await res.json();
    detail = typeof body?.detail === 'string' ? body.detail : '';
  } catch {
    /* not JSON */
  }
  if (res.status === 503) {
    return new AgentError('The agent is not enabled on this backend yet.', 503);
  }
  if (res.status === 401) {
    return new AgentError(detail || 'Sign in to do that.', 401);
  }
  if (res.status === 403) {
    return new AgentError(detail || 'This account is not allowed to do that.', 403);
  }
  if (res.status === 429) {
    return new AgentError('Too many requests. Give it a minute and try again.', 429);
  }
  return new AgentError(detail || `Request failed (${res.status}).`, res.status);
}

/**
 * POST and read the Server-Sent Events response. EventSource cannot POST or send the
 * X-Session-Token header, so the stream is read with fetch. Resolves with the final mission.
 */
async function stream(
  path: string,
  body: unknown,
  sessionToken: string | null,
  onEvent: (e: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<Mission> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...authHeaders() };
  if (sessionToken) headers['X-Session-Token'] = sessionToken;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    throw new AgentError('Could not reach the backend.');
  }
  if (!res.ok || !res.body) throw await failure(res);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let mission: Mission | null = null;

  const handle = (frame: string) => {
    const evt = parseFrame(frame);
    if (!evt) return;
    if (evt.event === 'error') {
      throw new AgentError(evt.data.detail || 'The mission failed.', evt.data.status);
    }
    if (evt.event === 'mission') mission = evt.data;
    onEvent(evt);
  };

  for (;;) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n');
    let cut: number;
    while ((cut = buffer.indexOf('\n\n')) !== -1) {
      handle(buffer.slice(0, cut));
      buffer = buffer.slice(cut + 2);
    }
    if (done) break;
  }
  if (buffer.trim()) handle(buffer);

  if (!mission) throw new AgentError('The connection closed before the mission finished.');
  return mission;
}

export function startMission(
  utterance: string,
  session: { id: string; token: string } | null,
  onEvent: (e: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<Mission> {
  return stream(
    '/agent/missions/stream',
    { utterance, session_id: session?.id ?? null },
    session?.token ?? null,
    onEvent,
    signal,
  );
}

export function resolveApproval(
  missionId: string,
  approved: boolean,
  sessionToken: string,
  onEvent: (e: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<Mission> {
  return stream(
    `/agent/missions/${encodeURIComponent(missionId)}/approval/stream`,
    { approved },
    sessionToken,
    onEvent,
    signal,
  );
}
