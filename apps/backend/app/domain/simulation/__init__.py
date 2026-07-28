"""Simulation framework — deterministic consultation simulation.

Provides interfaces and models for running consultations in simulation
mode without calling an LLM. Returns deterministic data for testing
and development purposes. No business scenarios are included here;
only the framework infrastructure.

Usage:
    SIMULATION_MODE=true # enables simulation in config
"""

from app.domain.simulation.framework import (
    Scenario,
    ScenarioRegistry,
    ScenarioResult,
    SimulationConfig,
    SimulationFramework,
    SimulationProvider,
)
