Project:
Enterprise AI Consultation Platform

Current Sprint:
Sprint 6.3

Project Status:
Sprint 6 Architecture finalized and approved.

Architecture Principles:

- FastAPI is the AI Orchestration Layer.
- ConsultationOrchestrator remains the deterministic engine.
- LLM integration begins in Sprint 6.3.
- n8n is Business Automation only.
- Frontend never calls AI providers directly.
- AutomationGateway architecture is fixed.
- Provider architecture is protocol-based.
- Dependency Injection is required.
- Existing API contracts must remain stable.
- No architectural redesign is permitted.

Authoritative Documents:

- SPRINT_6_ARCHITECTURE.md
- SYSTEM_ARCHITECTURE.md
- IMPLEMENTATION_STATUS.md
- CONSULTATION_STATE_MACHINE.md
- CONSULTATION_RESPONSE_CONTRACT.md

Documentation Policy:

If inconsistencies exist between documents, identify them but do not resolve them unless implementation is available. The implementation will become the source of truth.