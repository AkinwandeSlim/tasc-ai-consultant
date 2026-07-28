"""Banding — maps numeric scores to qualification bands.

Thresholds from configuration, not hardcoded.

Bands: Cold (0-34), Warm (35-59), Qualified (60-79), Hot (80-100).
Plus special band: exploring (before scoring), not_a_lead (override).

References: PRD Section 14.3, AI Blueprint Section 5.5
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BandInfo:
    """Information about a qualification band."""

    band: str
    label: str
    score_low: int
    score_high: int
    description: str
    routing: str = ""


BAND_DEFINITIONS: list[BandInfo] = [
    BandInfo(
        band="cold",
        label="Cold",
        score_low=0,
        score_high=34,
        description="Early exploration, no clear need",
        routing="Sheets only, no email, no alert",
    ),
    BandInfo(
        band="warm",
        label="Warm",
        score_low=35,
        score_high=59,
        description="Real need, weak commercial signals",
        routing="Sheets plus sales email, nurture queue",
    ),
    BandInfo(
        band="qualified",
        label="Qualified",
        score_low=60,
        score_high=79,
        description="Clear need and fit, at least one commercial signal",
        routing="Sheets plus sales email, follow up within 24 hours",
    ),
    BandInfo(
        band="hot",
        label="Hot",
        score_low=80,
        score_high=100,
        description="Clear need, fit, urgency, budget, and authority",
        routing="Sheets, sales email, Telegram alert, follow up same day",
    ),
]


def score_to_band(
    score: int,
    threshold_warm: int = 35,
    threshold_qualified: int = 60,
    threshold_hot: int = 80,
) -> str:
    """Map a numeric score to a qualification band.

    Args:
        score: The numeric lead score (0-100).
        threshold_warm: Minimum score for Warm band.
        threshold_qualified: Minimum score for Qualified band.
        threshold_hot: Minimum score for Hot band.

    Returns:
        The band string: 'cold', 'warm', 'qualified', or 'hot'.
    """
    if score >= threshold_hot:
        return "hot"
    if score >= threshold_qualified:
        return "qualified"
    if score >= threshold_warm:
        return "warm"
    return "cold"


def get_band_info(band: str) -> BandInfo | None:
    """Get BandInfo for a band name.

    Args:
        band: The band name.

    Returns:
        BandInfo if found, None otherwise.
    """
    for info in BAND_DEFINITIONS:
        if info.band == band:
            return info
    return None


def band_display_label(band: str) -> str:
    """Get the visitor-safe display label for a band.

    Args:
        band: The internal band name.

    Returns:
        A visitor-safe label string.
    """
    labels: dict[str, str] = {
        "exploring": "Getting to know your business",
        "cold": "Early stage conversation",
        "warm": "Clear need identified",
        "qualified": "Strong fit with Trizen services",
        "hot": "Priority lead, a consultant will follow up quickly",
        "not_a_lead": "Information only",
    }
    return labels.get(band, "Getting to know your business")
