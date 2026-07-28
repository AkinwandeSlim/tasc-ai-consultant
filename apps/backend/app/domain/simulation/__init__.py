"""Simulation framework — deterministic consultation simulation.

Provides interfaces, models, and realistic scenarios for running
consultations in simulation mode without calling an LLM. Returns
deterministic data for testing and development purposes.

Usage:
    SIMULATION_MODE=true # enables simulation in config
    register_default_scenarios(registry)
"""

from app.domain.simulation.framework import (
    Scenario,
    ScenarioRegistry,
    ScenarioResult,
    SimulationConfig,
    SimulationFramework,
    SimulationProvider,
)
from app.domain.simulation.scenarios import (
    DEFAULT_SCENARIOS,
    EDUCATION_SCENARIO,
    FAST_TRACK_SCENARIO,
    FINTECH_SCENARIO,
    HEALTHCARE_SCENARIO,
    HUMAN_REQUEST_SCENARIO,
    LOGISTICS_SCENARIO,
    MANUFACTURING_SCENARIO,
    PROFESSIONAL_SERVICES_SCENARIO,
    REAL_ESTATE_SCENARIO,
    RETAIL_SCENARIO,
    register_default_scenarios,
)
