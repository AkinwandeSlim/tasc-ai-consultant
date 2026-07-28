/** API DTO types — generated from backend OpenAPI schema. */

export interface CreateSessionResponse {
  session_id: string;
  created_at: string;
  expires_at: string;
  phase: string;
  greeting: GreetingMessage;
  analysis: AnalysisSnapshot;
  limits: SessionLimits;
}

export interface GreetingMessage {
  message_id: string;
  role: string;
  content: string;
  created_at: string;
}

export interface AnalysisSnapshot {
  turn_index: number;
  lead_status: string;
  lead_score: number | null;
  lead_score_delta: number | null;
  next_score_contributor: string | null;
  industry: SlotValue | null;
  business_size: SlotValue | null;
  pain_points: PainPoint[];
  recommended_services: RecommendedService[];
  conversation_progress: ConversationProgress;
  qualification_status: QualificationStatus;
}

export interface SlotValue {
  value: string | null;
  label: string | null;
  raw: string | null;
  confidence: number;
}

export interface PainPoint {
  id: string;
  label: string;
  service_codes: string[];
  quantified: boolean;
  turn_index: number;
}

export interface RecommendedService {
  service_code: string;
  name: string;
  rank: number;
  confidence: number;
  rationale: string;
  typical_engagement: string;
}

export interface ConversationProgress {
  phase: string;
  stage_index: number;
  stage_total: number;
  slots_filled: number;
  slots_total: number;
  percent: number;
}

export interface QualificationStatus {
  business_context_understood: "met" | "unmet" | "declined";
  challenges_identified: "met" | "unmet" | "declined";
  solution_matched: "met" | "unmet" | "declined";
  timeline_established: "met" | "unmet" | "declined";
  budget_discussed: "met" | "unmet" | "declined";
  contact_captured: "met" | "unmet" | "declined";
}

export interface SessionLimits {
  message_max_chars: number;
  session_ttl_minutes: number;
}

export interface SendMessageRequest {
  content: string;
  client_turn_id?: string;
}
