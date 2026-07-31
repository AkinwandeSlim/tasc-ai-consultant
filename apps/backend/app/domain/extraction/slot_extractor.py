"""Slot extractor — extracts structured discovery slots from visitor messages.

Rule-based deterministic extraction using keywords, patterns, and heuristics.
No AI calls. Pure domain logic.

References: PRD FR-22 to FR-29, PRD Section 12.5
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionResult:
    """Result of slot extraction for a single turn."""

    slots: dict[str, Any] = field(default_factory=dict)
    pain_points: list[dict[str, Any]] = field(default_factory=list)
    current_tools: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    turn_index: int = 0


# --- Industry detection patterns ---

_INDUSTRY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\blogistics\b|\bfreight\b|\bsupply\s*chain\b|\bshipping\b|\bcourier\b", re.IGNORECASE), "logistics"),
    (re.compile(r"\bfintech\b|\bfinancial\s*services\b|\bbanking\b|\bpayments\b|\binsurance\b", re.IGNORECASE), "fintech"),
    (re.compile(r"\bhealthcare\b|\bhealth\s*care\b|\bmedical\b|\bhospital\b|\bclinic\b", re.IGNORECASE), "healthcare"),
    (re.compile(r"\bretail\b|\becommerce\b|\be-commerce\b|\bstore\b|\bshop\b|\bwholesale\b", re.IGNORECASE), "retail"),
    (re.compile(r"\bmanufacturing\b|\bmanufacturer\b|\bfactory\b|\bproduction\b|\bindustrial\b", re.IGNORECASE), "manufacturing"),
    (re.compile(r"\bconsulting\b|\blegal\b|\blaw\s*firm\b|\baccounting\b|\bagency\b|\bprofessional\s*services\b", re.IGNORECASE), "professional_services"),
    (re.compile(r"\beducation\b|\bedtech\b|\bschool\b|\buniversity\b|\bcollege\b|\btraining\b", re.IGNORECASE), "education"),
    (re.compile(r"\breal\s*estate\b|\bproperty\b|\brealty\b|\bhousing\b|\bcommercial\s*property\b", re.IGNORECASE), "real_estate"),
]

# --- Business size patterns ---

_SIZE_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(\d+)\s*(?:employee|people|staff|head|worker)", re.IGNORECASE), None, None),  # type: ignore[list-item]
    (re.compile(r"\b(start|solo|freelancer|micro)\b", re.IGNORECASE), "1-10", "1 to 10 employees"),
    (re.compile(r"\b(small\s*team)\b", re.IGNORECASE), "11-50", "11 to 50 employees"),
    (re.compile(r"\b(mid[\-\s]?size|mid[\-\s]?market)\b", re.IGNORECASE), "51-200", "51 to 200 employees"),
    (re.compile(r"\b(enterprise|large\s*team|global|multinational)\b", re.IGNORECASE), "1000+", "Over 1000 employees"),
]

_SIZE_BANDS: list[tuple[int, int, str, str]] = [
    (1, 10, "1-10", "1 to 10 employees"),
    (11, 50, "11-50", "11 to 50 employees"),
    (51, 200, "51-200", "51 to 200 employees"),
    (201, 500, "201-500", "201 to 500 employees"),
    (501, 1000, "501-1000", "501 to 1000 employees"),
    (1001, 999999, "1000+", "Over 1000 employees"),
]

# --- Pain point patterns ---

_PAIN_PATTERNS: list[tuple[re.Pattern, str, list[str]]] = [
    (re.compile(r"\b(manual|repetitive|tedious)\s*(?:data\s+)?entry\b", re.IGNORECASE), "manual_data_entry", ["SVC-AIA"]),
    (re.compile(r"\b(copy[\-\s]?paste|duplicate\s+entry)\b", re.IGNORECASE), "duplicate_data_entry", ["SVC-AIA", "SVC-INT"]),
    (re.compile(r"\b(order\s*(?:processing|management)|invoice\s*(?:matching|processing))\b", re.IGNORECASE), "order_invoice_processing", ["SVC-AIA", "SVC-INT"]),
    (re.compile(r"\b(email|ticket|enquiry|inquiry)\s*(?:triage|overload|flood|volume)\b", re.IGNORECASE), "high_volume_triage", ["SVC-AIA", "SVC-DAT"]),
    (re.compile(r"\b(tools|systems|software)\s*(?:don'?t|do\s*not|doesn'?t)\s*(?:talk|integrate|connect)\b", re.IGNORECASE), "disconnected_tools", ["SVC-INT", "SVC-AIA"]),
    (re.compile(r"\b(manual|hand)\s*(?:reporting|report)\b", re.IGNORECASE), "manual_reporting", ["SVC-DAT", "SVC-INT"]),
    (re.compile(r"\b(spreadsheets?|excel)\s*(?:everywhere|chaos|mess|silo)\b", re.IGNORECASE), "manual_reporting", ["SVC-DAT", "SVC-INT"]),
    (re.compile(r"\b(no|without|lack)\s*(?:single\s+)?source\s*of\s*truth\b", re.IGNORECASE), "no_single_source_of_truth", ["SVC-DAT", "SVC-INT"]),
    (re.compile(r"\b(outdated|old|legacy)\s*(?:website|site|web)\b", re.IGNORECASE), "outdated_website", ["SVC-WEB", "SVC-CON"]),
    (re.compile(r"\b(website|online|web)\s*(?:conversion|traffic|sales)\b", re.IGNORECASE), "poor_web_conversion", ["SVC-WEB", "SVC-CON"]),
    (re.compile(r"\b(customer|client|portal|self[\-\s]?service)\s*(?:app|portal|platform)\b", re.IGNORECASE), "customer_portal_needed", ["SVC-WEB", "SVC-INT"]),
    (re.compile(r"\b(deployment|release|deploy)\s*(?:fragile|unreliable|broken|failed)\b", re.IGNORECASE), "fragile_deployments", ["SVC-CLD", "SVC-CON"]),
    (re.compile(r"\b(cloud|server|infrastructure)\s*(?:cost|spend|bill)\s*(?:high|too\s*much|rising)\b", re.IGNORECASE), "cloud_cost", ["SVC-CLD", "SVC-CON"]),
    (re.compile(r"\b(scaling|scale|grow|growth)\s*(?:problems?|issues?|challenges?)\b", re.IGNORECASE), "scaling_problems", ["SVC-CLD", "SVC-WEB"]),
    (re.compile(r"\b(no\s*roadmap|unclear\s*priority|not\s*sure\s*where\s*to\s*start)\b", re.IGNORECASE), "no_roadmap", ["SVC-CON", "SVC-AIA"]),
    (re.compile(r"\b(want|looking|need)\s*(?:ai|artificial\s*intelligence|machine\s*learning|automation)\b", re.IGNORECASE), "wants_ai", ["SVC-CON", "SVC-AIA"]),
    (re.compile(r"\b(compliance|audit|regulatory|gdpr|hipaa)\s*(?:gap|requirement|need|issue)\b", re.IGNORECASE), "compliance_gaps", ["SVC-CON", "SVC-DAT"]),
    (re.compile(r"\b(data|reporting)\s*(?:trapped|stuck|siloed)\s*(?:in|across)\b", re.IGNORECASE), "data_trapped", ["SVC-DAT", "SVC-INT"]),
]

# --- Goal patterns ---

_GOAL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(automate|automation|reduce\s*manual)\b", re.IGNORECASE), "automation"),
    (re.compile(r"\b(improve|increase)\s*(?:efficiency|productivity|speed)\b", re.IGNORECASE), "improve_efficiency"),
    (re.compile(r"\b(reduce|cut|lower)\s*(?:cost|overhead|spend)\b", re.IGNORECASE), "reduce_costs"),
    (re.compile(r"\b(grow|expand|scale)\s+(?:business|revenue|operations)\b", re.IGNORECASE), "growth"),
    (re.compile(r"\b(digital\s*transform|modernise|modernize)\b", re.IGNORECASE), "digital_transformation"),
    (re.compile(r"\b(better|improve|enhance)\s*(?:customer\s*experience|client\s*satisfaction)\b", re.IGNORECASE), "improve_cx"),
    (re.compile(r"\b(data[\-\s]?driven|insights|analytics|reporting)\b", re.IGNORECASE), "data_driven"),
    (re.compile(r"\b(compliance|audit\s*ready|regulatory)\b", re.IGNORECASE), "compliance"),
]

# --- Tool patterns ---

_TOOL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bexcel\b|\bspreadsheets?\b", re.IGNORECASE), "Excel"),
    (re.compile(r"\b(google\s*sheets|gsheets)\b", re.IGNORECASE), "Google Sheets"),
    (re.compile(r"\boutlook\b", re.IGNORECASE), "Outlook"),
    # Negative lookbehind for @ avoids matching "gmail" inside email addresses
    (re.compile(r"(?<!@)\bgmail\b", re.IGNORECASE), "Gmail"),
    (re.compile(r"\bsalesforce\b|\bcrm\b", re.IGNORECASE), "Salesforce"),
    (re.compile(r"\bhubspot\b", re.IGNORECASE), "HubSpot"),
    (re.compile(r"\bslack\b", re.IGNORECASE), "Slack"),
    (re.compile(r"\bjira\b", re.IGNORECASE), "Jira"),
    (re.compile(r"\btrello\b", re.IGNORECASE), "Trello"),
    (re.compile(r"\basana\b", re.IGNORECASE), "Asana"),
    (re.compile(r"\bquick(?:| )books\b", re.IGNORECASE), "QuickBooks"),
    (re.compile(r"\bsap\b", re.IGNORECASE), "SAP"),
    (re.compile(r"\boracle\b", re.IGNORECASE), "Oracle"),
    (re.compile(r"\berp\b", re.IGNORECASE), "ERP"),
    (re.compile(r"\b(sharepoint|teams)\b", re.IGNORECASE), "Microsoft Teams/SharePoint"),
    (re.compile(r"\bzoho\b", re.IGNORECASE), "Zoho"),
]

# --- Contact extraction patterns ---
# Email regex: requires at least one character before @, a domain with a dot, and a TLD
_CONTACT_EMAIL_PATTERN: re.Pattern = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

_CONTACT_NAME_PATTERNS: list[re.Pattern] = [
    # "Name: John Smith" — lazy capture stops at boundary words or "\nEmail:"
    re.compile(r"(?:name\s*[:\-]?\s*)([A-Za-z .']+?)(?:\s*,\s*|\s+and\s+|\s+email\b|\s+my\s+|\s+is\s+|\s+at\s+|\s+phone\s+|$)", re.IGNORECASE),
    # "my name is John Smith"
    re.compile(r"(?:my\s+name\s+is\s+)([A-Za-z .']+)", re.IGNORECASE),
    # "I'm John Smith"
    re.compile(r"(?:i'?m\s+)([A-Za-z .']+?)(?:\s*,\s*|\s+and\s+|\s+my\s+|\s+the\s+|$)", re.IGNORECASE),
]

# --- Company / organisation extraction patterns ---
# Conservative: only extract when an explicit company-introduction pattern is present.
# Broad patterns like standalone "at X" are excluded to avoid false positives.
_COMPANY_PATTERNS: list[re.Pattern] = [
    # "Company: Swift Freight" or "Company name: Swift Freight"
    re.compile(r"(?:company\s*(?:name)?\s*[:\-]?\s*)([A-Za-z0-9 .'&]+?)(?:\s*[,\.;]|\s+and\s+|\s+is\s+|\s+a\s+|$)", re.IGNORECASE),
    # "We are Swift Freight, a logistics company" / "We're Swift Freight"
    re.compile(r"(?:we'?re|we\s+are)\s+([A-Za-z0-9 .'&]+?)(?:\s*,|\s+i'?m|\s+my\s+|\s+we\s+|\s+the\s+|\s+a\s+|$)", re.IGNORECASE),
    # "I work at Swift Freight" / "I am with Swift Freight" / "I'm at Swift Freight"
    re.compile(r"(?:i\s+(?:work|am)\s+(?:at|with)|i'?m\s+(?:at|with))\s+([A-Za-z0-9 .'&]+?)(?:\s*,|\s+i'?m|\s+my\s+|\s+we\s+|\s+the\s+|\s+a\s+|$)", re.IGNORECASE),
]

# --- Refusal detection ---

_REFUSAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(?:i'?d\s+)?rather\s+not\s+say\b", re.IGNORECASE),
    re.compile(r"\b(?:i'?d\s+)?prefer\s+not\s+to\s+(?:answer|share|disclose|say)\b", re.IGNORECASE),
    re.compile(r"\b(?:that'?s\s+)?private\b", re.IGNORECASE),
    re.compile(r"\b(?:i\s+)?don'?t\s+(?:know|want\s+to\s+share|want\s+to\s+discuss)\b", re.IGNORECASE),
    re.compile(r"\b(?:not\s+)?(?:sure|certain)\s+about\s+(?:budget|timeline|timing)\b", re.IGNORECASE),
    re.compile(r"\bcannot\s+(?:disclose|share|reveal)\b", re.IGNORECASE),
    re.compile(r"\b(?:i\s+)?can'?t\s+(?:say|tell|share)\b", re.IGNORECASE),
]


def _detect_refusal(text: str) -> bool:
    """Check if the message contains a refusal."""
    return any(p.search(text) for p in _REFUSAL_PATTERNS)


def _extract_number(text: str) -> int | None:
    """Extract the first number from text."""
    match = re.search(r"\b(\d{1,3}(?:,\d{3})*|\d+)\b", text.replace(",", ""))
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


class SlotExtractor:
    """Rule-based deterministic slot extractor.

    Extracts discovery slots from visitor messages using pattern matching
    and heuristics. No AI calls.
    """

    def extract(self, message: str, turn_index: int = 0) -> ExtractionResult:
        """Extract discovery slots from a visitor message.

        Args:
            message: The visitor's message text.
            turn_index: The current turn index.

        Returns:
            ExtractionResult with extracted slots.
        """
        result = ExtractionResult(turn_index=turn_index)
        text = message.strip()

        if not text:
            return result

        # Check for refusal signals first
        if _detect_refusal(text):
            # Return empty result — the merger handles marking declined
            return result

        # 1. Extract industry
        industry = self._extract_industry(text)
        if industry:
            result.slots["industry"] = {
                "value": industry,
                "raw": text,
                "confidence": 0.7,
                "source_turn": turn_index,
            }

        # 2. Extract business size
        size_result = self._extract_business_size(text)
        if size_result:
            result.slots["business_size"] = size_result

        # 3. Extract pain points
        pains = self._extract_pain_points(text, turn_index)
        result.pain_points = pains

        # 4. Extract current tools
        tools = self._extract_tools(text)
        result.current_tools = tools

        # 5. Extract goals
        goals = self._extract_goals(text)
        result.goals = goals

        # 6. Extract timeline
        timeline = self._extract_timeline(text)
        if timeline:
            result.slots["timeline"] = timeline

        # 7. Extract budget
        budget = self._extract_budget(text)
        if budget:
            result.slots["budget_band"] = budget

        # 8. Extract decision role
        role = self._extract_decision_role(text)
        if role:
            result.slots["decision_role"] = role

        # 9. Extract contact information
        # Contact extraction only extracts; it does not validate here beyond
        # the email regex pattern requiring a valid-looking email address.
        contact_email = self._extract_contact_email(text)
        if contact_email:
            result.slots["contact_email"] = {
                "value": contact_email,
                "raw": text,
                "confidence": 0.8,
                "source_turn": turn_index,
            }
        contact_name = self._extract_contact_name(text)
        if contact_name:
            result.slots["contact_name"] = {
                "value": contact_name,
                "raw": text,
                "confidence": 0.7,
                "source_turn": turn_index,
            }

        # 10. Extract company / organisation name
        company = self._extract_company(text)
        if company:
            result.slots["contact_company"] = {
                "value": company,
                "raw": text,
                "confidence": 0.6,
                "source_turn": turn_index,
            }

        # Calculate overall extraction confidence
        filled_slots = [s for s in result.slots.values() if s.get("confidence", 0) > 0]
        if filled_slots:
            result.confidence = sum(s.get("confidence", 0) for s in filled_slots) / len(filled_slots)

        return result

    def _extract_industry(self, text: str) -> str | None:
        """Extract industry from text."""
        for pattern, value in _INDUSTRY_PATTERNS:
            if pattern.search(text):
                return value
        return None

    def _extract_business_size(self, text: str) -> dict | None:
        """Extract business size from text."""
        # Try explicit number patterns
        for pattern, val, label in _SIZE_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            if val is None and label is None:
                # Number pattern — extract and map to band
                num_str = match.group(1)
                try:
                    num = int(num_str)
                    for low, high, band, _band_label in _SIZE_BANDS:
                        if low <= num <= high:
                            return {
                                "value": band,
                                "raw": num_str,
                                "confidence": 0.85,
                                "source_turn": 0,
                            }
                except ValueError:
                    continue
            else:
                return {
                    "value": val,
                    "raw": text,
                    "confidence": 0.7,
                    "source_turn": 0,
                }
        return None

    def _extract_pain_points(self, text: str, turn_index: int) -> list[dict[str, Any]]:
        """Extract pain points from text."""
        pains: list[dict[str, Any]] = []
        seen: set[str] = set()

        for pattern, pain_id, service_codes in _PAIN_PATTERNS:
            if pattern.search(text):
                if pain_id not in seen:
                    seen.add(pain_id)
                    pains.append({
                        "id": pain_id,
                        "label": self._pain_id_to_label(pain_id),
                        "raw_text": text,
                        "specificity": "specific",
                        "service_codes": service_codes,
                        "confidence": 0.6,
                        "source_turn": turn_index,
                    })

        # If no structured pain points found but message is substantial,
        # add a generic pain point
        if not pains and len(text.split()) >= 6:
            pains.append({
                "id": "unstructured_pain",
                "label": text[:80] + "..." if len(text) > 80 else text,
                "raw_text": text,
                "specificity": "vague",
                "service_codes": [],
                "confidence": 0.3,
                "source_turn": turn_index,
            })

        return pains

    def _extract_tools(self, text: str) -> list[str]:
        """Extract tool mentions from text."""
        tools: list[str] = []
        seen: set[str] = set()
        for pattern, tool_name in _TOOL_PATTERNS:
            if pattern.search(text) and tool_name not in seen:
                seen.add(tool_name)
                tools.append(tool_name)
        return tools

    def _extract_goals(self, text: str) -> list[str]:
        """Extract goal mentions from text."""
        goals: list[str] = []
        seen: set[str] = set()
        for pattern, goal_id in _GOAL_PATTERNS:
            if pattern.search(text) and goal_id not in seen:
                seen.add(goal_id)
                goals.append(goal_id)
        return goals

    def _extract_timeline(self, text: str) -> dict | None:
        """Extract timeline from text."""
        # Immediate indicators
        if re.search(r"\b(asap|urgent|right\s*now|immediately)\b", text, re.IGNORECASE):
            return {"value": "immediate", "raw": text, "confidence": 0.7, "source_turn": 0}
        # Short term (1-3 months)
        if re.search(r"\b(\d[\s-]*(?:month|week)s?)\s*(?:\s+timeframe|horizon|period)?\b", text, re.IGNORECASE):
            match = re.search(r"\b(\d+)\s*(month|week)", text, re.IGNORECASE)
            if match:
                num = int(match.group(1))
                unit = match.group(2).lower()
                weeks = num * 4.33 if unit == "month" else num
                if weeks <= 12:
                    return {"value": "1-3_months", "raw": text, "confidence": 0.7, "source_turn": 0}
                elif weeks <= 26:
                    return {"value": "3-6_months", "confidence": 0.65, "raw": text, "source_turn": 0}
                else:
                    return {"value": "6-12_months", "confidence": 0.6, "raw": text, "source_turn": 0}
        if re.search(r"\b(next\s*quarter|soon)\b", text, re.IGNORECASE):
            return {"value": "1-3_months", "raw": text, "confidence": 0.6, "source_turn": 0}
        if re.search(r"\b(this\s*year|q[2-4])\b", text, re.IGNORECASE):
            return {"value": "3-6_months", "raw": text, "confidence": 0.6, "source_turn": 0}
        if re.search(r"\b(next\s*year|exploring|considering|evaluating|no\s*rush)\b", text, re.IGNORECASE):
            return {"value": "exploring", "raw": text, "confidence": 0.6, "source_turn": 0}
        return None

    def _extract_budget(self, text: str) -> dict | None:
        """Extract budget from text."""
        if re.search(r"\b(budget|spend|invest|afford)\b", text, re.IGNORECASE):
            numbers = re.findall(r"\b\d+(?:[\d,]*\.?\d*)\s*k\b|\b£?\s*\d+(?:,\d{3})*\s*", text)
            if numbers:
                # Budget mentioned with numbers
                return {"value": "undisclosed", "raw": text, "confidence": 0.4, "source_turn": 0}
            if re.search(r"\b(don'?t\s*know|not\s*sure|undisclosed)\b", text, re.IGNORECASE):
                return {"value": "undisclosed", "raw": text, "confidence": 0.6, "source_turn": 0}
        return None

    def _extract_decision_role(self, text: str) -> dict | None:
        """Extract decision role from text."""
        if re.search(r"\b(owner|founder|ceo|cto|director|head|vp|chief|decision\s*maker)\b", text, re.IGNORECASE):
            return {"value": "decision_maker", "raw": text, "confidence": 0.7, "source_turn": 0}
        if re.search(r"\b(manager|lead|senior|advisor)\b", text, re.IGNORECASE):
            return {"value": "influencer", "raw": text, "confidence": 0.6, "source_turn": 0}
        if re.search(r"\b(analyst|junior|associate|coordinator)\b", text, re.IGNORECASE):
            return {"value": "researcher", "raw": text, "confidence": 0.5, "source_turn": 0}
        return None

    @staticmethod
    def _extract_contact_email(text: str) -> str | None:
        """Extract a valid email address from text.

        The regex requires an @ symbol with a domain containing a dot
        and a top-level domain (e.g. user@example.com). Addresses without
        an @domain pattern (e.g. "akinwandealex9507") are rejected.
        """
        match = _CONTACT_EMAIL_PATTERN.search(text)
        if match:
            return match.group(0)
        return None

    @staticmethod
    def _extract_contact_name(text: str) -> str | None:
        """Extract a contact name from structured patterns.

        Matches patterns like "Name: John Doe", "my name is John Doe",
        or "I'm John Doe". Returns the captured name or None.
        """
        for pattern in _CONTACT_NAME_PATTERNS:
            # Use finditer to scan for all matches in the text.
            # If the first match fails validation (e.g., captures "and"
            # from "your name and email"), the next match may succeed
            # (e.g., "Name: Fakorede Akinwande Alex").
            for match in pattern.finditer(text):
                if match:
                    name = match.group(1).strip()
                    # Reject strings that are clearly not names
                    if name and len(name) >= 2 and len(name) <= 60:
                        # Require at least one uppercase letter to avoid
                        # capturing generic trailing words like "and" or "email"
                        # that get picked up from "your name and email" patterns.
                        if any(c.isupper() for c in name):
                            return name
        return None

    @staticmethod
    def _extract_company(text: str) -> str | None:
        """Extract a company / organisation name from text.

        Conservative extraction — only matches explicit company-introduction
        patterns. The captured name must start with an uppercase letter to
        avoid capturing generic phrases like "a logistics company".

        Matches patterns like "Company: Swift Freight",
        "We are Swift Freight", or "I work at Swift Freight".
        Returns the captured name or None.
        """
        for pattern in _COMPANY_PATTERNS:
            match = pattern.search(text)
            if match:
                company = match.group(1).strip()
                # Reject strings that are clearly not company names
                if company and len(company) >= 2 and len(company) <= 80:
                    # Require uppercase first letter to avoid capturing
                    # generic phrases like "a logistics company"
                    if company[0].isupper():
                        return company
        return None

    @staticmethod
    def _pain_id_to_label(pain_id: str) -> str:
        """Convert a pain point ID to a human-readable label."""
        labels: dict[str, str] = {
            "manual_data_entry": "Manual data entry is time-consuming",
            "duplicate_data_entry": "Duplicate data entry across systems",
            "order_invoice_processing": "Order and invoice processing is manual",
            "high_volume_triage": "High volume of emails or enquiries to triage",
            "disconnected_tools": "Tools and systems don't talk to each other",
            "manual_reporting": "Reporting is manual, data trapped in spreadsheets",
            "no_single_source_of_truth": "No single source of truth for data",
            "outdated_website": "Outdated website needs modernisation",
            "poor_web_conversion": "Website conversion and traffic challenges",
            "customer_portal_needed": "Need a customer portal or self-service platform",
            "fragile_deployments": "Deployments are fragile and unreliable",
            "cloud_cost": "Cloud infrastructure costs are too high",
            "scaling_problems": "Systems struggling to scale with growth",
            "no_roadmap": "No clear technology roadmap or priorities",
            "wants_ai": "Wanting to leverage AI and automation",
            "compliance_gaps": "Compliance and audit trail requirements",
            "data_trapped": "Data is trapped across disconnected systems",
        }
        return labels.get(pain_id, pain_id.replace("_", " ").title())
