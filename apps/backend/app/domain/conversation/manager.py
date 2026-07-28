"""Conversation manager — session lifecycle and message handling.

Coordinates session creation, message processing, state updates,
slot extraction, phase evaluation, and response generation.

Stateless design: all state lives in the repository. The manager
receives state, processes, and returns new state.

References: PRD FR-01 to FR-10, PRD Section 7
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from app.domain.conversation.completion import CompletionDetector, CompletionResult
from app.domain.conversation.memory import ConversationMemory, MemoryState
from app.domain.conversation.phase_controller import PhaseController
from app.domain.conversation.question_selector import QuestionSelector, SelectedQuestion
from app.domain.extraction.intent_classifier import IntentClassifier, IntentResult
from app.domain.extraction.merger import MergeResult, SlotMerger
from app.domain.extraction.normaliser import Normaliser
from app.domain.extraction.slot_extractor import ExtractionResult, SlotExtractor
from app.domain.models.conversation import (
    ConversationContext,
    ConversationHistory,
    ConversationMetadata,
    ConversationProgress,
    ConversationStage,
    ConversationState,
    SessionStatus,
)
from app.domain.models.slots import SlotMap
from app.domain.business.models import BusinessProfile, SlotValue


@dataclass
class ProcessedTurn:
    """The result of processing a single visitor turn."""

    assistant_message: str = ""
    conversation_phase: str = "greeting"
    business_profile: BusinessProfile | None = None
    lead_score: dict[str, Any] | None = None
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    completion_percentage: int = 0
    next_question: str | None = None
    completion_result: CompletionResult | None = None
    intent_result: IntentResult | None = None
    extraction_result: ExtractionResult | None = None
    merge_result: MergeResult | None = None
    slot_map: SlotMap | None = None


class ConversationManager:
    """Manages conversation sessions and turn processing.

    Coordinates: creation → intent classification → slot extraction →
    normalisation → merging → phase evaluation → question selection →
    response generation → completion check.
    """

    def __init__(
        self,
        phase_controller: PhaseController | None = None,
        intent_classifier: IntentClassifier | None = None,
        slot_extractor: SlotExtractor | None = None,
        normaliser: Normaliser | None = None,
        slot_merger: SlotMerger | None = None,
        question_selector: QuestionSelector | None = None,
        completion_detector: CompletionDetector | None = None,
        memory: ConversationMemory | None = None,
    ) -> None:
        self._phase_controller = phase_controller or PhaseController()
        self._intent_classifier = intent_classifier or IntentClassifier()
        self._slot_extractor = slot_extractor or SlotExtractor()
        self._normaliser = normaliser or Normaliser()
        self._slot_merger = slot_merger or SlotMerger()
        self._question_selector = question_selector or QuestionSelector()
        self._completion_detector = completion_detector or CompletionDetector()
        self._memory = memory or ConversationMemory()

    def create_session(self) -> dict[str, Any]:
        """Create a new session with initial greeting.

        Returns:
            Dict with session_id, greeting message, and initial state.
        """
        import uuid
        session_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return {
            "session_id": session_id,
            "created_at": now,
            "phase": "greeting",
            "status": "active",
            "messages": [
                {
                    "message_id": f"msg_{session_id[:8]}_000",
                    "role": "assistant",
                    "content": (
                        "I'm Nova, AI Solutions Consultant at Trizen. "
                        "I help visitors figure out whether we're the right "
                        "fit for what they're building. What's the problem "
                        "you're trying to solve?"
                    ),
                    "created_at": now,
                }
            ],
            "business_profile": BusinessProfile(),
            "slot_map": SlotMap(),
            "questions_asked": [],
            "visitor_turn_count": 0,
            "turn_index": 0,
        }

    def process_turn(
        self,
        session_state: dict[str, Any],
        context: ConversationContext,
    ) -> ProcessedTurn:
        """Process a single visitor turn.

        Args:
            session_state: Current session state dict.
            context: Turn context with visitor message.

        Returns:
            ProcessedTurn with all turn results.
        """
        turn_index = session_state.get("turn_index", 0) + 1
        current_phase = session_state.get("phase", "greeting")
        visitor_message = context.visitor_message

        # Get existing slot map and business profile
        slot_map = session_state.get("slot_map", SlotMap())
        business_profile = session_state.get("business_profile", BusinessProfile())
        questions_asked = session_state.get("questions_asked", [])
        visitor_turn_count = session_state.get("visitor_turn_count", 0)

        # --- Step 1: Classify intent ---
        intent_result = self._intent_classifier.classify(
            visitor_message, turn_index=turn_index,
        )

        # Handle termination immediately
        if intent_result.intent == "anti_persona":
            return self._create_terminated_turn(
                turn_index, current_phase, intent_result,
            )

        # --- Step 2: Extract slots ---
        extraction_result = self._slot_extractor.extract(
            visitor_message, turn_index=turn_index,
        )

        # --- Step 3: Normalise extracted values ---
        extraction_result = self._normalise_extraction(extraction_result)

        # --- Step 4: Merge slots ---
        merge_result = self._slot_merger.merge(
            slot_map, extraction_result, turn_index,
        )

        # --- Step 5: Update slot map ---
        updated_slot_map = merge_result.slot_map

        # --- Step 6: Sync business profile from slot map ---
        business_profile = self._sync_business_profile(
            business_profile, updated_slot_map,
        )

        # --- Step 7: Evaluate phase transition ---
        filled_slots = business_profile.total_slots_filled
        core_filled = business_profile.core_slots_filled
        pain_count = len(business_profile.manageable_pain_points)

        next_phase, trigger = self._phase_controller.evaluate(
            current_phase=current_phase,
            core_slots_filled=core_filled,
            confidence_met=core_filled >= 3,
            recommendation_ready=(pain_count >= 2 and business_profile.industry.value is not None),
            recommendation_acknowledged=intent_result.intent == "answer_question",
            commercial_slots_resolved=business_profile.commercial_slots_filled >= 3,
            visitor_requested_human=intent_result.intent == "request_human",
            anti_persona=intent_result.intent == "anti_persona",
            discovery_refused_count=0,
        )

        # --- Step 8: Select next question ---
        selected_question = self._question_selector.select_question(
            current_phase=next_phase,
            slot_map=updated_slot_map,
            questions_asked=questions_asked,
        )

        # --- Step 9: Generate response ---
        assistant_message = self._generate_response(
            current_phase=next_phase,
            business_profile=business_profile,
            intent_result=intent_result,
            selected_question=selected_question,
            merge_result=merge_result,
            visitor_message=visitor_message,
        )

        # --- Step 10: Check completion ---
        has_contact = bool(
            business_profile.contact_email.value
            and business_profile.consent_granted
        )
        completion_result = self._completion_detector.evaluate(
            phase=next_phase,
            intent=intent_result.intent,
            commercial_slots_resolved=business_profile.commercial_slots_filled >= 3,
            contact_captured=has_contact,
            visitor_turn_count=visitor_turn_count + 1,
        )

        # --- Step 11: Build progress ---
        progress = ConversationProgress(
            phase=next_phase,
            stage_index=self._phase_controller.get_stage_index(next_phase),
            slots_filled=filled_slots,
            slots_total=9,
        )

        return ProcessedTurn(
            assistant_message=assistant_message,
            conversation_phase=next_phase,
            business_profile=business_profile,
            lead_score={
                "score": 0,
                "band": "exploring",
                "confidence": 0.0,
                "next_contributor": None,
            },
            recommendations=[],
            completion_percentage=progress.percent,
            next_question=selected_question.question_text if selected_question else None,
            completion_result=completion_result,
            intent_result=intent_result,
            extraction_result=extraction_result,
            merge_result=merge_result,
            slot_map=updated_slot_map,
        )

    def _normalise_extraction(
        self,
        extraction: ExtractionResult,
    ) -> ExtractionResult:
        """Normalise extracted values to controlled vocabularies."""
        if "industry" in extraction.slots:
            raw = extraction.slots["industry"].get("raw", "")
            normalised = self._normaliser.normalise_industry(raw)
            if normalised.value:
                extraction.slots["industry"]["value"] = normalised.value
                extraction.slots["industry"]["normalised"] = normalised.normalised
                extraction.slots["industry"]["confidence"] = max(
                    extraction.slots["industry"].get("confidence", 0.0),
                    normalised.confidence if normalised.confidence > 0 else 0.0,
                )

        if "business_size" in extraction.slots:
            raw = extraction.slots["business_size"].get("raw", "")
            normalised = self._normaliser.normalise_business_size(raw)
            if normalised.value:
                extraction.slots["business_size"]["value"] = normalised.value
                extraction.slots["business_size"]["normalised"] = normalised.normalised
                extraction.slots["business_size"]["confidence"] = max(
                    extraction.slots["business_size"].get("confidence", 0.0),
                    normalised.confidence if normalised.confidence > 0 else 0.0,
                )

        if "timeline" in extraction.slots:
            raw = extraction.slots["timeline"].get("raw", "")
            normalised = self._normaliser.normalise_timeline(raw)
            if normalised.value:
                extraction.slots["timeline"]["value"] = normalised.value
                extraction.slots["timeline"]["normalised"] = normalised.normalised

        if "budget_band" in extraction.slots:
            raw = extraction.slots["budget_band"].get("raw", "")
            normalised = self._normaliser.normalise_budget(raw)
            if normalised.value:
                extraction.slots["budget_band"]["value"] = normalised.value
                extraction.slots["budget_band"]["normalised"] = normalised.normalised

        if "decision_role" in extraction.slots:
            raw = extraction.slots["decision_role"].get("raw", "")
            normalised = self._normaliser.normalise_decision_role(raw)
            if normalised.value:
                extraction.slots["decision_role"]["value"] = normalised.value
                extraction.slots["decision_role"]["normalised"] = normalised.normalised

        return extraction

    def _sync_business_profile(
        self,
        profile: BusinessProfile,
        slot_map: SlotMap,
    ) -> BusinessProfile:
        """Sync BusinessProfile from the canonical SlotMap."""
        if slot_map.industry.value:
            profile.industry = SlotValue(
                value=slot_map.industry.value,
                normalised=slot_map.industry.normalised,
                raw=slot_map.industry.raw,
                confidence=slot_map.industry.confidence,
                source_turn=slot_map.industry.source_turn,
                declined=slot_map.industry.declined,
            )
        if slot_map.business_size.value:
            profile.company_size = SlotValue(
                value=slot_map.business_size.value,
                normalised=slot_map.business_size.normalised,
                raw=slot_map.business_size.raw,
                confidence=slot_map.business_size.confidence,
                source_turn=slot_map.business_size.source_turn,
                declined=slot_map.business_size.declined,
            )
        if slot_map.pain_points:
            profile.pain_points = slot_map.pain_points
        if slot_map.current_tools:
            profile.current_tools = slot_map.current_tools
        if slot_map.goals:
            profile.goals = slot_map.goals
        if slot_map.timeline.value:
            profile.timeline = SlotValue(
                value=slot_map.timeline.value,
                normalised=slot_map.timeline.normalised,
                raw=slot_map.timeline.raw,
                confidence=slot_map.timeline.confidence,
                source_turn=slot_map.timeline.source_turn,
                declined=slot_map.timeline.declined,
            )
        if slot_map.budget_band.value:
            profile.budget_band = SlotValue(
                value=slot_map.budget_band.value,
                normalised=slot_map.budget_band.normalised,
                raw=slot_map.budget_band.raw,
                confidence=slot_map.budget_band.confidence,
                source_turn=slot_map.budget_band.source_turn,
                declined=slot_map.budget_band.declined,
            )
        if slot_map.decision_role.value:
            profile.decision_authority = SlotValue(
                value=slot_map.decision_role.value,
                normalised=slot_map.decision_role.normalised,
                raw=slot_map.decision_role.raw,
                confidence=slot_map.decision_role.confidence,
                source_turn=slot_map.decision_role.source_turn,
                declined=slot_map.decision_role.declined,
            )
        return profile

    def _generate_response(
        self,
        current_phase: str,
        business_profile: BusinessProfile,
        intent_result: IntentResult,
        selected_question: SelectedQuestion | None,
        merge_result: MergeResult,
        visitor_message: str,
    ) -> str:
        """Generate a deterministic response based on current state.

        In Sprint 2B+ this will use an LLM. For Sprint 3, uses templates.
        """
        phase = current_phase
        intent = intent_result.intent

        # Handle special intents
        if intent == "request_human":
            return (
                "I understand you'd like to speak with someone directly. "
                "I'll make sure a consultant follows up with you promptly. "
                "To help them prepare, could you share your name and email?"
            )

        if intent == "end_conversation":
            return (
                "Thank you for the conversation today. I'll summarise "
                "what we've discussed and make sure it's available for "
                "a follow-up. You should hear from a consultant soon."
            )

        if intent == "smalltalk":
            return (
                "I appreciate that! To make sure I can help you find "
                "the right solution, could you tell me a bit about "
                "the business challenge you're working on?"
            )

        # Phase-specific responses
        if phase == "greeting":
            return (
                "I'm Nova, AI Solutions Consultant at Trizen. I help visitors "
                "figure out whether we're the right fit for what they're building. "
                "What's the problem you're trying to solve?"
            )

        if phase == "discovery":
            if merge_result.changed:
                changed_list = ", ".join(merge_result.changed)
                if selected_question:
                    return (
                        f"Thanks for sharing that about {changed_list}. "
                        f"{selected_question.question_text}"
                    )
                return (
                    f"Good, I'm getting a clearer picture of your situation. "
                    f"Is there anything else you'd like to add?"
                )
            if selected_question:
                return selected_question.question_text
            return (
                "Could you tell me more about your business and "
                "the challenges you're facing?"
            )

        if phase == "exploration":
            if merge_result.new_pain_points:
                pp = merge_result.new_pain_points[0]
                if selected_question:
                    return (
                        f"That's helpful context — {pp.label.lower()}. "
                        f"{selected_question.question_text}"
                    )
                return (
                    f"I see — {pp.label.lower()}. "
                    f"Could you tell me more about how that impacts your operations?"
                )
            if selected_question:
                return selected_question.question_text
            return (
                "Can you help me understand more about your "
                "current processes and what's driving the need for change?"
            )

        if phase == "recommendation":
            return (
                "Based on what you've shared, I have some thoughts on "
                "services that could help. Let me present those to you "
                "and you can tell me what you think."
            )

        if phase == "qualification":
            if selected_question:
                return selected_question.question_text
            return (
                "To help scope this properly for a consultant follow-up, "
                "could you share a bit about your timeline and budget?"
            )

        if phase == "capture_and_close":
            if selected_question:
                return selected_question.question_text
            return (
                "If you'd like, I can pass a summary to a consultant "
                "who'll follow up within one working day. That just needs "
                "your name and email. Happy to skip it if you'd rather not."
            )

        # Fallback
        return (
            "Thank you for sharing that. Could you tell me more "
            "about what you're hoping to achieve?"
        )

    def _create_terminated_turn(
        self,
        turn_index: int,
        current_phase: str,
        intent_result: IntentResult,
    ) -> ProcessedTurn:
        """Create a terminated turn result."""
        return ProcessedTurn(
            assistant_message=(
                "I understand you may be looking for something different. "
                "If you'd like to explore how Trizen can help your business, "
                "please feel free to start a new conversation. Otherwise, "
                "you can visit our website for more information."
            ),
            conversation_phase="terminated",
            business_profile=None,
            completion_percentage=100,
            intent_result=intent_result,
        )
