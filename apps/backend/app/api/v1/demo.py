"""Demo / simulation scenario endpoints.

GET /api/v1/demo/scenarios — list all available simulation scenarios

These endpoints expose the simulation framework's scenario registry
for frontend development, integration testing, and evaluation.

References: AI Blueprint Section 22
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.domain.simulation.framework import Scenario, ScenarioRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])


# ── Response DTOs ─────────────────────────────────────────────────────


class ScenarioResponse(BaseModel):
    """A single simulation scenario exposed via the API."""
    scenario_id: str
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    turn_count: int = 0
    initial_phase: str = "greeting"
    expected_band: str = ""
    expected_score: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ListScenariosResponse(BaseModel):
    """Response from GET /api/v1/demo/scenarios."""
    scenarios: list[ScenarioResponse]
    count: int = 0
    simulation_enabled: bool = False


# ── Dependencies ──────────────────────────────────────────────────────


def _get_scenario_registry() -> ScenarioRegistry:
    """Return a populated scenario registry singleton.

    Seeds default scenarios on first access. Will be replaced with
    proper DI container resolution.
    """
    if not hasattr(_get_scenario_registry, "_registry"):
        from app.domain.simulation.scenarios import register_default_scenarios
        registry = ScenarioRegistry()
        register_default_scenarios(registry)
        _get_scenario_registry._registry = registry  # type: ignore[attr-defined]
    return _get_scenario_registry._registry  # type: ignore[attr-defined]


# ── Routes ────────────────────────────────────────────────────────────


@router.get("/scenarios", response_model=ListScenariosResponse)
async def list_scenarios(
    registry: ScenarioRegistry = Depends(_get_scenario_registry),
) -> ListScenariosResponse:
    """List all available simulation scenarios.

    Returns metadata for each scenario including expected lead band,
    turn count, description, and tags. Useful for frontend scenario
    selectors and test configuration.
    """
    from app.core.config import get_settings

    settings = get_settings()
    scenarios = registry.list_scenarios()

    return ListScenariosResponse(
        scenarios=[
            ScenarioResponse(
                scenario_id=s.scenario_id,
                name=s.name,
                description=s.description,
                tags=list(s.tags),
                turn_count=s.turn_count,
                initial_phase=s.initial_phase,
                expected_band=s.expected_band,
                expected_score=s.expected_score,
                metadata=dict(s.metadata),
            )
            for s in scenarios
        ],
        count=len(scenarios),
        simulation_enabled=settings.SIMULATION_MODE,
    )
