"""Pipeline — stage definitions and sequencing.

Defines the consultation turn pipeline stages and their ordering.

The pipeline runs in this order for each turn:
1. Guardrail check
2. Intent classification + Slot extraction (parallel)
3. Normalisation + Merging
4. Scoring (deterministic)
5. Recommendation evaluation
6. Phase transition
7. Question selection
8. Response generation
9. Completion check
10. Snapshot emission

References: PRD Section 13, AI Blueprint Section 12
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StageType(str, Enum):
    """Types of pipeline stages."""

    GUARDRAIL = "guardrail"
    INTENT = "intent"
    EXTRACTION = "extraction"
    NORMALISATION = "normalisation"
    MERGE = "merge"
    SCORING = "scoring"
    RECOMMENDATION = "recommendation"
    PHASE_TRANSITION = "phase_transition"
    QUESTION_SELECTION = "question_selection"
    RESPONSE_GENERATION = "response_generation"
    COMPLETION_CHECK = "completion_check"
    SNAPSHOT_EMISSION = "snapshot_emission"


@dataclass
class StageDefinition:
    """Definition of a single pipeline stage."""

    name: str
    stage_type: StageType
    description: str
    is_deterministic: bool = True
    timeout_ms: int = 100
    required: bool = True
    parallel_group: str | None = None  # Stages with same group run in parallel


@dataclass
class PipelineContext:
    """Context passed through the pipeline stages.

    Carries all state accumulated during turn processing.
    """

    turn_index: int = 0
    visitor_message: str = ""
    current_phase: str = "greeting"
    intent: dict[str, Any] = field(default_factory=dict)
    extraction: dict[str, Any] = field(default_factory=dict)
    slot_map: dict[str, Any] = field(default_factory=dict)
    business_profile: dict[str, Any] = field(default_factory=dict)
    lead_score: dict[str, Any] = field(default_factory=dict)
    recommendations: dict[str, Any] = field(default_factory=dict)
    next_question: dict[str, Any] = field(default_factory=dict)
    assistant_message: str = ""
    phase_transition: dict[str, Any] = field(default_factory=dict)
    completion: dict[str, Any] = field(default_factory=dict)
    analysis_snapshot: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    degradations: list[str] = field(default_factory=list)

    def record_error(self, stage: str, error: str) -> None:
        """Record a pipeline stage error."""
        self.errors.append({"stage": stage, "error": error})
        self.degradations.append(stage)


# Standard pipeline stages in order
STANDARD_STAGES: list[StageDefinition] = [
    StageDefinition(
        name="guardrail_check",
        stage_type=StageType.GUARDRAIL,
        description="Validate message length, content type, abuse check",
        timeout_ms=20,
    ),
    StageDefinition(
        name="intent_classification",
        stage_type=StageType.INTENT,
        description="Classify visitor message intent",
        is_deterministic=True,
        timeout_ms=50,
        parallel_group="understanding",
    ),
    StageDefinition(
        name="slot_extraction",
        stage_type=StageType.EXTRACTION,
        description="Extract discovery slots from message",
        is_deterministic=True,
        timeout_ms=100,
        parallel_group="understanding",
    ),
    StageDefinition(
        name="normalisation",
        stage_type=StageType.NORMALISATION,
        description="Normalise values to controlled vocabularies",
        timeout_ms=10,
    ),
    StageDefinition(
        name="slot_merging",
        stage_type=StageType.MERGE,
        description="Merge extraction into existing slot state",
        timeout_ms=10,
    ),
    StageDefinition(
        name="scoring",
        stage_type=StageType.SCORING,
        description="Compute deterministic lead score",
        timeout_ms=10,
    ),
    StageDefinition(
        name="recommendation",
        stage_type=StageType.RECOMMENDATION,
        description="Build and rank service recommendations",
        timeout_ms=50,
    ),
    StageDefinition(
        name="phase_transition",
        stage_type=StageType.PHASE_TRANSITION,
        description="Evaluate and apply phase transition",
        timeout_ms=5,
    ),
    StageDefinition(
        name="question_selection",
        stage_type=StageType.QUESTION_SELECTION,
        description="Select next discovery question",
        timeout_ms=5,
    ),
    StageDefinition(
        name="response_generation",
        stage_type=StageType.RESPONSE_GENERATION,
        description="Generate assistant response",
        timeout_ms=20,
    ),
    StageDefinition(
        name="completion_check",
        stage_type=StageType.COMPLETION_CHECK,
        description="Check if consultation should complete",
        timeout_ms=10,
    ),
    StageDefinition(
        name="snapshot_emission",
        stage_type=StageType.SNAPSHOT_EMISSION,
        description="Build and emit analysis snapshot",
        timeout_ms=20,
    ),
]
