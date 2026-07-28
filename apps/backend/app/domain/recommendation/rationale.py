"""Rationale writer — generates human-readable rationale for each recommendation.

In production, this will use an LLM call for natural language rationales.
For Sprint 3, uses template-based rationale generation.

Falls back to template rationale on failure.

References: PRD Section 15.4, AI Blueprint Section 6.4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RationaleResult:
    """Generated rationale for a service recommendation."""

    service_code: str
    rationale: str
    source: str = "template"  # template | model


# --- Template rationales by service code ---

_RATIONALE_TEMPLATES: dict[str, str] = {
    "SVC-AIA": (
        "Given your challenges with {pain_summary}, AI Automation could help "
        "streamline those repetitive workflows. Trizen typically delivers this "
        "as a 4 to 10 week engagement, starting with discovery and moving "
        "into a focused build phase."
    ),
    "SVC-WEB": (
        "Based on your need for {pain_summary}, a modern web platform could "
        "transform how you engage with customers. Trizen's web development "
        "team typically delivers this type of project in 6 to 16 weeks."
    ),
    "SVC-DAT": (
        "With data challenges around {pain_summary}, a Data Engineering "
        "engagement could unlock reliable reporting and decision-making. "
        "Typical engagements run 6 to 12 weeks."
    ),
    "SVC-INT": (
        "Your description of {pain_summary} suggests a Systems Integration "
        "approach could eliminate the manual handoffs between tools. Trizen "
        "typically delivers this in 3 to 8 weeks."
    ),
    "SVC-CLD": (
        "Given the infrastructure challenges with {pain_summary}, a Cloud "
        "and DevOps engagement could stabilise your environment and optimise "
        "costs. Typical engagements run 4 to 10 weeks."
    ),
    "SVC-CON": (
        "Based on your situation with {pain_summary}, a Technology Strategy "
        "consultation could help clarify the best path forward. Trizen "
        "typically delivers this as a focused 2 to 6 week engagement."
    ),
}

_FALLBACK_RATIONALE: str = (
    "This service aligns with the business needs you've described. "
    "A consultant can provide more detail on how this would work "
    "for your specific situation."
)


class RationaleWriter:
    """Generates rationale text for service recommendations.

    Uses template-based rationales for deterministic operation.
    In Sprint 2B+, this will use an LLM call for more natural phrasing.
    """

    def __init__(self) -> None:
        self._templates = _RATIONALE_TEMPLATES

    def write_rationale(
        self,
        service_code: str,
        pain_point_labels: list[str],
        pain_point_ids: list[str] | None = None,
    ) -> RationaleResult:
        """Generate a rationale for a recommended service.

        Args:
            service_code: The service code (e.g. SVC-AIA).
            pain_point_labels: Labels of matched pain points.
            pain_point_ids: Optional IDs of matched pain points.

        Returns:
            RationaleResult with generated rationale.
        """
        if not pain_point_labels:
            return RationaleResult(
                service_code=service_code,
                rationale=_FALLBACK_RATIONALE,
                source="template",
            )

        # Build pain summary from labels
        pain_summary = self._summarise_pains(pain_point_labels)

        template = self._templates.get(service_code, _FALLBACK_RATIONALE)
        rationale = template.format(pain_summary=pain_summary)

        return RationaleResult(
            service_code=service_code,
            rationale=rationale,
            source="template",
        )

    def write_all_rationales(
        self,
        service_codes: list[str],
        pain_point_labels: list[str],
        pain_point_map: dict[str, list[str]] | None = None,
    ) -> list[RationaleResult]:
        """Generate rationales for all service codes.

        Args:
            service_codes: List of service codes to generate for.
            pain_point_labels: All matched pain point labels.
            pain_point_map: Optional per-service-code pain point labels.

        Returns:
            List of RationaleResult for each service code.
        """
        results: list[RationaleResult] = []
        for code in service_codes:
            labels = (pain_point_map or {}).get(code, pain_point_labels)
            result = self.write_rationale(code, labels)
            results.append(result)
        return results

    @staticmethod
    def _summarise_pains(labels: list[str]) -> str:
        """Summarise pain point labels into a short phrase."""
        if not labels:
            return "your current processes"

        if len(labels) == 1:
            return labels[0].lower()

        if len(labels) == 2:
            return f"{labels[0].lower()} and {labels[1].lower()}"

        return f"{labels[0].lower()}, along with other operational challenges"
