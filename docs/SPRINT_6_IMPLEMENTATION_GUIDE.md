# Sprint 6 Architecture
## AI Automation Integration

Version: 1.1

Status: Approved

---

# Objective

Sprint 6 transforms the existing consultation platform into a complete AI Automation solution that satisfies the internship assignment requirements.

The objective is **NOT** to redesign the current application.

Instead, Sprint 6 extends the existing architecture by introducing:

- n8n as the Business Automation Platform for downstream workflow execution and external integrations.
- An LLM provider integrated through FastAPI's provider layer to enhance consultation reasoning in later Sprint 6 phases.
- An AutomationGateway abstraction that decouples the application from external automation providers and enables seamless switching between local mock implementations and n8n-based automation.

The existing frontend and FastAPI backend remain intact.

---

# Architecture Philosophy

The platform follows strict separation of responsibilities.

```
Frontend
      │
      ▼
FastAPI Backend  ─── AI Orchestration Layer
      │
      ├──► ConsultationOrchestrator (deterministic engine)
      │       ├── IntentClassifier
      │       ├── SlotExtractor
      │       ├── QualificationEngine
      │       └── RecommendationEngine
      │
      ├──► AutomationGateway (abstraction)
      │       ├── MockAutomationGateway (local, N8N_ENABLED=false)
      │       └── N8nAutomationGateway  (remote, N8N_ENABLED=true)
      │               │
      │               ▼
      │         n8n Workflow ─── Business Automation Layer
      │               │
      │               ▼
      │         Google Sheets, Gmail, Telegram
      │
      └──► LLM Provider (future — Sprint 6.3)
              │
              ▼
         OpenAI (reasoning engine)
```

Core principles:

- The frontend never communicates directly with an LLM.
- The frontend never communicates directly with Google services.
- **FastAPI owns AI orchestration** — all consultation logic, scoring, recommendations, and phase management live in the domain layer.
- **n8n owns business automation only** — it receives a validated payload and fans out to Google Sheets, Gmail, Telegram. No AI calls, no business rules in n8n.
- The LLM (OpenAI) is the **reasoning engine**, invoked by FastAPI via a provider protocol — not by n8n.
- The `AutomationGateway` abstraction (Protocol) lets the system switch between mock (local deterministic engine) and n8n (external) with zero code changes — toggled via `N8N_ENABLED` config.

---

# Consultation Philosophy

The system is **not** a chatbot.

It behaves as an AI Business Consultant.

Every interaction should:

- Understand business context
- Maintain a natural conversation
- Ask intelligent follow-up questions
- Progressively build the business profile
- Assess AI readiness
- Qualify the lead
- Recommend implementation opportunities
- Guide the user through a professional consultation

The user should feel they are speaking with an experienced digital transformation consultant rather than completing a questionnaire.

---

# Final System Architecture

```
                        User
                          │
                          ▼
              Next.js Enterprise UI
                          │
                    REST API Calls
                          │
                          ▼
                  ┌──────────────────┐
                  │  FastAPI Backend  │ ◄── AI Orchestration Layer
                  │                   │
                  │  ┌─────────────┐  │
                  │  │ Consultation│  │
                  │  │ Orchestrator│  │
                  │  │ - Intent    │  │
                  │  │ - Slots     │  │
                  │  │ - Scoring   │  │
                  │  │ - Recs      │  │
                  │  └─────────────┘  │
                  │         │         │
                  │  ┌─────────────┐  │
                  │  │Automation   │  │
                  │  │Gateway      │  │
                  │  │(Protocol)   │  │
                  │  └─────────────┘  │
                  └──────────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
     N8N_ENABLED=false       N8N_ENABLED=true
              │                       │
              ▼                       ▼
    MockAutomationGateway    N8nAutomationGateway
    (local deterministic)    (signed HTTP POST)
              │                       │
              │                       ▼
              │              ┌──────────────────┐
              │              │  n8n Workflow    │ ◄── Business Automation
              │              │  (no AI calls)   │
              │              └──────────────────┘
              │                       │
              │          ┌────────────┼────────────┐
              │          ▼            ▼            ▼
              │    Google Sheets   Gmail       Telegram
              │
              └──► Response returned to frontend
                          │
                          ▼
                  Next.js Enterprise UI
```

---

# Component Responsibilities

## Next.js

Responsible for:

- Enterprise user interface
- Conversation experience
- AI Thinking Panel
- Business Intelligence Dashboard
- Session state
- API consumption
- Responsive UI

The frontend contains **no AI reasoning**.

---

## FastAPI

FastAPI is the **AI Orchestration Layer**.

Responsible for:

- REST API contracts and request validation
- Session management and persistence
- **Consultation orchestration** — coordinating intent classification, slot extraction, lead qualification, and recommendation generation via the existing deterministic engine (ConsultationOrchestrator)
- **Automation Gateway abstraction** — dispatching to MockAutomationGateway (local, N8N_ENABLED=false) or N8nAutomationGateway (signed HTTP POST to n8n, N8N_ENABLED=true) with zero code change
- Error handling and structured error envelopes
- Future LLM provider integration (OpenAI, etc., via provider protocol — Sprint 6.3)
- Future RAG retrieval (ChromaDB — Sprint 6.3)

FastAPI is **not responsible** for business automation (Sheets, Gmail, Telegram) — those belong to the n8n layer.

---

## n8n

n8n is the **Business Automation Layer**.

It does **not** perform AI reasoning, orchestrate the consultation, or invoke an LLM.

Responsibilities:

- Receive a validated consultation payload via signed HTTP POST from the N8nAutomationGateway
- Fan out to downstream services:
  - Google Sheets (log leads — Sprint 6.4)
  - Gmail (sales briefing, visitor confirmation — Sprint 6.5)
  - Telegram (team notifications — Sprint 6.5)
- Return an acknowledgement to FastAPI (the consultation response itself is built by FastAPI)
- Handle idempotency (409 on duplicate requests treated as success)

n8n receives a fully structured payload — no AI calls, no business rules, no prompt engineering.
All AI reasoning lives in FastAPI's domain layer.

---

## LLM

The LLM (OpenAI) is the **Reasoning Engine**, invoked by FastAPI through a provider protocol.

Responsibilities include:

- Understanding business context and holding natural conversation
- Asking intelligent follow-up questions to progressively build the business profile
- Extracting structured business information from unstructured dialogue
- Assessing AI readiness and evaluating lead quality
- Generating implementation recommendations
- Producing professional business responses with structured outputs

The LLM never communicates directly with the frontend or with n8n.
It is called by FastAPI's provider layer and returns a structured response that FastAPI maps into the ConsultationResult contract.

**Note:** LLM integration is scheduled for Sprint 6.3. In Sprint 6.1–6.2, FastAPI uses its deterministic consultation engine (ConsultationOrchestrator) for all AI reasoning.

---

# Existing Components

The following components remain unchanged.

✅ Enterprise Frontend

✅ FastAPI API Layer

✅ Conversation Workspace

✅ AI Thinking Panel

✅ Business Intelligence Dashboard

✅ Session Management

✅ Analysis Components

These continue operating exactly as implemented.

---

# Runtime Flow

## Default Path (N8N_ENABLED=false — development/testing)

1. User opens the consultation platform.

↓

2. Frontend calls `POST /api/v1/chat/start`.

↓

3. FastAPI creates a session via `ConsultationOrchestrator.start_consultation()`, returns a greeting.

↓

4. User submits a message via `POST /api/v1/chat/message`.

↓

5. FastAPI validates the request and resolves the session.

↓

6. `MockAutomationGateway.process_consultation()` delegates to the `ConsultationOrchestrator`:

   - IntentClassifier classifies the message (12-class taxonomy)
   - SlotExtractor extracts business information (industry, budget, pain points, etc.)
   - Normaliser maps free-text to controlled vocabularies
   - SlotMerger merges into the existing business profile
   - QualificationEngine scores the lead (6 components, 0-100)
   - RecommendationEngine matches pain to services (max 3)
   - PhaseController evaluates state machine transitions
   - CompletionDetector checks for end conditions

↓

7. FastAPI returns the `ConsultationResult` to the frontend.

↓

8. Frontend updates conversation, business profile, lead score, recommendations, and all analysis panels.

## n8n Path (N8N_ENABLED=true — production)

1-5. Same as default path.

↓

6. `N8nAutomationGateway.process_consultation()` builds a signed payload (HMAC-SHA256) and POSTs to the n8n webhook.

↓

7. n8n validates the request (shared secret + signature), fans out to business automations:

   - Google Sheets: log the lead (Sprint 6.4)
   - Gmail: send sales briefing / visitor confirmation (Sprint 6.5)
   - Telegram: team notification (Sprint 6.5)

↓

8. n8n returns an acknowledgement to FastAPI.

↓

9. FastAPI returns the response to the frontend.

↓

10. Frontend updates all UI panels.

**Note:** The consultation response itself (assistant message, lead score, recommendations) is built by FastAPI's domain layer in both paths. n8n handles only downstream business automation.

---

# Consultation Response Contract

Every consultation request returns a **Consultation Response Object**.

During Sprint 6.1–6.2 the object is produced by the deterministic `ConsultationOrchestrator`.

Beginning in Sprint 6.3, the LLM provider will produce structured reasoning outputs that FastAPI maps into the same `Consultation Response Object`.

This guarantees a stable API contract regardless of the underlying consultation engine.

Example

```json
{
  "assistant_message": "Thank you for sharing that. Since your inventory is managed manually across multiple warehouses, I'd like to understand your current operational scale. Approximately how many warehouse locations do you operate?",

  "conversation": {
    "stage": "DISCOVERY",
    "should_continue": true,
    "completion_percentage": 35,
    "next_question": "How many warehouse locations do you operate?"
  },

  "business_profile": {
    "industry": "Logistics",
    "company_size": "SME",
    "pain_points": [
      "Manual inventory management"
    ],
    "business_goals": [
      "Reduce operational costs"
    ],
    "current_systems": [],
    "budget": null,
    "timeline": null,
    "decision_maker": null
  },

  "lead_qualification": {
    "score": 45,
    "level": "Warm",
    "confidence": 0.82
  },

  "recommendations": [
    {
      "service": "Inventory Automation",
      "priority": "High",
      "reason": "Manual inventory processes present a strong automation opportunity."
    }
  ],

  "workflow_actions": {
    "save_to_google_sheets": true,
    "notify_sales": false,
    "send_followup_email": false
  },

  "metadata": {
    "model": "gpt-4.1",
    "timestamp": "ISO8601"
  }
}
```

The assistant message should always read naturally.

The structured sections enable the frontend dashboard and automation workflows.

---

# External Integrations

Sprint 6 introduces or prepares integration with:

✅ n8n Business Automation

⬜ OpenAI Provider (Sprint 6.3)

⬜ Google Sheets Automation (Sprint 6.4)

⬜ Gmail Notifications (Sprint 6.5)

These satisfy the internship assignment requirements.

---

# Existing Qualification Engine

The deterministic ConsultationOrchestrator remains the primary consultation engine throughout Sprint 6.1 and Sprint 6.2.

It is responsible for:

- Intent classification
- Business profile extraction
- Slot normalization and merging
- Consultation phase management
- Lead qualification
- Recommendation generation
- Consultation completion detection

This preserves the existing production implementation and provides deterministic, testable consultation behaviour.

Beginning in Sprint 6.3, an LLM provider will be integrated through FastAPI's provider abstraction to enhance conversational reasoning and natural language understanding.

The deterministic engine will continue to exist as a fallback, validation layer, and audit mechanism, enabling hybrid AI workflows and ensuring predictable system behaviour even when an external LLM is unavailable.

---

# Future Enhancements

The following capabilities are intentionally outside the scope of Sprint 6 and may be introduced in future releases:

- Advanced RAG architectures beyond the initial implementation
- Production-scale vector search and retrieval optimization
- Streaming responses
- Redis caching
- Authentication and authorization
- Multi-user sessions
- Voice interface
- WhatsApp integration
- Slack integration
- CRM integrations
- Additional LLM providers
- Advanced analytics and monitoring

These enhancements can be introduced without requiring architectural changes because the current architecture is designed around protocol abstractions and clear separation of responsibilities.

---

# Success Criteria

Sprint 6 is delivered incrementally across sub-sprints:

## Sprint 6.1 — FastAPI → n8n Gateway ✅

✅ `AutomationGateway` Protocol defined with typed request/response contracts

✅ `MockAutomationGateway` wraps the local `ConsultationOrchestrator` (N8N_ENABLED=false)

✅ `N8nAutomationGateway` forwards signed payloads to n8n webhook (N8N_ENABLED=true)

✅ HMAC-SHA256 payload signing with constant-time verification

✅ Exponential backoff retry with jitter (configurable max_retries, timeout)

✅ Gateway error hierarchy: `GatewayConnectionError`, `GatewayTimeoutError`, `GatewayInvalidResponseError`, `GatewayRejectedError`

✅ Dependency injection via `N8N_ENABLED` config — switch between mock and n8n with zero code change

✅ Config validation — requires `N8N_WEBHOOK_URL` when `N8N_ENABLED=true`

✅ 32 comprehensive gateway tests (protocol, mock, n8n, DI, signing, API integration)

## Sprint 6.2 — n8n Workflow Definition ⬜

⬜ n8n webhook trigger with payload validation

⬜ Idempotency and retry handling in n8n

⬜ n8n Docker container wired to existing `docker-compose.yml`

## Sprint 6.3 — LLM Integration ⬜

⬜ OpenAI chat provider wired via provider protocol

⬜ OpenAI embedding provider wired for RAG

⬜ ChromaDB vector store integration

⬜ LLM-augmented consultation (natural conversation, enhanced extraction)

## Sprint 6.4 — Google Sheets Automation ⬜

⬜ n8n Sheets node configured for lead logging

⬜ Validated payload fields mapped to sheet columns

## Sprint 6.5 — Gmail Notifications ⬜

⬜ n8n Gmail node for sales briefing email

⬜ n8n Gmail node for visitor confirmation email

## Sprint 6.6 — End-to-End Testing ⬜

⬜ Full integration tests (FastAPI → n8n → Sheets → Gmail)

⬜ Contract tests (ConsultationRequest ↔ ConsultationResult fields)

⬜ Evaluation tests (lead scoring accuracy, recommendation relevance)

No additional architectural changes should be introduced after Sprint 6 begins.