"""Override rules — disqualification and band modifications (PRD 14.4).

OV-01 to OV-07 applied in order after score computation.

Each override returns an OverrideResult that can modify the band or add flags.

References: PRD Section 14.4, AI Blueprint Section 5.5
"""

from __future__ import annotations

from dataclasses import dataclass, field


_BAND_ORDER: list[str] = ["cold", "warm", "qualified", "hot"]


def _band_lt(band_a: str, band_b: str) -> bool:
    """Check if band_a is a lower/worse band than band_b."""
    try:
        return _BAND_ORDER.index(band_a) < _BAND_ORDER.index(band_b)
    except (ValueError, IndexError):
        return False


@dataclass
class OverrideResult:
    """Result of applying override rules."""

    applied_overrides: list[str] = field(default_factory=list)
    force_band: str | None = None
    cap_band: str | None = None
    suppress_automation: bool = False
    force_telegram: bool = False
    flag_partial: bool = False
    disqualified: bool = False


def apply_overrides(
    raw_score: int,
    band: str,
    visitor_turn_count: int = 0,
    anti_persona: bool = False,
    human_requested: bool = False,
    has_contact: bool = False,
    budget_band: str | None = None,
    timeline: str | None = None,
    business_size_value: str | None = None,
    decision_role_value: str | None = None,
    is_abandoned: bool = False,
    is_terminated: bool = False,
) -> OverrideResult:
    """Apply all override rules in order (OV-01 to OV-07).

    Args:
        raw_score: The computed raw score.
        band: The computed band before overrides.
        visitor_turn_count: Number of visitor turns.
        anti_persona: Whether anti-persona detected.
        human_requested: Whether human requested.
        has_contact: Whether valid contact with consent exists.
        budget_band: The budget band value.
        timeline: The timeline value.
        business_size_value: The business size value.
        decision_role_value: The decision role value.
        is_abandoned: Whether session is abandoned.
        is_terminated: Whether session is terminated.

    Returns:
        OverrideResult with overrides applied.
    """
    result = OverrideResult()
    result.flag_partial = False

    # OV-01: Anti-persona detected
    if anti_persona or is_terminated:
        result.applied_overrides.append("OV-01")
        result.force_band = "not_a_lead"
        result.suppress_automation = True
        result.disqualified = True
        return result

    # OV-02: Explicit human request
    if human_requested:
        result.applied_overrides.append("OV-02")
        result.force_telegram = True
        # Minimum band Qualified — upgrade if currently lower
        if _band_lt(result.force_band or band, "qualified"):
            result.force_band = "qualified"

    # OV-03: No contact captured
    if not has_contact:
        result.applied_overrides.append("OV-03")
        if not result.force_band:
            result.cap_band = "warm"

    # OV-04: Low budget, exploring only
    if budget_band == "under_5k" and timeline == "exploring":
        result.applied_overrides.append("OV-04")
        if not result.force_band:
            result.cap_band = "warm"

    # OV-05: Fewer than 2 visitor turns
    if visitor_turn_count < 2:
        result.applied_overrides.append("OV-05")
        result.force_band = "cold"

    # OV-06: Enterprise decision maker
    if business_size_value == "1000+" and decision_role_value == "decision_maker":
        result.applied_overrides.append("OV-06")
        # Minimum band Qualified — upgrade if currently lower
        if _band_lt(result.force_band or band, "qualified"):
            result.force_band = "qualified"

    # OV-07: Abandonment with contact
    if is_abandoned:
        result.applied_overrides.append("OV-07")
        result.flag_partial = True
        # Compute band normally (already computed, just flag it)

    # Resolve final band considering caps and forces
    if result.force_band:
        result.flag_partial = result.flag_partial and not result.disqualified
        return result

    # Apply cap if no force
    if result.cap_band:
        band_order = ["cold", "warm", "qualified", "hot"]
        try:
            current_idx = band_order.index(band)
            cap_idx = band_order.index(result.cap_band)
            if current_idx > cap_idx:
                band = result.cap_band
        except ValueError:
            pass

    result.flag_partial = result.flag_partial and not result.disqualified
    return result
