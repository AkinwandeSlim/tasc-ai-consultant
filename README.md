# TASC — Trizen AI Solutions Consultant

[![CI](https://github.com/trizen-ventures/tasc/actions/workflows/ci.yml/badge.svg)](https://github.com/trizen-ventures/tasc/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Selected Problem Statement

**Option 2 — AI Lead Qualification Assistant.**

TASC (Trizen AI Solutions Consultant) is a conversational pre-sales consultant. A website
visitor has a structured multi-turn conversation; the system extracts their business facts,
identifies pain points, scores the lead against a deterministic 100-point rubric, recommends
matching services, and hands the completed consultation to n8n, which logs qualified leads to
Google Sheets and notifies the sales team through Telegram.

A runnable end-to-end demo of the whole flow is in
[`apps/backend/demo_flow.py`](apps/backend/demo_flow.py) — it drives a full Swift Freight
logistics consultation through every phase and prints the transcript.

## How It Works

```
Browser (Next.js 15)
│  REST JSON
▼
FastAPI (Python 3.12+) — AI orchestration layer
│  • intent classification (12-class taxonomy)
│  • slot extraction + normalisation + confidence-based merge
│  • deterministic qualification (6 components / 100 pts, 7 override rules)
│  • recommendation ranking (pain → service catalogue, max 3)
│  • optional LLM layer: natural-language reply + next question only
▼  AutomationGateway (protocol)
│      ├─ MockAutomationGateway   (N8N_ENABLED=false)
│      └─ N8nAutomationGateway    (N8N_ENABLED=true, signed HTTP POST)
▼
n8n — business automation only
webhook → auth + validate → lead gate → branch on qualification
        → Sheets → Telegram → 200 ack
```

### Why the AI lives in FastAPI, not in n8n

This is the one architectural invariant of the project. Qualification scoring must be
**auditable and reproducible** — the same transcript must always produce the same score, and
sales must be able to see which of the six components produced it. That belongs in tested
Python, not in a workflow canvas. n8n is excellent at fan-out, retries, and credential
management, so it does exactly that and nothing else: it receives a decision that has
already been made and executes the business consequences.

### Workflow explanation (`automation/n8n/workflows/tasc_lead_qualification.json`)

| # | Node | Responsibility |
|---|------|----------------|
| 1 | **Consultation Webhook** | `POST /webhook/tasc/consultation`, responds via a response node so FastAPI gets a real ack |
| 2 | **Validate & Normalize** (Code) | Checks the shared-secret header, verifies the HMAC-SHA256 signature (advisory by default), asserts `session_id`/`consultation_id` and a qualification band exist, then flattens the consultation payload. Reads both documented field spellings (`band`/`level`, `conversation.message`/`assistant_message`) so it does not depend on an unreconciled contract. **Computes `shouldCreateLead`** — `true` only when the band is qualified **and** `conversation_finished` **and** a contact name + email were captured. This is the single gate that stops mid-conversation turns from creating duplicate sales events. Failures route to a 400 response. |
| 3 | **Is Lead Qualified?** (IF) | Branches on `is_qualified` (== `shouldCreateLead`). n8n makes no scoring decision of its own. |
| 4 | **Log Lead to Google Sheets** | Appends one row per qualified lead, 16 mapped columns, 3 retries with backoff |
| 5 | **Alert Sales Channel (Telegram)** | Short HTML alert to the team channel; non-blocking (`continueOnFail`) so a Telegram outage cannot fail a logged lead |
| 6 | **Build Acknowledgement** (Code) | Emits `workflow_actions[]` records with `idempotency_key`s so FastAPI can audit what fired |
| 7 | **Respond 200 to FastAPI** | Returns the acknowledgement |
| 8 | **Respond 400 (Rejected)** | Returns a structured rejection on auth/validation failure |

Qualified leads flow Webhook → Validate → IF → **Sheets → Telegram**, then merge into the
acknowledgement. Unqualified or in-progress leads short-circuit to the acknowledgement with a
`skipped` action — nothing is written and nobody is alerted.

**Lead gate behaviour.** FastAPI dispatches every turn, but only the **terminal turn** of a
completed consultation can produce a sales lead. A consultation that reaches a qualified band
mid-conversation (e.g. score 65 on turn 6) produces no Sheets row and no Telegram alert until
the conversation actually finishes and contact has been captured — so exactly **one** sales
event is generated per consultation. Consultations where the visitor declines to share
contact, or that finish below the qualified threshold, never create a lead. The
`idempotency_key` (`${consultationId}::log_lead`) is recorded in the acknowledgement and
written to Sheets, laying the groundwork for retry-safe deduplication.

## AI Model Used

| Layer | What it decides | Implementation |
|-------|-----------------|----------------|
| Deterministic consultation engine | Intent, extracted slots, qualification score and band, service recommendations, phase transitions, completion | Rule/regex/weighted-scoring Python in `app/domain/` — 437 tests |
| LLM layer (optional) | Wording of the assistant's reply and the single next question | Provider-agnostic `ChatProvider` protocol; OpenAI-compatible adapters (OpenAI, OpenRouter, Groq) via configuration, structured output at temperature 0.0 |

The LLM layer is **deterministic-first**: the deterministic engine runs on every turn and the
LLM may only replace two natural-language fields (`assistant_message`, `next_question`). Any
provider timeout, rate limit, transport error, malformed JSON, or schema mismatch falls back
to the deterministic wording. It is gated behind `LLM_ENABLED` and defaults to `false`, so the
whole system runs end to end with no API key.

**Provider-portable LLM layer.** The natural-language generation layer is provider-agnostic.
The application supports OpenAI, OpenRouter, and Groq through a common OpenAI-compatible
adapter. Provider selection is controlled through environment variables rather than being
coupled to the consultation engine:

```env
LLM_ENABLED=true
LLM_PROVIDER=openrouter      # openai | openrouter | groq
LLM_API_KEY=your-key
LLM_MODEL=your-model
LLM_BASE_URL=                # optional — provider default applied when empty
```

The default deterministic engine still runs with `LLM_ENABLED=false` — no API key needed.
The legacy `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `LLM_CHAT_MODEL` spellings are still accepted
as aliases.

**Architecture, precisely.** The deterministic engine owns all decision-making and business
logic (intent, extraction, scoring, recommendation, phases). The LLM layer is language
enhancement only — it may rephrase the reply and pick the next question, never the business
decision. n8n owns business automation only. That separation is what keeps scoring auditable
and the whole system runnable without an API key.

**Not implemented:** RAG, embeddings, and ChromaDB. The `knowledge/` corpus and the vector
store protocol exist but are not wired, so no factual claim in this repo is retrieval-grounded.

## External Integrations

| Service | Reached via | Purpose |
|---------|-------------|---------|
| Google Sheets | n8n | Qualified-lead log (the CRM stand-in) |
| Telegram | n8n | Real-time team alert |
| OpenAI-compatible LLM provider | FastAPI | Optional natural-language generation |

Two external business services, all behind n8n. The frontend never touches any of them.

**Email notification:** Gmail was evaluated during development but is **not part of the final
submitted n8n workflow**. The final demonstration focuses on the working Google Sheets +
Telegram automation path, so no OAuth credential was required for the demonstrated submission.

## Automation

The workflow integrates with the following services:

| Integration | Status | Notes |
|-------------|--------|-------|
| Google Sheets | ✅ Working | Qualified leads logged with 16 mapped columns, 3 retries with backoff |
| Telegram | ✅ Working | Real-time team alerts via the sales channel; non-blocking (`continueOnFail`) so an outage cannot fail a logged lead |

The workflow was validated end-to-end with Google Sheets and Telegram active — qualified,
completed consultations produce exactly one Sheets row and one Telegram alert.

### Payload security

FastAPI signs every dispatch to n8n with HMAC-SHA256 and sends a shared secret alongside it.
The n8n Code node validates both headers. Signature verification is **advisory by default**
(`TASC_N8N_REQUIRE_SIGNATURE=false`) because n8n re-serialises the JSON body before the Code
node sees it; set it to `true` when the n8n host is untrusted.

## Features

- Multi-turn AI business consultation with a persistent business profile built up over the conversation.
- **Deterministic-first architecture** — the deterministic engine always runs first; the LLM (when enabled) enhances only natural-language wording.
- Deterministic lead qualification scoring (6 components, 0–100) and service recommendation (up to 3, ranked).
- Robust slot extraction: contact names, companies, budgets (with `k` suffix handling), tools, and pain points — with conservative validation to avoid false positives.
- **Single-sales-event guarantee** — n8n creates a lead only on a finished, contact-captured, qualified consultation, never on mid-conversation turns.
- Optional LLM layer (`LLM_ENABLED=false` by default) that falls back to deterministic output on any failure.
- Pluggable business-automation dispatch (mock for local development, n8n for production) with signed, retried, idempotent delivery.
- OpenAPI-documented REST API with correlation IDs, structured error envelopes, and health probes.
- Enterprise Next.js frontend with conversation workspace, live analysis panels, and light/dark mode.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.12+), Pydantic v2, httpx |
| Automation | n8n (webhook + Sheets + Telegram) |
| AI reasoning (deterministic) | Rule-based engine: intent classification, slot extraction, scoring, recommendation |
| AI reasoning (optional LLM) | Provider-agnostic `ChatProvider` protocol; OpenAI-compatible adapters (OpenAI, OpenRouter, Groq) |
| Payload security | HMAC-SHA256 signed dispatch between FastAPI and n8n |
| Quality | pytest (437 tests), ruff, mypy --strict |

## Validation and Testing

All quality gates run from `apps/backend/`:

```bash
cd apps/backend
source .venv/Scripts/activate

# Run all tests
pytest tests/ -v                           # 437 tests, ~30s

# Lint
ruff check app/ tests/                     # must pass clean

# Type check
mypy app/ --strict                         # 0 errors

# Run a specific test suite
pytest tests/unit/test_llm_engine.py -v    # 23 LLM engine tests
pytest tests/unit/test_chat_provider.py -v # 17 ChatProvider tests
pytest tests/integration/ -v               # API smoke tests
```

The CI pipeline (`.github/workflows/ci.yml`) runs all three gates on every push.

### Test coverage by area

| Suite | Tests | What it covers |
|-------|-------|----------------|
| Sprint 2A (domain, state machine) | 123 | Models, serialization, validation, configuration, exceptions |
| Sprint 3 (consultation engine) | 163 | Intent, extraction, normalisation, scoring, recommendations, phases, completion, end-to-end |
| REST API | 32 unit + 32 integration | All endpoints, error envelopes, correlation IDs, concurrent sessions |
| Gateway (n8n) | 28 | Mock and N8n gateways, HMAC signing, retry/backoff, error mapping, header contract |
| LLM engine | 23 | Deterministic-first contract, NL-only fields, failure-mode fallbacks, DI wiring |
| Chat provider | 17 | Provider protocol, `OpenAIChatProvider`, structured output, error mapping |
| Provider config & selection | 16 | Generic LLM settings, legacy aliases, OpenAI/OpenRouter/Groq selection |
| Config & security | 3 | Settings loading, secret handling, security helpers |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (optional, for n8n + ChromaDB)

### Backend

```bash
cd apps/backend
cp .env.example .env          # runs fully deterministically with no API keys
pip install -e ".[dev]"
uvicorn app.main:app --reload  # http://localhost:8000
```

Docs: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

### Frontend

```bash
cd apps/frontend
cp .env.example .env.local
npm install
npm run dev                   # http://localhost:3000
```

### Docker (full stack)

```bash
docker compose up -d
```

This brings up the backend (`:8000`), frontend (`:3000`), n8n (`:5678`), and ChromaDB (`:8001`).
The n8n container preloads the workflow from `automation/n8n/workflows/` into its data volume.

### Enabling n8n automation

Set the following in `apps/backend/.env` and in the n8n container environment:

```env
# FastAPI side
N8N_ENABLED=true
N8N_WEBHOOK_URL=http://localhost:5678/webhook/tasc/consultation
N8N_SHARED_SECRET=change-me-shared-secret
N8N_SIGNING_SECRET=change-me-signing-secret

# n8n side (must match)
TASC_N8N_SHARED_SECRET=change-me-shared-secret
TASC_N8N_SIGNING_SECRET=change-me-signing-secret
TASC_N8N_REQUIRE_SIGNATURE=false
TASC_QUALIFIED_BANDS=qualified,hot
TASC_SHEETS_DOCUMENT_ID=your-google-sheet-id
TASC_SHEETS_TAB_NAME=Leads
TASC_TELEGRAM_CHAT_ID=-1000000000000
```

### Enabling the LLM layer

Set the following in `apps/backend/.env`:

```env
LLM_ENABLED=true
LLM_PROVIDER=openai           # openai | openrouter | groq
LLM_API_KEY=sk-...            # provider API key
LLM_MODEL=gpt-4.1-mini        # provider model id
LLM_BASE_URL=                 # optional: override for OpenAI-compatible endpoints
```

Examples for the other providers (all served by the same OpenAI-compatible adapter):

```env
# OpenRouter
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-...
LLM_MODEL=openai/gpt-4o-mini

# Groq
LLM_PROVIDER=groq
LLM_API_KEY=sk-groq-...
LLM_MODEL=llama-3.3-70b-versatile
```

`LLM_BASE_URL` is optional — the provider default is applied when left empty (OpenAI SDK
default, `https://openrouter.ai/api/v1`, or `https://api.groq.com/openai/v1` respectively).

The app will continue to work without these — with `LLM_ENABLED=false` (the default)
the deterministic engine handles every turn end to end.

### Running the consultation demo

```bash
cd apps/backend
source .venv/Scripts/activate
python demo_flow.py
```

## Project Structure

```
├── apps/
│   ├── backend/              # FastAPI application
│   │   ├── app/
│   │   │   ├── api/          # Transport layer (routes, middleware, errors)
│   │   │   ├── core/         # Configuration, exceptions, logging, security
│   │   │   ├── schemas/      # Pydantic v2 boundary contracts
│   │   │   ├── domain/       # Business logic (conversation, extraction,
│   │   │   │                 #   qualification, recommendation)
│   │   │   ├── orchestration/# Turn pipeline sequencing + LLM engine
│   │   │   ├── infrastructure/# Providers (OpenAI), automation gateways,
│   │   │   │                 #   repositories, signing
│   │   │   └── resources/    # Prompts, catalogue, weights, vocabularies
│   │   ├── tests/            # 425 unit + integration tests
│   │   ├── demo_flow.py      # Runnable end-to-end consultation demo
│   │   └── knowledge/        # RAG corpus (markdown, not yet wired)
│   └── frontend/             # Next.js 15 App Router
│       └── src/
│           ├── app/          # Routes, layouts, pages
│           ├── components/   # UI components (conversation, analysis, landing)
│           ├── features/     # Feature composition
│           ├── contexts/     # Client state providers
│           ├── services/     # HTTP + SSE transport
│           ├── types/        # Backend DTO type definitions
│           └── hooks/        # Custom React hooks
├── automation/
│   └── n8n/workflows/        # n8n workflow definitions (lead qualification)
├── docker/                   # Dockerfiles (backend, frontend, nginx)
├── scripts/                  # Utility scripts
├── docs/                     # Product and engineering documentation
└── .github/workflows/        # CI/CD pipelines
```

## Key Documentation

| Document | Purpose |
|----------|---------|
| `docs/01_PRD.md` | Product Requirements Document — the single source of truth |
| `docs/02_Backend_Engineering_Blueprint.md` | Backend architecture and contracts |
| `docs/03_Frontend_Engineering_Blueprint.md` | Frontend architecture and UX specification |
| `docs/04_AI_Automation_Blueprint.md` | AI, RAG, and n8n automation design |
| `docs/05_Implementation_Constitution.md` | Engineering governance and standards |
| `docs/SYSTEM_ARCHITECTURE.md` | End-to-end system architecture and component responsibilities |
| `docs/CONSULTATION_STATE_MACHINE.md` | The phase state machine and transitions |
| `docs/CONSULTATION_RESPONSE_CONTRACT.md` | Backend ↔ frontend response contract |
| `docs/DEPLOYMENT_GUIDE.md` | Deployment, environment variables, and runbooks |
| `docs/MASTER_SYSTEM_PROMPT.md` | The master system prompt for the LLM layer |

## License

MIT — see [LICENSE](LICENSE).
