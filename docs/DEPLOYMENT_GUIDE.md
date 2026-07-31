# Deployment Guide

**Document ID:** TASC-DEPLOY-001
**Status:** Reflects Sprint 6.1 (complete) — n8n workflow, LLM provider, Sheets, and Gmail deployment steps are documented as placeholders pending Sprints 6.2–6.5
**Audience:** Engineers deploying or operating the system

This guide covers how to run and deploy the system as it exists after Sprint 6.1. See `IMPLEMENTATION_STATUS.md` for what is and isn't yet implemented, and the Sprint 6 Architecture document for why the deployment shape looks the way it does.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Variables](#2-environment-variables)
3. [Running Frontend](#3-running-frontend)
4. [Running FastAPI](#4-running-fastapi)
5. [Running Docker](#5-running-docker)
6. [Running n8n](#6-running-n8n)
7. [Running Mock Mode](#7-running-mock-mode)
8. [Running Production Mode](#8-running-production-mode)
9. [Configuration](#9-configuration)
10. [Health Checks](#10-health-checks)
11. [Testing](#11-testing)
12. [Troubleshooting](#12-troubleshooting)
13. [Deployment Checklist](#13-deployment-checklist)
14. [Production Checklist](#14-production-checklist)
15. [Security Checklist](#15-security-checklist)

---

## 1. Prerequisites

- Node.js (for the Next.js frontend) — version per the frontend's own `package.json` engines field.
- Python 3.12 (for the FastAPI backend).
- Docker and Docker Compose, if running via containers (Section 5).
- An n8n instance, self-hosted or cloud, once Sprint 6.2 is complete (n8n is not required to run the system in Mock Mode, Section 7).
- An OpenAI API key, once Sprint 6.3 is complete (not required before then — the deterministic engine has no external model dependency).

## 2. Environment Variables

**FastAPI backend:**

| Variable | Required | Purpose |
|---|---|---|
| `N8N_ENABLED` | Yes | `true` selects `N8nAutomationGateway`; `false` selects `MockAutomationGateway`. Governs which gateway is wired via dependency injection, with zero code change either way. |
| `N8N_WEBHOOK_URL` | Required only when `N8N_ENABLED=true` | Target n8n webhook endpoint. Config validation fails startup if this is missing while `N8N_ENABLED=true`. |
| `N8N_SHARED_SECRET` | Required only when `N8N_ENABLED=true` | Used for HMAC-SHA256 payload signing between FastAPI and n8n. |
| `GATEWAY_MAX_RETRIES` | No | Configurable retry count for the exponential-backoff-with-jitter retry strategy on gateway dispatch. |
| `GATEWAY_TIMEOUT_SECONDS` | No | Timeout applied to the gateway's outbound HTTP call. |
| `OPENAI_API_KEY` | Not yet required | Reserved for Sprint 6.3 (LLM provider integration). Do not configure before that sprint begins. |

**Frontend (Next.js):**

| Variable | Required | Purpose |
|---|---|---|
| API base URL (e.g. `NEXT_PUBLIC_API_BASE_URL`) | Yes | Points the frontend at the FastAPI backend's `POST /api/v1/chat/start` and `POST /api/v1/chat/message` endpoints. |

No frontend environment variable ever names an LLM provider or a Google service credential — per the Sprint 6 Architecture principle that the frontend never communicates with either directly.

## 3. Running Frontend

Standard Next.js development/production commands apply (install dependencies, then run the dev server or build-and-start), pointed at the FastAPI backend via the API base URL variable above. The frontend requires no configuration related to `N8N_ENABLED` — automation-mode switching is entirely a backend concern.

## 4. Running FastAPI

Start the FastAPI application with the environment variables in Section 2 set. On startup, configuration validation enforces that `N8N_WEBHOOK_URL` (and the shared secret) are present whenever `N8N_ENABLED=true` — startup fails loudly rather than allowing a misconfigured production deployment to silently fall back to a broken gateway.

## 5. Running Docker

Both the FastAPI backend and, once Sprint 6.2 is complete, the n8n instance are wired into the project's `docker-compose.yml`. Until Sprint 6.2 lands, the compose file covers the frontend and backend only; running n8n today (Section 6) is a manual/external step, not yet part of the compose stack.

## 6. Running n8n

**Status: Sprint 6.2, not yet implemented.** Once complete, n8n will be wired into `docker-compose.yml` with a webhook trigger validating incoming payloads (shared secret + HMAC signature), idempotency handling (a duplicate request returns `409`, treated as success by `N8nAutomationGateway`), and retry handling on the n8n side. Until then, setting `N8N_ENABLED=true` without a working n8n endpoint at `N8N_WEBHOOK_URL` will result in dispatch failures surfaced through the gateway's error hierarchy (`GatewayConnectionError`, `GatewayTimeoutError`).

## 7. Running Mock Mode

Set `N8N_ENABLED=false`. `MockAutomationGateway` delegates directly to the local `ConsultationOrchestrator` — no n8n instance, webhook, or shared secret is required. This is the correct mode for local development and for any environment where n8n is not yet deployed (i.e., every environment today, since Sprint 6.2 has not landed). All reasoning (intent classification, extraction, scoring, recommendation) behaves identically to production mode; only the downstream business-automation dispatch differs.

## 8. Running Production Mode

Set `N8N_ENABLED=true`, and provide `N8N_WEBHOOK_URL` and `N8N_SHARED_SECRET`. FastAPI's config validation will refuse to start otherwise. In this mode, completed consultations are dispatched as a signed HTTP POST to n8n; n8n's actual fan-out to Google Sheets, Gmail, and Telegram is not yet functional until Sprints 6.2, 6.4, and 6.5 are complete respectively — enabling this mode today will result in a gateway that can reach n8n (if deployed) but with no workflow yet defined to receive it meaningfully.

## 9. Configuration

Configuration is validated once, at FastAPI startup. The only conditional requirement currently enforced is `N8N_WEBHOOK_URL` (and the shared secret) when `N8N_ENABLED=true`. No other environment-dependent branching exists yet in the deployed system — `OPENAI_API_KEY` and any RAG/vector-store configuration are reserved names for Sprint 6.3 and have no effect on the system today.

## 10. Health Checks

A health check should confirm, at minimum:

- The FastAPI process is serving `POST /api/v1/chat/start` successfully (a session can be created and a greeting returned).
- If `N8N_ENABLED=true`, that the configured `N8N_WEBHOOK_URL` is reachable — a failure here should surface as a `degraded`, not necessarily `unhealthy`, status, since Mock Mode remains available as a fallback path architecturally even if it isn't the currently configured mode.

A dedicated `/health` endpoint with structured component statuses is not specified in the Sprint 6 Architecture document as it stands; if one is added, it should follow the pattern above rather than perform a full consultation round-trip.

## 11. Testing

Run the existing gateway test suite (32 tests covering protocol, mock, n8n, dependency injection, HMAC signing, and API integration) and the pre-existing `ConsultationOrchestrator`/qualification/recommendation unit tests. Full integration testing against a real n8n instance, Google Sheets, and Gmail is Sprint 6.6 scope and not yet available — do not expect end-to-end automation testing to be meaningful until that sub-sprint lands.

## 12. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Startup fails with a config error naming `N8N_WEBHOOK_URL` | `N8N_ENABLED=true` with the webhook URL unset | Set `N8N_WEBHOOK_URL` (and shared secret), or switch to `N8N_ENABLED=false` for local/dev use |
| Gateway dispatch raises `GatewayConnectionError` / `GatewayTimeoutError` | n8n unreachable or not yet deployed (expected pre-Sprint 6.2) | Confirm n8n is deployed and reachable, or run in Mock Mode |
| Gateway dispatch raises `GatewayRejectedError` | Signature/shared-secret mismatch, or n8n-side validation rejected the payload | Verify `N8N_SHARED_SECRET` matches on both sides |
| Duplicate automation dispatch suspected | n8n returned `409` | This is expected, idempotent behavior — `N8nAutomationGateway` treats `409` as success, not a failure to retry |
| LLM-related environment variables have no effect | Sprint 6.3 not yet implemented | Expected — no code path currently reads these variables |

## 13. Deployment Checklist

- [ ] Frontend built and pointed at the correct FastAPI API base URL.
- [ ] FastAPI deployed with `N8N_ENABLED` explicitly set (not left to a default).
- [ ] If `N8N_ENABLED=true`: `N8N_WEBHOOK_URL` and `N8N_SHARED_SECRET` set and verified reachable.
- [ ] Gateway test suite passing in CI before deploy.
- [ ] No LLM-related environment variables configured prematurely (they have no effect before Sprint 6.3 and should not be mistaken for a working integration).

## 14. Production Checklist

- [ ] `N8N_ENABLED=true` only once an actual n8n workflow exists to receive dispatches (post–Sprint 6.2) — enabling it earlier is valid for gateway-transport testing but will not produce working business automation.
- [ ] Retry/backoff configuration (`GATEWAY_MAX_RETRIES`, `GATEWAY_TIMEOUT_SECONDS`) reviewed against expected n8n latency.
- [ ] Confirm idempotent handling end-to-end: a duplicate dispatch does not create a duplicate Sheets row or duplicate email, once Sprints 6.2/6.4/6.5 are complete.
- [ ] Confirm no architectural changes have been introduced beyond the fixed Sprint 6 sub-sprint scope, per the Sprint 6 Architecture document's explicit instruction that no additional architectural changes should be introduced once Sprint 6 begins.

## 15. Security Checklist

- [ ] `N8N_SHARED_SECRET` is a genuinely secret value, stored in environment/secret management, never committed to source control.
- [ ] HMAC-SHA256 verification on the n8n side uses constant-time comparison (as implemented on the FastAPI signing side) once the n8n workflow (Sprint 6.2) is built.
- [ ] The frontend never holds, references, or is configured with any LLM provider credential or Google service credential — these remain exclusively backend (FastAPI) and automation-layer (n8n) concerns respectively.
- [ ] `OPENAI_API_KEY`, once introduced in Sprint 6.3, is held only in the FastAPI backend's environment, never exposed to the frontend bundle.