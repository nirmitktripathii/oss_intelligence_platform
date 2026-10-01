'use client';

import * as React from 'react';
import { AgentError, resolveApproval, startMission } from '@/lib/agent-client';
import type { AgentEvent, Mission, MissionStep } from '@/types/agent';

export type LiveStepState = 'planned' | 'running' | 'done' | 'failed' | 'awaiting' | 'rejected';

export interface LiveStep {
  index: number;
  tool: string;
  thought: string;
  arguments: Record<string, unknown>;
  requiresApproval: boolean;
  state: LiveStepState;
  error?: string | null;
}

export interface Turn {
  id: string;
  utterance: string;
  /** True while the planner is deciding its next move or a tool is running. */
  working: boolean;
  steps: LiveStep[];
  mission?: Mission;
  error?: string;
  /** The server could not run the agent at all (503): show a setup hint, not a retry. */
  unavailable?: boolean;
}

const fromStep = (s: MissionStep): LiveStep => ({
  index: s.index,
  tool: s.tool,
  thought: s.thought,
  arguments: s.arguments,
  requiresApproval: s.requires_approval,
  state:
    s.status === 'awaiting_approval'
      ? 'awaiting'
      : s.status === 'done'
        ? 'done'
        : s.status === 'rejected'
          ? 'rejected'
          : 'failed',
  error: s.error,
});

function upsert(steps: LiveStep[], next: LiveStep): LiveStep[] {
  const i = steps.findIndex((s) => s.index === next.index);
  if (i === -1) return [...steps, next].sort((a, b) => a.index - b.index);
  const copy = steps.slice();
  copy[i] = { ...copy[i], ...next };
  return copy;
}

function applyEvent(turn: Turn, e: AgentEvent): Turn {
  switch (e.event) {
    case 'thinking':
      return { ...turn, working: true };
    case 'step':
      return {
        ...turn,
        steps: upsert(turn.steps, {
          index: e.data.index,
          tool: e.data.tool,
          thought: e.data.thought,
          arguments: e.data.arguments,
          requiresApproval: e.data.requires_approval,
          state: e.data.requires_approval ? 'awaiting' : 'planned',
        }),
      };
    case 'tool_start':
      return {
        ...turn,
        steps: turn.steps.map((s) => (s.index === e.data.index ? { ...s, state: 'running' } : s)),
      };
    case 'tool_done':
      return {
        ...turn,
        steps: turn.steps.map((s) =>
          s.index === e.data.index
            ? { ...s, state: e.data.status === 'done' ? 'done' : 'failed', error: e.data.error }
            : s,
        ),
      };
    case 'mission':
      // The final mission is authoritative: it replaces whatever the events built.
      return { ...turn, working: false, mission: e.data, steps: e.data.steps.map(fromStep) };
    default:
      return turn;
  }
}

interface Options {
  /** Called with the assistant's spoken text when a mission finishes or pauses for approval. */
  onSpeech?: (text: string) => void;
}

/**
 * One conversation with the agent planner. The session token is a bearer secret, so it lives
 * only in memory: never in storage or a URL. Reloading the page starts a new conversation.
 */
export function useAgentSession({ onSpeech }: Options = {}) {
  const [turns, setTurns] = React.useState<Turn[]>([]);
  const session = React.useRef<{ id: string; token: string } | null>(null);
  const abort = React.useRef<AbortController | null>(null);
  const counter = React.useRef(0);
  const speech = React.useRef(onSpeech);
  speech.current = onSpeech;

  const busy = turns.some((t) => t.working);

  const patch = React.useCallback((id: string, fn: (t: Turn) => Turn) => {
    setTurns((all) => all.map((t) => (t.id === id ? fn(t) : t)));
  }, []);

  const finish = React.useCallback(
    (id: string, mission: Mission) => {
      if (mission.session_token) {
        session.current = { id: mission.session_id, token: mission.session_token };
      }
      patch(id, (t) => ({ ...t, working: false, mission: { ...mission, session_token: null } }));
      if (mission.speech) speech.current?.(mission.speech);
    },
    [patch],
  );

  const fail = React.useCallback(
    (id: string, err: unknown) => {
      if ((err as Error)?.name === 'AbortError') {
        patch(id, (t) => ({ ...t, working: false, error: 'Stopped.' }));
        return;
      }
      const e = err instanceof AgentError ? err : new AgentError('Something went wrong.');
      patch(id, (t) => ({ ...t, working: false, error: e.message, unavailable: e.status === 503 }));
    },
    [patch],
  );

  const send = React.useCallback(
    async (utterance: string) => {
      const text = utterance.trim();
      if (!text || abort.current) return;
      const id = `turn-${++counter.current}`;
      setTurns((all) => [...all, { id, utterance: text, working: true, steps: [] }]);
      const ctl = new AbortController();
      abort.current = ctl;
      try {
        const mission = await startMission(
          text,
          session.current,
          (e) => {
            if (e.event === 'mission_started' && e.data.session_token) {
              session.current = { id: e.data.session_id, token: e.data.session_token };
            }
            patch(id, (t) => applyEvent(t, e));
          },
          ctl.signal,
        );
        finish(id, mission);
      } catch (err) {
        fail(id, err);
      } finally {
        abort.current = null;
      }
    },
    [fail, finish, patch],
  );

  const decide = React.useCallback(
    async (turnId: string, approved: boolean) => {
      const turn = turns.find((t) => t.id === turnId);
      const mission = turn?.mission;
      if (!mission || !session.current || abort.current) return;
      patch(turnId, (t) => ({ ...t, working: true, error: undefined }));
      const ctl = new AbortController();
      abort.current = ctl;
      try {
        const done = await resolveApproval(
          mission.id,
          approved,
          session.current.token,
          (e) => patch(turnId, (t) => applyEvent(t, e)),
          ctl.signal,
        );
        finish(turnId, done);
      } catch (err) {
        fail(turnId, err);
      } finally {
        abort.current = null;
      }
    },
    [fail, finish, patch, turns],
  );

  const stop = React.useCallback(() => abort.current?.abort(), []);

  const reset = React.useCallback(() => {
    abort.current?.abort();
    abort.current = null;
    session.current = null;
    setTurns([]);
  }, []);

  // Abort an in-flight mission when the page unmounts.
  React.useEffect(() => () => abort.current?.abort(), []);

  return { turns, busy, send, decide, stop, reset, hasSession: session.current !== null };
}
