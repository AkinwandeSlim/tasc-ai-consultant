/**
 * SSE event types — for the message endpoint streaming response.
 *
 * References: apps/backend/app/schemas/events.py (blueprint)
 */

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
  consultation_id: string | null;
}

export interface AnalysisSnapshotEvent {
  v?: number; // Optional — frontend-constructed snapshots may omit this
  turn_index: number;
  lead_status: string;
  lead_score: number | null;
  lead_score_delta: number | null;
  next_score_contributor: string | null;
  industry: SlotValueDTO | null;
  business_size: SlotValueDTO | null;
  pain_points: SSEMappedPainPoint[];
  recommended_services: SSEMappedService[];
  conversation_progress: ConversationProgressDTO;
  qualification_status: QualificationStatusDTO;
}

export interface SlotValueDTO {
  value: string | null;
  label: string | null;
  raw: string | null;
  confidence: number;
}

export interface SSEMappedPainPoint {
  id: string;
  label: string;
  service_codes: string[];
  quantified: boolean;
  turn_index: number;
}

export interface SSEMappedService {
  service_code: string;
  name: string;
  rank: number;
  confidence: number;
  rationale: string;
  typical_engagement: string;
}

export interface ConversationProgressDTO {
  phase: string;
  stage_index: number;
  stage_total: number;
  slots_filled: number;
  slots_total: number;
  percent: number;
}

export interface QualificationStatusDTO {
  business_context_understood: "met" | "unmet" | "declined";
  challenges_identified: "met" | "unmet" | "declined";
  solution_matched: "met" | "unmet" | "declined";
  timeline_established: "met" | "unmet" | "declined";
  budget_discussed: "met" | "unmet" | "declined";
  contact_captured: "met" | "unmet" | "declined";
}

export type SSEPayload =
  | PhaseEvent
  | TokenEvent
  | AnalysisSnapshotEvent
  | ErrorEvent
  | DoneEvent;

export interface SSEEvent {
  type: "phase" | "token" | "analysis_snapshot" | "error" | "done";
  data: SSEPayload;
}

export type SessionStatus =
  | "idle"
  | "landing"
  | "starting"
  | "active"
  | "streaming"
  | "completed"
  | "terminated"
  | "error";

export interface ConsultationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: "pending" | "streaming" | "complete" | "error";
  createdAt: string;
}