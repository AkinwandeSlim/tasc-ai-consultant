"""Scoring component definitions — each component is a pure function.

Components: need_clarity (25), fit (20), urgency (15), budget (15),
authority (10), engagement (15). Total = 100.

Each function takes slot data and engagement signals and returns
awarded points plus a human-readable basis string.

References: PRD Section 14.2, AI Blueprint Section 5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComponentResult:
    """Result of a single scoring component."""

    awarded: int = 0
    max_points: int = 0
    basis: str = ""


def compute_need_clarity(
    pain_points: list[Any],
    pain_point_count: int | None = None,
) -> ComponentResult:
    """Compute Need Clarity (max 25).

    | Condition | Points |
    | No pain point identified | 0 |
    | One vague pain point | 8 |
    | One specific pain point with operational detail | 15 |
    | Two or more specific pain points | 21 |
    | Two or more pain points with quantified impact | 25 |
    """
    if pain_point_count is not None:
        count = pain_point_count
    else:
        count = len(pain_points)

    if count == 0:
        return ComponentResult(
            awarded=0, max_points=25,
            basis="No pain points identified yet",
        )

    if count == 1:
        # Check specificity
        if pain_points and hasattr(pain_points[0], "specificity"):
            spec = pain_points[0].specificity or "vague"
            if spec in ("quantified", "specific"):
                return ComponentResult(
                    awarded=15, max_points=25,
                    basis="One specific pain point with operational detail",
                )
        return ComponentResult(
            awarded=8, max_points=25,
            basis="One pain point identified, limited detail",
        )

    # Two or more pain points
    quantified_count = sum(
        1 for p in pain_points
        if hasattr(p, "specificity") and p.specificity == "quantified"
    )

    if quantified_count >= 2:
        return ComponentResult(
            awarded=25, max_points=25,
            basis=f"Two or more pain points with quantified impact ({quantified_count} quantified)",
        )

    if count >= 2:
        return ComponentResult(
            awarded=21, max_points=25,
            basis=f"{count} specific pain points identified",
        )

    return ComponentResult(awarded=8, max_points=25, basis="Pain points identified")


def compute_fit(
    has_service_mapping: bool = False,
    has_case_study_coverage: bool = False,
    weak_mapping: bool = False,
) -> ComponentResult:
    """Compute Fit (max 20).

    | Condition | Points |
    | No mappable service | 0 |
    | Weak mapping, single service, low confidence | 7 |
    | Clear mapping to one catalogue service | 14 |
    | Clear mapping plus industry covered by case study | 20 |
    """
    if has_case_study_coverage:
        return ComponentResult(
            awarded=20, max_points=20,
            basis="Strong service fit with industry case study coverage",
        )

    if has_service_mapping:
        return ComponentResult(
            awarded=14, max_points=20,
            basis="Clear mapping to Trizen services",
        )

    if weak_mapping:
        return ComponentResult(
            awarded=7, max_points=20,
            basis="Partial service fit identified",
        )

    return ComponentResult(
        awarded=0, max_points=20,
        basis="No service mapping established yet",
    )


def compute_urgency(timeline_value: str | None = None) -> ComponentResult:
    """Compute Urgency (max 15).

    | Timeline | Points |
    | immediate | 15 |
    | 1-3_months | 13 |
    | 3-6_months | 9 |
    | 6-12_months | 5 |
    | exploring | 2 |
    | unknown/None | 0 |
    """
    timeline_map: dict[str, tuple[int, str]] = {
        "immediate": (15, "Immediate timeline"),
        "1-3_months": (13, "1 to 3 month timeline"),
        "3-6_months": (9, "3 to 6 month timeline"),
        "6-12_months": (5, "6 to 12 month timeline"),
        "exploring": (2, "Exploring options, no fixed timeline"),
    }

    if timeline_value and timeline_value in timeline_map:
        points, basis = timeline_map[timeline_value]
        return ComponentResult(awarded=points, max_points=15, basis=basis)

    return ComponentResult(
        awarded=0, max_points=15,
        basis="Timeline not yet discussed",
    )


def compute_budget(budget_value: str | None = None) -> ComponentResult:
    """Compute Budget (max 15).

    | Band | Points |
    | 100k+ | 15 |
    | 50k-100k | 14 |
    | 15k-50k | 12 |
    | 5k-15k | 7 |
    | under_5k | 2 |
    | undisclosed | 5 |
    | unknown/None | 0 |
    """
    budget_map: dict[str, tuple[int, str]] = {
        "100k+": (15, "Budget over £100,000"),
        "50k-100k": (14, "Budget £50,000 to £100,000"),
        "15k-50k": (12, "Budget £15,000 to £50,000"),
        "5k-15k": (7, "Budget £5,000 to £15,000"),
        "under_5k": (2, "Budget under £5,000"),
        "undisclosed": (5, "Budget not disclosed"),
    }

    if budget_value and budget_value in budget_map:
        points, basis = budget_map[budget_value]
        return ComponentResult(awarded=points, max_points=15, basis=basis)

    return ComponentResult(
        awarded=0, max_points=15,
        basis="Budget not yet discussed",
    )


def compute_authority(role_value: str | None = None) -> ComponentResult:
    """Compute Authority (max 10).

    | Role | Points |
    | decision_maker | 10 |
    | influencer | 7 |
    | researcher | 3 |
    | unknown/None | 0 |
    """
    role_map: dict[str, tuple[int, str]] = {
        "decision_maker": (10, "Decision maker engaged"),
        "influencer": (7, "Influencer in the decision process"),
        "researcher": (3, "Researcher gathering information"),
    }

    if role_value and role_value in role_map:
        points, basis = role_map[role_value]
        return ComponentResult(awarded=points, max_points=10, basis=basis)

    return ComponentResult(
        awarded=0, max_points=10,
        basis="Decision authority not yet established",
    )


def compute_engagement(
    visitor_turn_count: int = 0,
    asked_company_question: bool = False,
    responded_to_recommendation: bool = False,
    volunteered_contact: bool = False,
) -> ComponentResult:
    """Compute Engagement (max 15).

    | Signal | Points |
    | 3 or more visitor turns | 4 |
    | 6 or more visitor turns | 3 additional |
    | Asked a company/capability question | 3 |
    | Responded substantively to recommendation | 3 |
    | Provided contact details voluntarily | 2 |
    """
    total = 0
    reasons: list[str] = []

    if visitor_turn_count >= 6:
        total += 7
        reasons.append(f"{visitor_turn_count} visitor turns")
    elif visitor_turn_count >= 3:
        total += 4
        reasons.append(f"{visitor_turn_count} visitor turns")

    if asked_company_question:
        total += 3
        reasons.append("asked company or capability question")

    if responded_to_recommendation:
        total += 3
        reasons.append("responded to recommendations")

    if volunteered_contact:
        total += 2
        reasons.append("volunteered contact details")

    if not reasons:
        basis = "Engagement signals not yet observed"
    else:
        basis = "; ".join(reasons)

    return ComponentResult(awarded=min(total, 15), max_points=15, basis=basis)
