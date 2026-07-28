/** SSE event types — matches backend schemas/events.py */

export interface PhaseEvent {
  v: number;
  phase: string;
  turn_index: number;
  at: string;
}

export interface TokenEvent {
  v: number;
  delta: string;
  turn_index: number;
}

export interface AnalysisSnapshotEvent {
  v: number;
  turn_index: number;
  lead_status: string;
  lead_score: number | null;
  lead_score_delta: number | null;
  next_score_contributor: string | null;
  industry: unknown;
  business_size: unknown;
  pain_points: unknown[];
  recommended_services: unknown[];
  conversation_progress: unknown;
  qualification_status: unknown;
}

export interface ErrorEvent {
  v: number;
  code: string;
  message: string;
  retryable: boolean;
  turn_index: number;
}

export interface DoneEvent {
  v: number;
  turn_index: number;
  client_turn_id?: string;
  message_id?: string;
  finish_reason: string;
  consultation_complete: boolean;
  consultation_id?: string;
}

export type SSEEvent =
  | { type: "phase"; data: PhaseEvent }
  | { type: "token"; data: TokenEvent }
  | { type: "analysis_snapshot"; data: AnalysisSnapshotEvent }
  | { type: "error"; data: ErrorEvent }
  | { type: "done"; data: DoneEvent };
