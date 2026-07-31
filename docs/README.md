# README.md — Sections to Update

**Note:** This is not a full README rewrite. These are the specific sections that should be updated or inserted into the existing `README.md` to reflect Sprint 6. Insert each under its existing heading, or add the heading if it doesn't yet exist.

---

## Architecture Overview

The system follows a strict separation of responsibilities, finalized in Sprint 6:

- **Next.js frontend** — the enterprise UI, conversation workspace, AI Thinking Panel, and Business Intelligence Dashboard. Contains no AI reasoning and never communicates directly with an LLM or with Google services.
- **FastAPI backend** — the AI Orchestration Layer. Owns consultation orchestration, intent classification, slot extraction, lead qualification, and recommendation generation, currently via a deterministic engine (`ConsultationOrchestrator`), with LLM-augmented reasoning planned for Sprint 6.3 through a provider abstraction.
- **AutomationGateway** — a Protocol-based abstraction that lets the backend dispatch completed consultations to either a `MockAutomationGateway` (local, for development) or an `N8nAutomationGateway` (signed HTTP POST to n8n, for production), switched entirely by the `N8N_ENABLED` environment variable with zero code changes.
- **n8n** — the Business Automation Layer. Performs no AI reasoning; receives a validated, signed payload and fans out to Google Sheets, Gmail, and Telegram.

Full detail: [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) and the Sprint 6 Architecture document.

## Features

- Multi-turn AI business consultation with a persistent business profile built up over the conversation.
- Deterministic lead qualification scoring (6 components, 0–100) and service recommendation (up to 3, ranked).
- Pluggable business-automation dispatch (mock for local development, n8n for production) with signed, retried, idempotent delivery.
- Planned: LLM-augmented natural-language reasoning (Sprint 6.3), Google Sheets lead logging (Sprint 6.4), Gmail and Telegram notifications (Sprint 6.5).

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js |
| Backend | FastAPI (Python) |
| Automation | n8n |
| Reasoning (current) | Deterministic `ConsultationOrchestrator` |
| Reasoning (planned, Sprint 6.3) | OpenAI, via FastAPI's provider abstraction, with ChromaDB for RAG |
| Payload security | HMAC-SHA256 signed dispatch between FastAPI and n8n |

## Project Structure

```
├── frontend/               # Next.js enterprise UI
├── backend/                 # FastAPI — AI Orchestration Layer
│   ├── orchestrator/         # ConsultationOrchestrator, PhaseController, CompletionDetector
│   ├── understanding/          # IntentClassifier, SlotExtractor, Normaliser, SlotMerger
│   ├── qualification/            # QualificationEngine
│   ├── recommendation/             # RecommendationEngine
│   └── gateway/                      # AutomationGateway protocol, Mock and N8n implementations
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── IMPLEMENTATION_STATUS.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── SPRINT_6_ARCHITECTURE.md
│   ├── MASTER_SYSTEM_PROMPT.md
│   ├── CONSULTATION_STATE_MACHINE.md
│   └── CONSULTATION_RESPONSE_CONTRACT.md
```

(Adjust paths above to match the actual repository layout — this reflects the logical structure described in the Sprint 6 Architecture document, not a verified file tree.)

## Getting Started

1. Install frontend and backend dependencies.
2. Set `N8N_ENABLED=false` for local development (no n8n instance required — see [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md), Section 7, Running Mock Mode).
3. Start the FastAPI backend, then the frontend, pointing the frontend at the backend's API base URL.
4. Open the frontend and start a consultation via `POST /api/v1/chat/start`.

Full setup, environment variables, and production configuration: [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md).

## Current Sprint Status

**Sprint 6.1 — FastAPI → n8n Gateway: Complete.** The `AutomationGateway` abstraction, both implementations, signed dispatch, retry/backoff, and the full gateway test suite are done. Sprints 6.2 through 6.6 (n8n workflow, LLM integration, Google Sheets, Gmail/Telegram, end-to-end testing) have not started.

Full status and completion tracking: [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md).

## Roadmap

| Sub-sprint | Scope | Status |
|---|---|---|
| 6.1 | FastAPI → n8n Gateway | ✅ Complete |
| 6.2 | n8n Workflow Definition | ⬜ Planned |
| 6.3 | LLM Integration | ⬜ Planned |
| 6.4 | Google Sheets Automation | ⬜ Planned |
| 6.5 | Gmail + Telegram Notifications | ⬜ Planned |
| 6.6 | End-to-End Testing | ⬜ Planned |

## Documentation Links

- [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) — architecture entry point
- [`docs/SPRINT_6_ARCHITECTURE.md`](docs/SPRINT_6_ARCHITECTURE.md) — authoritative Sprint 6 architecture specification
- [`docs/MASTER_SYSTEM_PROMPT.md`](docs/MASTER_SYSTEM_PROMPT.md) — production LLM system prompt (Sprint 6.3)
- [`docs/CONSULTATION_STATE_MACHINE.md`](docs/CONSULTATION_STATE_MACHINE.md) — consultation stage logic
- [`docs/CONSULTATION_RESPONSE_CONTRACT.md`](docs/CONSULTATION_RESPONSE_CONTRACT.md) — response object schema *(pending reconciliation against the Sprint 6 Architecture document's worked example — see `IMPLEMENTATION_STATUS.md`, Section 8)*
- [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) — current build status and roadmap
- [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md) — running and deploying the system