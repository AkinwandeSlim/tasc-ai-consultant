"""Consultation orchestrator — sequences per-turn pipeline stages.

Coordinates: guardrails → intent + extraction → normalisation → merge →
scoring → recommendation → phase transition → question selection →
response generation → completion check → snapshot emission.

References: PRD Section 13, AI Blueprint Section 12, Backend Blueprint Section 7
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any

from app.domain.conversation.completion import CompletionDetector
from app.domain.conversation.manager import ConversationManager, ProcessedTurn
from app.domain.conversation.memory import ConversationMemory
from app.domain.conversation.phase_controller import PhaseController
from app.domain.conversation.question_selector import QuestionSelector
from app.domain.extraction.intent_classifier import IntentClassifier
from app.domain.extraction.merger import SlotMerger
from app.domain.extraction.normaliser import Normaliser
from app.domain.extraction.slot_extractor import SlotExtractor
from app.domain.models.conversation import ConversationContext, ConversationState
from app.domain.models.slots import SlotMap
from app.domain.qualification.scoring_engine import ScoringEngine, ScoringInput
from app.domain.recommendation.engine import RecommendationEngine, RecommendationInput
from app.orchestration.event_emitter import EventEmitter
from app.orchestration.pipeline import PipelineContext, StageDefinition, StageType

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """Complete result of orchestrating a turn."""

    assistant_message: str = ""
    conversation_phase: str = "greeting"
    business_profile: dict[str, Any] | None = None
    lead_score: dict[str, Any] | None = None
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    completion_percentage: int = 0
    next_question: str | None = None
    is_complete: bool = False
    completion_reason: str = ""
    analysis_snapshot: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)


class ConsultationOrchestrator:
    """Main orchestrator that coordinates the per-turn consultation pipeline.

    Manages the full lifecycle of a consultation turn:
    1. Receives visitor message and session state
    2. Runs the pipeline stages in order
    3. Returns structured results
    """

    def __init__(
        self,
        conversation_manager: ConversationManager | None = None,
        scoring_engine: ScoringEngine | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        event_emitter: EventEmitter | None = None,
        phase_controller: PhaseController | None = None,
    ) -> None:
        self._conversation_manager = conversation_manager or ConversationManager()
        self._scoring_engine = scoring_engine or ScoringEngine()
        self._recommendation_engine = recommendation_engine or RecommendationEngine()
        self._event_emitter = event_emitter or EventEmitter()
        self._phase_controller = phase_controller or PhaseController()

    async def start_consultation(self) -> dict[str, Any]:
        """Start a new consultation with a greeting.

        Returns:
            Dict with session state including greeting message.
        """
        session = self._conversation_manager.create_session()
        logger.info(
            "Started consultation session %s",
            session.get("session_id", "unknown"),
        )
        return session

    async def process_turn(
        self,
        session_state: dict[str, Any],
        visitor_message: str,
        client_turn_id: str | None = None,
    ) -> OrchestrationResult:
        """Process a single turn of the consultation.

        Args:
            session_state: The current session state.
            visitor_message: The visitor's message.
            client_turn_id: Optional client-side turn ID.

        Returns:
            OrchestrationResult with complete turn output.
        """
        turn_index = session_state.get("turn_index", 0) + 1
        current_phase = session_state.get("phase", "greeting")
        slot_map = session_state.get("slot_map", SlotMap())
        business_profile = session_state.get("business_profile", {})
        questions_asked = session_state.get("questions_asked", [])

        # Build context
        context = ConversationContext(
            session_id=session_state.get("session_id", ""),
            turn_index=turn_index,
            visitor_message=visitor_message,
            client_turn_id=client_turn_id,
            current_phase=current_phase,
        )

        # --- Step 1: Run conversation manager for base processing ---
        self._event_emitter.begin_turn(turn_index)
        self._event_emitter.emit_phase("understanding")

        processed = self._conversation_manager.process_turn(session_state, context)

        if processed.intent_result and processed.intent_result.intent == "anti_persona":
            return self._build_result(
                processed, turn_index, business_profile,
            )

        # --- Step 2: Compute score if we have slots ---
        self._event_emitter.emit_phase("evaluating")

        # Build scoring input from processed turn
        scoring_input = self._build_scoring_input(
            processed, session_state, business_profile,
        )
        score, breakdown = self._scoring_engine.compute(scoring_input)

        lead_score = {
            "score": score.score,
            "raw_score": score.raw_score,
            "band": score.band,
            "confidence": score.confidence,
            "components": [
                {"name": c.name, "awarded": c.awarded, "max": c.max, "basis": c.basis}
                for c in score.components
            ],
            "applied_overrides": score.applied_overrides,
            "next_contributor": score.next_contributor,
            "justification": score.justification,
            "disqualified": score.disqualified,
            "partial": score.partial,
        }

        # --- Step 3: Evaluate recommendations ---
        self._event_emitter.emit_phase("preparing")

        pain_labels = []
        pain_signal_ids = []
        if processed.business_profile:
            for pp in processed.business_profile.pain_points:
                pain_labels.append(pp.label if hasattr(pp, "label") else "")
                if hasattr(pp, "id"):
                    pain_signal_ids.append(pp.id)
            if not pain_signal_ids:
                pain_signal_ids = [f"pp_{i}" for i in range(len(pain_labels))]

        industry = None
        if processed.business_profile and processed.business_profile.industry:
            industry = processed.business_profile.industry.value

        size = None
        if processed.business_profile and processed.business_profile.company_size:
            size = processed.business_profile.company_size.value

        budget = None
        if processed.business_profile and processed.business_profile.budget_band:
            budget = processed.business_profile.budget_band.value

        rec_input = RecommendationInput(
            pain_point_labels=pain_labels,
            pain_signal_ids=pain_signal_ids,
            industry=industry,
            business_size=size,
            budget_band=budget,
            current_phase=processed.conversation_phase,
        )
        rec_summary = self._recommendation_engine.evaluate(rec_input)

        recommendations = [
            {
                "service_code": item.service_code,
                "name": item.name,
                "rank": item.rank,
                "confidence": item.confidence,
                "confidence_label": item.confidence_label,
                "category": item.category,
                "priority": item.priority,
                "matched_pain_point_ids": item.matched_pain_point_ids,
                "rationale": item.rationale,
                "rationale_source": item.rationale_source,
                "typical_engagement": item.typical_engagement,
            }
            for item in rec_summary.items
        ]

        # --- Step 4: Build completion percentage ---
        total_slots = 9
        filled = 0
        if processed.business_profile:
            filled = processed.business_profile.total_slots_filled

        stage_idx = self._phase_controller.get_stage_index(processed.conversation_phase)
        completion_pct = min(
            int((stage_idx / 5) * 50 + (filled / total_slots) * 50),
            100,
        )

        # --- Step 5: Build qualification status ---
        qual_status = {
            "business_context_understood": "unmet",
            "challenges_identified": "unmet",
            "solution_matched": "unmet",
            "timeline_established": "unmet",
            "budget_discussed": "unmet",
            "contact_captured": "unmet",
        }
        if processed.business_profile:
            bp = processed.business_profile
            qual_status["business_context_understood"] = (
                "met" if (bp.industry.value or bp.company_size.value) else "unmet"
            )
            qual_status["challenges_identified"] = (
                "met" if bp.pain_points else "unmet"
            )
            qual_status["solution_matched"] = "met" if recommendations else "unmet"
            qual_status["timeline_established"] = (
                "met" if (bp.timeline.value or bp.timeline.declined) else "unmet"
            )
            qual_status["budget_discussed"] = (
                "met" if (bp.budget_band.value or bp.budget_band.declined) else "unmet"
            )
            qual_status["contact_captured"] = "met" if bp.has_contact else "unmet"

        # --- Step 6: Build analysis snapshot ---
        industry_data = None
        size_data = None
        if processed.business_profile:
            if processed.business_profile.industry.value:
                ind = processed.business_profile.industry
                industry_data = {
                    "value": ind.value, "label": ind.value.title() if ind.value else None,
                    "raw": ind.raw, "confidence": ind.confidence,
                }
            if processed.business_profile.company_size.value:
                sz = processed.business_profile.company_size
                size_data = {
                    "value": sz.value, "label": sz.value,
                    "raw": sz.raw, "confidence": sz.confidence,
                }

        pain_point_list = []
        if processed.business_profile:
            for pp in processed.business_profile.pain_points:
                pain_point_list.append({
                    "id": pp.id if hasattr(pp, "id") else "",
                    "label": pp.label if hasattr(pp, "label") else "",
                    "service_codes": pp.service_codes if hasattr(pp, "service_codes") else [],
                    "turn_index": pp.source_turn if hasattr(pp, "source_turn") else 0,
                })

        snapshot = self._event_emitter.build_analysis_snapshot(
            turn_index=turn_index,
            lead_status=score.band,
            lead_score=score.score,
            lead_score_delta=0,
            next_score_contributor=score.next_contributor,
            business_profile_industry=industry_data,
            business_profile_size=size_data,
            pain_points=pain_point_list,
            recommended_services=[
                {
                    "service_code": r["service_code"],
                    "name": r["name"],
                    "rank": r["rank"],
                    "confidence": r["confidence"],
                    "rationale": r["rationale"],
                }
                for r in recommendations
            ],
            slot_fill_count=filled,
            total_slots=total_slots,
            stage_index=stage_idx,
            qualification_status=qual_status,
        )
        self._event_emitter.emit_analysis_snapshot(snapshot)

        # --- Step 7: Check completion ---
        is_complete = False
        completion_reason = ""
        if processed.completion_result:
            is_complete = processed.completion_result.should_complete
            completion_reason = processed.completion_result.reason
            completion_reason = processed.completion_result.reason_code

        self._event_emitter.emit_done(
            finish_reason="complete",
            client_turn_id=client_turn_id,
            message_id=f"msg_{turn_index}",
            consultation_complete=is_complete,
        )

        # --- Step 8: Build profile dict for output ---
        profile_dict = None
        if processed.business_profile:
            bp = processed.business_profile
            profile_dict = {
                "industry": bp.industry.value if bp.industry.value else None,
                "company_size": bp.company_size.value if bp.company_size.value else None,
                "pain_points": [{"label": p.label, "source_turn": p.source_turn} for p in bp.pain_points],
                "current_tools": bp.current_tools,
                "goals": bp.goals,
                "timeline": bp.timeline.value if bp.timeline.value else None,
                "budget_band": bp.budget_band.value if bp.budget_band.value else None,
                "decision_authority": bp.decision_authority.value if bp.decision_authority.value else None,
                "has_contact": bp.has_contact,
                "core_slots_filled": bp.core_slots_filled,
                "commercial_slots_filled": bp.commercial_slots_filled,
                "total_slots_filled": bp.total_slots_filled,
            }

        result = OrchestrationResult(
            assistant_message=processed.assistant_message,
            conversation_phase=processed.conversation_phase,
            business_profile=profile_dict,
            lead_score=lead_score,
            recommendations=recommendations,
            completion_percentage=completion_pct,
            next_question=processed.next_question,
            is_complete=is_complete,
            completion_reason=completion_reason,
            analysis_snapshot={
                "turn_index": snapshot.turn_index,
                "lead_status": snapshot.lead_status,
                "lead_score": snapshot.lead_score,
                "lead_score_delta": snapshot.lead_score_delta,
                "next_score_contributor": snapshot.next_score_contributor,
                "industry": snapshot.industry,
                "business_size": snapshot.business_size,
                "pain_points": snapshot.pain_points,
                "recommended_services": snapshot.recommended_services,
                "conversation_progress": snapshot.conversation_progress,
                "qualification_status": snapshot.qualification_status,
            },
            errors=processed.merge_result.conflicts if processed.merge_result else [],
        )

        logger.info(
            "Processed turn %d: phase=%s score=%d slots=%d recommendations=%d",
            turn_index, result.conversation_phase,
            score.score, filled, len(recommendations),
        )

        return result

    def _build_scoring_input(
        self,
        processed: ProcessedTurn,
        session_state: dict[str, Any],
        business_profile: Any,
    ) -> ScoringInput:
        """Build ScoringInput from processed turn data."""
        pain_points = []
        timeline_value = None
        budget_value = None
        authority_value = None
        has_contact = False

        if processed.business_profile:
            bp = processed.business_profile
            pain_points = bp.pain_points
            timeline_value = bp.timeline.value if bp.timeline.value else None
            budget_value = bp.budget_band.value if bp.budget_band.value else None
            authority_value = bp.decision_authority.value if bp.decision_authority.value else None
            has_contact = bp.has_contact

        return ScoringInput(
            pain_points=pain_points,
            service_mappings=[],
            timeline_value=timeline_value,
            budget_value=budget_value,
            authority_value=authority_value,
            visitor_turn_count=session_state.get("visitor_turn_count", 0) + 1,
            has_contact=has_contact,
        )

    def _build_result(
        self,
        processed: ProcessedTurn,
        turn_index: int,
        business_profile: Any,
    ) -> OrchestrationResult:
        """Build an OrchestrationResult from termination state."""
        return OrchestrationResult(
            assistant_message=processed.assistant_message,
            conversation_phase="terminated",
            business_profile=None,
            completion_percentage=100,
            is_complete=True,
            completion_reason="terminated",
        )
