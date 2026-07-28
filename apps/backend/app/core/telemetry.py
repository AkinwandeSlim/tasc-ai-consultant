"""Telemetry utilities: timing context managers, token accounting.

Provides per-turn timing and token cost tracking used by the orchestrator
to emit observability data (FR-67 to FR-71).
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class PhaseTiming:
    """Timing for a single pipeline phase."""

    phase_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0

    def start(self) -> None:
        self.start_time = time.monotonic()

    def stop(self) -> None:
        self.end_time = time.monotonic()
        self.duration_ms = (self.end_time - self.start_time) * 1000


@dataclass
class TurnTelemetry:
    """Aggregated telemetry for one turn."""

    turn_index: int = 0
    correlation_id: str = ""
    phase_timings: dict[str, PhaseTiming] = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    retrieval_chunk_ids: list[str] = field(default_factory=list)
    prompt_manifest_version: str = ""
    degradation_flags: list[str] = field(default_factory=list)


@contextmanager
def track_phase(telemetry: TurnTelemetry, phase_name: str) -> Iterator[PhaseTiming]:
    """Context manager that records a phase's timing.

    Args:
        telemetry: The turn telemetry object to record into.
        phase_name: Unique identifier for this phase.

    Yields:
        PhaseTiming object that is populated on exit.
    """
    timing = PhaseTiming(phase_name=phase_name)
    timing.start()
    try:
        yield timing
    finally:
        timing.stop()
        telemetry.phase_timings[phase_name] = timing


def calculate_cost(
    input_tokens: int, output_tokens: int, cost_per_1k_input: float, cost_per_1k_output: float
) -> float:
    """Calculate estimated cost for a model call.

    Args:
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        cost_per_1k_input: Cost per 1,000 input tokens (USD).
        cost_per_1k_output: Cost per 1,000 output tokens (USD).

    Returns:
        Estimated cost in USD.
    """
    return (input_tokens / 1000 * cost_per_1k_input) + (
        output_tokens / 1000 * cost_per_1k_output
    )
