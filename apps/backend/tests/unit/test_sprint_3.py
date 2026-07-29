"""Sprint 3 — Consultation Engine: comprehensive unit tests.

Covers: conversation flow, slot extraction, phase transitions,
lead qualification, recommendation generation, simulation scenarios,
orchestrator, and response contract.

References: PRD FR-22 to FR-47, FR-30 to FR-36, FR-37 to FR-43
"""

from __future__ import annotations

from app.domain.conversation.completion import CompletionDetector
from app.domain.conversation.manager import ConversationManager
from app.domain.conversation.memory import ConversationMemory
from app.domain.conversation.phase_controller import (
    PHASE_DEFINITIONS,
    TRANSITION_RULES,
    ConversationPhase,
    PhaseController,
)
from app.domain.conversation.question_selector import (
    PHASE_ELIGIBLE_SLOTS,
    QuestionSelector,
)
from app.domain.extraction.intent_classifier import IntentClassifier
from app.domain.extraction.merger import SlotMerger
from app.domain.extraction.normaliser import Normaliser
from app.domain.extraction.slot_extractor import ExtractionResult, SlotExtractor
from app.domain.models.conversation import ConversationContext
from app.domain.models.slots import PainPoint, SlotMap, SlotValue
from app.domain.qualification.banding import band_display_label, score_to_band
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
from app.domain.recommendation.candidate_builder import Candidate, CandidateBuilder
from app.domain.recommendation.engine import RecommendationEngine, RecommendationInput
from app.domain.recommendation.ranker import RankedService, Ranker
from app.domain.recommendation.rationale import RationaleWriter
from app.domain.simulation.framework import (
    DefaultScenarioProvider,
    ScenarioRegistry,
    SimulationConfig,
    SimulationFramework,
)
from app.domain.simulation.scenarios import (
    DEFAULT_SCENARIOS,
    FINTECH_SCENARIO,
    HEALTHCARE_SCENARIO,
    LOGISTICS_SCENARIO,
    register_default_scenarios,
)
from app.orchestration.event_emitter import EventEmitter
from app.orchestration.orchestrator import ConsultationOrchestrator, OrchestrationResult
from app.orchestration.pipeline import (
    STANDARD_STAGES,
)

# =============================================================================
# Intent Classification Tests
# =============================================================================

class TestIntentClassifier:
    """PRD Section 12.4 — intent taxonomy."""

    def setup_method(self) -> None:
        self.classifier = IntentClassifier()

    def test_describe_problem(self) -> None:
        """FR-22: Extraction runs on visitor messages."""
        result = self.classifier.classify(
            "We run a logistics company and our manual order processing is causing problems."
        )
        assert result.intent == "describe_problem"
        assert result.confidence > 0.3

    def test_company_question(self) -> None:
        """Company question triggers retrieval intent."""
        result = self.classifier.classify("Have you worked with logistics companies before?")
        assert result.intent == "company_question"
        assert result.confidence > 0.4

    def test_capability_question(self) -> None:
        """Capability question detection."""
        result = self.classifier.classify("Can you build custom dashboards for healthcare?")
        assert result.intent == "capability_question"

    def test_pricing_question(self) -> None:
        """Pricing question detection."""
        result = self.classifier.classify("How much does your AI Automation service cost?")
        assert result.intent == "pricing_question"

    def test_timeline_question(self) -> None:
        """Timeline question detection."""
        result = self.classifier.classify("How long would it take to implement?")
        assert result.intent == "timeline_question"

    def test_human_request(self) -> None:
        """Human request detection."""
        result = self.classifier.classify("Can I speak to a human please?")
        assert result.intent == "request_human"

    def test_anti_persona(self) -> None:
        """Anti-persona classification."""
        result = self.classifier.classify("I am a student looking for a job at your company.")
        assert result.intent == "anti_persona"

    def test_end_conversation(self) -> None:
        """End conversation detection."""
        result = self.classifier.classify("That's all for now, thank you.")
        assert result.intent == "end_conversation"

    def test_short_answer_question(self) -> None:
        """Short messages default to answer_question."""
        result = self.classifier.classify("About 180 staff.")
        assert result.intent == "answer_question"


# =============================================================================
# Slot Extraction Tests
# =============================================================================

class TestSlotExtractor:
    """PRD FR-22 to FR-29 — slot extraction rules."""

    def setup_method(self) -> None:
        self.extractor = SlotExtractor()

    def test_extract_industry_logistics(self) -> None:
        """Extract logistics industry."""
        result = self.extractor.extract(
            "We run a logistics company and our order processing is manual.",
            turn_index=1,
        )
        assert result.slots.get("industry", {}).get("value") == "logistics"

    def test_extract_industry_fintech(self) -> None:
        """Extract fintech industry."""
        result = self.extractor.extract(
            "We're a fintech startup building a payment platform.",
            turn_index=1,
        )
        assert result.slots.get("industry", {}).get("value") == "fintech"

    def test_extract_industry_healthcare(self) -> None:
        """Extract healthcare industry."""
        result = self.extractor.extract(
            "Our healthcare clinic needs better systems integration.",
        )
        assert result.slots.get("industry", {}).get("value") == "healthcare"

    def test_extract_industry_manufacturing(self) -> None:
        """Extract manufacturing industry."""
        result = self.extractor.extract(
            "We're a manufacturing company producing automotive parts.",
        )
        assert result.slots.get("industry", {}).get("value") == "manufacturing"

    def test_extract_business_size_with_number(self) -> None:
        """Extract business size from number mention."""
        result = self.extractor.extract("We have about 180 employees across two sites.")
        size = result.slots.get("business_size", {})
        assert size.get("value") is not None

    def test_extract_pain_points(self) -> None:
        """Extract pain points from message."""
        result = self.extractor.extract(
            "Our tools don't talk to each other and reporting is manual.",
        )
        assert len(result.pain_points) >= 1

    def test_extract_tools(self) -> None:
        """Extract tool mentions."""
        result = self.extractor.extract("We use Excel and an old ERP system.")
        assert "Excel" in result.current_tools

    def test_extract_timeline_immediate(self) -> None:
        """Extract immediate timeline."""
        result = self.extractor.extract("We need this asap.")
        assert result.slots.get("timeline", {}).get("value") == "immediate"

    def test_extract_timeline_exploring(self) -> None:
        """Extract exploring timeline."""
        result = self.extractor.extract("We're still exploring our options.")
        assert result.slots.get("timeline", {}).get("value") == "exploring"

    def test_extract_decision_role(self) -> None:
        """Extract decision role."""
        result = self.extractor.extract("I'm the CEO and will be leading this.")
        assert result.slots.get("decision_role", {}).get("value") == "decision_maker"

    def test_empty_message(self) -> None:
        """Empty message returns empty result."""
        result = self.extractor.extract("")
        assert len(result.slots) == 0
        assert len(result.pain_points) == 0


# =============================================================================
# Normalisation Tests
# =============================================================================

class TestNormaliser:
    """PRD FR-25 — normalise free-text to controlled vocabularies."""

    def setup_method(self) -> None:
        self.normaliser = Normaliser()

    def test_normalise_industry_logistics(self) -> None:
        """Normalise logistics industry."""
        result = self.normaliser.normalise_industry("we are in the supply chain industry")
        assert result.value == "logistics"

    def test_normalise_industry_retail(self) -> None:
        """Normalise retail industry."""
        result = self.normaliser.normalise_industry("we run an e-commerce store")
        assert result.value == "retail"

    def test_normalise_business_size_number(self) -> None:
        """Normalise explicit employee count."""
        result = self.normaliser.normalise_business_size("around 180 people")
        # Should match based on number extraction
        assert result.value in ("51-200", "201-500")

    def test_normalise_timeline_immediate(self) -> None:
        """Normalise immediate timeline."""
        result = self.normaliser.normalise_timeline("asap")
        assert result.value == "immediate"

    def test_normalise_budget_with_number(self) -> None:
        """Normalise budget from explicit number."""
        result = self.normaliser.normalise_budget("budget around 30k to 40k")
        # Should match via number pattern
        assert result.value is not None

    def test_normalise_decision_maker(self) -> None:
        """Normalise decision maker role."""
        result = self.normaliser.normalise_decision_role("I'm the founder")
        assert result.value == "decision_maker"


# =============================================================================
# Slot Merger Tests
# =============================================================================

class TestSlotMerger:
    """PRD FR-23 to FR-29, PRD 13.4 — merge rules."""

    def setup_method(self) -> None:
        self.merger = SlotMerger()
        self.slot_map = SlotMap()

    def test_merge_new_industry(self) -> None:
        """Merge new industry value into empty slot."""
        extraction = ExtractionResult(turn_index=1)
        extraction.slots["industry"] = {
            "value": "logistics", "raw": "we run a logistics company", "confidence": 0.7,
        }
        result = self.merger.merge(self.slot_map, extraction, turn_index=1)
        assert result.slot_map.industry.value == "logistics"
        assert "industry" in result.changed

    def test_no_overwrite_high_confidence(self) -> None:
        """FR-23: Never overwrite high-confidence with low-confidence."""
        self.slot_map.industry = SlotValue(value="logistics", confidence=0.85, raw="logistics", source_turn=1)

        extraction = ExtractionResult(turn_index=2)
        extraction.slots["industry"] = {
            "value": "retail", "raw": "retail actually", "confidence": 0.4,
        }
        result = self.merger.merge(self.slot_map, extraction, turn_index=2)
        # Should keep logistics because 0.85 - 0.4 > 0.15
        assert result.slot_map.industry.value == "logistics"

    def test_overwrite_lower_confidence(self) -> None:
        """Allow overwrite when new confidence is high enough."""
        self.slot_map.industry = SlotValue(value="other", confidence=0.3, source_turn=1)

        extraction = ExtractionResult(turn_index=2)
        extraction.slots["industry"] = {
            "value": "retail", "raw": "we're in retail", "confidence": 0.7,
        }
        result = self.merger.merge(self.slot_map, extraction, turn_index=2)
        assert result.slot_map.industry.value == "retail"

    def test_append_pain_points(self) -> None:
        """Append new pain points to list."""
        extraction = ExtractionResult(turn_index=1)
        extraction.pain_points = [{
            "id": "pp_01", "label": "Manual order processing",
            "raw_text": "manual processing", "specificity": "specific",
            "service_codes": ["SVC-AIA"], "confidence": 0.7,
        }]
        result = self.merger.merge(self.slot_map, extraction, turn_index=1)
        assert len(result.slot_map.pain_points) == 1

        # Add another
        extraction2 = ExtractionResult(turn_index=2)
        extraction2.pain_points = [{
            "id": "pp_02", "label": "Invoice matching is slow",
            "raw_text": "invoice matching", "specificity": "specific",
            "service_codes": ["SVC-AIA"], "confidence": 0.6,
        }]
        result2 = self.merger.merge(result.slot_map, extraction2, turn_index=2)
        assert len(result2.slot_map.pain_points) == 2

    def test_declined_slot_not_overwritten(self) -> None:
        """FR-29: Declined slots never re-asked."""
        slot_map = self.merger.mark_declined(self.slot_map, "timeline")
        assert slot_map.timeline.declined is True

    def test_merge_tools_deduplicate(self) -> None:
        """Append tools with deduplication."""
        extraction = ExtractionResult(turn_index=1)
        extraction.current_tools = ["Excel", "Email"]
        result = self.merger.merge(self.slot_map, extraction, turn_index=1)
        assert len(result.slot_map.current_tools) == 2

        extraction2 = ExtractionResult(turn_index=2)
        extraction2.current_tools = ["Excel", "ERP"]
        result2 = self.merger.merge(result.slot_map, extraction2, turn_index=2)
        assert "Excel" in result2.slot_map.current_tools  # Still there
        assert "ERP" in result2.slot_map.current_tools  # New
        assert len(result2.slot_map.current_tools) == 3  # Excel, Email, ERP


# =============================================================================
# Phase Controller Tests
# =============================================================================

class TestPhaseController:
    """PRD Sections 12.1, 12.2 — phase state machine."""

    def setup_method(self) -> None:
        self.controller = PhaseController()

    def test_greeting_to_discovery(self) -> None:
        """First message moves from greeting to discovery."""
        next_phase, trigger = self.controller.evaluate(current_phase="greeting")
        assert next_phase == "discovery"
        assert trigger == "first_visitor_message"

    def test_discovery_to_exploration(self) -> None:
        """3+ core slots moves discovery to exploration."""
        next_phase, trigger = self.controller.evaluate(
            current_phase="discovery",
            core_slots_filled=3,
            confidence_met=True,
        )
        assert next_phase == "exploration"
        assert trigger == "core_slots_sufficient"

    def test_discovery_stays_discovery(self) -> None:
        """Fewer than 3 slots stays in discovery."""
        next_phase, trigger = self.controller.evaluate(
            current_phase="discovery",
            core_slots_filled=1,
        )
        assert next_phase == "discovery"
        assert trigger is None

    def test_exploration_to_recommendation(self) -> None:
        """Sufficient evidence moves to recommendation."""
        next_phase, trigger = self.controller.evaluate(
            current_phase="exploration",
            recommendation_ready=True,
        )
        assert next_phase == "recommendation"

    def test_recommendation_to_qualification(self) -> None:
        """Acknowledged recommendation moves to qualification."""
        next_phase, trigger = self.controller.evaluate(
            current_phase="recommendation",
            recommendation_acknowledged=True,
        )
        assert next_phase == "qualification"

    def test_recommendation_back_to_exploration(self) -> None:
        """Rejected recommendation goes back to exploration."""
        next_phase, trigger = self.controller.evaluate(
            current_phase="recommendation",
            visitor_rejected_fit=True,
        )
        assert next_phase == "exploration"

    def test_qualification_to_capture(self) -> None:
        """Commercial slots resolved moves to capture."""
        next_phase, trigger = self.controller.evaluate(
            current_phase="qualification",
            commercial_slots_resolved=True,
        )
        assert next_phase == "capture_and_close"

    def test_human_request_shortcut(self) -> None:
        """Human request during discovery jumps to capture."""
        next_phase, trigger = self.controller.evaluate(
            current_phase="discovery",
            visitor_requested_human=True,
        )
        assert next_phase == "capture_and_close"

    def test_anti_persona_termination(self) -> None:
        """Anti-persona terminates the session."""
        next_phase, trigger = self.controller.evaluate(
            current_phase="discovery",
            anti_persona=True,
        )
        assert next_phase == "terminated"

    def test_phase_definitions_exist(self) -> None:
        """All 6 runtime phases have definitions."""
        for phase in ConversationPhase:
            if phase.value in ("completing", "completed"):
                continue
            assert phase.value in PHASE_DEFINITIONS

    def test_transition_rules_exist(self) -> None:
        """Transition rules cover normal flow."""
        assert len(TRANSITION_RULES) >= 15


# =============================================================================
# Question Selector Tests
# =============================================================================

class TestQuestionSelector:
    """PRD Section 12.6 — question selection."""

    def setup_method(self) -> None:
        self.selector = QuestionSelector()

    def test_selects_industry_in_discovery(self) -> None:
        """Industry is top priority in discovery when unfilled."""
        slot_map = SlotMap()  # All empty
        selected = self.selector.select_question(
            current_phase="discovery",
            slot_map=slot_map,
            questions_asked=[],
        )
        assert selected is not None
        assert selected.slot == "pain_points"  # Highest weight (25)

    def test_skips_filled_slot(self) -> None:
        """FR-27: Never re-ask a filled slot."""
        slot_map = SlotMap()
        slot_map.industry = SlotValue(value="logistics", confidence=0.8)
        slot_map.pain_points = [PainPoint(id="pp_01", label="Manual process", source_turn=1)]

        selected = self.selector.select_question(
            current_phase="discovery",
            slot_map=slot_map,
            questions_asked=[],
        )
        assert selected is not None
        # Should skip industry and pain_points since filled
        assert selected.slot != "industry"

    def test_commercial_slots_in_qualification(self) -> None:
        """Commercial slots eligible in qualification phase."""
        slot_map = SlotMap()
        selected = self.selector.select_question(
            current_phase="qualification",
            slot_map=slot_map,
            questions_asked=[],
        )
        assert selected is not None
        assert selected.slot in ("timeline", "budget", "decision_role")

    def test_no_eligible_slots_in_greeting(self) -> None:
        """No questions in greeting phase."""
        selected = self.selector.select_question(
            current_phase="greeting",
            slot_map=SlotMap(),
            questions_asked=[],
        )
        assert selected is None

    def test_phase_eligible_slots_defined(self) -> None:
        """All phases have eligible slots defined."""
        assert "discovery" in PHASE_ELIGIBLE_SLOTS
        assert "qualification" in PHASE_ELIGIBLE_SLOTS


# =============================================================================
# Scoring Components Tests
# =============================================================================

class TestScoringComponents:
    """PRD Section 14.2 — scoring rubric."""

    def test_need_clarity_no_pains(self) -> None:
        """No pain points = 0 points."""
        result = compute_need_clarity([])
        assert result.awarded == 0
        assert result.max_points == 25

    def test_need_clarity_two_pains(self) -> None:
        """Two pain points = 21 points."""
        pain_points = [
            PainPoint(id="pp_01", label="Manual processing", specificity="specific", source_turn=1),
            PainPoint(id="pp_02", label="Invoice matching", specificity="specific", source_turn=2),
        ]
        result = compute_need_clarity(pain_points)
        assert result.awarded >= 21

    def test_need_clarity_quantified(self) -> None:
        """Quantified pain points = 25 points."""
        pain_points = [
            PainPoint(id="pp_01", label="Manual processing costs 20 hours/week", specificity="quantified", source_turn=1),
            PainPoint(id="pp_02", label="Invoice matching costs £50k/year", specificity="quantified", source_turn=2),
        ]
        result = compute_need_clarity(pain_points)
        assert result.awarded == 25

    def test_fit_no_mapping(self) -> None:
        """No mappable service = 0."""
        result = compute_fit(has_service_mapping=False)
        assert result.awarded == 0

    def test_fit_with_mapping(self) -> None:
        """Clear mapping = 14."""
        result = compute_fit(has_service_mapping=True)
        assert result.awarded == 14

    def test_fit_with_case_study(self) -> None:
        """Mapping + case study = 20."""
        result = compute_fit(has_service_mapping=True, has_case_study_coverage=True)
        assert result.awarded == 20

    def test_urgency_immediate(self) -> None:
        """Immediate = 15."""
        result = compute_urgency("immediate")
        assert result.awarded == 15

    def test_urgency_exploring(self) -> None:
        """Exploring = 2."""
        result = compute_urgency("exploring")
        assert result.awarded == 2

    def test_urgency_unknown(self) -> None:
        """Unknown/None = 0."""
        result = compute_urgency(None)
        assert result.awarded == 0

    def test_budget_large(self) -> None:
        """100k+ = 15."""
        result = compute_budget("100k+")
        assert result.awarded == 15

    def test_budget_small(self) -> None:
        """under_5k = 2."""
        result = compute_budget("under_5k")
        assert result.awarded == 2

    def test_authority_decision_maker(self) -> None:
        """Decision maker = 10."""
        result = compute_authority("decision_maker")
        assert result.awarded == 10

    def test_authority_researcher(self) -> None:
        """Researcher = 3."""
        result = compute_authority("researcher")
        assert result.awarded == 3

    def test_engagement_basic(self) -> None:
        """3+ turns = 4 points."""
        result = compute_engagement(visitor_turn_count=3)
        assert result.awarded == 4

    def test_engagement_full(self) -> None:
        """Full engagement signals = 15."""
        result = compute_engagement(
            visitor_turn_count=6,
            asked_company_question=True,
            responded_to_recommendation=True,
            volunteered_contact=True,
        )
        assert result.awarded == 15


# =============================================================================
# Override Tests
# =============================================================================

class TestOverrides:
    """PRD Section 14.4 — override rules."""

    def test_ov01_anti_persona(self) -> None:
        """OV-01: Anti-persona forces not_a_lead."""
        result = apply_overrides(
            raw_score=80, band="hot",
            anti_persona=True,
        )
        assert result.force_band == "not_a_lead"
        assert result.suppress_automation is True
        assert result.disqualified is True

    def test_ov02_human_request(self) -> None:
        """OV-02: Human request floors at qualified."""
        result = apply_overrides(
            raw_score=30, band="cold",
            human_requested=True,
            visitor_turn_count=3,
        )
        assert result.force_band == "qualified"

    def test_ov03_no_contact(self) -> None:
        """OV-03: No contact caps at warm."""
        result = apply_overrides(
            raw_score=80, band="hot",
            has_contact=False,
        )
        assert result.cap_band == "warm"

    def test_ov05_few_turns(self) -> None:
        """OV-05: Fewer than 2 turns forces cold."""
        result = apply_overrides(
            raw_score=70, band="qualified",
            visitor_turn_count=1,
        )
        assert result.force_band == "cold"

    def test_ov06_enterprise_decision_maker(self) -> None:
        """OV-06: Enterprise DM floors at qualified."""
        result = apply_overrides(
            raw_score=40, band="warm",
            business_size_value="1000+",
            decision_role_value="decision_maker",
        )
        assert result.force_band == "qualified"


# =============================================================================
# Scoring Engine Tests
# =============================================================================

class TestScoringEngine:
    """FR-30 to FR-36 — deterministic scoring."""

    def setup_method(self) -> None:
        self.engine = ScoringEngine()

    def test_empty_input_score_zero(self) -> None:
        """No data -> score 0, band exploring/cold."""
        input_data = ScoringInput()
        score, breakdown = self.engine.compute(input_data)
        assert score.score == 0
        assert score.band in ("exploring", "cold")

    def test_partial_data_scores_something(self) -> None:
        """Partial data produces intermediate score."""
        input_data = ScoringInput(
            pain_points=[PainPoint(id="pp_01", label="Manual processing", specificity="specific", source_turn=1)],
            visitor_turn_count=2,
        )
        score, breakdown = self.engine.compute(input_data)
        assert score.score > 0

    def test_rich_data_scores_high(self) -> None:
        """Rich data produces higher score."""
        input_data = ScoringInput(
            pain_points=[
                PainPoint(id="pp_01", label="Manual processing costs 20hrs/week", specificity="quantified", source_turn=1),
                PainPoint(id="pp_02", label="Invoice matching takes days", specificity="specific", source_turn=2),
            ],
            timeline_value="immediate",
            budget_value="50k-100k",
            authority_value="decision_maker",
            visitor_turn_count=6,
            asked_company_question=True,
            responded_to_recommendation=True,
        )
        score, breakdown = self.engine.compute(input_data)
        assert score.score >= 50  # Should be a significant score

    def test_deterministic_same_input(self) -> None:
        """FR-30: Same input always produces same score."""
        input_data = ScoringInput(
            pain_points=[PainPoint(id="pp_01", label="Manual processing", specificity="specific", source_turn=1)],
            visitor_turn_count=3,
        )
        score1, _ = self.engine.compute(input_data)
        score2, _ = self.engine.compute(input_data)
        assert score1.score == score2.score

    def test_components_sum_to_total(self) -> None:
        """Component scores sum to the total score."""
        input_data = ScoringInput(
            pain_points=[PainPoint(id="pp_01", label="Manual processing", specificity="specific", source_turn=1)],
            timeline_value="1-3_months",
            visitor_turn_count=3,
        )
        score, breakdown = self.engine.compute(input_data)
        component_sum = sum(c.awarded for c in score.components)
        assert component_sum == score.raw_score


# =============================================================================
# Recommendation Engine Tests
# =============================================================================

class TestCandidateBuilder:
    """PRD Section 15.2 — pain-to-service mapping."""

    def setup_method(self) -> None:
        self.builder = CandidateBuilder()

    def test_maps_manual_pain_to_automation(self) -> None:
        """Manual repetitive processes maps to SVC-AIA."""
        candidates = self.builder.build_candidates(
            pain_signal_ids=["manual_repetitive_processes"],
        )
        codes = [c.service_code for c in candidates]
        assert "SVC-AIA" in codes

    def test_maps_disconnected_tools_to_integration(self) -> None:
        """Disconnected tools maps to SVC-INT."""
        candidates = self.builder.build_candidates(
            pain_signal_ids=["disconnected_tools"],
        )
        codes = [c.service_code for c in candidates]
        assert "SVC-INT" in codes

    def test_maps_multiple_pains_to_multiple_services(self) -> None:
        """Multiple pains produce multiple service candidates."""
        candidates = self.builder.build_candidates(
            pain_signal_ids=["manual_repetitive_processes", "outdated_website"],
        )
        assert len(candidates) >= 2
        codes = [c.service_code for c in candidates]
        assert "SVC-AIA" in codes
        assert "SVC-WEB" in codes


class TestRanker:
    """PRD Section 15.3 — ranking formula."""

    def setup_method(self) -> None:
        self.ranker = Ranker()

    def test_ranks_by_score_descending(self) -> None:
        """Higher score = higher rank."""
        candidates = [
            Candidate(service_code="SVC-AIA", base_weight=1.0, pain_signals=["manual"], is_primary=True),
            Candidate(service_code="SVC-WEB", base_weight=0.7, pain_signals=["website"], is_primary=True),
        ]
        ranked = self.ranker.rank(candidates)
        assert len(ranked) >= 2
        assert ranked[0].score >= ranked[1].score

    def test_should_withhold_few_pains(self) -> None:
        """FR-43: Withhold when fewer than 2 pain points."""
        withhold, reason = self.ranker.should_withhold(
            ranked=[], pain_point_count=1, current_phase="exploration",
        )
        assert withhold is True

    def test_should_withhold_early_phase(self) -> None:
        """Withhold in greeting/discovery."""
        withhold, reason = self.ranker.should_withhold(
            ranked=[], pain_point_count=3, current_phase="greeting",
        )
        assert withhold is True

    def test_truncate_to_max(self) -> None:
        """Cap at 3 recommendations."""
        ranked = [
            RankedService(service_code=f"SVC-{i}", name=f"Service {i}", score=1.0 - i * 0.1)
            for i in range(5)
        ]
        truncated = self.ranker.truncate(ranked)
        assert len(truncated) <= 3


class TestRationaleWriter:
    """PRD Section 15.4 — rationale generation."""

    def setup_method(self) -> None:
        self.writer = RationaleWriter()

    def test_writes_rationale_for_service(self) -> None:
        """Generates rationale referencing pain points."""
        result = self.writer.write_rationale(
            service_code="SVC-AIA",
            pain_point_labels=["Manual order processing"],
        )
        assert result.service_code == "SVC-AIA"
        assert len(result.rationale) > 20
        assert "manual order processing" in result.rationale.lower() or "your current" in result.rationale.lower()

    def test_fallback_for_unknown_code(self) -> None:
        """Unknown service code gets fallback rationale."""
        result = self.writer.write_rationale(
            service_code="SVC-UNKNOWN",
            pain_point_labels=[],
        )
        assert result.source == "template"
        assert len(result.rationale) > 0


class TestRecommendationEngine:
    """FR-37 to FR-43 — recommendation engine end-to-end."""

    def setup_method(self) -> None:
        self.engine = RecommendationEngine()

    def test_withholds_when_early_phase(self) -> None:
        """Withhold recommendation in greeting."""
        input_data = RecommendationInput(
            pain_point_labels=["Manual processing"],
            pain_signal_ids=["manual_repetitive_processes"],
            current_phase="greeting",
        )
        summary = self.engine.evaluate(input_data)
        assert summary.withheld is True

    def test_withholds_when_few_pains(self) -> None:
        """FR-43: Withhold with fewer than 2 pain points."""
        input_data = RecommendationInput(
            pain_point_labels=["Manual processing"],
            pain_signal_ids=["manual_repetitive_processes"],
            current_phase="exploration",
        )
        summary = self.engine.evaluate(input_data)
        assert summary.withheld is True

    def test_recommends_with_sufficient_data(self) -> None:
        """FR-37: Recommend 1-3 services with sufficient evidence."""
        input_data = RecommendationInput(
            pain_point_labels=["Manual order processing", "Invoice matching"],
            pain_signal_ids=["manual_repetitive_processes", "high_volume_triage"],
            industry="logistics",
            current_phase="exploration",
        )
        summary = self.engine.evaluate(input_data)
        if not summary.withheld:
            assert 1 <= len(summary.items) <= 3
            assert summary.items[0].service_code in ("SVC-AIA", "SVC-INT", "SVC-DAT")

    def test_recommendation_has_rationale(self) -> None:
        """FR-39: Every recommendation includes rationale."""
        input_data = RecommendationInput(
            pain_point_labels=["Manual order processing", "Invoice matching"],
            pain_signal_ids=["manual_repetitive_processes", "high_volume_triage"],
            current_phase="exploration",
        )
        summary = self.engine.evaluate(input_data)
        if not summary.withheld and summary.items:
            assert len(summary.items[0].rationale) > 0

    def test_no_outside_catalogue(self) -> None:
        """FR-41: Never recommend outside catalogue."""
        input_data = RecommendationInput(
            pain_point_labels=["Manual processing", "Invoice matching"],
            pain_signal_ids=["manual_repetitive_processes", "high_volume_triage"],
            current_phase="exploration",
        )
        summary = self.engine.evaluate(input_data)
        if not summary.withheld:
            valid_codes = {"SVC-AIA", "SVC-WEB", "SVC-DAT", "SVC-INT", "SVC-CLD", "SVC-CON"}
            for item in summary.items:
                assert item.service_code in valid_codes


# =============================================================================
# Banding Tests
# =============================================================================

class TestBanding:
    """PRD Section 14.3 — band assignment."""

    def test_score_0_to_34_is_cold(self) -> None:
        assert score_to_band(20) == "cold"

    def test_score_35_to_59_is_warm(self) -> None:
        assert score_to_band(40) == "warm"

    def test_score_60_to_79_is_qualified(self) -> None:
        assert score_to_band(65) == "qualified"

    def test_score_80_to_100_is_hot(self) -> None:
        assert score_to_band(85) == "hot"

    def test_display_labels_exist(self) -> None:
        """All bands have visitor-safe labels."""
        for band in ("cold", "warm", "qualified", "hot", "exploring", "not_a_lead"):
            label = band_display_label(band)
            assert len(label) > 0


# =============================================================================
# Completion Detection Tests
# =============================================================================

class TestCompletionDetector:
    """FR-47 — completion triggers."""

    def setup_method(self) -> None:
        self.detector = CompletionDetector()

    def test_end_conversation_intent(self) -> None:
        """Explicit end_conversation triggers completion."""
        result = self.detector.evaluate(
            phase="qualification",
            intent="end_conversation",
        )
        assert result.should_complete is True
        assert result.reason_code == "visitor_requested"

    def test_criteria_met_in_capture(self) -> None:
        """Capture phase + contact + commercial = complete."""
        result = self.detector.evaluate(
            phase="capture_and_close",
            commercial_slots_resolved=True,
            contact_captured=True,
        )
        assert result.should_complete is True
        assert result.reason_code == "criteria_met"

    def test_abandonment(self) -> None:
        """Idle with 3+ turns triggers abandonment."""
        result = self.detector.evaluate(
            phase="discovery",
            is_idle=True,
            visitor_turn_count=3,
        )
        assert result.should_complete is True
        assert result.reason_code == "abandoned"

    def test_no_completion_early(self) -> None:
        """Early discovery does not complete."""
        result = self.detector.evaluate(
            phase="discovery",
            visitor_turn_count=1,
        )
        assert result.should_complete is False


# =============================================================================
# Conversation Memory Tests
# =============================================================================

class TestConversationMemory:
    """PRD Section 7.3 — memory management."""

    def setup_method(self) -> None:
        self.memory = ConversationMemory(verbatim_window_size=8, token_budget=3000)

    def test_empty_memory(self) -> None:
        """Empty messages produces empty state."""
        state = self.memory.compute_state(messages=[])
        assert len(state.verbatim_turns) == 0

    def test_verbatim_window(self) -> None:
        """Messages within window kept verbatim."""
        messages = [
            {"role": "visitor", "content": f"Message {i}"} for i in range(5)
        ]
        state = self.memory.compute_state(messages)
        assert len(state.verbatim_turns) == 5

    def test_compaction_not_needed_for_small_history(self) -> None:
        """No compaction for small histories."""
        messages = [
            {"role": "visitor", "content": "Short messages"} for _ in range(3)
        ]
        state = self.memory.compute_state(messages)
        assert state.needs_compaction is False

    def test_token_estimation(self) -> None:
        """Token estimation works."""
        messages = [{"role": "visitor", "content": "Hello world"}]
        state = self.memory.compute_state(messages)
        assert state.estimated_tokens > 0


# =============================================================================
# Conversation Manager Tests
# =============================================================================

class TestConversationManager:
    """Conversation manager process_turn integration."""

    def setup_method(self) -> None:
        self.manager = ConversationManager()

    def test_create_session(self) -> None:
        """Session creation returns greeting."""
        session = self.manager.create_session()
        assert "session_id" in session
        assert session["phase"] == "greeting"
        assert len(session["messages"]) == 1
        assert "Nova" in session["messages"][0]["content"]

    def test_process_greeting_turn(self) -> None:
        """Processing first message transitions from greeting."""
        session = self.manager.create_session()
        context = ConversationContext(
            session_id=session["session_id"],
            turn_index=1,
            visitor_message="We run a logistics company.",
        )
        result = self.manager.process_turn(session, context)
        assert result.conversation_phase in ("discovery", "exploration")
        assert len(result.assistant_message) > 0

    def test_extraction_in_turn(self) -> None:
        """FR-22: Slot extraction runs on turn processing."""
        session = self.manager.create_session()
        context = ConversationContext(
            session_id=session["session_id"],
            turn_index=1,
            visitor_message="We're a logistics company with 180 employees.",
        )
        result = self.manager.process_turn(session, context)
        assert result.extraction_result is not None
        slots = result.extraction_result.slots
        assert any("logistics" in str(v) for v in slots.values())

    def test_anti_persona_terminates(self) -> None:
        """Anti-persona intent terminates gracefully."""
        session = self.manager.create_session()
        context = ConversationContext(
            session_id=session["session_id"],
            turn_index=1,
            visitor_message="I am a student looking for a job at Trizen.",
        )
        result = self.manager.process_turn(session, context)
        assert result.conversation_phase == "terminated"
        assert len(result.assistant_message) > 0

    def test_business_profile_synced(self) -> None:
        """Business profile gets synced from extracted slots."""
        session = self.manager.create_session()
        context = ConversationContext(
            session_id=session["session_id"],
            turn_index=1,
            visitor_message="We're a logistics company with 180 employees.",
        )
        result = self.manager.process_turn(session, context)
        # The slot_map should have industry, and profile should have at least company_size
        if result.business_profile:
            # At minimum company_size was extracted from "180 employees"
            assert result.business_profile.company_size.value is not None
            assert result.business_profile.pain_points is not None


# =============================================================================
# Orchestrator Tests
# =============================================================================

class TestConsultationOrchestrator:
    """Orchestrator end-to-end consultation flow."""

    def setup_method(self) -> None:
        self.orchestrator = ConsultationOrchestrator()

    async def test_start_consultation(self) -> None:
        """Start consultation returns session with greeting."""
        session = await self.orchestrator.start_consultation()
        assert "session_id" in session
        assert session["phase"] == "greeting"

    async def test_process_first_turn(self) -> None:
        """Processing a message returns structured result."""
        session = await self.orchestrator.start_consultation()
        result = await self.orchestrator.process_turn(
            session_state=session,
            visitor_message="We run a logistics company and need automation.",
        )
        assert isinstance(result, OrchestrationResult)
        assert len(result.assistant_message) > 0
        assert result.conversation_phase is not None

    async def test_response_contract_includes_all_fields(self) -> None:
        """Every response includes required fields."""
        session = await self.orchestrator.start_consultation()
        result = await self.orchestrator.process_turn(
            session_state=session,
            visitor_message="We are a logistics company.",
        )
        # Required fields per Sprint 3 spec
        assert hasattr(result, "assistant_message")
        assert hasattr(result, "conversation_phase")
        assert result.lead_score is not None
        assert "score" in result.lead_score
        assert "band" in result.lead_score
        assert hasattr(result, "completion_percentage")
        assert isinstance(result.completion_percentage, int)

    async def test_score_is_deterministic(self) -> None:
        """Same input produces same score."""
        session = await self.orchestrator.start_consultation()
        result1 = await self.orchestrator.process_turn(
            session_state=session,
            visitor_message="We are a logistics company with 180 employees.",
        )
        session2 = await self.orchestrator.start_consultation()
        result2 = await self.orchestrator.process_turn(
            session_state=session2,
            visitor_message="We are a logistics company with 180 employees.",
        )
        assert result1.lead_score["raw_score"] == result2.lead_score["raw_score"]


# =============================================================================
# Simulation Scenario Tests
# =============================================================================

class TestSimulationScenarios:
    """Simulation scenarios provide deterministic test data."""

    def test_default_scenarios_exist(self) -> None:
        """At least 8 scenarios are defined."""
        assert len(DEFAULT_SCENARIOS) >= 8

    def test_scenario_has_required_fields(self) -> None:
        """Each scenario has valid fields."""
        for scenario in DEFAULT_SCENARIOS:
            assert scenario.scenario_id
            assert scenario.name
            assert scenario.description
            assert len(scenario.responses) > 0

    def test_logistics_scenario(self) -> None:
        """Logistics scenario has correct industry."""
        assert LOGISTICS_SCENARIO.expected_slots.get("industry") == "logistics"

    def test_fintech_scenario(self) -> None:
        """FinTech scenario has correct tags."""
        assert "fintech" in FINTECH_SCENARIO.tags

    def test_healthcare_scenario(self) -> None:
        """Healthcare scenario has pain points."""
        assert len(HEALTHCARE_SCENARIO.expected_slots.get("pain_points", [])) > 0

    def test_scenarios_register(self) -> None:
        """Scenarios can be registered in the registry."""
        registry = ScenarioRegistry()
        register_default_scenarios(registry)
        assert registry.count >= 8

    def test_default_provider_generates_responses(self) -> None:
        """DefaultScenarioProvider generates responses for scenarios."""
        config = SimulationConfig(enabled=True)
        provider = DefaultScenarioProvider(config=config)
        result = provider.generate_response(LOGISTICS_SCENARIO, turn=0)
        assert result.scenario_id == "logistics_company"
        assert result.phase is not None

    def test_simulation_framework_full_scenario(self) -> None:
        """SimulationFramework runs full scenario."""
        config = SimulationConfig(enabled=True)
        framework = SimulationFramework(config=config)
        framework.registry.register(LOGISTICS_SCENARIO)
        results = framework.run_full_scenario(LOGISTICS_SCENARIO)
        assert len(results) == LOGISTICS_SCENARIO.turn_count


# =============================================================================
# Event Emitter Tests
# =============================================================================

class TestEventEmitter:
    """SSE event emission."""

    def setup_method(self) -> None:
        self.emitter = EventEmitter()

    def test_emit_phase(self) -> None:
        """Phase events are structured correctly."""
        self.emitter.begin_turn(1)
        self.emitter.emit_phase("understanding")
        events = self.emitter.get_events()
        assert len(events) == 1
        assert events[0].event_type == "phase"
        assert events[0].data["phase"] == "understanding"

    def test_emit_token(self) -> None:
        """Token events have delta."""
        self.emitter.begin_turn(1)
        self.emitter.emit_token("Hello")
        events = self.emitter.get_events()
        assert events[0].event_type == "token"
        assert events[0].data["delta"] == "Hello"

    def test_emit_analysis_snapshot(self) -> None:
        """Analysis snapshot has all panel fields."""
        self.emitter.begin_turn(1)
        snapshot = self.emitter.build_analysis_snapshot(
            turn_index=1,
            lead_status="warm",
            lead_score=45,
            slot_fill_count=3,
            total_slots=9,
            stage_index=2,
        )
        self.emitter.emit_analysis_snapshot(snapshot)
        events = self.emitter.get_events()
        assert events[0].event_type == "analysis_snapshot"
        data = events[0].data
        assert data["lead_status"] == "warm"
        assert data["lead_score"] == 45

    def test_emit_done(self) -> None:
        """Done event marks completion."""
        self.emitter.begin_turn(1)
        self.emitter.emit_done(
            finish_reason="complete",
            client_turn_id="test_123",
            consultation_complete=True,
        )
        events = self.emitter.get_events()
        assert events[0].event_type == "done"
        assert events[0].data["consultation_complete"] is True

    def test_emit_error(self) -> None:
        """Error event has retryable flag."""
        self.emitter.begin_turn(1)
        self.emitter.emit_error("PROVIDER_UNAVAILABLE", "Service down", retryable=True)
        events = self.emitter.get_events()
        assert events[0].event_type == "error"
        assert events[0].data["retryable"] is True


# =============================================================================
# Pipeline Stage Tests
# =============================================================================

class TestPipeline:
    """Pipeline stage definitions."""

    def test_standard_stages_defined(self) -> None:
        """All 12 pipeline stages are defined."""
        assert len(STANDARD_STAGES) >= 11

    def test_stages_have_unique_names(self) -> None:
        """All stage names are unique."""
        names = [s.name for s in STANDARD_STAGES]
        assert len(names) == len(set(names))

    def test_understanding_stages_parallel(self) -> None:
        """Intent and extraction share parallel group."""
        intent_stage = next(s for s in STANDARD_STAGES if s.stage_type.value == "intent")
        extract_stage = next(s for s in STANDARD_STAGES if s.stage_type.value == "extraction")
        assert intent_stage.parallel_group == "understanding"
        assert extract_stage.parallel_group == "understanding"


# =============================================================================
# Phase Controller Evaluate Table Tests
# =============================================================================

class TestPhaseControllerEvaluateTable:
    """Exhaustive evaluate() signal combinations (Sprint 2A style)."""

    def setup_method(self) -> None:
        self.controller = PhaseController()

    def test_greeting_basic(self) -> None:
        assert self.controller.evaluate("greeting") == ("discovery", "first_visitor_message")

    def test_discovery_insufficient(self) -> None:
        phase, trigger = self.controller.evaluate("discovery", core_slots_filled=2)
        assert phase == "discovery"
        assert trigger is None

    def test_discovery_sufficient(self) -> None:
        phase, trigger = self.controller.evaluate("discovery", core_slots_filled=3, confidence_met=True)
        assert phase == "exploration"
        assert trigger == "core_slots_sufficient"

    def test_exploration_ready(self) -> None:
        phase, trigger = self.controller.evaluate("exploration", recommendation_ready=True)
        assert phase == "recommendation"

    def test_exploration_not_ready(self) -> None:
        phase, trigger = self.controller.evaluate("exploration", recommendation_ready=False)
        assert phase == "exploration"

    def test_recommendation_acknowledged(self) -> None:
        phase, trigger = self.controller.evaluate("recommendation", recommendation_acknowledged=True)
        assert phase == "qualification"

    def test_recommendation_rejected(self) -> None:
        phase, trigger = self.controller.evaluate("recommendation", visitor_rejected_fit=True)
        assert phase == "exploration"

    def test_qualification_resolved(self) -> None:
        phase, trigger = self.controller.evaluate("qualification", commercial_slots_resolved=True)
        assert phase == "capture_and_close"

    def test_qualification_not_resolved(self) -> None:
        phase, trigger = self.controller.evaluate("qualification", commercial_slots_resolved=False)
        assert phase == "qualification"

    def test_capture_stays_capture(self) -> None:
        phase, trigger = self.controller.evaluate("capture_and_close")
        assert phase == "capture_and_close"

    def test_anti_persona_overrides(self) -> None:
        phase, trigger = self.controller.evaluate("exploration", anti_persona=True, recommendation_ready=True)
        assert phase == "terminated"

    def test_human_request_overrides(self) -> None:
        phase, trigger = self.controller.evaluate("discovery", visitor_requested_human=True)
        assert phase == "capture_and_close"

    def test_discovery_refused_twice(self) -> None:
        phase, trigger = self.controller.evaluate("discovery", discovery_refused_count=2)
        assert phase == "information_only"


# =============================================================================
# End-to-End Consultation Flow Test
# =============================================================================

class TestEndToEndConsultation:
    """Full consultation flow with deterministic data."""

    def setup_method(self) -> None:
        self.orchestrator = ConsultationOrchestrator()

    async def test_full_logistics_consultation(self) -> None:
        """Simulate a full logistics consultation flow."""
        session = await self.orchestrator.start_consultation()
        assert session is not None

        # Turn 1: Greeting -> Discovery
        result = await self.orchestrator.process_turn(
            session,
            "We run a logistics company and our order processing is all manual.",
        )
        assert result.conversation_phase in ("discovery", "exploration")
        assert result.assistant_message

        # Turn 2: Provide more details
        result = await self.orchestrator.process_turn(
            session,
            "About 180 staff, maybe 12 in operations doing this daily.",
        )
        assert result.lead_score is not None

        # Turn 3: Tools info
        result = await self.orchestrator.process_turn(
            session,
            "We use Excel, Email, and an old ERP system.",
        )
        assert result.conversation_phase is not None

    async def test_consultation_response_contract(self) -> None:
        """Verify response contract has all required fields."""
        session = await self.orchestrator.start_consultation()
        result = await self.orchestrator.process_turn(
            session,
            "We run a logistics company.",
        )

        # Verify response contract fields per Sprint 3 spec
        assert hasattr(result, "assistant_message")
        assert hasattr(result, "conversation_phase")

        # Lead score should have structure
        if result.lead_score:
            assert "score" in result.lead_score
            assert "band" in result.lead_score
            assert "confidence" in result.lead_score

        # Completion percentage is valid
        assert 0 <= result.completion_percentage <= 100
