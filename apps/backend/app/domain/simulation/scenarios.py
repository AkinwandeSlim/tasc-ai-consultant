"""Simulation scenarios — realistic consultation scenarios for testing.

8+ scenarios covering diverse industries, business sizes, and pain points.
Each scenario defines the expected conversation flow, extracted slots,
score bands, and recommendations.

References: PRD Section 8, AI Blueprint Section 2
"""

from __future__ import annotations

from typing import Any

from app.domain.simulation.framework import Scenario

# =============================================================================
# Scenario 1: Logistics Company
# =============================================================================

LOGISTICS_SCENARIO = Scenario(
    scenario_id="logistics_company",
    name="Logistics Company - Order Processing Automation",
    description="A logistics company with 180 employees struggling with manual order processing",
    tags=["logistics", "mid-market", "automation", "recommended"],
    turn_count=8,
    initial_phase="greeting",
    responses=[
        "We run a logistics company and our order processing is all manual.",
        "About 180 staff, maybe 12 in operations doing this daily.",
        "Email, Excel, and an old ERP that nobody trusts.",
        "Invoice matching. Takes two people three days a week.",
        "What does that involve?",
        "That sounds about right. When can you start?",
        "We'd want this live before Q4. Budget is probably 30 to 40k.",
        "Chidi Okafor, chidi@northline-logistics.example.com, Northline Logistics",
    ],
    expected_slots={
        "industry": "logistics",
        "business_size": "51-200",
        "pain_points": ["manual_order_processing", "invoice_matching"],
        "current_tools": ["Email", "Excel", "ERP"],
        "timeline": "3-6_months",
        "budget_band": "15k-50k",
        "decision_role": "decision_maker",
    },
    expected_band="qualified",
    expected_score=74,
    metadata={
        "company": "Northline Logistics",
        "revenue_band": "£10M-50M",
        "pain_focus": "operational_efficiency",
    },
)

# =============================================================================
# Scenario 2: Retail Business
# =============================================================================

RETAIL_SCENARIO = Scenario(
    scenario_id="retail_business",
    name="Retail Business - E-commerce Platform",
    description="A growing retail business needing a modern e-commerce platform",
    tags=["retail", "growing", "ecommerce", "development"],
    turn_count=7,
    initial_phase="greeting",
    responses=[
        "We run an online retail store and our current website is really outdated.",
        "We have about 25 employees, mostly in warehouse and customer service.",
        "We use Shopify but it's limited for what we need now.",
        "Customers can't track orders properly and our conversion rate is dropping.",
        "We want a proper customer portal and better analytics.",
        "Looking to start in the next 3 months. Budget around 20-30k.",
        "Sarah Chen, sarah@bloomretail.example.com, Bloom Retail",
    ],
    expected_slots={
        "industry": "retail",
        "business_size": "11-50",
        "pain_points": ["outdated_website", "customer_portal_needed"],
        "current_tools": ["Shopify"],
        "timeline": "1-3_months",
        "budget_band": "15k-50k",
    },
    expected_band="warm",
    expected_score=55,
    metadata={
        "company": "Bloom Retail",
        "pain_focus": "digital_presence",
    },
)

# =============================================================================
# Scenario 3: Healthcare Clinic
# =============================================================================

HEALTHCARE_SCENARIO = Scenario(
    scenario_id="healthcare_clinic",
    name="Healthcare Clinic - Data Integration",
    description="A multi-location healthcare clinic with disconnected systems",
    tags=["healthcare", "mid-market", "integration", "data"],
    turn_count=8,
    initial_phase="greeting",
    responses=[
        "We're a healthcare clinic with three locations. Our systems don't talk to each other.",
        "About 120 staff across all locations.",
        "We use different EHR systems at each clinic and patient data is scattered.",
        "Reporting is manual — someone spends two days a week pulling data together.",
        "We need a single source of truth for patient records and operations.",
        "Compliance is a big concern, especially with GDPR and data protection.",
        "We'd like to get started within 6 months. Budget is flexible, maybe 50-80k.",
        "Dr. James Wilson, j.wilson@cityhealth.example.com, City Health Clinics",
    ],
    expected_slots={
        "industry": "healthcare",
        "business_size": "51-200",
        "pain_points": ["disconnected_tools", "manual_reporting", "no_single_source_of_truth"],
        "current_tools": ["EHR"],
        "timeline": "3-6_months",
        "budget_band": "50k-100k",
        "decision_role": "decision_maker",
    },
    expected_band="qualified",
    expected_score=76,
    metadata={
        "company": "City Health Clinics",
        "pain_focus": "data_integration",
    },
)

# =============================================================================
# Scenario 4: Manufacturing SME
# =============================================================================

MANUFACTURING_SCENARIO = Scenario(
    scenario_id="manufacturing_sme",
    name="Manufacturing SME - Production Analytics",
    description="A manufacturing company wanting data-driven production insights",
    tags=["manufacturing", "data", "analytics"],
    turn_count=6,
    initial_phase="greeting",
    responses=[
        "We're a manufacturing company producing automotive parts. Production data is all over the place.",
        "Around 350 employees across two factories.",
        "We track everything in Excel spreadsheets that don't connect to our ERP.",
        "No real-time visibility into production efficiency or quality metrics.",
        "We want a data platform that gives us dashboards and alerts.",
        "Looking at a 6-12 month timeline for a full rollout. Budget around 60k.",
    ],
    expected_slots={
        "industry": "manufacturing",
        "business_size": "201-500",
        "pain_points": ["manual_reporting", "no_single_source_of_truth"],
        "current_tools": ["Excel", "ERP"],
        "timeline": "6-12_months",
        "budget_band": "50k-100k",
    },
    expected_band="warm",
    expected_score=52,
    metadata={
        "company": "Precision Auto Parts Ltd",
        "pain_focus": "data_analytics",
    },
)

# =============================================================================
# Scenario 5: FinTech Startup
# =============================================================================

FINTECH_SCENARIO = Scenario(
    scenario_id="fintech_startup",
    name="FinTech Startup - Platform Development",
    description="A fintech startup needing a production-grade platform built quickly",
    tags=["fintech", "startup", "development", "cloud"],
    turn_count=7,
    initial_phase="greeting",
    responses=[
        "We're a fintech startup building a payment processing platform.",
        "8 people — mostly engineers and product.",
        "We need a production-grade platform built before our seed round closes.",
        "Currently using basic cloud setup but deployments are fragile and slow.",
        "We need proper cloud infrastructure and a solid web platform.",
        "Timeline is ASAP — we're aiming for launch in 8 weeks. Budget is 40-60k.",
        "Amara Obi, amara@paysprint.example.com, PaySprint Technologies",
    ],
    expected_slots={
        "industry": "fintech",
        "business_size": "1-10",
        "pain_points": ["fragile_deployments", "scaling_problems"],
        "current_tools": [],
        "timeline": "immediate",
        "budget_band": "50k-100k",
        "decision_role": "decision_maker",
    },
    expected_band="qualified",
    expected_score=65,
    metadata={
        "company": "PaySprint Technologies",
        "pain_focus": "infrastructure_scaling",
    },
)

# =============================================================================
# Scenario 6: Real Estate Agency
# =============================================================================

REAL_ESTATE_SCENARIO = Scenario(
    scenario_id="real_estate_agency",
    name="Real Estate Agency - Digital Transformation",
    description="A real estate agency looking to modernise its digital operations",
    tags=["real_estate", "digital_transformation", "web"],
    turn_count=5,
    initial_phase="greeting",
    responses=[
        "We're a real estate agency and our online presence is really dated.",
        "About 45 agents and office staff.",
        "Our website doesn't have proper property search or virtual tours.",
        "We're losing listings to agencies with better digital platforms.",
        "We need a roadmap for digital transformation but not sure where to start.",
    ],
    expected_slots={
        "industry": "real_estate",
        "business_size": "11-50",
        "pain_points": ["outdated_website", "no_roadmap"],
        "current_tools": [],
    },
    expected_band="cold",
    expected_score=28,
    metadata={
        "company": "Premier Properties",
        "pain_focus": "digital_transformation",
    },
)

# =============================================================================
# Scenario 7: Educational Institution
# =============================================================================

EDUCATION_SCENARIO = Scenario(
    scenario_id="educational_institution",
    name="Educational Institution - Systems Integration",
    description="A university needing to integrate its student management and learning systems",
    tags=["education", "integration", "data"],
    turn_count=7,
    initial_phase="greeting",
    responses=[
        "We're a university with disconnected student systems across departments.",
        "About 500 staff supporting 5000 students.",
        "Student records, timetabling, and the LMS all run on separate platforms.",
        "Data entry is duplicated everywhere and reporting takes weeks.",
        "We need systems integration and better data analytics.",
        "Looking at a phased rollout over 6-12 months. Budget is significant.",
        "Prof. Michael Adebayo, m.adebayo@cityuniversity.example.com, City University",
    ],
    expected_slots={
        "industry": "education",
        "business_size": "501-1000",
        "pain_points": ["disconnected_tools", "manual_reporting", "duplicate_data_entry"],
        "current_tools": ["LMS"],
        "timeline": "6-12_months",
        "decision_role": "decision_maker",
    },
    expected_band="warm",
    expected_score=52,
    metadata={
        "company": "City University",
        "pain_focus": "systems_integration",
    },
)

# =============================================================================
# Scenario 8: Professional Services Firm
# =============================================================================

PROFESSIONAL_SERVICES_SCENARIO = Scenario(
    scenario_id="professional_services_firm",
    name="Professional Services Firm - AI Readiness",
    description="A consulting firm exploring AI automation for their operations",
    tags=["professional_services", "ai", "automation", "strategy"],
    turn_count=6,
    initial_phase="greeting",
    responses=[
        "We're a management consulting firm and we want to explore AI for our internal processes.",
        "Around 200 consultants and support staff.",
        "We have a lot of manual report generation and proposal writing that takes up time.",
        "We're not sure where AI would have the most impact for us.",
        "We need someone to help us figure out the right AI use cases and build a roadmap.",
        "Timeline is exploring — we want to understand options first. Budget TBD.",
    ],
    expected_slots={
        "industry": "professional_services",
        "business_size": "51-200",
        "pain_points": ["no_roadmap", "wants_ai"],
        "current_tools": [],
        "timeline": "exploring",
    },
    expected_band="cold",
    expected_score=27,
    metadata={
        "company": "McKinley Consulting Group",
        "pain_focus": "ai_strategy",
    },
)

# =============================================================================
# Scenario 9: Fast Track (everything in one message)
# =============================================================================

FAST_TRACK_SCENARIO = Scenario(
    scenario_id="fast_track_logistics",
    name="Fast Track - Logistics with Full Context",
    description="A visitor who provides all relevant information in the first message",
    tags=["logistics", "fast_track", "automation", "recommended"],
    turn_count=4,
    initial_phase="greeting",
    responses=[
        "We're a logistics company with 180 employees. Our manual order and invoice processing "
        "is costing us days of labour every week. We use Excel and email. We need automation "
        "and want to start within 3 months with a budget of 30-40k. I'm the operations director.",
        "Yes, invoice matching is our biggest bottleneck.",
        "AI Automation sounds like exactly what we need. How quickly can you start?",
        "Chidi Okafor, chidi@northline.example.com, Northline Logistics",
    ],
    expected_slots={
        "industry": "logistics",
        "business_size": "51-200",
        "pain_points": ["manual_order_processing", "invoice_matching"],
        "current_tools": ["Excel", "Email"],
        "timeline": "1-3_months",
        "budget_band": "15k-50k",
        "decision_role": "decision_maker",
    },
    expected_band="qualified",
    expected_score=85,
    metadata={
        "company": "Northline Logistics (Fast Track)",
        "pain_focus": "automation",
    },
)

# =============================================================================
# Scenario 10: Human Request
# =============================================================================

HUMAN_REQUEST_SCENARIO = Scenario(
    scenario_id="human_request",
    name="Human Request - Immediate Human Escalation",
    description="A visitor who immediately requests to speak to a human",
    tags=["human_request", "escalation"],
    turn_count=3,
    initial_phase="greeting",
    responses=[
        "Hi, I need to speak to a human about a potential project.",
        "It's about cloud infrastructure migration for our fintech company.",
        "David Kim, david@finscale.example.com, FinScale Technologies",
    ],
    expected_slots={
        "industry": "fintech",
    },
    expected_band="qualified",
    expected_score=0,
    metadata={
        "override": "human_request",
    },
)

# =============================================================================
# Register all scenarios
# =============================================================================

DEFAULT_SCENARIOS: list[Scenario] = [
    LOGISTICS_SCENARIO,
    RETAIL_SCENARIO,
    HEALTHCARE_SCENARIO,
    MANUFACTURING_SCENARIO,
    FINTECH_SCENARIO,
    REAL_ESTATE_SCENARIO,
    EDUCATION_SCENARIO,
    PROFESSIONAL_SERVICES_SCENARIO,
    FAST_TRACK_SCENARIO,
    HUMAN_REQUEST_SCENARIO,
]


def register_default_scenarios(registry: Any) -> None:
    """Register all default scenarios into a ScenarioRegistry.

    Args:
        registry: The ScenarioRegistry instance to register into.
    """
    for scenario in DEFAULT_SCENARIOS:
        registry.register(scenario)
