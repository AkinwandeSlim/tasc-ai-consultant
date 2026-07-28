"""Business profile domain models.

Represents the structured understanding of a visitor's business
as captured through extraction and normalisation. Every field
carries confidence, source turn, and declined state metadata.

References: AI Blueprint Section 4, PRD Section 12.5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# --- Controlled Vocabulary Enums ---


class Industry(str, Enum):
    """Controlled industry vocabulary from PRD Section 12.5."""

    LOGISTICS = "logistics"
    FINTECH = "fintech"
    HEALTHCARE = "healthcare"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    PROFESSIONAL_SERVICES = "professional_services"
    EDUCATION = "education"
    REAL_ESTATE = "real_estate"
    OTHER = "other"


class BusinessSize(str, Enum):
    """Controlled business size bands."""

    SIZE_1_10 = "1-10"
    SIZE_11_50 = "11-50"
    SIZE_51_200 = "51-200"
    SIZE_201_500 = "201-500"
    SIZE_501_1000 = "501-1000"
    SIZE_1000_PLUS = "1000+"


class Timeline(str, Enum):
    """Controlled timeline vocabulary."""

    IMMEDIATE = "immediate"
    MONTHS_1_3 = "1-3_months"
    MONTHS_3_6 = "3-6_months"
    MONTHS_6_12 = "6-12_months"
    EXPLORING = "exploring"


class BudgetBand(str, Enum):
    """Controlled budget band vocabulary."""

    UNDER_5K = "under_5k"
    RANGE_5K_15K = "5k-15k"
    RANGE_15K_50K = "15k-50k"
    RANGE_50K_100K = "50k-100k"
    OVER_100K = "100k+"
    UNDISCLOSED = "undisclosed"


class DecisionAuthority(str, Enum):
    """Decision authority role."""

    DECISION_MAKER = "decision_maker"
    INFLUENCER = "influencer"
    RESEARCHER = "researcher"
    UNKNOWN = "unknown"


class DigitalMaturity(str, Enum):
    """Digital maturity level."""

    AD_HOC = "ad_hoc"
    DEVELOPING = "developing"
    STANDARDISED = "standardised"
    ADVANCED = "advanced"
    UNKNOWN = "unknown"


class AIReadiness(str, Enum):
    """AI readiness assessment."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class PainSpecificity(str, Enum):
    """Specificity level of a captured pain point."""

    VAGUE = "vague"
    SPECIFIC = "specific"
    QUANTIFIED = "quantified"


class GrowthStage(str, Enum):
    """Business growth stage."""

    EXPLORING = "exploring"
    EARLY = "early"
    SCALING = "scaling"
    ESTABLISHED = "established"
    ENTERPRISE = "enterprise"
    UNKNOWN = "unknown"


class TechnicalCapability(str, Enum):
    """Technical capability level."""

    NONE = "none"
    BASIC = "basic"
    MODERATE = "moderate"
    ADVANCED = "advanced"
    UNKNOWN = "unknown"


class Urgency(str, Enum):
    """Urgency level derived from timeline and impact."""

    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNKNOWN = "unknown"


# --- Value Objects ---


@dataclass
class SlotValue:
    """A single extracted value with provenance metadata.

    Matches the pattern used in domain/models/slots.py for consistency.
    """

    value: str | None = None
    normalised: str | None = None
    raw: str | None = None
    confidence: float = 0.0
    source_turn: int = 0
    declined: bool = False


@dataclass
class PainPoint:
    """A captured pain point with specificity, impact, and service mappings.

    References: AI Blueprint Section 4.1
    """

    id: str = ""
    label: str = ""
    raw_text: str = ""
    specificity: str = PainSpecificity.VAGUE.value
    severity: str | None = None
    frequency: str | None = None
    impact: str | None = None
    service_codes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source_turn: int = 0


@dataclass
class AIReadinessFactors:
    """AI readiness enrichment factors.

    References: AI Blueprint Section 4.2
    """

    process_repeatability: str | None = None
    data_availability: str | None = None
    data_quality: str | None = None
    process_ownership: str | None = None
    exception_rate: str | None = None
    integration_feasibility: str | None = None
    change_readiness: str | None = None

    @property
    def overall(self) -> str:
        """Derive overall AI readiness from factors."""
        if not any(
            [
                self.process_repeatability,
                self.data_availability,
                self.data_quality,
                self.process_ownership,
                self.exception_rate,
                self.integration_feasibility,
                self.change_readiness,
            ]
        ):
            return AIReadiness.UNKNOWN.value

        positives = sum(
            1
            for f in [
                self.process_repeatability,
                self.data_availability,
                self.data_quality,
                self.process_ownership,
                self.change_readiness,
            ]
            if f and f.lower() in ("high", "yes", "good", "automated")
        )

        negatives = sum(
            1
            for f in [
                self.exception_rate,
                self.integration_feasibility,
            ]
            if f and f.lower() in ("high", "poor", "none", "manual")
        )

        if positives >= 4 and negatives <= 0:
            return AIReadiness.HIGH.value
        if positives >= 2:
            return AIReadiness.MEDIUM.value
        if positives >= 1:
            return AIReadiness.LOW.value
        return AIReadiness.UNKNOWN.value


# --- Business Profile ---


@dataclass
class BusinessProfile:
    """Structured understanding of the visitor's business.

    All fields default to None/empty — a profile is built incrementally
    as extraction fills slots. Optional enrichment fields are never
    turned into mandatory discovery questions.

    References: AI Blueprint Section 4, PRD Section 12.5
    """

    # Core fields
    industry: SlotValue = field(default_factory=SlotValue)
    company_size: SlotValue = field(default_factory=SlotValue)
    pain_points: list[PainPoint] = field(default_factory=list)
    current_tools: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)

    # Commercial fields
    timeline: SlotValue = field(default_factory=SlotValue)
    budget_band: SlotValue = field(default_factory=SlotValue)
    decision_authority: SlotValue = field(default_factory=SlotValue)

    # Contact
    contact_name: SlotValue = field(default_factory=SlotValue)
    contact_email: SlotValue = field(default_factory=SlotValue)
    contact_company: SlotValue = field(default_factory=SlotValue)
    contact_phone: SlotValue = field(default_factory=SlotValue)
    consent_granted: bool = False

    # Optional enrichment fields
    business_model: str | None = None
    target_customers: list[str] = field(default_factory=list)
    manual_processes: list[str] = field(default_factory=list)
    growth_stage: str | None = None
    technical_maturity: str | None = None
    urgency: str | None = None
    ai_readiness: str | None = None
    ai_readiness_factors: AIReadinessFactors | None = None
    digital_maturity: str | None = None
    expected_roi: str | None = None

    # Conflicts
    conflicts: list[dict] = field(default_factory=list)

    @property
    def core_slots_filled(self) -> int:
        """Count of core discovery slots that have values."""
        count = 0
        if self.industry.value:
            count += 1
        if self.company_size.value:
            count += 1
        if self.pain_points:
            count += 1
        if self.current_tools:
            count += 1
        if self.goals:
            count += 1
        return count

    @property
    def commercial_slots_filled(self) -> int:
        """Count of commercial slots that have values or are declined."""
        count = 0
        if self.timeline.value or self.timeline.declined:
            count += 1
        if self.budget_band.value or self.budget_band.declined:
            count += 1
        if self.decision_authority.value or self.decision_authority.declined:
            count += 1
        if self.contact_email.value or self.contact_email.declined:
            count += 1
        return count

    @property
    def total_slots_filled(self) -> int:
        """Total count of filled or declined slots."""
        return self.core_slots_filled + self.commercial_slots_filled

    @property
    def has_contact(self) -> bool:
        """Whether contact information has been captured with consent."""
        return bool(self.contact_email.value and self.consent_granted)

    @property
    def manageable_pain_points(self) -> list[PainPoint]:
        """Pain points with adequate confidence for use in scoring."""
        return [p for p in self.pain_points if p.confidence >= 0.5]


@dataclass
class BusinessConstraints:
    """Constraints and limitations on the business engagement."""

    budget_range: str | None = None
    timeline_window: str | None = None
    technical_limitations: list[str] = field(default_factory=list)
    compliance_requirements: list[str] = field(default_factory=list)
    resource_availability: str | None = None
    geographic_constraints: list[str] = field(default_factory=list)
    integration_requirements: list[str] = field(default_factory=list)
