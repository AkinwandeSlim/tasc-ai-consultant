"""TASC consultation demo — complete flow through all phases."""

import asyncio
from app.orchestration.orchestrator import ConsultationOrchestrator


async def demo():
    orch = ConsultationOrchestrator()
    session = await orch.start_consultation()
    greeting = session["messages"][0]["content"]

    print("=" * 60)
    print("TASC CONSULTATION DEMO — Swift Freight")
    print("=" * 60)
    print()
    print("--- TURN 0: Greeting ---")
    print(f"Nova: {greeting}")
    print()

    turns = [
        (
            "We are Swift Freight, a logistics company handling deliveries "
            "across Nigeria. We have about 30 employees and manage "
            "500 deliveries per month.",
            "Industry + Size + Pain",
        ),
        (
            "We currently use Excel spreadsheets and WhatsApp to coordinate "
            "orders, drivers, and customers.",
            "Current Tools",
        ),
        (
            "We want to automate order processing and provide customers "
            "with real-time delivery tracking.",
            "Goals",
        ),
        (
            "We need this within the next 3 months — it is urgent.",
            "Timeline",
        ),
        (
            "Our budget is around 15k-20k for the first phase.",
            "Budget",
        ),
        (
            "I am the operations director and will make the decision.",
            "Decision Role",
        ),
        (
            "That sounds great, what do you recommend?",
            "Acknowledge",
        ),
    ]

    for i, (msg, label) in enumerate(turns, 1):
        result = await orch.process_turn(session_state=session, visitor_message=msg)
        sm = session.get("slot_map")
        phase = result.conversation_phase
        score = result.lead_score["score"] if result.lead_score else "?"
        band = result.lead_score["band"] if result.lead_score else "?"

        # Build slot state summary
        slots = []
        if sm:
            if sm.industry.value:
                slots.append(f"industry={sm.industry.value}")
            if sm.business_size.value:
                slots.append(f"size={sm.business_size.value}")
            if sm.current_tools:
                slots.append(f"tools={sm.current_tools}")
            if sm.goals:
                slots.append(f"goals={sm.goals}")
            if sm.timeline.value:
                slots.append(f"timeline={sm.timeline.value}")
            if sm.budget_band.value:
                slots.append(f"budget={sm.budget_band.value}")
            if sm.decision_role.value:
                slots.append(f"decision_role={sm.decision_role.value}")
            if sm.contact_email.value:
                slots.append("contact=captured")
            if sm.pain_points:
                slots.append(f"pain_points={len(sm.pain_points)}")

        print(f"--- TURN {i}: {label} ---")
        print(f"User: {msg}")
        print(f"Phase: {phase}  |  Score: {score}  |  Band: {band}")
        if slots:
            print(f"Slots: {' | '.join(slots)}")
        if result.recommendations:
            for r in result.recommendations:
                print(
                    f"  REC: {r['name']} (rank={r['rank']}, "
                    f"conf={r['confidence_label']})"
                )
        print(f"Nova: {result.assistant_message}")
        print()

    bp = result.business_profile
    print("=" * 60)
    print("FINAL STATE")
    print("=" * 60)
    print(f"Phase: {result.conversation_phase}")
    print(f"Complete: {result.is_complete}")
    if bp:
        print(
            f"Slots filled: {bp.get('total_slots_filled', '?')}/9  "
            f"(core={bp.get('core_slots_filled', '?')}, "
            f"commercial={bp.get('commercial_slots_filled', '?')})"
        )
        print(f"Lead score: {bp.get('lead_score', 'N/A')}")
    print()


if __name__ == "__main__":
    asyncio.run(demo())
