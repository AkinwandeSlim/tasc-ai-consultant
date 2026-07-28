# TASC — Trizen AI Solutions Consultant

**TASC** is an AI-powered pre-sales consultant for Trizen Ventures. It holds a structured discovery conversation with website visitors, recommends Trizen services based on their needs, scores the lead against a deterministic rubric, and hands a validated consultation payload to automation (n8n) for downstream delivery.

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────┐     ┌─────────────────┐
│   Next.js 15    │     │            FastAPI (Python 3.12)       │     │     n8n         │
│   Frontend      │────▶│                                        │────▶│  Orchestration  │
│                 │     │  ┌──────────┐  ┌────────────────────┐  │     │                 │
│  • Conversation │     │  │ API      │  │ Domain Services    │  │     │  • Google Sheets│
│  • Live Panel   │     │  │ Layer    │─▶│ • Intent Classifier│  │     │  • Gmail Sales  │
│  • SSE Stream   │     │  │          │  │ • Slot Extractor   │  │     │  • Telegram     │
└─────────────────┘     │  │ • Routes │  │ • Scoring Engine   │  │     │  • Visitor Email│
                         │  │ • Middle-│  │ • Recommendation  │  │     └─────────────────┘
                         │  │   ware   │  │ • RAG / Retrieval │  │
                         │  └──────────┘  │ • Summary Gen.    │  │
                         │                └────────────────────┘  │
                         │  ┌──────────────────────────────────┐  │
                         │  │ Infrastructure Adapters          │  │
                         │  │ • OpenAI (GPT-4.1-mini)          │  │
                         │  │ • ChromaDB (Vector Store)        │  │
                         │  │ • Session/Payload Repositories  │  │
                         │  │ • n8n Dispatcher                │  │
                         │  └──────────────────────────────────┘  │
                         └──────────────────────────────────────┘
```

### Non-negotiable principles

1. **The browser never calls a model provider.** All AI intelligence lives in FastAPI.
2. **FastAPI owns all decisions** — prompt orchestration, retrieval, extraction, scoring, recommendation, and JSON generation.
3. **n8n is orchestration only** — it receives a validated payload and fans out to Google Sheets, Gmail, and Telegram. No AI calls, no business rules.
4. **Factual claims come from RAG.** The curated knowledge base is the single source of truth for Trizen facts.
5. **Scoring is deterministic code.** The same transcript always yields the same score.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (optional, for ChromaDB + n8n)

### Backend

```bash
cd apps/backend
cp .env.example .env
# Edit .env with your API keys
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend

```bash
cd apps/frontend
cp .env.example .env.local
npm install
npm run dev
```

### Docker (full stack)

```bash
docker compose up -d
```

## Project Structure

```
├── apps/
│   ├── backend/           # FastAPI application
│   │   ├── app/
│   │   │   ├── api/       # Transport layer (routes, middleware, errors)
│   │   │   ├── core/      # Configuration, exceptions, logging, security
│   │   │   ├── schemas/   # Pydantic v2 boundary contracts
│   │   │   ├── domain/    # Business logic (conversation, extraction,
│   │   │   │              #   qualification, recommendation, RAG, summary)
│   │   │   ├── orchestration/  # Turn pipeline sequencing
│   │   │   ├── infrastructure/ # Providers, vector store, repositories
│   │   │   └── resources/      # Prompts, catalogue, weights, vocabularies
│   │   ├── tests/
│   │   ├── knowledge/     # RAG corpus (markdown + YAML front matter)
│   │   └── data/          # Runtime persistence (git-ignored)
│   └── frontend/          # Next.js 15 App Router
│       └── src/
│           ├── app/       # Routes, layouts, pages
│           ├── components/# UI components
│           ├── features/  # Feature composition
│           ├── contexts/  # Client state providers
│           ├── services/  # HTTP + SSE transport
│           ├── types/     # Backend DTO types
│           └── hooks/     # Custom React hooks
├── automation/
│   └── n8n/              # n8n workflow definitions
├── docker/               # Dockerfiles
├── scripts/              # Utility scripts
├── docs/                 # Product and engineering documentation
└── .github/workflows/    # CI/CD pipelines
```

## Key Documentation

| Document | Purpose |
|----------|---------|
| `docs/01_PRD.md` | Product Requirements Document — the single source of truth |
| `docs/02_Backend_Engineering_Blueprint.md` | Backend architecture and contracts |
| `docs/03_Frontend_Engineering_Blueprint.md` | Frontend architecture and UX specification |
| `docs/04_AI_Automation_Blueprint.md` | AI, RAG, and n8n automation design |
| `docs/05_Implementation_Constitution.md` | Engineering governance and standards |
| `BUILD_STATUS.md` | Current build status and progress tracker |

## License

MIT — see [LICENSE](LICENSE).
