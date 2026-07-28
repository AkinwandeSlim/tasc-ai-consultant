# TASC Build Status

> **Last updated:** 2026-07-28
> **Document authority:** Implementation Constitution, Phase G0 (Governance)

## Build Progress

| Phase | Status | Description |
|-------|--------|-------------|
| **G0 — Repository Foundation** | ✅ **COMPLETE** | Directory structure, root config files, license, gitignore |
| **G1 — Backend Scaffold** | ✅ **COMPLETE** | FastAPI project structure, all __init__.py files, core modules, schemas, domain stubs, infrastructure stubs, resource files, test structure |
| **G2 — Frontend Scaffold** | ✅ **COMPLETE** | Next.js 15 project, TypeScript, Tailwind config, providers, services, types, component stubs, contexts, analysis panel components |
| **G3 — Docker & CI** | ✅ **COMPLETE** | Docker Compose, backend/frontend Dockerfiles, CI workflow |
| **G4 — Documentation** | ✅ **COMPLETE** | README.md, BUILD_STATUS.md, CONTRIBUTING.md |
| **G5 — Sprint 2A: AI Domain Foundation** | ✅ **COMPLETE** | Conversation domain, business domain, lead qualification models, recommendation models, prompt registry, state definitions, simulation framework, configuration, exceptions, tests |
| **G6 — Sprint 3: Consultation Engine** | ✅ **COMPLETE** | Rule-based extraction, deterministic qualification, recommendation engine, conversation services, consultation orchestrator, simulation scenarios, response contract, 140 unit tests |
| **G7 — Sprint 4: API Integration Layer** | ✅ **COMPLETE** | FastAPI REST endpoints, in-memory session store, request/response DTOs, correlation middleware, error handling, health/demo endpoints, 32 API tests |

## What Has Been Created

### Repository Level
- [x] `.gitignore` — comprehensive ignores for Python, Node, IDE, Docker
- [x] `.env.example` — all environment variables with documentation
- [x] `LICENSE` — MIT
- [x] `docker-compose.yml` — full stack (backend, frontend, ChromaDB, n8n)
- [x] `README.md` — project overview with architecture diagram
- [x] `BUILD_STATUS.md` — this file
- [x] `CONTRIBUTING.md` — contribution guidelines
- [x] Directory structure matching blueprints

### Backend (`apps/backend/`)
- [x] `pyproject.toml` — project metadata, dependencies, dev tooling config
- [x] `app/main.py` — FastAPI app creation with middleware, CORS, error handlers
- [x] `app/lifespan.py` — ordered startup/shutdown sequence (S1-S11)
- [x] `app/container.py` — dependency injection container
- [x] `app/core/` — config, constants, exceptions, logging, security, telemetry
- [x] `app/api/` — router, deps, errors, middleware stubs, v1 route stubs
- [x] `app/schemas/` — all Pydantic v2 contracts (requests, responses, events, automation payload)
- [x] `app/domain/` — all domain service stubs with docstrings
- [x] `app/domain/models/` — session, message, slots, score, knowledge models
- [x] `app/orchestration/` — orchestrator, pipeline, stages, event emitter stubs
- [x] `app/infrastructure/` — provider protocols, adapter stubs, repository stubs
- [x] `app/resources/` — prompts (identity, policy, task), catalogue, weights, vocabularies, copy
- [x] `tests/` — conftest, unit tests (config, security), test structure
- [x] `knowledge/` — RAG corpus directory structure with manifest

### Sprint 2A — AI Domain Foundation
- [x] **Conversation Domain Models** — ConversationState, ConversationContext, ConversationHistory, ConversationMetadata, ConversationProgress, ConversationEvent, SessionStatus enum
- [x] **Business Domain Models** — BusinessProfile, Industry, CompanySize, PainPoint, SlotValue, BudgetBand, Timeline, DecisionAuthority, DigitalMaturity, AIReadiness, AIReadinessFactors, BusinessConstraints, PainSpecificity, GrowthStage, TechnicalCapability, Urgency
- [x] **Lead Qualification Domain Models** — LeadScore, LeadQualification, QualificationDimension, QualificationConfidence, QualificationReason, ScoreComponent, ScoringBreakdown
- [x] **Recommendation Domain Models** — Recommendation, RecommendedService, RecommendationReason, RecommendationSummary, Confidence, Priority, RecommendationCategory
- [x] **Conversation State Definitions** — PhaseController with full state machine, PHASE_DEFINITIONS, TRANSITION_RULES, evaluate() for phase transitions, anti-persona override, human request shortcut, wrap-up detection
- [x] **Prompt Registry** — PromptRegistry with manifest loading, template caching, category-based retrieval, FilePromptLoader, PromptRenderer with 5-layer composition (L1-L5), structured prompt support
- [x] **Simulation Framework** — SimulationConfig, Scenario, ScenarioResult, ScenarioRegistry, DefaultScenarioProvider, SimulationFramework with per-turn and full-scenario execution
- [x] **Configuration** — AI settings (AI_PROMPT_MANIFEST_PATH, AI_PROMPT_BASE_PATH, AI_KNOWLEDGE_MANIFEST_PATH, AI_RULESET_VERSION, AI_DEFAULT_TEMPERATURE), simulation settings (SIMULATION_MODE, SIMULATION_SCENARIO_ID, latency/error config)
- [x] **Custom Exceptions** — 18 domain-specific exceptions: ConversationError, PhaseTransitionError, HistoryCompactionError, QualificationError, ScoringError, OverrideEvaluationError, RecommendationError, CandidateGenerationError, RationaleGenerationError, PromptError, PromptNotFoundError, PromptRenderError, ManifestError, KnowledgeError, KnowledgeNotFoundError, ChunkingError, IndexError, SimulationError, ScenarioNotFoundError, SimulationConfigError
- [x] **Tests** — 123 unit tests covering model serialization, validation, configuration, prompt loading, simulation configuration, conversation state definitions, exception hierarchy

### Sprint 3 — Consultation Engine
- [x] **Rule-Based Intent Classification** — 12-class intent taxonomy via keyword/pattern matching: describe_problem, company_question, capability_question, pricing_question, timeline_question, objection, request_human, anti_persona, end_conversation, smalltalk, off_topic, answer_question
- [x] **Rule-Based Slot Extraction** — Deterministic extraction for industry, business size, pain points, current tools, goals, timeline, budget band, decision role using regex patterns and heuristics
- [x] **Value Normalisation** — Maps free-text to controlled vocabularies for industry, business size, timeline, budget band, decision role with confidence scoring
- [x] **Slot Merger** — Merge rules per PRD 13.4: confidence-based overwrite protection, list deduplication, declined slot permanence, conflict recording
- [x] **Deterministic Qualification Engine** — Six scoring components (need_clarity, fit, urgency, budget, authority, engagement) totalling 100 points, band assignment (cold/warm/qualified/hot), 7 override rules (OV-01 to OV-07), qualification confidence calculation
- [x] **Rule-Based Recommendation Engine** — Pain-to-service candidate generation from catalogue mapping, ranking formula with frequency factor/evidence boost/industry boost/constraint penalty, confidence calculation, withholding logic (FR-43), 3-max enforcement, template rationale writing
- [x] **Conversation Manager** — Session creation with static greeting, per-turn message processing, slot extraction orchestration, business profile syncing, phase evaluation, response generation, termination handling
- [x] **Conversation Memory** — Three-tier memory with verbatim window, compaction trigger, token estimation, prompt message assembly
- [x] **Question Selector** — Deterministic selection using scoring_weight × phase_multiplier × recency_penalty, phase-eligible slot constraints, tie-breaking by slot order (PRD 12.6)
- [x] **Completion Detection** — Three triggers: explicit end_conversation, criteria_met (capture phase + contact + commercial resolved), abandonment (idle + 3+ turns)
- [x] **Phase Controller Integration** — Full state machine integration with the existing PhaseController for greeting→discovery→exploration→recommendation→qualification→capture_and_close flow
- [x] **Consultation Orchestrator** — End-to-end turn pipeline: process_turn coordinates extraction → scoring → recommendations → phase evaluation → snapshot building → completion checking
- [x] **SSE Event Emitter** — Phase, token, analysis_snapshot, error, and done event construction with full analysis snapshot builder
- [x] **Pipeline Stage Definitions** — 12 standard stages with parallel groups (intent+extraction), stage types, timeout configs
- [x] **Simulation Scenarios** — 10 realistic scenarios: Logistics Company, Retail Business, Healthcare Clinic, Manufacturing SME, FinTech Startup, Real Estate Agency, Educational Institution, Professional Services Firm, Fast Track Logistics, Human Request
- [x] **Response Contract** — ConsultationResponse model with all required fields: assistant_message, conversation_phase, business_profile, lead_score, recommendations, completion_percentage, next_question
- [x] **Tests** — 140 unit tests covering intent classification, slot extraction, normalisation, merging, phase transitions, scoring components, overrides, recommendation engine, banding, completion detection, memory, conversation manager, orchestrator, simulation scenarios, event emitter, pipeline stages, and end-to-end consultation flow

### Sprint 4 — API Integration Layer
- [x] **In-Memory Session Store** — Abstract SessionRepository interface with InMemorySessionStore, async methods designed for future Redis swap
- [x] **Chat Endpoints** — POST /api/v1/chat/start (201 with session_id + greeting), POST /api/v1/chat/message (full consultation contract), GET /api/v1/chat/{session_id} (state snapshot + message history)
- [x] **Health Endpoint** — GET /api/health with status, version, simulation_mode, timestamp; /api/health/live and /api/health/ready probes
- [x] **Demo Scenarios Endpoint** — GET /api/v1/demo/scenarios listing all simulation scenarios with metadata
- [x] **Request/Response DTOs** — Pydantic models for all API contracts, separate from internal domain models
- [x] **Correlation ID Middleware** — X-Correlation-Id header on all requests/responses with UUID generation
- [x] **Exception Handlers** — Standard error envelope for 400, 404, 422, 500 responses with correlation_id
- [x] **OpenAPI / Swagger** — Auto-generated schema at /api/docs with endpoint summaries and descriptions
- [x] **Dependency Injection** — Singleton providers for ConsultationOrchestrator, ScenarioRegistry, InMemorySessionStore via FastAPI Depends()
- [x] **requirements.txt** — Generated from pyproject.toml for pip-based installation
- [x] **Tests** — 32 API tests covering health, start session, send message, invalid session, anti-persona, completed sessions, session snapshots, demo scenarios, error envelopes, correlation IDs, full consultation flow, concurrent sessions, edge cases

### Frontend (`apps/frontend/`)
- [x] `package.json` — dependencies (Next.js 15, React 19, TanStack Query, etc.)
- [x] `tsconfig.json` — strict TypeScript configuration
- [x] `next.config.ts` — Next.js 15 configuration
- [x] `tailwind.config.ts` — design tokens system
- [x] `postcss.config.js` — PostCSS with Tailwind
- [x] `vitest.config.ts` — test configuration
- [x] `src/app/` — all routes (layout, home, consultation, session, about, error, not-found)
- [x] `src/providers/` — AppProvider, ThemeProvider
- [x] `src/contexts/` — session, conversation, analysis, UI contexts
- [x] `src/services/` — API client, session service, consultation service, SSE parser
- [x] `src/types/` — API DTOs, SSE event types
- [x] `src/lib/` — config, constants, formatting utilities
- [x] `src/utils/` — className helper, assertNever
- [x] `src/components/` — header, lead status, lead score, pain points, recommendations, progress, qualification cards
- [x] `src/features/` — consultation feature composition, copy catalogue
- [x] CSS design tokens system (light + dark mode)

### Automation & Docker
- [x] `automation/n8n/` — workflow directory
- [x] `docker/backend/Dockerfile` (stub)
- [x] `docker/frontend/Dockerfile` (stub)
- [x] `.github/workflows/ci.yml` — CI pipeline

## What Has NOT Been Implemented (by design)

Per the implementation brief, the following are intentionally **not implemented**:
- Chat UI business logic
- AI model integration (OpenAI, embeddings)
- RAG / ChromaDB integration
- OpenAI provider integration
- LLM-based extraction (intent/entity)
- Authentication / authorisation
- Persistent database (PostgreSQL, etc.)
- Streaming / SSE endpoints
- Frontend components
- n8n workflow definitions and dispatcher integration

## Next Steps

### Sprint 5 — AI Integration & Advanced Services
1. **AI**: Integrate OpenAI chat and embedding providers via provider protocol
2. **RAG**: Implement ChromaDB adapter, chunking, embedding pipeline, retrieval service
3. **Advanced Extraction**: LLM-based intent classification, structured slot extraction with repair
4. **Scoring**: Wire configurable weights from resource files into scoring engine
5. **Recommendation**: LLM-based rationale generation instead of templates
6. **Summary**: Implement executive summary generation
7. **Frontend**: Implement SSE streaming, conversation UI, session management
8. **Automation**: Define n8n workflows for Sheets, Gmail, Telegram
9. **Testing**: Integration, contract, and evaluation tests
