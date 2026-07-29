"""Normaliser — maps free-text values to controlled vocabularies.

Pure deterministic function. No I/O, no model calls.

Given a raw text phrase and a vocabulary configuration, returns the
best-matching normalised value and a confidence score.

References: PRD FR-25, PRD 12.5
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class NormalisedValue:
    """Result of normalising a free-text value."""

    value: str | None = None
    normalised: str | None = None
    raw: str | None = None
    confidence: float = 0.0
    label: str = ""


# --- Built-in vocabularies as fallback when resource files are unavailable ---

INDUSTRY_VOCAB: list[dict[str, Any]] = [
    {"value": "logistics", "label": "Logistics", "aliases": ["freight", "supply chain", "transportation", "shipping", "courier", "delivery", "warehouse"]},
    {"value": "fintech", "label": "Financial Technology", "aliases": ["financial services", "banking", "payments", "insurance", "fin tech", "finance", "lending", "investment"]},
    {"value": "healthcare", "label": "Healthcare", "aliases": ["medical", "health", "hospital", "clinic", "health tech", "medtech", "pharma"]},
    {"value": "retail", "label": "Retail", "aliases": ["ecommerce", "e-commerce", "online store", "wholesale", "brick and mortar", "shop"]},
    {"value": "manufacturing", "label": "Manufacturing", "aliases": ["production", "factory", "industrial", "make", "assembly"]},
    {"value": "professional_services", "label": "Professional Services", "aliases": ["consulting", "legal", "accounting", "agency", "professional svcs", "law firm", "audit"]},
    {"value": "education", "label": "Education", "aliases": ["edtech", "school", "university", "training", "e-learning", "college", "academy"]},
    {"value": "real_estate", "label": "Real Estate", "aliases": ["property", "reality", "housing", "commercial property", "realty"]},
    {"value": "other", "label": "Other", "aliases": []},
]

BUSINESS_SIZE_VOCAB: list[dict[str, Any]] = [
    {"value": "1-10", "label": "1 to 10 employees", "aliases": ["startup", "solo", "freelancer", "micro"]},
    {"value": "11-50", "label": "11 to 50 employees", "aliases": ["small team", "small business", "growing"]},
    {"value": "51-200", "label": "51 to 200 employees", "aliases": ["mid size", "mid-market", "medium"]},
    {"value": "201-500", "label": "201 to 500 employees", "aliases": ["large small", "established"]},
    {"value": "501-1000", "label": "501 to 1000 employees", "aliases": ["enterprise", "large"]},
    {"value": "1000+", "label": "Over 1000 employees", "aliases": ["large enterprise", "global", "multinational"]},
]

TIMELINE_VOCAB: list[dict[str, Any]] = [
    {"value": "immediate", "label": "Immediate", "aliases": ["asap", "right now", "urgent", "now", "yesterday"]},
    {"value": "1-3_months", "label": "1 to 3 months", "aliases": ["next quarter", "soon", "next few months", "short term"]},
    {"value": "3-6_months", "label": "3 to 6 months", "aliases": ["this year", "q2", "q3", "by the end of"]},
    {"value": "6-12_months", "label": "6 to 12 months", "aliases": ["next year", "next financial year", "long term", "next 12"]},
    {"value": "exploring", "label": "Just exploring", "aliases": ["no rush", "looking", "exploring", "considering", "evaluating"]},
]

BUDGET_VOCAB: list[dict[str, Any]] = [
    {"value": "under_5k", "label": "Under £5,000", "aliases": ["small", "tight", "minimal", "very little"]},
    {"value": "5k-15k", "label": "£5,000 to £15,000", "aliases": ["limited", "modest"]},
    {"value": "15k-50k", "label": "£15,000 to £50,000", "aliases": ["moderate", "mid range"]},
    {"value": "50k-100k", "label": "£50,000 to £100,000", "aliases": ["substantial", "significant"]},
    {"value": "100k+", "label": "Over £100,000", "aliases": ["large", "enterprise", "major", "unlimited"]},
    {"value": "undisclosed", "label": "Prefer not to say", "aliases": ["unknown", "not sure", "don't know"]},
]

DECISION_ROLE_VOCAB: list[dict[str, Any]] = [
    {"value": "decision_maker", "label": "Decision Maker", "aliases": ["owner", "founder", "ceo", "director", "head of", "vp", "cto", "chief"]},
    {"value": "influencer", "label": "Influencer", "aliases": ["manager", "lead", "senior", "advisor", "consultant"]},
    {"value": "researcher", "label": "Researcher", "aliases": ["analyst", "junior", "associate", "coordinator"]},
    {"value": "unknown", "label": "Unknown", "aliases": []},
]


def _find_best_match(
    raw_text: str, vocab: list[dict[str, Any]]
) -> tuple[str | None, str | None, str | None, float]:
    """Find the best vocabulary match for raw text.

    Args:
        raw_text: The free-text to normalise.
        vocab: List of vocabulary entries with value, label, aliases.

    Returns:
        Tuple of (value, label, normalised, confidence).
    """
    text_lower = raw_text.lower().strip()
    words = set(text_lower.split())

    best_value: str | None = None
    best_label: str | None = None
    best_normalised: str | None = None
    best_score: float = 0.0

    for entry in vocab:
        score = 0.0
        value = entry["value"]
        label = entry["label"]
        aliases = entry.get("aliases", [])

        # Check exact match
        if text_lower == value or text_lower == label.lower():
            score = 1.0
            best_value = value
            best_label = label
            best_normalised = value
            best_score = score
            break

        # Check if any word in the text matches the value itself
        value_lower = value.lower()
        for word in words:
            if word == value_lower:
                score = max(score, 0.85)
                break

        # Check alias matches with word-level overlap
        for alias in aliases:
            alias_lower = alias.lower()
            # Substring match
            if alias_lower in text_lower or text_lower in alias_lower:
                alias_word_count = len(alias_lower.split())
                overlap = len(words & set(alias_lower.split()))
                if alias_word_count > 0:
                    score = max(score, overlap / alias_word_count * 0.9)

        # Check number patterns for business size
        if "size" in str(vocab) or any(k in str(entry) for k in ["employees", "Over"]):
            numbers = re.findall(r"\d[\d,]*", text_lower.replace(",", ""))
            for num_str in numbers:
                try:
                    num = int(num_str)
                    range_match = _match_number_range(num, value)
                    if range_match:
                        score = max(score, 0.85)
                except ValueError:
                    continue

        if score > best_score:
            best_value = value
            best_label = label
            best_normalised = value
            best_score = score

    return best_value, best_label, best_normalised, best_score


def _match_number_range(num: int, band: str) -> bool:
    """Check if a number falls within a band range."""
    ranges = {
        "1-10": (1, 10),
        "11-50": (11, 50),
        "51-200": (51, 200),
        "201-500": (201, 500),
        "501-1000": (501, 1000),
        "1000+": (1000, 999999),
    }
    if band in ranges:
        low, high = ranges[band]
        return low <= num <= high
    return False


class Normaliser:
    """Normalises free-text values to controlled vocabularies.

    Pure deterministic function. Provides normalisation for industry,
    business size, timeline, budget band, and decision role.
    """

    def __init__(
        self,
        industry_vocab: list[dict[str, Any]] | None = None,
        business_size_vocab: list[dict[str, Any]] | None = None,
        timeline_vocab: list[dict[str, Any]] | None = None,
        budget_vocab: list[dict[str, Any]] | None = None,
        decision_role_vocab: list[dict[str, Any]] | None = None,
    ) -> None:
        self._industry_vocab = industry_vocab or INDUSTRY_VOCAB
        self._business_size_vocab = business_size_vocab or BUSINESS_SIZE_VOCAB
        self._timeline_vocab = timeline_vocab or TIMELINE_VOCAB
        self._budget_vocab = budget_vocab or BUDGET_VOCAB
        self._decision_role_vocab = decision_role_vocab or DECISION_ROLE_VOCAB

    def normalise_industry(self, raw_text: str) -> NormalisedValue:
        """Normalise an industry value."""
        value, label, normalised, confidence = _find_best_match(raw_text, self._industry_vocab)
        return NormalisedValue(value=value, normalised=normalised, raw=raw_text, confidence=confidence, label=label or "")

    def normalise_business_size(self, raw_text: str) -> NormalisedValue:
        """Normalise a business size value."""
        value, label, normalised, confidence = _find_best_match(raw_text, self._business_size_vocab)
        return NormalisedValue(value=value, normalised=normalised, raw=raw_text, confidence=confidence, label=label or "")

    def normalise_timeline(self, raw_text: str) -> NormalisedValue:
        """Normalise a timeline value."""
        value, label, normalised, confidence = _find_best_match(raw_text, self._timeline_vocab)
        return NormalisedValue(value=value, normalised=normalised, raw=raw_text, confidence=confidence, label=label or "")

    def normalise_budget(self, raw_text: str) -> NormalisedValue:
        """Normalise a budget band value."""
        # Check for explicit numbers
        numbers = re.findall(r"\d[\d,]*", raw_text.replace(",", ""))
        for num_str in numbers:
            try:
                num = int(num_str)
                budget_ranges = [
                    ("under_5k", 0, 4999),
                    ("5k-15k", 5000, 15000),
                    ("15k-50k", 15001, 50000),
                    ("50k-100k", 50001, 100000),
                    ("100k+", 100001, 99999999),
                ]
                for band, low, high in budget_ranges:
                    if low <= num <= high:
                        return NormalisedValue(
                            value=band,
                            normalised=band,
                            raw=raw_text,
                            confidence=0.9,
                            label=band,
                        )
            except ValueError:
                continue

        value, label, normalised, confidence = _find_best_match(raw_text, self._budget_vocab)
        return NormalisedValue(value=value, normalised=normalised, raw=raw_text, confidence=confidence, label=label or "")

    def normalise_decision_role(self, raw_text: str) -> NormalisedValue:
        """Normalise a decision role value."""
        value, label, normalised, confidence = _find_best_match(raw_text, self._decision_role_vocab)
        return NormalisedValue(value=value, normalised=normalised, raw=raw_text, confidence=confidence, label=label or "")
