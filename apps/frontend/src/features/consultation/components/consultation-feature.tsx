"use client";

import { useEffect, useCallback, useState } from "react";
import { useConversation } from "@/contexts/conversation-context";
import { useAnalysis } from "@/contexts/analysis-context";
import { useSession } from "@/contexts/session-context";
import { useUI } from "@/contexts/ui-context";
import type { HealthState } from "@/hooks/use-health-check";
import type { ConsultationHook } from "@/hooks/use-consultation";

// Layout
import { Header } from "@/components/layout/header";
// Conversation
import { ConversationWindow } from "@/components/conversation/conversation-window";
import { ChatInput } from "@/components/conversation/chat-input";
// Analysis
import { LeadStatusCard } from "@/components/analysis/lead-status-card";
import { LeadScoreCard } from "@/components/analysis/lead-score-card";
import { BusinessProfileCard } from "@/components/analysis/business-profile-card";
import { PainPointsCard } from "@/components/analysis/pain-points-card";
import { RecommendedServicesCard } from "@/components/analysis/recommended-services-card";
import { ConversationProgressCard } from "@/components/analysis/conversation-progress-card";
import { QualificationStatusCard } from "@/components/analysis/qualification-status-card";
import { SimulationCard } from "@/components/simulation/simulation-card";

interface ConsultationFeatureProps {
  consultation: ConsultationHook;
  health: HealthState;
  isConnected: boolean;
}

export function ConsultationFeature({
  consultation,
  health,
  isConnected,
}: ConsultationFeatureProps) {
  const session = useSession();
  const conversation = useConversation();
  const analysis = useAnalysis();
  const ui = useUI();

  const isWaiting =
    (consultation.isSending || conversation.isStreaming) ?? false;
  const [thinking, setThinking] = useState(false);

  // Start thinking when sending, stop when streaming ends
  useEffect(() => {
    if (consultation.isSending) {
      setThinking(true);
    } else if (!conversation.isStreaming) {
      // Small delay to ensure the thinking panel transitions smoothly
      const timer = setTimeout(() => setThinking(false), 100);
      return () => clearTimeout(timer);
    }
  }, [consultation.isSending, conversation.isStreaming]);

  // Handle sending a message
  const handleSend = useCallback(
    (message: string) => {
      consultation.sendMessage(message);
    },
    [consultation],
  );

  const phase = analysis.snapshot?.conversation_progress.phase ?? "idle";
  const isEmpty = !conversation.hasMessages;

  return (
    <div className="flex h-screen flex-col bg-surface-base">
      {/* ── Header ── */}
      <Header
        isConnected={isConnected}
        isSimulationMode={health.simulationMode}
        phase={phase}
      />

      {/* ── Main Content ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Left Panel: Conversation Workspace ── */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto">
            <ConversationWindow
              messages={conversation.messages}
              isStreaming={!!conversation.isStreaming}
              isThinking={thinking}
              isEmpty={isEmpty}
              greeting={consultation.greeting}
              error={consultation.error}
            />
          </div>

          {/* Input */}
          <ChatInput
            onSend={handleSend}
            disabled={isWaiting || session.status === "completed" || session.status === "terminated"}
          />
        </div>

        {/* ── Right Panel: Live Consultation Intelligence ── */}
        <aside className="hidden w-[340px] shrink-0 overflow-y-auto border-l border-border bg-surface-raised p-3 lg:block xl:w-[380px]">
          <div className="space-y-3">
            {/* Panel title */}
            <div className="mb-2">
              <p className="text-heading-sm font-semibold">
                Live Consultation Intelligence
              </p>
              <p className="text-body-xs text-muted-foreground">
                Updates after every response
              </p>
            </div>

            {/* Progress */}
            {analysis.snapshot && (
              <ConversationProgressCard
                progress={analysis.snapshot.conversation_progress}
              />
            )}

            {/* Lead Status */}
            <LeadStatusCard
              status={analysis.snapshot?.lead_status ?? "exploring"}
            />

            {/* Lead Score */}
            <LeadScoreCard
              score={analysis.snapshot?.lead_score ?? null}
              delta={analysis.snapshot?.lead_score_delta ?? null}
              nextContributor={
                analysis.snapshot?.next_score_contributor ?? null
              }
            />

            {/* Business Profile */}
            <BusinessProfileCard
              profile={
                analysis.snapshot
                  ? {
                      industry:
                        analysis.snapshot.industry?.value ?? null,
                      company_size:
                        analysis.snapshot.business_size?.value ??
                        null,
                      pain_points: (
                        analysis.snapshot.pain_points ?? []
                      ).map((pp) => ({
                        label: pp.label,
                        source_turn: pp.turn_index,
                      })),
                      current_tools: [],
                      goals: [],
                      timeline: null,
                      budget_band: null,
                      decision_authority: null,
                      has_contact: false,
                      core_slots_filled:
                        analysis.snapshot.conversation_progress
                          .slots_filled,
                      commercial_slots_filled: 0,
                      total_slots_filled:
                        analysis.snapshot.conversation_progress
                          .slots_filled,
                    }
                  : {
                      industry: null,
                      company_size: null,
                      pain_points: [],
                      current_tools: [],
                      goals: [],
                      timeline: null,
                      budget_band: null,
                      decision_authority: null,
                      has_contact: false,
                      core_slots_filled: 0,
                      commercial_slots_filled: 0,
                      total_slots_filled: 0,
                    }
              }
            />

            {/* Pain Points */}
            <PainPointsCard
              painPoints={
                analysis.snapshot?.pain_points?.map((pp) => ({
                  id: pp.id,
                  label: pp.label,
                  service_codes: pp.service_codes,
                  quantified: pp.quantified,
                  turn_index: pp.turn_index,
                })) ?? []
              }
            />

            {/* Recommendations */}
            <RecommendedServicesCard
              services={
                analysis.snapshot?.recommended_services?.map((rs) => ({
                  service_code: rs.service_code,
                  name: rs.name,
                  rank: rs.rank,
                  confidence: rs.confidence,
                  rationale: rs.rationale,
                  typical_engagement: rs.typical_engagement,
                })) ?? []
              }
            />

            {/* Qualification Status */}
            {analysis.snapshot && (
              <QualificationStatusCard
                status={analysis.snapshot.qualification_status}
              />
            )}

            {/* Simulation */}
            <SimulationCard
              sessionId={session.sessionId}
              startedAt={consultation.startedAt}
            />
          </div>
        </aside>
      </div>

      {/* ── Mobile: Floating panel toggle ── */}
      {session.sessionId && (
        <button
          onClick={() => ui.setMobilePanelOpen(!ui.isMobilePanelOpen)}
          className="fixed bottom-20 right-4 z-50 flex size-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg lg:hidden"
          aria-label="Toggle analysis panel"
        >
          <span className="text-body-sm font-bold">
            {analysis.snapshot?.lead_score ?? "?"}
          </span>
        </button>
      )}

      {/* Mobile analysis sheet */}
      {ui.isMobilePanelOpen && (
        <div
          className="fixed inset-0 z-40 flex items-end bg-black/30 lg:hidden"
          onClick={() => ui.setMobilePanelOpen(false)}
        >
          <div
            className="max-h-[80vh] w-full overflow-y-auto rounded-t-2xl bg-surface-raised p-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-border" />
            <div className="space-y-3">
              {/* Mobile panel renders same cards */}
              {analysis.snapshot && (
                <ConversationProgressCard
                  progress={analysis.snapshot.conversation_progress}
                />
              )}
              <LeadStatusCard
                status={analysis.snapshot?.lead_status ?? "exploring"}
              />
              <LeadScoreCard
                score={analysis.snapshot?.lead_score ?? null}
                delta={analysis.snapshot?.lead_score_delta ?? null}
                nextContributor={
                  analysis.snapshot?.next_score_contributor ?? null
                }
              />
              <BusinessProfileCard
                profile={
                  analysis.snapshot
                    ? {
                        industry:
                          analysis.snapshot.industry?.value ?? null,
                        company_size:
                          analysis.snapshot.business_size?.value ??
                          null,
                        pain_points: (
                          analysis.snapshot.pain_points ?? []
                        ).map((pp) => ({
                          label: pp.label,
                          source_turn: pp.turn_index,
                        })),
                        current_tools: [],
                        goals: [],
                        timeline: null,
                        budget_band: null,
                        decision_authority: null,
                        has_contact: false,
                        core_slots_filled:
                          analysis.snapshot.conversation_progress
                            .slots_filled,
                        commercial_slots_filled: 0,
                        total_slots_filled:
                          analysis.snapshot.conversation_progress
                            .slots_filled,
                      }
                    : {
                        industry: null,
                        company_size: null,
                        pain_points: [],
                        current_tools: [],
                        goals: [],
                        timeline: null,
                        budget_band: null,
                        decision_authority: null,
                        has_contact: false,
                        core_slots_filled: 0,
                        commercial_slots_filled: 0,
                        total_slots_filled: 0,
                      }
                }
              />
              <PainPointsCard
                painPoints={
                  analysis.snapshot?.pain_points?.map((pp) => ({
                    id: pp.id,
                    label: pp.label,
                    service_codes: pp.service_codes,
                    quantified: pp.quantified,
                    turn_index: pp.turn_index,
                  })) ?? []
                }
              />
              <RecommendedServicesCard
                services={
                  analysis.snapshot?.recommended_services?.map(
                    (rs) => ({
                      service_code: rs.service_code,
                      name: rs.name,
                      rank: rs.rank,
                      confidence: rs.confidence,
                      rationale: rs.rationale,
                      typical_engagement: rs.typical_engagement,
                    }),
                  ) ?? []
                }
              />
              {analysis.snapshot && (
                <QualificationStatusCard
                  status={analysis.snapshot.qualification_status}
                />
              )}
              <SimulationCard
                sessionId={session.sessionId}
                startedAt={consultation.startedAt}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}