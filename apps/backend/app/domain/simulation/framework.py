"""Simulation framework core — interfaces, models, and registry.

Enables deterministic consultation data without calling an LLM.
Useful for frontend development, integration testing, and evaluation
scenarios. Controlled by SIMULATION_MODE configuration flag.

References: AI Blueprint Section 22 (testing infrastructure)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class SimulationConfig:
    """Configuration for simulation mode.

    Controls whether simulation is enabled and what behaviour
    the simulation provider should exhibit.
    """

    enabled: bool = False
    scenario_id: str = ""
    deterministic_response: bool = True
    simulate_latency: bool = False
    latency_range_ms: tuple[int, int] = (200, 1500)
    simulate_errors: bool = False
    error_rate: float = 0.0
    log_level: str = "INFO"


@dataclass
class ScenarioResult:
    """Result produced by a simulation scenario."""

    scenario_id: str
    turn_index: int
    response_text: str = ""
    phase: str = "discovery"
    intent: str = "describe_problem"
    analysis_snapshot: dict[str, Any] = field(default_factory=dict)
    slots_delta: dict[str, Any] = field(default_factory=dict)
    finish_reason: str = "complete"
    latency_ms: float = 0.0
    completed: bool = False


@dataclass
class Scenario:
    """A single simulation scenario with configuration and expected outcomes.

    Scenarios are registered in the ScenarioRegistry and selected
    by ID when simulation mode is active.
    """

    scenario_id: str
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    turn_count: int = 5
    initial_phase: str = "greeting"
    responses: list[str] = field(default_factory=list)
    expected_slots: dict[str, Any] = field(default_factory=dict)
    expected_band: str = "exploring"
    expected_score: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class SimulationProvider(Protocol):
    """Protocol for simulation data providers.

    Implementations return deterministic consultation data
    without calling an LLM.
    """

    def generate_response(self, scenario: Scenario, turn: int) -> ScenarioResult:
        """Generate a deterministic response for the given turn."""
        ...


class ScenarioRegistry:
    """Registry of simulation scenarios.

    Scenarios are registered by ID and can be retrieved for
    deterministic simulation runs. Acts as the catalogue of
    available test/development scenarios.
    """

    def __init__(self) -> None:
        self._scenarios: dict[str, Scenario] = {}
        self._loaded: bool = False

    def register(self, scenario: Scenario) -> None:
        """Register a scenario in the registry.

        Args:
            scenario: The Scenario to register.

        Raises:
            ValueError: If a scenario with the same ID already exists.
        """
        if scenario.scenario_id in self._scenarios:
            raise ValueError(
                f"Scenario '{scenario.scenario_id}' already registered"
            )
        self._scenarios[scenario.scenario_id] = scenario
        logger.debug(
            "Registered scenario '%s': %s", scenario.scenario_id, scenario.name
        )

    def register_many(self, scenarios: list[Scenario]) -> None:
        """Register multiple scenarios at once.

        Args:
            scenarios: List of Scenario instances to register.
        """
        for scenario in scenarios:
            self.register(scenario)

    def get(self, scenario_id: str) -> Scenario | None:
        """Get a scenario by ID.

        Args:
            scenario_id: The scenario identifier.

        Returns:
            The Scenario if found, None otherwise.
        """
        return self._scenarios.get(scenario_id)

    def get_or_raise(self, scenario_id: str) -> Scenario:
        """Get a scenario by ID or raise KeyError.

        Args:
            scenario_id: The scenario identifier.

        Returns:
            The Scenario.

        Raises:
            KeyError: If the scenario is not found.
        """
        if scenario_id not in self._scenarios:
            raise KeyError(
                f"Scenario '{scenario_id}' not found. "
                f"Available: {list(self._scenarios.keys())}"
            )
        return self._scenarios[scenario_id]

    def list_scenarios(self, tag: str | None = None) -> list[Scenario]:
        """List all registered scenarios, optionally filtered by tag.

        Args:
            tag: Optional tag to filter by.

        Returns:
            List of matching Scenario instances.
        """
        if tag:
            return [
                s for s in self._scenarios.values() if tag in s.tags
            ]
        return list(self._scenarios.values())

    def remove(self, scenario_id: str) -> None:
        """Remove a scenario from the registry.

        Args:
            scenario_id: The scenario identifier to remove.
        """
        self._scenarios.pop(scenario_id, None)
        logger.debug("Removed scenario '%s'", scenario_id)

    def clear(self) -> None:
        """Remove all registered scenarios."""
        self._scenarios.clear()
        self._loaded = False

    @property
    def count(self) -> int:
        """Number of registered scenarios."""
        return len(self._scenarios)

    @property
    def is_empty(self) -> bool:
        """Whether the registry contains any scenarios."""
        return len(self._scenarios) == 0


@dataclass
class DefaultScenarioProvider:
    """Default simulation provider with template-based responses.

    Generates deterministic responses based on the scenario definition
    and current turn. Used when no custom provider is configured.
    """

    config: SimulationConfig = field(default_factory=SimulationConfig)

    def generate_response(
        self, scenario: Scenario, turn: int
    ) -> ScenarioResult:
        """Generate a deterministic response for the given turn.

        Args:
            scenario: The scenario to generate from.
            turn: The current turn index (0-based).

        Returns:
            A ScenarioResult with deterministic content.
        """
        response_index = min(turn, len(scenario.responses) - 1) if scenario.responses else 0
        response_text = (
            scenario.responses[response_index]
            if scenario.responses
            else f"[Simulated response for turn {turn}]"
        )

        # Simulate latency if configured
        latency = 0.0
        if self.config.simulate_latency:
            import random

            min_ms, max_ms = self.config.latency_range_ms
            latency = float(random.randint(min_ms, max_ms))

        # Determine phase progression
        phases = [
            "greeting",
            "discovery",
            "discovery",
            "exploration",
            "exploration",
            "recommendation",
            "qualification",
            "capture_and_close",
        ]
        phase = phases[min(turn, len(phases) - 1)] if turn < len(phases) else "capture_and_close"

        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            turn_index=turn,
            response_text=response_text,
            phase=phase,
            intent="answer_question",
            finish_reason="complete",
            latency_ms=latency,
            completed=(turn >= scenario.turn_count - 1),
        )


class SimulationFramework:
    """Top-level simulation framework.

    Coordinates the scenario registry, provider, and configuration.
    Provides a single entry point for running simulated consultations.

    Usage:
        framework = SimulationFramework()
        framework.config.enabled = True
        scenario = framework.registry.get("my_scenario")
        result = framework.run_turn(scenario, turn=0)
    """

    def __init__(
        self,
        config: SimulationConfig | None = None,
        registry: ScenarioRegistry | None = None,
        provider: SimulationProvider | None = None,
    ) -> None:
        self.config = config or SimulationConfig()
        self.registry = registry or ScenarioRegistry()
        self._provider = provider

    @property
    def provider(self) -> SimulationProvider:
        """Get the active simulation provider.

        Returns the configured provider or creates a DefaultScenarioProvider.
        """
        if self._provider is None:
            self._provider = DefaultScenarioProvider(config=self.config)
        return self._provider

    @provider.setter
    def provider(self, provider: SimulationProvider) -> None:
        """Set a custom simulation provider."""
        self._provider = provider

    def run_turn(
        self,
        scenario: Scenario | str,
        turn: int = 0,
    ) -> ScenarioResult | None:
        """Run a single simulated turn.

        Args:
            scenario: A Scenario instance or scenario ID string.
            turn: The turn index to simulate.

        Returns:
            A ScenarioResult, or None if the scenario is not found.
        """
        if isinstance(scenario, str):
            resolved = self.registry.get(scenario)
            if resolved is None:
                logger.warning("Scenario '%s' not found", scenario)
                return None
            scenario = resolved

        if not self.config.enabled:
            logger.debug(
                "Simulation is disabled (SIMULATION_MODE=false)"
            )
            return None

        result = self.provider.generate_response(scenario, turn)
        logger.debug(
            "Simulated turn %d for scenario '%s': phase=%s latency=%.0fms",
            turn,
            scenario.scenario_id,
            result.phase,
            result.latency_ms,
        )
        return result

    def run_full_scenario(
        self,
        scenario: Scenario | str,
    ) -> list[ScenarioResult]:
        """Run all turns of a scenario and return the results.

        Args:
            scenario: A Scenario instance or scenario ID string.

        Returns:
            List of ScenarioResult for each turn.
        """
        if isinstance(scenario, str):
            resolved = self.registry.get(scenario)
            if resolved is None:
                logger.warning("Scenario '%s' not found", scenario)
                return []
            scenario = resolved

        results: list[ScenarioResult] = []
        for turn in range(scenario.turn_count):
            result = self.run_turn(scenario, turn)
            if result is not None:
                results.append(result)

        logger.info(
            "Completed simulation of scenario '%s': %d turns",
            scenario.scenario_id,
            len(results),
        )
        return results

    def is_active(self) -> bool:
        """Whether simulation mode is currently active."""
        return self.config.enabled
