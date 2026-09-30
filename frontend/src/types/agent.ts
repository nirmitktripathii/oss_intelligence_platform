// Wire types for the agent planner API (backend/app/schemas/agent.py).

export type MissionStatus = 'running' | 'awaiting_approval' | 'completed' | 'failed';
export type StepStatus = 'awaiting_approval' | 'done' | 'failed' | 'rejected';

export interface MissionStep {
  index: number;
  thought: string;
  tool: string;
  arguments: Record<string, unknown>;
  requires_approval: boolean;
  status: StepStatus;
  result?: unknown;
  error?: string | null;
}

export interface Mission {
  id: string;
  session_id: string;
  /** Present only in the response that created the session. */
  session_token?: string | null;
  utterance: string;
  status: MissionStatus;
  steps: MissionStep[];
  speech?: string | null;
  display?: string | null;
  error?: string | null;
  providers: string[];
  created_at: string;
  updated_at: string;
}

/** Progress events of the /stream endpoints, in the order the server sends them. */
export type AgentEvent =
  | { event: 'mission_started'; data: { id: string; session_id: string; session_token?: string } }
  | { event: 'thinking'; data: { step: number } }
  | {
      event: 'step';
      data: {
        index: number;
        tool: string;
        arguments: Record<string, unknown>;
        thought: string;
        requires_approval: boolean;
      };
    }
  | { event: 'tool_start'; data: { index: number; tool: string } }
  | { event: 'tool_done'; data: { index: number; tool: string; status: StepStatus; error?: string | null } }
  | { event: 'mission'; data: Mission }
  | { event: 'error'; data: { status?: number; detail?: string } };
