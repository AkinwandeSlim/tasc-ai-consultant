/**
 * API DTO types — reconciled with backend /api/v1 contracts.
 *
 * References: apps/backend/app/api/v1/chat.py
 */

// ── Health ──────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  simulation_mode: boolean;
  timestamp: string;
}

export interface LivenessResponse {
  status: string;
}

// ── Consultation Start ──────────────────────────────────────────────────

export interface StartConsultationResponse {
  session_id: string;
  greeting: string;
  conversation_phase: string;
  business_profile: BusinessProfileDTO;
  lead_score: LeadScoreDTO;
  recommendations: RecommendationItemDTO[];
  completion_percentage: number;
  next_question: string | null;
  conversation_finished: boolean;
}

// ── Send Message ────────────────────────────────────────────────────────

export interface MessageResponse {
  assistant_message: string;
  conversation_phase: string;
  business_profile: BusinessProfileDTO;
  lead_score: LeadScoreDTO;
  recommendations: RecommendationItemDTO[];
  completion_percentage: number;
  next_question: string | null;
  conversation_finished: boolean;
}

// ── Session Snapshot ────────────────────────────────────────────────────

export interface SessionSnapshotResponse {
  session_id: string;
  phase: string;
  status: string;
  turn_index: number;
  visitor_turn_count: number;
  business_profile: BusinessProfileDTO;
  lead_score: LeadScoreDTO;
  recommendations: RecommendationItemDTO[];
  completion_percentage: number;
  last_question: string | null;
  conversation_finished: boolean;
  messages: RawMessage[];
}

export interface RawMessage {
  message_id?: string;
  role?: string;
  content?: string;
  created_at?: string;
}

// ── Demo Scenarios ──────────────────────────────────────────────────────

export interface ScenarioItemDTO {
  scenario_id: string;
  name: string;
  description: string;
  tags: string[];
  turn_count: number;
  expected_band: string;
  expected_score: number;
}

export interface ListScenariosResponse {
  scenarios: ScenarioItemDTO[];
  count: number;
  simulation_enabled: boolean;
}

// ── Domain DTOs ─────────────────────────────────────────────────────────

export interface BusinessProfileDTO {
  industry: string | null;
  company_size: string | null;
  pain_points: PainPointDTO[];
  current_tools: string[];
  goals: string[];
  timeline: string | null;
  budget_band: string | null;
  decision_authority: string | null;
  has_contact: boolean;
  core_slots_filled: number;
  commercial_slots_filled: number;
  total_slots_filled: number;
}

export interface PainPointDTO {
  label: string;
  source_turn: number;
}

export interface LeadScoreDTO {
  score: number;
  band: string;
  confidence: number;
  next_contributor: string | null;
  disqualified: boolean;
  partial: boolean;
  justification: string;
}

export interface RecommendationItemDTO {
  service_code: string;
  name: string;
  rank: number;
  confidence: number;
  confidence_label: string;
  category: string;
  priority: string;
  rationale: string;
  typical_engagement: string;
}

// ── Error ───────────────────────────────────────────────────────────────

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    correlation_id: string;
    retryable: boolean;
    details: Record<string, unknown> | null;
  };
}

// ── Conversation State ──────────────────────────────────────────────────

export const PHASE_LABELS = [
  "Understanding",
  "Exploring",
  "Recommending",
  "Qualifying",
  "Wrapping up",
] as const;

export type PhaseLabel = (typeof PHASE_LABELS)[number];

export const STATUS_BANDS = [
  "exploring",
  "cold",
  "warm",
  "qualified",
  "hot",
] as const;

export type StatusBand = (typeof STATUS_BANDS)[number];