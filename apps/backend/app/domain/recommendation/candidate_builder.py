"""Candidate builder — maps pain points to candidate service codes.

Rule-based mapping from pain signal IDs to Trizen service codes.
Uses the pain_mapping.yaml configuration.

References: PRD Section 15.2, AI Blueprint Section 6.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Candidate:
    """A single service candidate with mapping information."""

    service_code: str
    base_weight: float = 0.0
    pain_signals: list[str] = field(default_factory=list)
    is_primary: bool = False


# --- Default pain-to-service mapping (matches PRD 15.2) ---

DEFAULT_PAIN_MAPPINGS: list[dict[str, Any]] = [
    {"pain": "manual_repetitive_processes", "primary": "SVC-AIA", "secondary": "SVC-INT", "base_weight": 1.0},
    {"pain": "high_volume_triage", "primary": "SVC-AIA", "secondary": "SVC-DAT", "base_weight": 1.0},
    {"pain": "disconnected_tools", "primary": "SVC-INT", "secondary": "SVC-AIA", "base_weight": 1.0},
    {"pain": "manual_reporting", "primary": "SVC-DAT", "secondary": "SVC-INT", "base_weight": 1.0},
    {"pain": "no_single_source_of_truth", "primary": "SVC-DAT", "secondary": "SVC-INT", "base_weight": 0.9},
    {"pain": "outdated_website", "primary": "SVC-WEB", "secondary": "SVC-CON", "base_weight": 1.0},
    {"pain": "customer_portal_needed", "primary": "SVC-WEB", "secondary": "SVC-INT", "base_weight": 1.0},
    {"pain": "fragile_deployments", "primary": "SVC-CLD", "secondary": "SVC-CON", "base_weight": 1.0},
    {"pain": "scaling_problems", "primary": "SVC-CLD", "secondary": "SVC-WEB", "base_weight": 0.9},
    {"pain": "no_roadmap", "primary": "SVC-CON", "secondary": "SVC-AIA", "base_weight": 0.8},
    {"pain": "wants_ai", "primary": "SVC-CON", "secondary": "SVC-AIA", "base_weight": 0.9},
    {"pain": "compliance_gaps", "primary": "SVC-CON", "secondary": "SVC-DAT", "base_weight": 0.7},
    # Additional mappings for internal pain IDs from the extractor
    {"pain": "manual_data_entry", "primary": "SVC-AIA", "secondary": "SVC-INT", "base_weight": 1.0},
    {"pain": "duplicate_data_entry", "primary": "SVC-AIA", "secondary": "SVC-INT", "base_weight": 1.0},
    {"pain": "order_invoice_processing", "primary": "SVC-AIA", "secondary": "SVC-INT", "base_weight": 1.0},
    {"pain": "data_trapped", "primary": "SVC-DAT", "secondary": "SVC-INT", "base_weight": 0.9},
    {"pain": "poor_web_conversion", "primary": "SVC-WEB", "secondary": "SVC-CON", "base_weight": 0.9},
    {"pain": "cloud_cost", "primary": "SVC-CLD", "secondary": "SVC-CON", "base_weight": 0.9},
]

# Category mapping for services
SERVICE_CATEGORIES: dict[str, str] = {
    "SVC-AIA": "automation",
    "SVC-WEB": "development",
    "SVC-DAT": "data",
    "SVC-INT": "integration",
    "SVC-CLD": "infrastructure",
    "SVC-CON": "strategy",
}

# Service names
SERVICE_NAMES: dict[str, str] = {
    "SVC-AIA": "AI Automation and Agents",
    "SVC-WEB": "Web and Application Development",
    "SVC-DAT": "Data Engineering and Analytics",
    "SVC-INT": "Systems Integration",
    "SVC-CLD": "Cloud and DevOps",
    "SVC-CON": "Technology Strategy Consulting",
}

# Typical engagements
SERVICE_ENGAGEMENTS: dict[str, str] = {
    "SVC-AIA": "4 to 10 weeks, discovery plus build",
    "SVC-WEB": "6 to 16 weeks",
    "SVC-DAT": "6 to 12 weeks",
    "SVC-INT": "3 to 8 weeks",
    "SVC-CLD": "4 to 10 weeks",
    "SVC-CON": "2 to 6 weeks",
}


class CandidateBuilder:
    """Builds candidate service recommendations from pain points.

    Rule-based: maps pain signals to service codes using the configured
    pain mapping data. Pure function — no I/O, no model calls.
    """

    def __init__(
        self,
        pain_mappings: list[dict[str, Any]] | None = None,
    ) -> None:
        self._mappings = pain_mappings or DEFAULT_PAIN_MAPPINGS

    def build_candidates(
        self,
        pain_signal_ids: list[str],
        industry: str | None = None,
    ) -> list[Candidate]:
        """Build candidate services from identified pain signals.

        Args:
            pain_signal_ids: List of pain signal IDs identified from extraction.
            industry: Optional industry for targeting.

        Returns:
            List of Candidate with service codes and weights.
        """
        candidate_map: dict[str, Candidate] = {}

        for pain_id in pain_signal_ids:
            for mapping in self._mappings:
                if mapping["pain"] == pain_id:
                    primary = mapping["primary"]
                    secondary = mapping["secondary"]
                    weight = mapping["base_weight"]

                    # Add or update primary candidate
                    if primary in candidate_map:
                        candidate_map[primary].pain_signals.append(pain_id)
                        candidate_map[primary].base_weight = max(
                            candidate_map[primary].base_weight, weight
                        )
                    else:
                        candidate_map[primary] = Candidate(
                            service_code=primary,
                            base_weight=weight,
                            pain_signals=[pain_id],
                            is_primary=True,
                        )

                    # Add or update secondary candidate
                    if secondary in candidate_map:
                        candidate_map[secondary].pain_signals.append(pain_id)
                    else:
                        candidate_map[secondary] = Candidate(
                            service_code=secondary,
                            base_weight=weight * 0.8,
                            pain_signals=[pain_id],
                            is_primary=False,
                        )

        return list(candidate_map.values())

    def get_service_name(self, code: str) -> str:
        """Get the display name for a service code."""
        return SERVICE_NAMES.get(code, code)

    def get_category(self, code: str) -> str:
        """Get the category for a service code."""
        return SERVICE_CATEGORIES.get(code, "")

    def get_typical_engagement(self, code: str) -> str:
        """Get the typical engagement description."""
        return SERVICE_ENGAGEMENTS.get(code, "")
