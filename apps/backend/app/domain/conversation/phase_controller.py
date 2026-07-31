"""Phase controller — consultation state machine.

Implements the PRD-defined conversation phases and transition rules
(PRD Sections 12.1, 12.2) plus the AI Blueprint state machine
(Sections 3.1, 3.2). Pure deterministic logic: given current state
and slot fill, returns the next phase.

References: PRD 12.1, 12.2; AI Blueprint 3.1, 3.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConversationPhase(str, Enum):
    """Runtime consultation phases from PRD Section 12.1.

    These six phases are the actual state machine. The AI Blueprint's
    ten-stage framework is a conceptual decomposition mapped onto these.
    """

    GREETING = "greeting"
    DISCOVERY = "discovery"
    EXPLORATION = "exploration"
    RECOMMENDATION = "recommendation"
    QUALIFICATION = "qualification"
    CAPTURE_AND_CLOSE = "capture_and_close"
    COMPLETING = "completing"
    COMPLETED = "completed"


@dataclass
class PhaseDefinition:
    """Definition of a single conversation phase.

    Captures the entry condition, Nova's objective, exit condition,
    typical turn count, and eligible slots for question selection.
    """

    phase: str
    label: str
    stage_index: int
    objective: str
    entry_condition: str
    exit_condition: str
    typical_turns: str = ""
    eligible_slots: list[str] = field(default_factory=list)
    phase_multiplier: float = 0.0


@dataclass
class TransitionRule:
    """A single state transition rule.

    Defines a valid transition from one phase to another given
    a trigger condition and optional side effects.
    """

    from_phase: str
    to_phase: str
    trigger: str
    description: str
    side_effects: list[str] = field(default_factory=list)


@dataclass
class TransitionMetadata:
    """Metadata about a specific transition occurrence.

    Records what triggered the transition and what state changed.
    """

    from_phase: str
    to_phase: str
    trigger: str
    turn_index: int
    reason: str = ""


# --- Phase Definitions (PRD 12.1) ---

PHASE_DEFINITIONS: dict[str, PhaseDefinition] = {
    ConversationPhase.GREETING.value: PhaseDefinition(
        phase=ConversationPhase.GREETING.value,
        label="Greeting",
        stage_index=0,
        objective="Introduce Nova, set expectations, ask one opening question",
        entry_condition="Session created",
        exit_condition="First visitor message received",
        typical_turns="0 (static)",
        eligible_slots=[],
        phase_multiplier=0.0,
    ),
    ConversationPhase.DISCOVERY.value: PhaseDefinition(
        phase=ConversationPhase.DISCOVERY.value,
        label="Discovery",
        stage_index=1,
        objective="Fill industry, business size, pain points, current tools, goals",
        entry_condition="First visitor message",
        exit_condition="3 or more core slots filled at confidence >= 0.6",
        typical_turns="2 to 5",
        eligible_slots=["industry", "business_size", "pain_points", "current_tools"],
        phase_multiplier=1.0,
    ),
    ConversationPhase.EXPLORATION.value: PhaseDefinition(
        phase=ConversationPhase.EXPLORATION.value,
        label="Exploration",
        stage_index=2,
        objective="Deepen understanding, answer knowledge questions with grounding",
        entry_condition="P1 exit satisfied, or visitor asks a company question",
        exit_condition="Enough evidence for recommendation (2+ pain points, industry known)",
        typical_turns="2 to 4",
        eligible_slots=["pain_points", "goals", "current_tools"],
        phase_multiplier=0.8,
    ),
    ConversationPhase.RECOMMENDATION.value: PhaseDefinition(
        phase=ConversationPhase.RECOMMENDATION.value,
        label="Recommendation",
        stage_index=3,
        objective="Present 1-3 services with rationale, check resonance",
        entry_condition="Recommendation engine reaches confidence >= 0.6",
        exit_condition="Visitor responds to the recommendation",
        typical_turns="1 to 2",
        eligible_slots=["goals"],
        phase_multiplier=0.0,
    ),
    ConversationPhase.QUALIFICATION.value: PhaseDefinition(
        phase=ConversationPhase.QUALIFICATION.value,
        label="Qualification",
        stage_index=4,
        objective="Establish timeline, budget band, decision role",
        entry_condition="Recommendation acknowledged",
        exit_condition="Commercial slots filled or explicitly declined",
        typical_turns="1 to 3",
        eligible_slots=["timeline", "budget_band", "decision_role"],
        phase_multiplier=1.0,
    ),
    ConversationPhase.CAPTURE_AND_CLOSE.value: PhaseDefinition(
        phase=ConversationPhase.CAPTURE_AND_CLOSE.value,
        label="Capture and Close",
        stage_index=5,
        objective="Obtain consent and contact, deliver the executive summary",
        entry_condition="Qualification complete or visitor signals ending",
        exit_condition="Payload assembled and dispatched",
        typical_turns="1 to 2",
        eligible_slots=["contact"],
        phase_multiplier=0.0,
    ),
}

# --- Transition Rules (PRD 12.2 / AI Blueprint 3.2) ---

TRANSITION_RULES: list[TransitionRule] = [
    # Normal flow
    TransitionRule(
        from_phase=ConversationPhase.GREETING.value,
        to_phase=ConversationPhase.DISCOVERY.value,
        trigger="first_visitor_message",
        description="First visitor message received, start discovery",
        side_effects=["start_turn_1", "compute_initial_score"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.DISCOVERY.value,
        to_phase=ConversationPhase.EXPLORATION.value,
        trigger="core_slots_sufficient",
        description="3+ core slots filled at confidence >= 0.6",
        side_effects=["recompute_score", "update_progress"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.EXPLORATION.value,
        to_phase=ConversationPhase.RECOMMENDATION.value,
        trigger="evidence_sufficient",
        description="Enough evidence for recommendation (2+ pain points, industry known)",
        side_effects=["build_candidates", "compute_confidence"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.RECOMMENDATION.value,
        to_phase=ConversationPhase.QUALIFICATION.value,
        trigger="recommendation_acknowledged",
        description="Visitor acknowledges the recommendation",
        side_effects=["ask_commercial_question"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.QUALIFICATION.value,
        to_phase=ConversationPhase.CAPTURE_AND_CLOSE.value,
        trigger="commercial_slots_resolved",
        description="Commercial slots filled or declined",
        side_effects=["request_consent", "request_contact"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.CAPTURE_AND_CLOSE.value,
        to_phase=ConversationPhase.COMPLETING.value,
        trigger="completion_trigger",
        description="Completion criteria met or explicit request",
        side_effects=["generate_summary", "assemble_payload"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.COMPLETING.value,
        to_phase=ConversationPhase.COMPLETED.value,
        trigger="payload_persisted",
        description="Payload validated and persisted",
        side_effects=["schedule_dispatch", "log_completion"],
    ),
    # Reversion paths
    TransitionRule(
        from_phase=ConversationPhase.EXPLORATION.value,
        to_phase=ConversationPhase.DISCOVERY.value,
        trigger="new_gap_detected",
        description="New discovery gap detected during exploration",
        side_effects=["select_question", "update_progress"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.RECOMMENDATION.value,
        to_phase=ConversationPhase.EXPLORATION.value,
        trigger="visitor_rejects_fit",
        description="Visitor rejects recommendation fit",
        side_effects=["ask_missing_context", "do_not_immediately_pitch"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.QUALIFICATION.value,
        to_phase=ConversationPhase.EXPLORATION.value,
        trigger="new_requirement_raised",
        description="Visitor raises new requirement during qualification",
        side_effects=["capture_new_requirement", "reassess_recommendations"],
    ),
    # Special paths
    TransitionRule(
        from_phase=ConversationPhase.DISCOVERY.value,
        to_phase=ConversationPhase.CAPTURE_AND_CLOSE.value,
        trigger="human_requested",
        description="Visitor asks for a human",
        side_effects=["min_band_qualified", "set_priority_flag"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.EXPLORATION.value,
        to_phase=ConversationPhase.CAPTURE_AND_CLOSE.value,
        trigger="human_requested",
        description="Visitor asks for a human",
        side_effects=["min_band_qualified", "set_priority_flag"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.QUALIFICATION.value,
        to_phase=ConversationPhase.CAPTURE_AND_CLOSE.value,
        trigger="human_requested",
        description="Visitor asks for a human",
        side_effects=["capture_contact", "set_priority_flag"],
    ),
    # Termination paths
    TransitionRule(
        from_phase=ConversationPhase.DISCOVERY.value,
        to_phase="terminated",
        trigger="anti_persona_detected",
        description="Anti-persona detected (job seeker, vendor, student, competitor)",
        side_effects=["suppress_automation", "log_session"],
    ),
    TransitionRule(
        from_phase=ConversationPhase.EXPLORATION.value,
        to_phase="terminated",
        trigger="anti_persona_detected",
        description="Anti-persona detected",
        side_effects=["suppress_automation", "log_session"],
    ),
    # Discovery refusal
    TransitionRule(
        from_phase=ConversationPhase.DISCOVERY.value,
        to_phase="information_only",
        trigger="discovery_refused_twice",
        description="Visitor refuses discovery questions twice",
        side_effects=["offer_contact_form", "mark_information_only"],
    ),
]


class PhaseController:
    """Deterministic phase transition logic.

    Evaluates transition conditions given the current state and returns
    the next phase. Pure function — no I/O, no model calls.

    Usage:
        controller = PhaseController()
        next_phase = controller.evaluate(current_phase, slots, context)
    """

    @staticmethod
    def get_definition(phase: str) -> PhaseDefinition:
        """Get the definition for a given phase.

        Args:
            phase: The phase string identifier.

        Returns:
            PhaseDefinition for the requested phase.

        Raises:
            ValueError: If the phase is unknown.
        """
        if phase not in PHASE_DEFINITIONS:
            raise ValueError(f"Unknown phase: '{phase}'")
        return PHASE_DEFINITIONS[phase]

    @staticmethod
    def get_transitions(from_phase: str) -> list[TransitionRule]:
        """Get all valid transitions from a given phase.

        Args:
            from_phase: The source phase.

        Returns:
            List of TransitionRule for valid transitions.
        """
        return [r for r in TRANSITION_RULES if r.from_phase == from_phase]

    @staticmethod
    def can_transition(from_phase: str, to_phase: str) -> bool:
        """Check whether a transition between phases is valid.

        Args:
            from_phase: The source phase.
            to_phase: The target phase.

        Returns:
            True if a valid transition rule exists.
        """
        return any(
            r.from_phase == from_phase and r.to_phase == to_phase
            for r in TRANSITION_RULES
        )

    @staticmethod
    def evaluate(
        current_phase: str,
        core_slots_filled: int = 0,
        confidence_met: bool = False,
        recommendation_ready: bool = False,
        recommendation_acknowledged: bool = False,
        commercial_slots_resolved: bool = False,
        completion_triggered: bool = False,
        visitor_requested_human: bool = False,
        visitor_rejected_fit: bool = False,
        anti_persona: bool = False,
        discovery_refused_count: int = 0,
        wrap_up_flag: bool = False,
        all_eligible_filled: bool = False,
    ) -> tuple[str, str | None]:
        """Evaluate the next phase transition.

        Pure function. Given current phase and state signals, returns
        the next phase and the trigger that caused the transition.

        Args:
            current_phase: The current conversation phase.
            core_slots_filled: Number of core discovery slots filled.
            confidence_met: Whether recommendation confidence threshold met.
            recommendation_ready: Whether evidence is sufficient.
            recommendation_acknowledged: Whether visitor acknowledged.
            commercial_slots_resolved: Whether commercial slots done.
            completion_triggered: Whether completion criteria met.
            visitor_requested_human: Whether visitor asked for human.
            visitor_rejected_fit: Whether visitor rejected recommendations.
            anti_persona: Whether anti-persona detected.
            discovery_refused_count: Number of discovery refusals.
            wrap_up_flag: Whether session token ceiling approached.
            all_eligible_filled: Whether all eligible slots for current
                phase have data. Forces progression when no questions remain.

        Returns:
            Tuple of (next_phase, trigger or None if no change).
        """
        # Termination overrides everything
        if anti_persona:
            return "terminated", "anti_persona_detected"

        # Human request shortcut
        if visitor_requested_human and current_phase in (
            ConversationPhase.DISCOVERY.value,
            ConversationPhase.EXPLORATION.value,
            ConversationPhase.QUALIFICATION.value,
        ):
            return ConversationPhase.CAPTURE_AND_CLOSE.value, "human_requested"

        # Information-only path
        if discovery_refused_count >= 2 and current_phase == ConversationPhase.DISCOVERY.value:
            return "information_only", "discovery_refused_twice"

        # Wrap-up
        if wrap_up_flag and current_phase not in (
            ConversationPhase.CAPTURE_AND_CLOSE.value,
            ConversationPhase.COMPLETING.value,
            ConversationPhase.COMPLETED.value,
        ):
            return ConversationPhase.CAPTURE_AND_CLOSE.value, "wrap_up"

        # Completion
        if completion_triggered and current_phase in (
            ConversationPhase.CAPTURE_AND_CLOSE.value,
            ConversationPhase.QUALIFICATION.value,
        ):
            return ConversationPhase.COMPLETING.value, "completion_trigger"

        # Phase-specific transitions
        if current_phase == ConversationPhase.GREETING.value:
            return ConversationPhase.DISCOVERY.value, "first_visitor_message"

        if current_phase == ConversationPhase.DISCOVERY.value:
            if core_slots_filled >= 3 and confidence_met:
                return ConversationPhase.EXPLORATION.value, "core_slots_sufficient"
            return ConversationPhase.DISCOVERY.value, None

        if current_phase == ConversationPhase.EXPLORATION.value:
            if recommendation_ready or all_eligible_filled:
                return ConversationPhase.RECOMMENDATION.value, "evidence_sufficient"
            return ConversationPhase.EXPLORATION.value, None

        if current_phase == ConversationPhase.RECOMMENDATION.value:
            if visitor_rejected_fit:
                return ConversationPhase.EXPLORATION.value, "visitor_rejects_fit"
            if recommendation_acknowledged:
                return ConversationPhase.QUALIFICATION.value, "recommendation_acknowledged"
            return ConversationPhase.RECOMMENDATION.value, None

        if current_phase == ConversationPhase.QUALIFICATION.value:
            if commercial_slots_resolved:
                return ConversationPhase.CAPTURE_AND_CLOSE.value, "commercial_slots_resolved"
            return ConversationPhase.QUALIFICATION.value, None

        if current_phase == ConversationPhase.CAPTURE_AND_CLOSE.value:
            # Stay here until completion is triggered
            return ConversationPhase.CAPTURE_AND_CLOSE.value, None

        # Default: stay in current phase
        return current_phase, None

    @staticmethod
    def get_valid_phases() -> list[str]:
        """Get all valid conversation phases in order."""
        return [p.value for p in ConversationPhase]

    @staticmethod
    def get_stage_index(phase: str) -> int:
        """Get the numeric stage index for display purposes.

        Args:
            phase: The phase string identifier.

        Returns:
            0-based stage index, or 0 for unknown phases.
        """
        definition = PHASE_DEFINITIONS.get(phase)
        if definition:
            return definition.stage_index
        return 0
