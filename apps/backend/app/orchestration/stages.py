"""Stage implementations — individual pipeline processing stages.

Each stage is a callable that takes a PipelineContext and returns
an updated PipelineContext. Stages are pure (no I/O) for Sprint 3;
Sprint 2B+ will add AI provider calls for some stages.

References: PRD Section 13.2, Backend Blueprint Section 8
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.domain.conversation.completion import CompletionDetector
from app.domain.conversation.manager import ConversationManager
from app.domain.conversation.phase_controller import PhaseController
from app.domain.conversation.question_selector import QuestionSelector
from app.domain.extraction.intent_classifier import IntentClassifier
from app.domain.extraction.merger import SlotMerger
from app.domain.extraction.normaliser import Normaliser
from app.domain.extraction.slot_extractor import SlotExtractor
from app.domain.models.slots import SlotMap
from app.domain.qualification.banding import score_to_band
from app.domain.qualification.components import (
    compute_authority,
    compute_budget,
    compute_engagement,
    compute_fit,
    compute_need_clarity,
    compute_urgency,
)
from app.domain.qualification.overrides import apply_overrides
from app.domain.qualification.scoring_engine import ScoringEngine, ScoringInput
from app.domain.recommendation.engine import RecommendationEngine, RecommendationInput
from app.orchestration.event_emitter import EventEmitter
from app.orchestration.pipeline import PipelineContext, StageDefinition, StageType


class PipelineStage:
    """Base class for pipeline stages."""

    def __init__(self, definition: StageDefinition) -> None:
        self.definition = definition

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        """Execute the stage. Override in subclasses."""
        return ctx


# --- Context builders ---

def _build_qualification_status(profile: Any) -> dict[str, str]:
    """Build qualification status dict from business profile."""
    return {
        "business_context_understood": "met" if (profile.industry.value or profile.company_size.value) else "unmet",
        "challenges_identified": "met" if profile.pain_points else "unmet",
        "solution_matched": "unmet",
        "timeline_established": "met" if profile.timeline.value or profile.timeline.declined else "unmet",
        "budget_discussed": "met" if profile.budget_band.value or profile.budget_band.declined else "unmet",
        "contact_captured": "met" if profile.has_contact else "unmet",
    }


# --- Stage implementations ---


class GuardrailStage(PipelineStage):
    """Validate the visitor message."""

    def __init__(self, max_chars: int = 2000) -> None:
        super().__init__(STANDARD_DEFINITIONS[0])
        self._max_chars = max_chars

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        message = ctx.visitor_message
        if not message or not message.strip():
            ctx.record_error("guardrail_check", "Empty message")
            return ctx

        if len(message) > self._max_chars:
            ctx.record_error("guardrail_check", f"Message exceeds {self._max_chars} chars")
            return ctx

        return ctx


class IntentStage(PipelineStage):
    """Classify visitor message intent."""

    def __init__(self, classifier: IntentClassifier | None = None) -> None:
        super().__init__(STANDARD_DEFINITIONS[1])
        self._classifier = classifier or IntentClassifier()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        result = self._classifier.classify(ctx.visitor_message, ctx.turn_index)
        ctx.intent = {
            "intent": result.intent,
            "confidence": result.confidence,
            "trigger": result.trigger,
            "sub_intent": result.sub_intent,
        }
        return ctx


class ExtractionStage(PipelineStage):
    """Extract discovery slots from visitor message."""

    def __init__(self, extractor: SlotExtractor | None = None) -> None:
        super().__init__(STANDARD_DEFINITIONS[2])
        self._extractor = extractor or SlotExtractor()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        result = self._extractor.extract(ctx.visitor_message, ctx.turn_index)
        ctx.extraction = {
            "slots": {k: v for k, v in result.slots.items()},
            "pain_points": result.pain_points,
            "current_tools": result.current_tools,
            "goals": result.goals,
            "confidence": result.confidence,
            "turn_index": result.turn_index,
        }
        return ctx


class NormalisationStage(PipelineStage):
    """Normalise extracted values to controlled vocabularies."""

    def __init__(self, normaliser: Normaliser | None = None) -> None:
        super().__init__(STANDARD_DEFINITIONS[3])
        self._normaliser = normaliser or Normaliser()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        slots = ctx.extraction.get("slots", {})

        for slot_name, value in slots.items():
            if not isinstance(value, dict):
                continue
            raw = value.get("raw", "")
            if not raw:
                continue

            if slot_name == "industry":
                result = self._normaliser.normalise_industry(raw)
                if result.value:
                    slots[slot_name]["value"] = result.value
                    slots[slot_name]["normalised"] = result.normalised

            elif slot_name == "business_size":
                result = self._normaliser.normalise_business_size(raw)
                if result.value:
                    slots[slot_name]["value"] = result.value
                    slots[slot_name]["normalised"] = result.normalised

            elif slot_name == "timeline":
                result = self._normaliser.normalise_timeline(raw)
                if result.value:
                    slots[slot_name]["value"] = result.value
                    slots[slot_name]["normalised"] = result.normalised

            elif slot_name == "budget_band":
                result = self._normaliser.normalise_budget(raw)
                if result.value:
                    slots[slot_name]["value"] = result.value
                    slots[slot_name]["normalised"] = result.normalised

            elif slot_name == "decision_role":
                result = self._normaliser.normalise_decision_role(raw)
                if result.value:
                    slots[slot_name]["value"] = result.value
                    slots[slot_name]["normalised"] = result.normalised

        ctx.extraction["slots"] = slots
        return ctx


class MergeStage(PipelineStage):
    """Merge extraction results into slot map."""

    def __init__(self, merger: SlotMerger | None = None) -> None:
        super().__init__(STANDARD_DEFINITIONS[4])
        self._merger = merger or SlotMerger()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        # Load existing slot map from context
        existing = ctx.slot_map or {}
        slot_map = SlotMap()

        # Restore existing values
        for key, val in existing.items():
            if hasattr(slot_map, key):
                setattr(slot_map, key, val)

        # Extract into ExtractionResult
        extraction_result = self._extraction_to_result(ctx.extraction, ctx.turn_index)
        merge_result = self._merger.merge(slot_map, extraction_result, ctx.turn_index)

        # Store updated slot map
        ctx.slot_map = {
            "industry": merge_result.slot_map.industry,
            "business_size": merge_result.slot_map.business_size,
            "pain_points": merge_result.slot_map.pain_points,
            "current_tools": merge_result.slot_map.current_tools,
            "goals": merge_result.slot_map.goals,
            "timeline": merge_result.slot_map.timeline,
            "budget_band": merge_result.slot_map.budget_band,
            "decision_role": merge_result.slot_map.decision_role,
        }

        return ctx

    @staticmethod
    def _extraction_to_result(extraction: dict, turn_index: int) -> Any:
        """Convert extraction dict back to ExtractionResult-compatible object."""
        from app.domain.extraction.slot_extractor import ExtractionResult

        result = ExtractionResult(turn_index=turn_index)
        result.slots = extraction.get("slots", {})
        result.pain_points = extraction.get("pain_points", [])
        result.current_tools = extraction.get("current_tools", [])
        result.goals = extraction.get("goals", [])
        result.confidence = extraction.get("confidence", 0.0)
        return result


class ScoringStage(PipelineStage):
    """Compute deterministic lead score."""

    def __init__(self, engine: ScoringEngine | None = None) -> None:
        super().__init__(STANDARD_DEFINITIONS[5])
        self._engine = engine or ScoringEngine()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        slot_map = ctx.slot_map
        profile = ctx.business_profile

        # Build scoring input
        pain_points = slot_map.get("pain_points", [])
        input_data = ScoringInput(
            pain_points=pain_points,
            service_mappings=[],
            timeline_value=getattr(slot_map.get("timeline"), "value", None) if isinstance(slot_map.get("timeline"), object) else None,
            budget_value=getattr(slot_map.get("budget_band"), "value", None) if isinstance(slot_map.get("budget_band"), object) else None,
            authority_value=getattr(slot_map.get("decision_role"), "value", None) if isinstance(slot_map.get("decision_role"), object) else None,
            visitor_turn_count=ctx.turn_index,
            has_contact=bool(profile and profile.get("has_contact", False)),
        )

        score, breakdown = self._engine.compute(input_data)
        ctx.lead_score = {
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

        return ctx


class RecommendationStage(PipelineStage):
    """Build and rank service recommendations."""

    def __init__(self, engine: RecommendationEngine | None = None) -> None:
        super().__init__(STANDARD_DEFINITIONS[6])
        self._engine = engine or RecommendationEngine()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        slot_map = ctx.slot_map
        pain_points = slot_map.get("pain_points", [])
        profile = ctx.business_profile

        # Extract pain signal IDs
        pain_signal_ids = []
        pain_labels = []
        for pp in pain_points:
            if hasattr(pp, "id"):
                pain_signal_ids.append(pp.id)
            if hasattr(pp, "label"):
                pain_labels.append(pp.label)

        input_data = RecommendationInput(
            pain_point_labels=pain_labels,
            pain_signal_ids=pain_signal_ids,
            industry=getattr(slot_map.get("industry"), "value", None) if isinstance(slot_map.get("industry"), object) else None,
            business_size=getattr(slot_map.get("business_size"), "value", None) if isinstance(slot_map.get("business_size"), object) else None,
            budget_band=getattr(slot_map.get("budget_band"), "value", None) if isinstance(slot_map.get("budget_band"), object) else None,
            current_phase=ctx.current_phase,
        )

        summary = self._engine.evaluate(input_data)
        ctx.recommendations = {
            "withheld": summary.withheld,
            "withheld_reason": summary.withheld_reason,
            "changed_since_presented": summary.changed_since_presented,
            "items": [
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
                for item in summary.items
            ],
        }

        return ctx


class PhaseTransitionStage(PipelineStage):
    """Evaluate and apply phase transition."""

    def __init__(self, controller: PhaseController | None = None) -> None:
        super().__init__(STANDARD_DEFINITIONS[7])
        self._controller = controller or PhaseController()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        slot_map = ctx.slot_map
        profile = ctx.business_profile

        pain_count = len(slot_map.get("pain_points", []))
        core_filled = sum(
            1 for s in ["industry", "business_size", "pain_points", "current_tools"]
            if slot_map.get(s) and (
                (hasattr(slot_map[s], "value") and slot_map[s].value)
                or (isinstance(slot_map[s], list) and slot_map[s])
            )
        )

        next_phase, trigger = self._controller.evaluate(
            current_phase=ctx.current_phase,
            core_slots_filled=core_filled,
            confidence_met=core_filled >= 3,
            recommendation_ready=(pain_count >= 2),
            commercial_slots_resolved=core_filled >= 5,
            anti_persona=ctx.intent.get("intent") == "anti_persona",
            visitor_requested_human=ctx.intent.get("intent") == "request_human",
        )

        ctx.phase_transition = {
            "from": ctx.current_phase,
            "to": next_phase,
            "trigger": trigger,
        }
        ctx.current_phase = next_phase

        return ctx


class QuestionSelectionStage(PipelineStage):
    """Select next discovery question."""

    def __init__(self, selector: QuestionSelector | None = None) -> None:
        super().__init__(STANDARD_DEFINITIONS[8])
        self._selector = selector or QuestionSelector()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        slot_map = ctx.slot_map
        profile = ctx.business_profile

        # Build a simplified slot map for the selector
        class SimpleSlotMap:
            pass

        simple_map = SimpleSlotMap()
        for key, val in slot_map.items():
            setattr(simple_map, key, val)

        selected = self._selector.select_question(
            current_phase=ctx.current_phase,
            slot_map=simple_map,
            questions_asked=[],
        )

        if selected:
            ctx.next_question = {
                "slot": selected.slot,
                "template_id": selected.template_id,
                "question_text": selected.question_text,
                "reason": selected.reason,
            }
        else:
            ctx.next_question = {}

        return ctx


class ResponseGenerationStage(PipelineStage):
    """Generate assistant response."""

    def __init__(self) -> None:
        super().__init__(STANDARD_DEFINITIONS[9])

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        # Response is generated by the ConversationManager
        # This stage just passes through
        return ctx


class CompletionCheckStage(PipelineStage):
    """Check if consultation should complete."""

    def __init__(self, detector: CompletionDetector | None = None) -> None:
        super().__init__(STANDARD_DEFINITIONS[10])
        self._detector = detector or CompletionDetector()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        result = self._detector.evaluate(
            phase=ctx.current_phase,
            intent=ctx.intent.get("intent"),
            commercial_slots_resolved=False,
            contact_captured=False,
            visitor_turn_count=ctx.turn_index,
        )

        ctx.completion = {
            "should_complete": result.should_complete,
            "reason": result.reason,
            "reason_code": result.reason_code,
        }

        return ctx


class SnapshotStage(PipelineStage):
    """Build and emit analysis snapshot."""

    def __init__(self, emitter: EventEmitter | None = None) -> None:
        super().__init__(STANDARD_DEFINITIONS[11])
        self._emitter = emitter or EventEmitter()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        # Build analysis snapshot from accumulated state
        slot_map = ctx.slot_map
        profile = ctx.business_profile

        industry_data = None
        if slot_map.get("industry") and hasattr(slot_map["industry"], "value") and slot_map["industry"].value:
            sv = slot_map["industry"]
            industry_data = {
                "value": sv.value, "label": sv.value.title() if sv.value else None,
                "raw": sv.raw, "confidence": sv.confidence,
            }

        size_data = None
        if slot_map.get("business_size") and hasattr(slot_map["business_size"], "value") and slot_map["business_size"].value:
            sv = slot_map["business_size"]
            size_data = {
                "value": sv.value, "label": sv.value, "raw": sv.raw, "confidence": sv.confidence,
            }

        pain_list = []
        for pp in slot_map.get("pain_points", []):
            if hasattr(pp, "label"):
                pain_list.append({
                    "id": pp.id if hasattr(pp, "id") else "",
                    "label": pp.label,
                    "service_codes": pp.service_codes if hasattr(pp, "service_codes") else [],
                })

        recs = []
        for item in ctx.recommendations.get("items", []):
            recs.append({
                "service_code": item.get("service_code", ""),
                "name": item.get("name", ""),
                "rank": item.get("rank", 1),
                "confidence": item.get("confidence", 0.0),
                "rationale": item.get("rationale", ""),
            })

        score = ctx.lead_score.get("score")
        band = ctx.lead_score.get("band", "exploring")

        # Build qualification status
        qual_status = {
            "business_context_understood": "met" if industry_data or size_data else "unmet",
            "challenges_identified": "met" if pain_list else "unmet",
            "solution_matched": "met" if recs else "unmet",
            "timeline_established": "unmet",
            "budget_discussed": "unmet",
            "contact_captured": "unmet",
        }

        snapshot = self._emitter.build_analysis_snapshot(
            turn_index=ctx.turn_index,
            lead_status=band,
            lead_score=score,
            next_score_contributor=ctx.lead_score.get("next_contributor"),
            business_profile_industry=industry_data,
            business_profile_size=size_data,
            pain_points=pain_list,
            recommended_services=recs,
            slot_fill_count=len(pain_list),
            total_slots=9,
            stage_index=0,
            qualification_status=qual_status,
        )

        ctx.analysis_snapshot = {
            "turn_index": snapshot.turn_index,
            "lead_status": snapshot.lead_status,
            "lead_score": snapshot.lead_score,
            "next_score_contributor": snapshot.next_score_contributor,
            "industry": snapshot.industry,
            "business_size": snapshot.business_size,
            "pain_points": snapshot.pain_points,
            "recommended_services": snapshot.recommended_services,
            "conversation_progress": snapshot.conversation_progress,
            "qualification_status": snapshot.qualification_status,
        }

        return ctx


# Stage definitions for reference by the pipeline
STANDARD_DEFINITIONS: list[StageDefinition] = [
    StageDefinition(
        name="guardrail_check", stage_type=StageType.GUARDRAIL,
        description="Validate message", timeout_ms=20,
    ),
    StageDefinition(
        name="intent_classification", stage_type=StageType.INTENT,
        description="Classify intent", is_deterministic=True, timeout_ms=50,
        parallel_group="understanding",
    ),
    StageDefinition(
        name="slot_extraction", stage_type=StageType.EXTRACTION,
        description="Extract slots", is_deterministic=True, timeout_ms=100,
        parallel_group="understanding",
    ),
    StageDefinition(
        name="normalisation", stage_type=StageType.NORMALISATION,
        description="Normalise values", timeout_ms=10,
    ),
    StageDefinition(
        name="slot_merging", stage_type=StageType.MERGE,
        description="Merge slots", timeout_ms=10,
    ),
    StageDefinition(
        name="scoring", stage_type=StageType.SCORING,
        description="Compute score", timeout_ms=10,
    ),
    StageDefinition(
        name="recommendation", stage_type=StageType.RECOMMENDATION,
        description="Build recommendations", timeout_ms=50,
    ),
    StageDefinition(
        name="phase_transition", stage_type=StageType.PHASE_TRANSITION,
        description="Evaluate phase", timeout_ms=5,
    ),
    StageDefinition(
        name="question_selection", stage_type=StageType.QUESTION_SELECTION,
        description="Select question", timeout_ms=5,
    ),
    StageDefinition(
        name="response_generation", stage_type=StageType.RESPONSE_GENERATION,
        description="Generate response", timeout_ms=20,
    ),
    StageDefinition(
        name="completion_check", stage_type=StageType.COMPLETION_CHECK,
        description="Check completion", timeout_ms=10,
    ),
    StageDefinition(
        name="snapshot_emission", stage_type=StageType.SNAPSHOT_EMISSION,
        description="Emit snapshot", timeout_ms=20,
    ),
]
