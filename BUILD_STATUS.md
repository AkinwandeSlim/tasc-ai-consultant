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
- API endpoint handlers (route bodies)
- AI model integration (OpenAI, embeddings) — Sprint 2B
- RAG / ChromaDB integration — Sprint 2B
- Recommendation algorithms — Sprint 2B
- Lead scoring algorithms — Sprint 2B
- Intent classification and slot extraction — Sprint 2B
- Summary generation — Sprint 2B
- Session persistence — Sprint 2B
- n8n workflow definitions — Sprint 2B
- n8n dispatcher integration — Sprint 2B
- Frontend SSE streaming — Sprint 2B

## Next Steps

### Sprint 2B — AI Integration & Business Logic
1. **Backend**: Implement API route handlers for sessions, messages, consultations
2. **AI**: Integrate OpenAI chat and embedding providers
3. **RAG**: Implement ChromaDB adapter, chunking, embedding pipeline, retrieval service
4. **Extraction**: Implement intent classification, slot extraction, normalisation, merging
5. **Scoring**: Implement deterministic scoring engine with component maths and overrides
6. **Recommendation**: Implement candidate builder, ranker, rationale generator
7. **Frontend**: Implement SSE streaming, conversation UI, session management
8. **Automation**: Define n8n workflows for Sheets, Gmail, Telegram
9. **Testing**: Integration, contract, and evaluation tests
