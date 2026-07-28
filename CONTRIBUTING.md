# Contributing to TASC

## Governance

TASC is governed by the **Engineering Constitution** (`docs/05_Implementation_Constitution.md`). All contributors MUST read and follow it.

**Document hierarchy (higher wins on conflict):**
1. PRD (`docs/01_PRD.md`) — product scope and behaviour
2. Backend Blueprint (`docs/02_Backend_Engineering_Blueprint.md`) — backend structure
3. Frontend Blueprint (`docs/03_Frontend_Engineering_Blueprint.md`) — frontend structure
4. AI & Automation Blueprint (`docs/04_AI_Automation_Blueprint.md`) — intelligence design
5. Engineering Constitution (`docs/05_Implementation_Constitution.md`) — governance

## Principles

- **Single responsibility:** Each module has one reason to change.
- **Separation of concerns:** Presentation, intelligence, persistence, and automation have explicit boundaries.
- **Clean architecture:** Dependencies point inward through interfaces.
- **Type safety:** TypeScript strict mode and Pydantic v2 validation are mandatory.
- **Determinism:** Scores, question selection, phase transitions, routing, and service ranking are reproducible.
- **Observability:** Every turn and dispatch is traceable by correlation ID.

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in required values
3. Set up the backend: `cd apps/backend && pip install -e ".[dev]"`
4. Set up the frontend: `cd apps/frontend && npm install`
5. Start the stack: `docker compose up -d`

## Development Workflow

### Branches

- `main` is always releasable
- Use `feat/`, `fix/`, `refactor/`, `docs/`, `test/`, or `chore/` prefixes
- One branch, one coherent change

### Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): description
fix(scope): description
refactor(scope): description
test(scope): description
docs(scope): description
chore(scope): description
```

Reference requirement IDs in commit bodies when relevant (e.g., `FR-30`, `NFR-01`).

### Pull Requests

Every PR MUST include:

1. Problem and intended behaviour
2. Requirement and blueprint references
3. Files and ownership boundaries affected
4. Tests run and results
5. Contract, prompt, knowledge, or workflow compatibility impact
6. Security and PII impact
7. Performance impact
8. Rollback plan for runtime behaviour changes
9. Screenshots for frontend-visible changes
10. Evaluation report for prompt or knowledge changes

### Code Style

**Python:**
- Python 3.12, typed public functions
- Ruff for formatting and linting
- Strict mypy on domain code
- Pydantic v2 for all boundary contracts

**TypeScript/React:**
- TypeScript strict mode
- Server Components by default
- No `any` at API or event boundaries
- Tailwind CSS with the approved token system

### Tests

- Unit tests for pure domain logic (scoring, normalisation, ranking)
- Integration tests for API endpoints and services
- Contract tests for OpenAPI and JSON schema snapshots
- Evaluation tests for AI quality metrics
- Accessibility tests for frontend

## Architectural Guardrails

See Constitution Section 4 for the complete list. Key rules:

- 🚫 Never move AI reasoning into the frontend or n8n
- 🚫 Never call an LLM, embedding provider, ChromaDB, or n8n from the browser
- 🚫 Never duplicate business logic across layers
- 🚫 Never hardcode prompts, scoring weights, or thresholds in application code
- 🚫 Never commit half-processed session state after a failed turn

## Security

- Keep all secrets server-side
- Never log PII (email, phone, names)
- Redact personal data in logs at write time
- Capture contact details only after consent
- Validate all model outputs before they reach domain logic
- Use constant-time comparison for secrets

## Questions?

Open an issue or refer to the documentation in `docs/`.
