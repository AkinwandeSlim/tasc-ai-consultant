"""Tests for Sprint 2A — AI Domain Foundation.

Tests cover model serialization, validation, configuration,
prompt loading, simulation configuration, and conversation
state definitions. No business logic tests — those belong
to Sprint 2B and beyond.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from app.domain.models.conversation import (
    ConversationContext,
    ConversationEvent,
    ConversationHistory,
    ConversationMetadata,
    ConversationProgress,
    ConversationStage,
    ConversationState,
    SessionStatus,
)
from app.domain.business.models import (
    AIReadiness,
    AIReadinessFactors,
    BudgetBand,
    BusinessConstraints,
    BusinessProfile,
    BusinessSize,
    DecisionAuthority,
    DigitalMaturity,
    GrowthStage,
    Industry,
    PainPoint,
    PainSpecificity,
    SlotValue,
    TechnicalCapability,
    Timeline,
    Urgency,
)
from app.domain.models.score import (
    LeadQualification,
    LeadScore,
    QualificationConfidence,
    QualificationDimension,
    QualificationReason,
    ScoreComponent,
    ScoringBreakdown,
)
from app.domain.models.recommendation import (
    Confidence,
    Priority,
    Recommendation,
    RecommendationCategory,
    RecommendationReason,
    RecommendationSummary,
    RecommendedService,
)
from app.domain.conversation.phase_controller import (
    PHASE_DEFINITIONS,
    TRANSITION_RULES,
    ConversationPhase,
    PhaseController,
)
from app.domain.simulation.framework import (
    DefaultScenarioProvider,
    Scenario,
    ScenarioRegistry,
    ScenarioResult,
    SimulationConfig,
    SimulationFramework,
)
from app.infrastructure.prompts.registry import (
    FilePromptLoader,
    PromptCategory,
    PromptMetadata,
    PromptRegistry,
    PromptTemplate,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    CandidateGenerationError,
    ChunkingError,
    ConversationError,
    IndexError,
    KnowledgeError,
    ManifestError,
    PhaseTransitionError,
    PromptError,
    QualificationError,
    RecommendationError,
    ScenarioNotFoundError,
    ScoringError,
    SimulationError,
    TASCError,
)


# =============================================================================
# Conversation Domain Model Tests
# =============================================================================


class TestConversationStage:
    """ConversationStage enum tests."""

    def test_stages_in_order(self) -> None:
        stages = list(ConversationStage)
        assert len(stages) == 6
        assert stages[0] == ConversationStage.GREETING
        assert stages[-1] == ConversationStage.CAPTURE_AND_CLOSE

    def test_stage_values(self) -> None:
        assert ConversationStage.GREETING.value == "greeting"
        assert ConversationStage.DISCOVERY.value == "discovery"
        assert ConversationStage.EXPLORATION.value == "exploration"
        assert ConversationStage.RECOMMENDATION.value == "recommendation"
        assert ConversationStage.QUALIFICATION.value == "qualification"
        assert ConversationStage.CAPTURE_AND_CLOSE.value == "capture_and_close"


class TestConversationState:
    """ConversationState model tests."""

    def test_default_creation(self) -> None:
        state = ConversationState()
        assert state.phase == "greeting"
        assert state.turn_index == 0
        assert state.slots_filled == 0
        assert state.slots_total == 9

    def test_slots_percent_zero(self) -> None:
        state = ConversationState(slots_total=0)
        assert state.slots_percent == 0.0

    def test_slots_percent_partial(self) -> None:
        state = ConversationState(slots_filled=5, slots_total=9)
        assert state.slots_percent == pytest.approx(55.555, rel=0.01)


class TestConversationHistory:
    """ConversationHistory model tests."""

    def test_default_history(self) -> None:
        history = ConversationHistory()
        assert history.messages == []
        assert history.compacted_summary is None
        assert history.needs_compaction is False

    def test_add_message(self) -> None:
        history = ConversationHistory()
        history.add_message({"role": "visitor", "content": "hello"})
        assert len(history.messages) == 1
        assert history.estimated_tokens > 0

    def test_recent_turns(self) -> None:
        history = ConversationHistory(verbatim_window_size=2)
        for i in range(5):
            history.add_message({"role": "visitor", "content": f"msg {i}"})
        assert len(history.recent_turns) == 2
        assert history.recent_turns[-1]["content"] == "msg 4"

    def test_older_turns(self) -> None:
        history = ConversationHistory(verbatim_window_size=2)
        for i in range(5):
            history.add_message({"role": "visitor", "content": f"msg {i}"})
        assert len(history.older_turns) == 3

    def test_no_older_turns_when_under_window(self) -> None:
        history = ConversationHistory(verbatim_window_size=8)
        for i in range(3):
            history.add_message({"role": "visitor", "content": f"msg {i}"})
        assert history.older_turns == []


class TestConversationProgress:
    """ConversationProgress model tests."""

    def test_default_progress(self) -> None:
        progress = ConversationProgress()
        assert progress.phase == "greeting"
        assert progress.percent == 0
        assert progress.display_stage == "Understanding"

    def test_full_progress(self) -> None:
        progress = ConversationProgress(
            phase="capture_and_close",
            stage_index=5,
            stage_total=5,
            slots_filled=9,
            slots_total=9,
        )
        assert progress.percent == 100

    def test_display_stage_mapping(self) -> None:
        assert ConversationProgress(phase="exploration").display_stage == "Exploring"
        assert ConversationProgress(phase="recommendation").display_stage == "Recommending"
        assert ConversationProgress(phase="qualification").display_stage == "Qualifying"


# =============================================================================
# Business Domain Model Tests
# =============================================================================


class TestBusinessEnums:
    """Controlled vocabulary enum tests."""

    def test_industry_values(self) -> None:
        assert Industry.LOGISTICS.value == "logistics"
        assert Industry.OTHER.value == "other"
        assert len(list(Industry)) == 9

    def test_business_size_values(self) -> None:
        assert BusinessSize.SIZE_51_200.value == "51-200"
        assert BusinessSize.SIZE_1000_PLUS.value == "1000+"

    def test_timeline_values(self) -> None:
        assert Timeline.IMMEDIATE.value == "immediate"
        assert Timeline.MONTHS_3_6.value == "3-6_months"

    def test_budget_bands(self) -> None:
        assert BudgetBand.RANGE_15K_50K.value == "15k-50k"
        assert BudgetBand.UNDISCLOSED.value == "undisclosed"

    def test_decision_authority(self) -> None:
        assert DecisionAuthority.DECISION_MAKER.value == "decision_maker"

    def test_ai_readiness(self) -> None:
        assert AIReadiness.HIGH.value == "high"
        assert AIReadiness.UNKNOWN.value == "unknown"


class TestSlotValue:
    """SlotValue model tests."""

    def test_default_creation(self) -> None:
        slot = SlotValue()
        assert slot.value is None
        assert slot.confidence == 0.0
        assert slot.declined is False

    def test_populated_value(self) -> None:
        slot = SlotValue(
            value="logistics",
            normalised="logistics",
            raw="we run a logistics company",
            confidence=0.94,
            source_turn=1,
        )
        assert slot.value == "logistics"
        assert slot.confidence == 0.94

    def test_declined_value(self) -> None:
        slot = SlotValue(declined=True)
        assert slot.declined is True


class TestPainPoint:
    """PainPoint model tests."""

    def test_default_pain_point(self) -> None:
        pp = PainPoint(id="pp_01", label="Manual processing")
        assert pp.specificity == PainSpecificity.VAGUE.value
        assert pp.confidence == 0.0

    def test_quantified_pain(self) -> None:
        pp = PainPoint(
            id="pp_01",
            label="Invoice matching takes 2 people 3 days a week",
            specificity=PainSpecificity.QUANTIFIED.value,
            severity="high",
            service_codes=["SVC-AIA"],
            confidence=0.85,
        )
        assert pp.specificity == "quantified"
        assert pp.severity == "high"


class TestBusinessProfile:
    """BusinessProfile model tests."""

    def test_default_profile(self) -> None:
        profile = BusinessProfile()
        assert profile.core_slots_filled == 0
        assert profile.commercial_slots_filled == 0
        assert profile.has_contact is False

    def test_partial_profile(self) -> None:
        profile = BusinessProfile(
            industry=SlotValue(value="logistics", confidence=0.94),
            pain_points=[
                PainPoint(id="pp_01", label="Manual processing", confidence=0.8)
            ],
        )
        assert profile.core_slots_filled == 2  # industry + pain_points

    def test_contact_captured(self) -> None:
        profile = BusinessProfile(
            contact_email=SlotValue(value="test@example.com"),
            consent_granted=True,
        )
        assert profile.has_contact is True

    def test_contact_without_consent(self) -> None:
        profile = BusinessProfile(
            contact_email=SlotValue(value="test@example.com"),
            consent_granted=False,
        )
        assert profile.has_contact is False

    def test_high_confidence_pain_points(self) -> None:
        profile = BusinessProfile(
            pain_points=[
                PainPoint(id="pp_01", label="Vague problem", confidence=0.3),
                PainPoint(id="pp_02", label="Specific issue", confidence=0.7),
            ]
        )
        assert len(profile.manageable_pain_points) == 1
        assert profile.manageable_pain_points[0].id == "pp_02"


class TestAIReadinessFactors:
    """AIReadinessFactors model tests."""

    def test_unknown_when_no_factors(self) -> None:
        factors = AIReadinessFactors()
        assert factors.overall == AIReadiness.UNKNOWN.value

    def test_high_readiness(self) -> None:
        factors = AIReadinessFactors(
            process_repeatability="high",
            data_availability="yes",
            data_quality="good",
            process_ownership="yes",
            change_readiness="high",
        )
        assert factors.overall == AIReadiness.HIGH.value

    def test_medium_readiness(self) -> None:
        factors = AIReadinessFactors(
            process_repeatability="high",
            data_availability="yes",
            exception_rate="high",
        )
        assert factors.overall == AIReadiness.MEDIUM.value


class TestBusinessConstraints:
    """BusinessConstraints model tests."""

    def test_default_constraints(self) -> None:
        constraints = BusinessConstraints()
        assert constraints.budget_range is None
        assert constraints.compliance_requirements == []

    def test_with_constraints(self) -> None:
        constraints = BusinessConstraints(
            budget_range="15k-50k",
            timeline_window="3-6_months",
            compliance_requirements=["GDPR", "SOC2"],
        )
        assert constraints.budget_range == "15k-50k"
        assert len(constraints.compliance_requirements) == 2


# =============================================================================
# Lead Qualification Domain Model Tests
# =============================================================================


class TestScoreComponent:
    """ScoreComponent model tests."""

    def test_default_creation(self) -> None:
        sc = ScoreComponent(name="need_clarity")
        assert sc.awarded == 0
        assert sc.max == 0
        assert sc.remaining == 0
        assert sc.fraction == 0.0

    def test_partial_score(self) -> None:
        sc = ScoreComponent(name="need_clarity", awarded=15, max=25)
        assert sc.remaining == 10
        assert sc.fraction == 0.6


class TestScoringBreakdown:
    """ScoringBreakdown model tests."""

    def test_default(self) -> None:
        breakdown = ScoringBreakdown()
        assert breakdown.total == 0
        assert breakdown.components == []
        assert breakdown.max_possible == 100

    def test_with_components(self) -> None:
        breakdown = ScoringBreakdown(
            total=74,
            components=[
                ScoreComponent(name="need_clarity", awarded=21, max=25),
                ScoreComponent(name="fit", awarded=20, max=20),
            ],
        )
        assert breakdown.total == 74
        assert breakdown.max_possible == 45


class TestLeadScore:
    """LeadScore model tests."""

    def test_default(self) -> None:
        score = LeadScore()
        assert score.score == 0
        assert score.band == "exploring"
        assert score.disqualified is False

    def test_populated(self) -> None:
        score = LeadScore(
            score=74,
            band="qualified",
            confidence=0.79,
            components=[ScoreComponent(name="urgency", awarded=9, max=15)],
        )
        assert score.score == 74
        assert score.band == "qualified"


class TestQualificationConfidence:
    """QualificationConfidence model tests."""

    def test_strong_evidence(self) -> None:
        qc = QualificationConfidence(overall=0.85, coverage=0.8)
        assert qc.evidence_quality == "strong"

    def test_thin_evidence(self) -> None:
        qc = QualificationConfidence(overall=0.30, coverage=0.2)
        assert qc.evidence_quality == "thin"


# =============================================================================
# Recommendation Domain Model Tests
# =============================================================================


class TestRecommendedService:
    """RecommendedService model tests."""

    def test_default(self) -> None:
        rs = RecommendedService()
        assert rs.rank == 1
        assert rs.display_confidence == Confidence.LOW.value

    def test_high_confidence(self) -> None:
        rs = RecommendedService(
            service_code="SVC-AIA",
            name="AI Automation",
            rank=1,
            confidence=0.87,
        )
        assert rs.display_confidence == Confidence.HIGH.value
        assert rs.is_primary is True

    def test_medium_confidence(self) -> None:
        rs = RecommendedService(
            service_code="SVC-WEB",
            name="Web Development",
            confidence=0.75,
        )
        assert rs.display_confidence == Confidence.MEDIUM.value


class TestRecommendation:
    """Recommendation model tests."""

    def test_default(self) -> None:
        rec = Recommendation()
        assert rec.display_confidence == Confidence.LOW.value

    def test_with_reasons(self) -> None:
        rec = Recommendation(
            service_code="SVC-AIA",
            name="AI Automation",
            rank=1,
            confidence=0.87,
            reasons=[
                RecommendationReason(
                    pain_point_id="pp_01",
                    pain_point_label="Manual processing",
                    relevance="Directly addresses the manual workload",
                )
            ],
        )
        assert len(rec.reasons) == 1
        assert rec.reasons[0].pain_point_id == "pp_01"


class TestRecommendationSummary:
    """RecommendationSummary model tests."""

    def test_empty(self) -> None:
        summary = RecommendationSummary()
        assert summary.withheld is False
        assert summary.primary is None
        assert summary.has_recommendations is False

    def test_withheld(self) -> None:
        summary = RecommendationSummary(withheld=True, withheld_reason="Insufficient evidence")
        assert summary.has_recommendations is False

    def test_with_recommendations(self) -> None:
        summary = RecommendationSummary(
            items=[
                Recommendation(service_code="SVC-AIA", name="AI Automation", rank=1),
                Recommendation(service_code="SVC-INT", name="Integration", rank=2),
            ]
        )
        assert summary.has_recommendations is True
        assert summary.primary is not None
        assert summary.primary.service_code == "SVC-AIA"


# =============================================================================
# Conversation State Definition Tests (Phase Controller)
# =============================================================================


class TestPhaseDefinitions:
    """Phase definition tests."""

    def test_all_phases_defined(self) -> None:
        """Every conversation phase must have a definition."""
        for phase in ConversationPhase:
            if phase.value != "completing" and phase.value != "completed":
                assert (
                    phase.value in PHASE_DEFINITIONS
                ), f"Missing definition for {phase.value}"

    def test_phase_multipliers(self) -> None:
        """Commercial slots should have 0 multiplier in early phases."""
        discovery = PHASE_DEFINITIONS[ConversationPhase.DISCOVERY.value]
        qualification = PHASE_DEFINITIONS[ConversationPhase.QUALIFICATION.value]

        # Discovery should not ask commercial questions
        assert "timeline" not in discovery.eligible_slots
        assert "budget_band" not in discovery.eligible_slots
        assert "decision_role" not in discovery.eligible_slots

        # Qualification should have commercial slots
        assert "timeline" in qualification.eligible_slots
        assert "budget_band" in qualification.eligible_slots
        assert "decision_role" in qualification.eligible_slots


class TestTransitionRules:
    """Transition rule tests."""

    def test_transition_count(self) -> None:
        assert len(TRANSITION_RULES) > 0

    def test_greeting_transitions(self) -> None:
        greeting_rules = PhaseController.get_transitions("greeting")
        assert len(greeting_rules) >= 1
        assert any(r.to_phase == "discovery" for r in greeting_rules)

    def test_anti_persona_transitions(self) -> None:
        discovery_rules = PhaseController.get_transitions("discovery")
        assert any(r.to_phase == "terminated" for r in discovery_rules)


class TestPhaseControllerEvaluate:
    """PhaseController.evaluate tests."""

    def test_greeting_to_discovery(self) -> None:
        next_phase, trigger = PhaseController.evaluate(current_phase="greeting")
        assert next_phase == "discovery"
        assert trigger == "first_visitor_message"

    def test_discovery_insufficient_slots(self) -> None:
        next_phase, trigger = PhaseController.evaluate(
            current_phase="discovery",
            core_slots_filled=1,
        )
        assert next_phase == "discovery"
        assert trigger is None

    def test_discovery_sufficient_slots(self) -> None:
        next_phase, trigger = PhaseController.evaluate(
            current_phase="discovery",
            core_slots_filled=3,
            confidence_met=True,
        )
        assert next_phase == "exploration"
        assert trigger == "core_slots_sufficient"

    def test_exploration_to_recommendation(self) -> None:
        next_phase, trigger = PhaseController.evaluate(
            current_phase="exploration",
            recommendation_ready=True,
        )
        assert next_phase == "recommendation"
        assert trigger == "evidence_sufficient"

    def test_recommendation_acknowledged(self) -> None:
        next_phase, trigger = PhaseController.evaluate(
            current_phase="recommendation",
            recommendation_acknowledged=True,
        )
        assert next_phase == "qualification"

    def test_recommendation_rejected(self) -> None:
        next_phase, trigger = PhaseController.evaluate(
            current_phase="recommendation",
            visitor_rejected_fit=True,
        )
        assert next_phase == "exploration"

    def test_qualification_to_capture(self) -> None:
        next_phase, trigger = PhaseController.evaluate(
            current_phase="qualification",
            commercial_slots_resolved=True,
        )
        assert next_phase == "capture_and_close"

    def test_human_request_shortcut(self) -> None:
        next_phase, trigger = PhaseController.evaluate(
            current_phase="discovery",
            visitor_requested_human=True,
        )
        assert next_phase == "capture_and_close"
        assert trigger == "human_requested"

    def test_anti_persona_override(self) -> None:
        next_phase, trigger = PhaseController.evaluate(
            current_phase="discovery",
            anti_persona=True,
        )
        assert next_phase == "terminated"

    def test_discovery_refused(self) -> None:
        next_phase, trigger = PhaseController.evaluate(
            current_phase="discovery",
            discovery_refused_count=2,
        )
        assert next_phase == "information_only"

    def test_wrap_up(self) -> None:
        next_phase, trigger = PhaseController.evaluate(
            current_phase="exploration",
            wrap_up_flag=True,
        )
        assert next_phase == "capture_and_close"

    def test_valid_phases_in_order(self) -> None:
        phases = PhaseController.get_valid_phases()
        assert len(phases) >= 6
        assert phases[0] == "greeting"

    def test_get_stage_index(self) -> None:
        assert PhaseController.get_stage_index("greeting") == 0
        assert PhaseController.get_stage_index("capture_and_close") == 5
        assert PhaseController.get_stage_index("unknown") == 0


class TestCanTransition:
    """PhaseController.can_transition tests."""

    def test_valid_transitions(self) -> None:
        assert PhaseController.can_transition("greeting", "discovery") is True
        assert PhaseController.can_transition("discovery", "exploration") is True

    def test_invalid_transitions(self) -> None:
        assert PhaseController.can_transition("greeting", "completed") is False
        assert PhaseController.can_transition("greeting", "recommendation") is False

    def test_self_transitions(self) -> None:
        assert PhaseController.can_transition("discovery", "discovery") is False


# =============================================================================
# Prompt Registry Tests
# =============================================================================


class TestPromptMetadata:
    """PromptMetadata tests."""

    def test_default_metadata(self) -> None:
        meta = PromptMetadata(template_id="test", path="test.md")
        assert meta.template_id == "test"
        assert meta.version == "1.0.0"
        assert meta.category == PromptCategory.TASK.value

    def test_full_path(self) -> None:
        meta = PromptMetadata(template_id="identity", path="identity/nova.v1.md")
        assert "app/resources/prompts/" in meta.full_path


class TestPromptRegistry:
    """PromptRegistry tests — uses real manifest."""

    def test_registry_creation(self) -> None:
        registry = PromptRegistry()
        assert registry.manifest_version == ""
        assert registry._loaded is False

    def test_load_all_templates(self) -> None:
        """This test requires the manifest and template files to exist."""
        registry = PromptRegistry()
        templates = registry.load_all()
        assert len(templates) >= 1
        assert "identity" in templates

    def test_get_single_template(self) -> None:
        registry = PromptRegistry()
        template = registry.get("identity")
        assert template.template_id == "identity"
        assert len(template.content) > 0

    def test_get_unknown_template(self) -> None:
        registry = PromptRegistry()
        with pytest.raises(KeyError):
            registry.get("non_existent_template")

    def test_validate_all_valid(self) -> None:
        registry = PromptRegistry()
        errors = registry.validate_all()
        assert errors == []

    def test_get_by_category(self) -> None:
        registry = PromptRegistry()
        identity_templates = registry.get_identity_layer()
        assert len(identity_templates) >= 1
        assert identity_templates[0].metadata.category == PromptCategory.IDENTITY.value


class TestFilePromptLoader:
    """FilePromptLoader tests."""

    def test_loader_creation(self) -> None:
        loader = FilePromptLoader()
        assert loader.base_path is not None

    def test_identity_template_exists(self) -> None:
        loader = FilePromptLoader()
        assert loader.exists("identity/nova.v1.md") is True

    def test_unknown_template(self) -> None:
        loader = FilePromptLoader()
        assert loader.exists("does_not_exist.md") is False

    def test_load_identity_template(self) -> None:
        loader = FilePromptLoader()
        content = loader.load("identity/nova.v1.md")
        assert len(content) > 0
        assert "Nova" in content or "Trizen" in content


# =============================================================================
# Simulation Framework Tests
# =============================================================================


class TestSimulationConfig:
    """SimulationConfig tests."""

    def test_default_config(self) -> None:
        config = SimulationConfig()
        assert config.enabled is False
        assert config.deterministic_response is True
        assert config.error_rate == 0.0


class TestScenario:
    """Scenario model tests."""

    def test_default_scenario(self) -> None:
        scenario = Scenario(scenario_id="test", name="Test Scenario")
        assert scenario.turn_count == 5
        assert scenario.initial_phase == "greeting"
        assert scenario.responses == []

    def test_with_responses(self) -> None:
        scenario = Scenario(
            scenario_id="demo",
            name="Demo Scenario",
            turn_count=3,
            responses=["Hello", "Tell me more", "Goodbye"],
        )
        assert len(scenario.responses) == 3


class TestScenarioResult:
    """ScenarioResult tests."""

    def test_default_result(self) -> None:
        result = ScenarioResult(scenario_id="test", turn_index=0)
        assert result.phase == "discovery"
        assert result.finish_reason == "complete"
        assert result.completed is False

    def test_completed_result(self) -> None:
        result = ScenarioResult(
            scenario_id="test",
            turn_index=5,
            completed=True,
        )
        assert result.completed is True


class TestScenarioRegistry:
    """ScenarioRegistry tests."""

    def test_empty_registry(self) -> None:
        registry = ScenarioRegistry()
        assert registry.is_empty
        assert registry.count == 0

    def test_register_scenario(self) -> None:
        registry = ScenarioRegistry()
        scenario = Scenario(scenario_id="test", name="Test")
        registry.register(scenario)
        assert registry.count == 1
        assert registry.is_empty is False

    def test_get_scenario(self) -> None:
        registry = ScenarioRegistry()
        scenario = Scenario(scenario_id="test", name="Test")
        registry.register(scenario)
        assert registry.get("test") is not None
        assert registry.get("unknown") is None

    def test_duplicate_registration(self) -> None:
        registry = ScenarioRegistry()
        scenario = Scenario(scenario_id="test", name="Test")
        registry.register(scenario)
        with pytest.raises(ValueError):
            registry.register(scenario)

    def test_get_or_raise(self) -> None:
        registry = ScenarioRegistry()
        scenario = Scenario(scenario_id="test", name="Test")
        registry.register(scenario)
        assert registry.get_or_raise("test").scenario_id == "test"
        with pytest.raises(KeyError):
            registry.get_or_raise("unknown")

    def test_list_by_tag(self) -> None:
        registry = ScenarioRegistry()
        registry.register(Scenario(scenario_id="a", name="A", tags=["fast"]))
        registry.register(Scenario(scenario_id="b", name="B", tags=["slow"]))
        registry.register(Scenario(scenario_id="c", name="C", tags=["fast"]))
        assert len(registry.list_scenarios(tag="fast")) == 2

    def test_clear(self) -> None:
        registry = ScenarioRegistry()
        registry.register(Scenario(scenario_id="test", name="Test"))
        registry.clear()
        assert registry.is_empty

    def test_remove(self) -> None:
        registry = ScenarioRegistry()
        registry.register(Scenario(scenario_id="test", name="Test"))
        registry.remove("test")
        assert registry.is_empty


class TestSimulationFramework:
    """SimulationFramework tests."""

    def test_default_framework(self) -> None:
        framework = SimulationFramework()
        assert framework.is_active() is False

    def test_enabled_framework(self) -> None:
        config = SimulationConfig(enabled=True)
        framework = SimulationFramework(config=config)
        assert framework.is_active() is True

    def test_run_turn_disabled(self) -> None:
        framework = SimulationFramework()
        scenario = Scenario(scenario_id="test", name="Test")
        result = framework.run_turn(scenario, turn=0)
        assert result is None

    def test_run_turn_enabled(self) -> None:
        config = SimulationConfig(enabled=True)
        registry = ScenarioRegistry()
        scenario = Scenario(
            scenario_id="test",
            name="Test",
            turn_count=3,
            responses=["First", "Second", "Third"],
        )
        registry.register(scenario)
        framework = SimulationFramework(config=config, registry=registry)
        result = framework.run_turn(scenario, turn=1)
        assert result is not None
        assert result.turn_index == 1
        assert result.response_text == "Second"

    def test_run_by_string_id(self) -> None:
        config = SimulationConfig(enabled=True)
        registry = ScenarioRegistry()
        scenario = Scenario(scenario_id="demo", name="Demo")
        registry.register(scenario)
        framework = SimulationFramework(config=config, registry=registry)
        result = framework.run_turn("demo", turn=0)
        assert result is not None
        assert result.scenario_id == "demo"

    def test_run_unknown_id(self) -> None:
        framework = SimulationFramework(config=SimulationConfig(enabled=True))
        result = framework.run_turn("unknown", turn=0)
        assert result is None

    def test_run_full_scenario(self) -> None:
        config = SimulationConfig(enabled=True)
        registry = ScenarioRegistry()
        scenario = Scenario(
            scenario_id="test",
            name="Test",
            turn_count=2,
            responses=["First", "Second"],
        )
        registry.register(scenario)
        framework = SimulationFramework(config=config, registry=registry)
        results = framework.run_full_scenario(scenario)
        assert len(results) == 2
        assert results[0].response_text == "First"
        assert results[1].response_text == "Second"


class TestDefaultScenarioProvider:
    """DefaultScenarioProvider tests."""

    def test_with_responses(self) -> None:
        provider = DefaultScenarioProvider()
        scenario = Scenario(
            scenario_id="test",
            name="Test",
            responses=["Hello", "World"],
        )
        result = provider.generate_response(scenario, turn=0)
        assert result.response_text == "Hello"
        assert result.finish_reason == "complete"

    def test_fallback_response(self) -> None:
        provider = DefaultScenarioProvider()
        scenario = Scenario(scenario_id="test", name="Test")
        result = provider.generate_response(scenario, turn=0)
        assert "[Simulated response" in result.response_text


# =============================================================================
# Configuration Tests
# =============================================================================


class TestSettings:
    """Settings model tests."""

    def test_default_settings(self) -> None:
        settings = Settings()
        assert settings.APP_ENV.value == "local"
        assert settings.SIMULATION_MODE is False
        assert settings.SIMULATION_SCENARIO_ID == ""

    def test_simulation_settings(self) -> None:
        settings = Settings(
            SIMULATION_MODE=True,
            SIMULATION_SCENARIO_ID="demo",
            SIMULATION_DETERMINISTIC=True,
        )
        assert settings.SIMULATION_MODE is True

    def test_ai_settings(self) -> None:
        settings = Settings()
        assert "manifest" in settings.AI_PROMPT_MANIFEST_PATH
        assert settings.AI_DEFAULT_TEMPERATURE == 0.3


class TestGetSettings:
    """get_settings singleton tests."""

    def test_get_settings_singleton(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


# =============================================================================
# Custom Exception Tests
# =============================================================================


class TestDomainExceptions:
    """Domain exception hierarchy tests."""

    def test_conversation_error(self) -> None:
        err = ConversationError("Test conversation error")
        assert err.code == "CONVERSATION_ERROR"
        assert err.http_status == 500

    def test_phase_transition_error(self) -> None:
        err = PhaseTransitionError("Invalid transition")
        assert err.code == "INVALID_PHASE_TRANSITION"
        assert err.http_status == 409

    def test_scoring_error(self) -> None:
        err = ScoringError("Score computation failed")
        assert err.code == "SCORING_ERROR"
        assert err.http_status == 500

    def test_recommendation_error(self) -> None:
        err = RecommendationError()
        assert err.code == "RECOMMENDATION_ERROR"

    def test_candidate_generation_error(self) -> None:
        err = CandidateGenerationError("No candidates")
        assert err.code == "CANDIDATE_ERROR"

    def test_prompt_error(self) -> None:
        err = PromptError("Prompt error")
        assert err.code == "PROMPT_ERROR"
        assert err.http_status == 500

    def test_manifest_error(self) -> None:
        err = ManifestError("Invalid manifest")
        assert err.code == "MANIFEST_ERROR"

    def test_knowledge_error(self) -> None:
        err = KnowledgeError("Knowledge error")
        assert err.code == "KNOWLEDGE_ERROR"

    def test_chunking_error(self) -> None:
        err = ChunkingError("Chunking failed")
        assert err.code == "CHUNKING_ERROR"

    def test_index_error(self) -> None:
        err = IndexError("Index unavailable")
        assert err.code == "INDEX_ERROR"
        assert err.http_status == 503

    def test_simulation_error(self) -> None:
        err = SimulationError("Simulation error")
        assert err.code == "SIMULATION_ERROR"

    def test_scenario_not_found(self) -> None:
        err = ScenarioNotFoundError()
        assert err.code == "SCENARIO_NOT_FOUND"
        assert err.http_status == 404

    def test_exception_with_details(self) -> None:
        err = PhaseTransitionError(
            "Custom message",
            code="CUSTOM_CODE",
            details={"from": "a", "to": "b"},
        )
        assert err.message == "Custom message"
        assert err.code == "CUSTOM_CODE"
        assert err.details == {"from": "a", "to": "b"}

    def test_exception_hierarchy(self) -> None:
        assert issubclass(ScoringError, QualificationError)
        assert issubclass(QualificationError, TASCError)
        assert issubclass(PromptError, TASCError)
