/**
 * useConsultation — manages the full consultation lifecycle.
 *
 * Provides startConsultation, sendMessage, and getSnapshot operations
 * that call the backend API and update the Session / Conversation /
 * Analysis contexts.
 */

import { useCallback, useState } from "react";
import { useSession } from "@/contexts/session-context";
import { useConversation } from "@/contexts/conversation-context";
import { useAnalysis } from "@/contexts/analysis-context";
import { sessionService } from "@/services/session-service";
import { consultationService } from "@/services/consultation-service";
import type {
  MessageResponse,
  SessionSnapshotResponse,
  StartConsultationResponse,
} from "@/types/api";
import type {
  ConsultationMessage,
  SSEMappedPainPoint,
  SSEMappedService,
} from "@/types/events";

interface ConsultationState {
  isStarting: boolean;
  isSending: boolean;
  isFetchingSnapshot: boolean;
  error: string | null;
  greeting: string | null;
  scenarioId: string | null;
  startedAt: string | null;
}

const INITIAL: ConsultationState = {
  isStarting: false,
  isSending: false,
  isFetchingSnapshot: false,
  error: null,
  greeting: null,
  scenarioId: null,
  startedAt: null,
};

function toConsultationMessage(
  role: "user" | "assistant",
  content: string,
  status: ConsultationMessage["status"] = "complete",
): ConsultationMessage {
  return {
    id: `${role[0]}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    role,
    content,
    status,
    createdAt: new Date().toISOString(),
  };
}

export interface ConsultationHook {
  isStarting: boolean;
  isSending: boolean;
  isFetchingSnapshot: boolean;
  error: string | null;
  greeting: string | null;
  scenarioId: string | null;
  startedAt: string | null;
  startConsultation: () => Promise<void>;
  sendMessage: (_message: string) => Promise<void>;
  fetchSnapshot: (_sessionId: string) => Promise<SessionSnapshotResponse | null>;
  restoreFromSnapshot: (_snapshot: SessionSnapshotResponse) => void;
  clearError: () => void;
}

export function useConsultation(): ConsultationHook {
  const [state, setState] = useState<ConsultationState>(INITIAL);
  const session = useSession();
  const conversation = useConversation();
  const analysis = useAnalysis();

  /** Start a new consultation via POST /api/v1/chat/start. */
  const startConsultation = useCallback(async () => {
    setState((prev) => ({ ...prev, isStarting: true, error: null }));
    try {
      const data: StartConsultationResponse =
        await sessionService.start();

      session.setSessionId(data.session_id);
      session.setStatus("active");
      conversation.clearMessages();
      analysis.clearSnapshot();

      // Add greeting as first assistant message
      const greetingMsg = toConsultationMessage(
        "assistant",
        data.greeting,
      );
      conversation.addMessage(greetingMsg);

      // Map business profile to analysis snapshot shape
      analysis.replaceSnapshot({
        turn_index: 0,
        lead_status: data.lead_score.band,
        lead_score: data.lead_score.score,
        lead_score_delta: null,
        next_score_contributor: data.lead_score.next_contributor,
        industry: null,
        business_size: null,
        pain_points: [] as unknown as SSEMappedPainPoint[],
        recommended_services: [] as unknown as SSEMappedService[],
        conversation_progress: {
          phase: "greeting",
          stage_index: 0,
          stage_total: 5,
          slots_filled: 0,
          slots_total: 9,
          percent: 0,
        },
        qualification_status: {
          business_context_understood: "unmet",
          challenges_identified: "unmet",
          solution_matched: "unmet",
          timeline_established: "unmet",
          budget_discussed: "unmet",
          contact_captured: "unmet",
        },
      });

      setState((prev) => ({
        ...prev,
        isStarting: false,
        greeting: data.greeting,
        startedAt: new Date().toISOString(),
      }));
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to start consultation";
      setState((prev) => ({ ...prev, isStarting: false, error: message }));
      session.setStatus("error");
    }
  }, [session, conversation, analysis]);

  /** Send a message via POST /api/v1/chat/message. */
  const sendMessage = useCallback(
    async (message: string) => {
      if (!session.sessionId) return;
      if (state.isSending) return;

      // Optimistically add user message
      const userMsg = toConsultationMessage("user", message, "complete");
      conversation.addMessage(userMsg);
      conversation.setIsStreaming(true);

      setState((prev) => ({ ...prev, isSending: true, error: null }));

      try {
        const data: MessageResponse = await consultationService.send({
          session_id: session.sessionId,
          message,
        });

        // Add assistant response
        const assistantMsg = toConsultationMessage(
          "assistant",
          data.assistant_message,
        );
        conversation.addMessage(assistantMsg);

        // Update analysis snapshot from response data
        const bp = data.business_profile;
        const ls = data.lead_score;
        const stageIdx = phaseToStageIndex(data.conversation_phase);

        analysis.replaceSnapshot({
          turn_index: session.currentTurnIndex + 1,
          lead_status: ls.band,
          lead_score: ls.score,
          lead_score_delta: null,
          next_score_contributor: ls.next_contributor,
          industry: bp.industry
            ? {
                value: bp.industry,
                label: bp.industry,
                raw: bp.industry,
                confidence: 0.5,
              }
            : null,
          business_size: bp.company_size
            ? {
                value: bp.company_size,
                label: bp.company_size,
                raw: bp.company_size,
                confidence: 0.5,
              }
            : null,
          pain_points: bp.pain_points.map((pp, i) => ({
            id: `pp_${i + 1}`,
            label: pp.label,
            service_codes: [],
            quantified: false,
            turn_index: pp.source_turn,
          })),
          recommended_services: data.recommendations.map((r) => ({
            service_code: r.service_code,
            name: r.name,
            rank: r.rank,
            confidence: r.confidence,
            rationale: r.rationale,
            typical_engagement: r.typical_engagement,
          })),
          conversation_progress: {
            phase: data.conversation_phase,
            stage_index: stageIdx,
            stage_total: 5,
            slots_filled: bp.total_slots_filled,
            slots_total: 9,
            percent: data.completion_percentage,
          },
          qualification_status: {
            business_context_understood:
              bp.industry ? "met" : "unmet",
            challenges_identified:
              bp.pain_points.length > 0 ? "met" : "unmet",
            solution_matched:
              data.recommendations.length > 0 ? "met" : "unmet",
            timeline_established:
              bp.timeline ? "met" : "unmet",
            budget_discussed:
              bp.budget_band ? "met" : "unmet",
            contact_captured:
              bp.has_contact ? "met" : "unmet",
          },
        });

        session.setCurrentTurnIndex(session.currentTurnIndex + 1);

        if (data.conversation_finished) {
          session.setStatus(
            data.conversation_phase === "terminated"
              ? "terminated"
              : "completed",
          );
        }

        setState((prev) => ({
          ...prev,
          isSending: false,
        }));
      } catch (err: unknown) {
        const message =
          err instanceof Error
            ? err.message
            : "Failed to send message. Please try again.";
        // Mark user message as error
        conversation.setMessageStatus(userMsg.id, "error");
        setState((prev) => ({ ...prev, isSending: false, error: message }));
      } finally {
        conversation.setIsStreaming(false);
      }
    },
    [session, conversation, analysis, state.isSending],
  );

  /** Fetch session snapshot via GET /api/v1/chat/{session_id}. */
  const fetchSnapshot = useCallback(
    async (sessionId: string) => {
      setState((prev) => ({
        ...prev,
        isFetchingSnapshot: true,
        error: null,
      }));
      try {
        const data: SessionSnapshotResponse =
          await sessionService.get(sessionId);
        return data;
      } catch (err: unknown) {
        const message =
          err instanceof Error
            ? err.message
            : "Failed to fetch session snapshot";
        setState((prev) => ({ ...prev, error: message }));
        return null;
      } finally {
        setState((prev) => ({
          ...prev,
          isFetchingSnapshot: false,
        }));
      }
    },
    [],
  );

  /** Restore state from an existing snapshot (for session recovery). */
  const restoreFromSnapshot = useCallback(
    (snapshot: SessionSnapshotResponse) => {
      session.setSessionId(snapshot.session_id);
      session.setStatus(
        snapshot.status as "active" | "completed" | "terminated",
      );
      session.setCurrentTurnIndex(snapshot.turn_index);

      // Restore messages
      if (snapshot.messages) {
        for (const msg of snapshot.messages) {
          if (msg.role && msg.content) {
            const role = msg.role === "assistant" ? "assistant" : "user";
            conversation.addMessage({
              id: msg.message_id ?? `restored_${Date.now()}`,
              role,
              content: msg.content,
              status: "complete",
              createdAt: msg.created_at ?? new Date().toISOString(),
            });
          }
        }
      }

      // Restore analysis
      const bp = snapshot.business_profile;
      const stageIdx = phaseToStageIndex(snapshot.phase);
      analysis.replaceSnapshot({
        turn_index: snapshot.turn_index,
        lead_status: snapshot.lead_score?.band ?? "exploring",
        lead_score: snapshot.lead_score?.score ?? null,
        lead_score_delta: null,
        next_score_contributor: snapshot.lead_score?.next_contributor ?? null,
        industry: bp?.industry
          ? {
              value: bp.industry,
              label: bp.industry,
              raw: bp.industry,
              confidence: 0.5,
            }
          : null,
        business_size: bp?.company_size
          ? {
              value: bp.company_size,
              label: bp.company_size,
              raw: bp.company_size,
              confidence: 0.5,
            }
          : null,
        pain_points: (bp?.pain_points ?? []).map((pp, i) => ({
          id: `pp_${i + 1}`,
          label: pp.label,
          service_codes: [],
          quantified: false,
          turn_index: pp.source_turn,
        })),
        recommended_services: (snapshot.recommendations ?? []).map((r) => ({
          service_code: r.service_code,
          name: r.name,
          rank: r.rank,
          confidence: r.confidence,
          rationale: r.rationale,
          typical_engagement: r.typical_engagement,
        })),
        conversation_progress: {
          phase: snapshot.phase,
          stage_index: stageIdx,
          stage_total: 5,
          slots_filled: bp?.total_slots_filled ?? 0,
          slots_total: 9,
          percent: snapshot.completion_percentage,
        },
        qualification_status: {
          business_context_understood:
            bp?.industry ? "met" : "unmet",
          challenges_identified:
            (bp?.pain_points?.length ?? 0) > 0 ? "met" : "unmet",
          solution_matched:
            (snapshot.recommendations?.length ?? 0) > 0
              ? "met"
              : "unmet",
          timeline_established: bp?.timeline ? "met" : "unmet",
          budget_discussed: bp?.budget_band ? "met" : "unmet",
          contact_captured: bp?.has_contact ? "met" : "unmet",
        },
      });
    },
    [session, conversation, analysis],
  );

  /** Clear error state. */
  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    startConsultation,
    sendMessage,
    fetchSnapshot,
    restoreFromSnapshot,
    clearError,
  };
}

/** Map backend phase string to stage index (0-4). */
function phaseToStageIndex(phase: string): number {
  const mapping: Record<string, number> = {
    greeting: 0,
    discovery: 0,
    exploration: 1,
    recommendation: 2,
    qualification: 3,
    capture_and_close: 4,
    completed: 4,
    terminated: 4,
  };
  return mapping[phase] ?? 0;
}