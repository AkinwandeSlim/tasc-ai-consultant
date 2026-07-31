# Consultation Response Contract

**Document ID:** TASC-CONTRACT-001
**Version:** 1.0.0
**Status:** Authoritative — single source of truth for the Consultation Response Object
**Consumers:** FastAPI (producer), n8n (consumer/relay), LLM provider (producer of natural-language content within the object), Next.js Frontend (consumer), future integrations (CRM, analytics, BI)

This document defines exactly one thing: the **Consultation Response Object** — the structured payload exchanged at every turn of a consultation across the pipeline (Next.js → FastAPI → n8n → LLM → Google Sheets/Gmail → FastAPI → Frontend). It does not define how any component is implemented internally. Any field, type, or rule not stated here is undefined and must not be assumed by any consumer.

---

## 1. Purpose

The Consultation Response Object exists to solve one structural problem: a single AI consultation must simultaneously produce a natural conversational reply and a growing body of structured business intelligence, and every downstream system — a dashboard, an automation workflow, a spreadsheet row, a sales email — must be able to read the structured half without parsing the conversational half.

This contract is the object that makes that possible. It is:

- **The only shape** in which a consultation turn is represented once it leaves the component that produced it.
- **Provider-agnostic** — nothing in this contract names or assumes OpenAI, Gemini, or any specific model. Any LLM provider producing content for this object must produce content that fits this shape; the contract does not change if the provider changes.
- **Consumer-agnostic** — FastAPI, n8n, and the frontend all read the same object. A consumer that does not need a given section simply ignores it; no consumer requires a bespoke projection.
- **The unit of integration** for every future system (CRM, analytics warehouse, BI dashboard) — Section 19 exists specifically so that future consumers can be added without this contract changing shape for existing ones.

---

## 2. Design Philosophy

Five principles govern every decision in this contract:

1. **One object, two audiences.** Every response carries a `conversation` section for the human reading it and a set of structured sections for every system reading it. Neither is derived from the other at read time — both are produced together, by design, in the same response cycle.
2. **Progressive, never regressive.** Structured sections start `null` or empty and fill in over the life of a consultation as information becomes available. A field, once populated with a confirmed value, is never reset to `null` and a qualification score never decreases within a consultation except through an explicit, logged override. Consumers may treat the absence of regression as a contract guarantee, not an implementation detail they must defend against.
3. **Partial is a valid, permanent state — not an error.** A consultation may end (visitor abandons, declines to continue) with most structured sections still partially populated. This is not a failure mode. Every section is designed to be individually well-formed at any completeness level, and `metadata.completeness` (Section 12) tells every consumer exactly how complete the object is without them having to infer it from which fields are non-null.
4. **Structure is computed, language is generated.** Numeric and enumerated fields (scores, bands, confidence values, qualification status) are produced by deterministic business logic. Free-text fields (`conversation.message`, `recommendations[].rationale`, `lead_qualification.justification`) are the only fields an LLM is the source of truth for. This distinction is load-bearing: a consumer may trust a score for routing/automation decisions; a consumer must never parse a free-text field to extract a decision.
5. **Additive evolution, never silent breakage.** The contract only grows by addition (Section 18). A consumer built against `schema_version 1.0.0` must continue to function, unmodified, against every later `1.x.x` object it receives. Breaking change is a major version event, announced, never a silent field-shape change.

---

## 3. Response Lifecycle

A consultation is a sequence of Consultation Response Objects, one per turn, sharing a `session_id` and, once qualification begins, a `consultation_id`. The object's `response_type` (Section 4) names where in the lifecycle a given object sits:

| `response_type` | When it occurs | What is guaranteed populated |
|---|---|---|
| `greeting` | First response of a new session | `conversation` only. All structured sections `null`/empty. |
| `discovery` | Visitor is describing their situation; business facts are being gathered | `conversation`, `business_profile` (partial), `metadata` |
| `clarification` | The assistant needs one specific piece of information before proceeding | `conversation` (contains a single targeted question), `business_profile` (partial) |
| `qualification` | Enough is known to compute a lead score | `conversation`, `business_profile`, `lead_qualification`, `metadata` |
| `recommendation` | Enough is known to propose services | `conversation`, `business_profile`, `ai_readiness` (if applicable), `lead_qualification`, `recommendations`, `metadata` |
| `completion` | The consultation has ended (explicit close, criteria met, or abandonment) | Every section at its final state for the consultation, plus `workflow_actions` populated with the dispatch action(s) triggered by completion |
| `error` | The pipeline could not produce a normal turn | `conversation` (visitor-safe apology), `metadata`, and an `error` object (Section 17) in place of any section that could not be computed |

Two lifecycle guarantees apply regardless of `response_type`:

- **Monotonic turn index.** `metadata.turn_index` strictly increases within a session. A consumer receiving an out-of-order or duplicate `turn_index` must discard it rather than apply it.
- **Idempotent completion.** Exactly one object in a session's history carries `response_type: "completion"`. If a consumer (e.g. n8n) receives what appears to be a second completion object for the same `consultation_id`, it is a replay (Section 11) and must be treated as a no-op, not a new event.

---

## 4. Top-Level JSON Structure

```json
{
  "schema_version": "1.0.0",
  "response_id": "resp_01HXYZ...",
  "session_id": "sess_9f3a2c...",
  "consultation_id": "cons_7b12ef...",
  "turn_index": 4,
  "timestamp": "2026-07-28T10:15:32Z",
  "response_type": "recommendation",
  "conversation": { "...": "Section 6" },
  "business_profile": { "...": "Section 7" },
  "ai_readiness": { "...": "Section 8" },
  "lead_qualification": { "...": "Section 9" },
  "recommendations": [ { "...": "Section 10" } ],
  "workflow_actions": [ { "...": "Section 11" } ],
  "metadata": { "...": "Section 12" },
  "error": null
}
```

Nine top-level fields are always present in the JSON structure (even if their value is `null` or an empty array): `schema_version`, `response_id`, `session_id`, `consultation_id`, `turn_index`, `timestamp`, `response_type`, `conversation`, `metadata`. The remaining structured sections (`business_profile`, `ai_readiness`, `lead_qualification`, `recommendations`, `workflow_actions`, `error`) are always present as keys but may be `null` (single objects) or `[]` (arrays) when not yet applicable — a consumer must never treat a missing key as different from a `null`/empty value; both mean "not yet available."

---

## 5. Complete Field-by-Field Specification

This section is the field dictionary every other section's examples draw from. Type notation: `string`, `int`, `float (0.0-1.0)`, `boolean`, `enum[...]`, `datetime (ISO 8601, UTC)`, `array<T>`, `object`.

| Path | Type | Nullable | Description |
|---|---|---|---|
| `schema_version` | string (semver) | No | Contract version this object conforms to (Section 18) |
| `response_id` | string (ULID/UUID) | No | Unique identifier for this specific response object |
| `session_id` | string | No | Identifies the conversation session |
| `consultation_id` | string | Yes | Assigned once qualification begins; `null` during `greeting`/early `discovery` |
| `turn_index` | int | No | Monotonically increasing per session |
| `timestamp` | datetime | No | When this object was produced |
| `response_type` | enum | No | One of the seven values in Section 3 |
| `conversation` | object | No | Section 6 |
| `business_profile` | object | Yes | Section 7 |
| `ai_readiness` | object | Yes | Section 8 |
| `lead_qualification` | object | Yes | Section 9 |
| `recommendations` | array | No (may be `[]`) | Section 10 |
| `workflow_actions` | array | No (may be `[]`) | Section 11 |
| `metadata` | object | No | Section 12 |
| `error` | object | Yes | Section 17; non-null only when `response_type: "error"` |

---

## 6. Conversation Section

Carries everything a human-facing surface needs to render the assistant's turn. This is the only section an LLM directly authors; every other structured section is computed and then, at most, *described* in prose by the LLM (e.g. `lead_qualification.justification`), never decided by it.

| Field | Type | Description |
|---|---|---|
| `conversation.message` | string | The full natural-language reply, in final (non-streaming) form as recorded in this object. Streaming delivery, if used, is a transport concern outside this contract — this field is always the complete message. |
| `conversation.role` | enum: `"assistant"` | Fixed value; reserved for future multi-agent scenarios (Section 19). |
| `conversation.tone` | enum: `consultative`, `empathetic`, `direct`, `celebratory` | Optional descriptor a rendering surface may use for stylistic cues; never affects downstream logic. |
| `conversation.follow_up_question` | string \| null | If the assistant is asking one specific question this turn, it is duplicated here in isolation (in addition to being part of `message`) so automation and analytics can identify "a question was asked" without parsing prose. |
| `conversation.suggested_replies` | array<string> | Optional quick-reply suggestions, 0–4 items, for surfaces that support tappable responses. |
| `conversation.language` | string (ISO 639-1) | Language of `message`. Defaults to `"en"`. Present from `schema_version 1.0.0` to support Section 19's multilingual roadmap without a later contract change. |

Example:

```json
"conversation": {
  "message": "Manual order processing at that volume is exactly the kind of bottleneck automation tends to solve well. Roughly how many orders are you handling in a typical week?",
  "role": "assistant",
  "tone": "consultative",
  "follow_up_question": "Roughly how many orders are you handling in a typical week?",
  "suggested_replies": ["Under 100", "100–500", "500+"],
  "language": "en"
}
```

---

## 7. Business Profile Section

The progressively-built factual record of the visitor's business. Every leaf value is wrapped in a confidence envelope so consumers can distinguish a confirmed fact from an inferred one — this envelope shape is used consistently across this section and Section 8.

| Field | Type | Description |
|---|---|---|
| `business_profile.industry` | value-envelope \| null | See envelope shape below |
| `business_profile.company_size` | value-envelope \| null | Normalised band (e.g. `"11-50"`) |
| `business_profile.current_tools` | array<string> | Tools/systems the visitor has named |
| `business_profile.pain_points` | array<pain-point-object> | See below |
| `business_profile.goals` | array<string> | Stated objectives, normalised phrasing |
| `business_profile.decision_maker` | value-envelope \| null | Enum: `decision_maker`, `influencer`, `researcher`, `unknown` |
| `business_profile.completeness_percentage` | int (0-100) | Share of the profile's defined fields currently populated |

**Value envelope** (used for every field that can be confirmed, inferred, or declined):

```json
{
  "value": "logistics",
  "raw_text": "we run a small freight brokerage",
  "confidence": 0.86,
  "status": "confirmed",
  "captured_at_turn": 2
}
```

`status` is one of `confirmed` (visitor stated directly), `inferred` (derived by the assistant with reasonable confidence), `declined` (visitor was asked and chose not to answer — permanently distinct from `unknown`, so no consumer re-prompts for it), or `unknown` (not yet gathered).

**Pain-point object:**

```json
{
  "description": "Order processing is entirely manual",
  "category": "operational_efficiency",
  "severity": "high",
  "confidence": 0.9,
  "captured_at_turn": 3
}
```

---

## 8. AI Readiness Section

Assesses how prepared the business is to adopt an AI/automation solution — distinct from *what* they need (Section 7) or *whether they're a good lead* (Section 9). This section may remain `null` for consultations that never reach a depth where readiness can be meaningfully assessed (e.g. an early-abandonment session) — that is expected, not a defect.

| Field | Type | Description |
|---|---|---|
| `ai_readiness.digital_maturity_level` | enum: `nascent`, `developing`, `established`, `advanced` | Overall assessment |
| `ai_readiness.current_automation_level` | enum: `none`, `minimal`, `partial`, `substantial` | How much of their current process is already automated |
| `ai_readiness.data_infrastructure_status` | enum: `absent`, `informal`, `structured`, `mature` | Whether the business has data in a state a solution could act on |
| `ai_readiness.ai_readiness_score` | int (0-100) | Composite score; computed deterministically from the factors below, never a raw model output |
| `ai_readiness.readiness_factors` | array<{factor, contribution}> | The named inputs to the score, for transparency/audit |
| `ai_readiness.blockers` | array<string> | Identified obstacles to adoption (e.g. `"no dedicated technical staff"`) |
| `ai_readiness.opportunities` | array<string> | Identified quick-win areas |

Example:

```json
"ai_readiness": {
  "digital_maturity_level": "developing",
  "current_automation_level": "minimal",
  "data_infrastructure_status": "informal",
  "ai_readiness_score": 58,
  "readiness_factors": [
    { "factor": "has_existing_order_management_system", "contribution": 15 },
    { "factor": "no_dedicated_technical_staff", "contribution": -10 }
  ],
  "blockers": ["No dedicated technical staff"],
  "opportunities": ["Order intake is already digital — a clean integration point"]
}
```

---

## 9. Lead Qualification Section

The deterministic, auditable assessment of how qualified the lead is. Every numeric field here is computed by business logic; `justification` is the only LLM-authored field in this section, and it is generated *from* the computed fields, never the reverse.

| Field | Type | Description |
|---|---|---|
| `lead_qualification.score` | int (0-100) | Current, post-override score |
| `lead_qualification.raw_score` | int (0-100) | Pre-override score, retained for audit |
| `lead_qualification.band` | enum: `cold`, `warm`, `qualified`, `hot`, `not_a_lead` | Banded classification |
| `lead_qualification.score_breakdown` | object | Named component contributions (e.g. `need_clarity`, `fit`, `urgency`, `budget`, `authority`, `engagement`) |
| `lead_qualification.qualification_status` | object | Checklist of qualification criteria, each `unmet` \| `met` \| `declined` |
| `lead_qualification.overrides_applied` | array<string> | Any override rules that fired, human-readable |
| `lead_qualification.justification` | string | One-paragraph, model-authored explanation grounded strictly in the fields above |

Example:

```json
"lead_qualification": {
  "score": 74,
  "raw_score": 74,
  "band": "qualified",
  "score_breakdown": {
    "need_clarity": 21, "fit": 20, "urgency": 9, "budget": 12, "authority": 7, "engagement": 5
  },
  "qualification_status": {
    "business_context_understood": "met",
    "challenges_identified": "met",
    "solution_matched": "met",
    "timeline_established": "met",
    "budget_discussed": "met",
    "contact_captured": "unmet"
  },
  "overrides_applied": [],
  "justification": "Qualified at 74. Two specific, quantified pain points were identified, a clear solution match exists, and the visitor indicated a near-term timeline. Score is capped below Hot pending contact capture."
}
```

---

## 10. Recommendations Section

An array (not a single object) — zero to N recommended services, ranked. An empty array is a valid, expected state (insufficient signal yet, or the consultation never reached a recommendation-appropriate depth) — it is never represented as `null`.

| Field | Type | Description |
|---|---|---|
| `recommendations[].service_id` | string | Stable identifier from the service catalogue |
| `recommendations[].service_name` | string | Human-readable name |
| `recommendations[].confidence` | float (0.0-0.98) | Never reports full certainty (1.0), by design |
| `recommendations[].priority_rank` | int | 1 = highest priority; unique within the array |
| `recommendations[].rationale` | string | Model-authored explanation, describing an already-ranked decision — the model never selects or reorders |
| `recommendations[].supporting_evidence_refs` | array<string> | Identifiers only (e.g. knowledge-base chunk IDs) — never raw source text |

Example:

```json
"recommendations": [
  {
    "service_id": "SVC-AIA",
    "service_name": "AI Process Automation",
    "confidence": 0.88,
    "priority_rank": 1,
    "rationale": "Directly addresses the manual order-processing bottleneck described, with a clear integration point into the existing order management system.",
    "supporting_evidence_refs": ["cs_logistics_01", "svc_aia_overview"]
  }
]
```

---

## 11. Workflow Actions Section

The only section this contract defines that is explicitly a **trigger record**, not a descriptive record — it tells n8n (or any automation consumer) what should happen as a result of this response, in a form that is safe to execute more than once.

| Field | Type | Description |
|---|---|---|
| `workflow_actions[].action_type` | enum: `log_lead`, `send_notification_email`, `schedule_followup`, `update_crm_record`, `trigger_human_handoff`, `none` | What should occur |
| `workflow_actions[].target_system` | enum: `google_sheets`, `gmail`, `crm`, `internal_alert` | Where the action is directed |
| `workflow_actions[].trigger_condition` | string | Human-readable reason the action fired (e.g. `"consultation completed, band=hot"`) |
| `workflow_actions[].idempotency_key` | string | Always equal to `consultation_id` (or `consultation_id` + `action_type` if multiple distinct actions occur in one response) — any consumer executing this action MUST check this key before acting |
| `workflow_actions[].status` | enum: `pending`, `dispatched`, `acknowledged`, `failed`, `skipped_duplicate` | Set by the executing system, not the producer, and reported back through the FastAPI→n8n callback path if the executing system updates it |
| `workflow_actions[].payload_ref` | string | Pointer to the full data the action needs (typically: this same `consultation_id`, since the executing system has access to the full stored object) rather than duplicating data inline |

Example:

```json
"workflow_actions": [
  {
    "action_type": "log_lead",
    "target_system": "google_sheets",
    "trigger_condition": "consultation completed, band=qualified",
    "idempotency_key": "cons_7b12ef::log_lead",
    "status": "pending",
    "payload_ref": "cons_7b12ef"
  },
  {
    "action_type": "send_notification_email",
    "target_system": "gmail",
    "trigger_condition": "consultation completed, band=qualified",
    "idempotency_key": "cons_7b12ef::send_notification_email",
    "status": "pending",
    "payload_ref": "cons_7b12ef"
  }
]
```

`workflow_actions` is populated almost exclusively on `response_type: "completion"` objects. It is legal, but expected to be rare, for an intermediate turn to carry a `trigger_human_handoff` action (e.g. the visitor explicitly asked for a human) — every other action type is a completion-time event.

---

## 12. Metadata Section

Operational and provenance data. Distinctly **not** a place for business content — nothing here duplicates or contradicts Sections 6–11.

| Field | Type | Description |
|---|---|---|
| `metadata.model_provider` | string | Name of the LLM provider that authored `conversation.message` this turn (e.g. `"openai"`) |
| `metadata.model_name` | string | Specific model identifier |
| `metadata.prompt_version` | string | Version tag of the prompt template set used |
| `metadata.latency_ms` | int | End-to-end time to produce this object |
| `metadata.token_usage` | object `{input, output}` | Token counts for this turn's generation call(s) |
| `metadata.correlation_id` | string | Threads this object back to logs across every component it passes through |
| `metadata.environment` | enum: `local`, `preview`, `production` | Which environment produced this object |
| `metadata.completeness` | int (0-100) | Overall completeness of the structured sections for this consultation so far (Section 2, principle 3) |
| `metadata.generated_at` | datetime | Redundant with top-level `timestamp` for consumers that only read `metadata` |

`metadata` never carries cost or token data intended for a visitor-facing surface to render — those fields exist for operational logging and internal dashboards only; a frontend consumer is expected to ignore this section entirely.

---

## 13. Example Response Objects

### 13.1 Greeting

```json
{
  "schema_version": "1.0.0",
  "response_id": "resp_01",
  "session_id": "sess_001",
  "consultation_id": null,
  "turn_index": 0,
  "timestamp": "2026-07-28T10:00:00Z",
  "response_type": "greeting",
  "conversation": {
    "message": "I'm Nova, AI Solutions Consultant at Trizen. What's the problem you're trying to solve?",
    "role": "assistant",
    "tone": "consultative",
    "follow_up_question": "What's the problem you're trying to solve?",
    "suggested_replies": [],
    "language": "en"
  },
  "business_profile": null,
  "ai_readiness": null,
  "lead_qualification": null,
  "recommendations": [],
  "workflow_actions": [],
  "metadata": { "model_provider": null, "model_name": null, "prompt_version": "l1:v1|l2:v1", "latency_ms": 12, "token_usage": {"input": 0, "output": 0}, "correlation_id": "corr_001", "environment": "production", "completeness": 0, "generated_at": "2026-07-28T10:00:00Z" },
  "error": null
}
```

### 13.2 Discovery

```json
{
  "schema_version": "1.0.0",
  "response_id": "resp_04",
  "session_id": "sess_001",
  "consultation_id": "cons_001",
  "turn_index": 2,
  "timestamp": "2026-07-28T10:03:00Z",
  "response_type": "discovery",
  "conversation": {
    "message": "That kind of manual order handling usually gets expensive as volume grows. What tools are you currently using to manage orders?",
    "role": "assistant",
    "follow_up_question": "What tools are you currently using to manage orders?",
    "suggested_replies": [],
    "language": "en"
  },
  "business_profile": {
    "industry": { "value": "logistics", "raw_text": "freight brokerage", "confidence": 0.86, "status": "confirmed", "captured_at_turn": 1 },
    "company_size": null,
    "current_tools": [],
    "pain_points": [ { "description": "Manual order processing", "category": "operational_efficiency", "severity": "high", "confidence": 0.85, "captured_at_turn": 2 } ],
    "goals": [],
    "decision_maker": null,
    "completeness_percentage": 22
  },
  "ai_readiness": null,
  "lead_qualification": null,
  "recommendations": [],
  "workflow_actions": [],
  "metadata": { "model_provider": "openai", "model_name": "gpt-4.1-mini", "prompt_version": "l1:v1|l2:v1|l5:v1", "latency_ms": 1840, "token_usage": {"input": 940, "output": 88}, "correlation_id": "corr_004", "environment": "production", "completeness": 22, "generated_at": "2026-07-28T10:03:00Z" },
  "error": null
}
```

### 13.3 Qualification

```json
{
  "schema_version": "1.0.0",
  "response_id": "resp_09",
  "session_id": "sess_001",
  "consultation_id": "cons_001",
  "turn_index": 6,
  "timestamp": "2026-07-28T10:09:00Z",
  "response_type": "qualification",
  "conversation": {
    "message": "Got it — sounds like this is a live priority for you. Do you have a rough budget range in mind for solving this?",
    "role": "assistant",
    "follow_up_question": "Do you have a rough budget range in mind for solving this?",
    "suggested_replies": ["Under $5k", "$5k-$20k", "$20k+", "Not yet"],
    "language": "en"
  },
  "business_profile": { "...": "populated, see Section 7" },
  "ai_readiness": { "...": "populated, see Section 8" },
  "lead_qualification": {
    "score": 61, "raw_score": 61, "band": "qualified",
    "score_breakdown": { "need_clarity": 21, "fit": 20, "urgency": 9, "budget": 0, "authority": 7, "engagement": 4 },
    "qualification_status": { "business_context_understood": "met", "challenges_identified": "met", "solution_matched": "met", "timeline_established": "met", "budget_discussed": "unmet", "contact_captured": "unmet" },
    "overrides_applied": [],
    "justification": "Qualified at 61. Strong need clarity and solution fit are established; budget has not yet been discussed."
  },
  "recommendations": [],
  "workflow_actions": [],
  "metadata": { "...": "as above" },
  "error": null
}
```

### 13.4 Recommendation

```json
{
  "schema_version": "1.0.0",
  "response_id": "resp_11",
  "session_id": "sess_001",
  "consultation_id": "cons_001",
  "turn_index": 8,
  "timestamp": "2026-07-28T10:12:00Z",
  "response_type": "recommendation",
  "conversation": {
    "message": "Based on everything you've shared, AI Process Automation looks like the strongest fit — it plugs directly into the order system you already have.",
    "role": "assistant",
    "follow_up_question": null,
    "suggested_replies": ["Tell me more", "What would this cost?", "Who would I work with?"],
    "language": "en"
  },
  "business_profile": { "...": "populated" },
  "ai_readiness": { "...": "populated" },
  "lead_qualification": { "...": "populated, see 13.3 shape, higher score" },
  "recommendations": [ { "...": "see Section 10 example" } ],
  "workflow_actions": [],
  "metadata": { "...": "as above" },
  "error": null
}
```

### 13.5 Completion

```json
{
  "schema_version": "1.0.0",
  "response_id": "resp_15",
  "session_id": "sess_001",
  "consultation_id": "cons_001",
  "turn_index": 12,
  "timestamp": "2026-07-28T10:20:00Z",
  "response_type": "completion",
  "conversation": {
    "message": "Thanks for walking me through this — I've put together a summary for our team and someone will reach out within a business day.",
    "role": "assistant",
    "follow_up_question": null,
    "suggested_replies": [],
    "language": "en"
  },
  "business_profile": { "...": "final state" },
  "ai_readiness": { "...": "final state" },
  "lead_qualification": { "score": 82, "band": "hot", "...": "final state" },
  "recommendations": [ { "...": "final ranked list" } ],
  "workflow_actions": [
    { "action_type": "log_lead", "target_system": "google_sheets", "trigger_condition": "consultation completed, band=hot", "idempotency_key": "cons_001::log_lead", "status": "pending", "payload_ref": "cons_001" },
    { "action_type": "send_notification_email", "target_system": "gmail", "trigger_condition": "consultation completed, band=hot", "idempotency_key": "cons_001::send_notification_email", "status": "pending", "payload_ref": "cons_001" }
  ],
  "metadata": { "...": "as above", "completeness": 100 },
  "error": null
}
```

---

## 14. Validation Rules

Every producer of a Consultation Response Object must satisfy these rules before the object is considered valid for transmission. A consumer receiving an object that violates any rule below should treat it as malformed and route it to error handling rather than partially process it.

| # | Rule |
|---|---|
| V-01 | `schema_version` is present and matches a version this consumer understands (Section 18). |
| V-02 | `turn_index` is a non-negative integer, strictly greater than the `turn_index` of the previous object in the same `session_id`. |
| V-03 | `response_type` is one of the seven enumerated values (Section 3); no other string is valid. |
| V-04 | `consultation_id` is `null` if and only if `response_type` is `greeting` or an early `discovery` turn that has not yet begun qualification; once non-null, it never reverts to `null` for that session. |
| V-05 | Every `confidence` field is a float strictly between `0.0` and `1.0` inclusive of `0.0`, exclusive of values above `0.98` for `recommendations[].confidence` specifically (Section 10). |
| V-06 | `lead_qualification.score` and `ai_readiness.ai_readiness_score` are integers in `[0, 100]`. |
| V-07 | `lead_qualification.score` never decreases from its value in a previous object in the same session unless `overrides_applied` is non-empty in the object where it decreases. |
| V-08 | `recommendations` array, when non-empty, has unique `priority_rank` values starting at 1 with no gaps. |
| V-09 | Every `workflow_actions[].idempotency_key` is unique within the object and stable (identical) if the same logical action is ever re-emitted (e.g. on retry). |
| V-10 | If `response_type` is `error`, the top-level `error` field is non-null and every other structured section reflects the last known-good state (not stripped to `null`) unless that section itself could never have been computed. |
| V-11 | `conversation.message` is never empty for any `response_type` other than `error` cases where a message genuinely cannot be produced (Section 17). |
| V-12 | No field anywhere in the object contains raw source text from the knowledge base — only identifiers (`supporting_evidence_refs`) are permitted (Section 10). |
| V-13 | No field anywhere in the object contains a system prompt, instruction text, or model/provider credential. |
| V-14 | `metadata.correlation_id` is present and non-empty on every object, including `error` objects. |

---

## 15. Required Fields

Fields that MUST be present (key must exist; value may still be `null`/`[]` where the field is nullable per Section 5) on **every** Consultation Response Object regardless of `response_type`:

```
schema_version
response_id
session_id
consultation_id          (key present; value nullable)
turn_index
timestamp
response_type
conversation              (object; value nullable? No — always populated, see rule V-11)
conversation.message
conversation.role
conversation.language
business_profile           (key present; value nullable)
ai_readiness                (key present; value nullable)
lead_qualification            (key present; value nullable)
recommendations                 (key present; array, may be empty)
workflow_actions                  (key present; array, may be empty)
metadata
metadata.correlation_id
metadata.environment
metadata.completeness
metadata.generated_at
error                                (key present; value nullable)
```

Additionally required **conditionally**, based on `response_type` (per the lifecycle table in Section 3):

| `response_type` | Additionally required non-null |
|---|---|
| `qualification`, `recommendation`, `completion` | `lead_qualification` |
| `recommendation`, `completion` | `recommendations` (non-empty array) |
| `completion` | `workflow_actions` (non-empty array) |
| `error` | `error` |

---

## 16. Optional Fields

Fields that may legitimately be absent in their nullable/empty state at any point in a consultation, and whose absence never constitutes a malformed object:

```
business_profile.company_size
business_profile.current_tools
business_profile.pain_points
business_profile.goals
business_profile.decision_maker
ai_readiness (entire section, until sufficient signal exists)
ai_readiness.readiness_factors
ai_readiness.blockers
ai_readiness.opportunities
conversation.follow_up_question
conversation.suggested_replies
conversation.tone
lead_qualification.overrides_applied  (empty array is the common case)
recommendations[].supporting_evidence_refs
workflow_actions (empty array is the common case for non-completion turns)
metadata.model_provider / metadata.model_name  (null for non-generative turns, e.g. the static greeting)
```

A field appearing in this section is never required by any consumer's validation logic; consumers must be built to function correctly when these fields are absent.

---

## 17. Error Contract

When the pipeline cannot produce a normal turn (provider outage, retrieval failure beyond its degraded-mode threshold, a downstream validation failure), the object is still emitted in the standard top-level shape (Section 4), with `response_type: "error"` and the `error` field populated:

| Field | Type | Description |
|---|---|---|
| `error.code` | string (enum-like, stable identifier) | Machine-readable failure category, e.g. `PROVIDER_UNAVAILABLE`, `VALIDATION_FAILED`, `RETRIEVAL_DEGRADED`, `DOWNSTREAM_TIMEOUT` |
| `error.message` | string | Visitor-safe description; never a stack trace or internal detail |
| `error.recoverable` | boolean | Whether the visitor can reasonably retry the same turn |
| `error.origin_component` | string | Which pipeline component raised the error (`fastapi`, `n8n`, `llm_provider`) — for operational triage, not for visitor display |
| `error.correlation_id` | string | Duplicated from `metadata.correlation_id` for convenience in error-specific tooling |

On an `error` object, `conversation.message` still carries a natural-language apology suitable for display (Section 17's whole purpose is that an error is never surfaced to a human as raw JSON or a broken UI state), and every other structured section carries the **last known-good value** for that consultation rather than being wiped — a consumer reading `lead_qualification` off an error-turn object still sees the most recent valid qualification state, not `null`.

Example:

```json
{
  "schema_version": "1.0.0",
  "response_id": "resp_20",
  "session_id": "sess_001",
  "consultation_id": "cons_001",
  "turn_index": 9,
  "timestamp": "2026-07-28T10:13:00Z",
  "response_type": "error",
  "conversation": {
    "message": "Something went wrong on my end. Your conversation is still here — go ahead and try that again.",
    "role": "assistant",
    "follow_up_question": null,
    "suggested_replies": [],
    "language": "en"
  },
  "business_profile": { "...": "last known-good state" },
  "ai_readiness": { "...": "last known-good state" },
  "lead_qualification": { "...": "last known-good state" },
  "recommendations": [ { "...": "last known-good state" } ],
  "workflow_actions": [],
  "metadata": { "...": "as above" },
  "error": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "Something went wrong on my end. Your conversation is still here — go ahead and try that again.",
    "recoverable": true,
    "origin_component": "llm_provider",
    "correlation_id": "corr_020"
  }
}
```

---

## 18. Versioning Strategy

`schema_version` follows semantic versioning (`MAJOR.MINOR.PATCH`):

- **PATCH** (`1.0.0` → `1.0.1`) — clarification of an existing field's description or validation rule with no shape change. No consumer action required.
- **MINOR** (`1.0.0` → `1.1.0`) — purely additive: a new optional field, a new enum value appended to a non-exhaustively-matched enum, a new `response_type` that older consumers can safely ignore by falling back to generic handling. Existing consumers continue to function without modification; new fields are simply absent from their perspective if unrecognised.
- **MAJOR** (`1.x.x` → `2.0.0`) — any change that could break an existing consumer: a field renamed or removed, a type changed, a required field added, an enum value's meaning changed. A major version increment requires: (a) a deprecation notice attached to the outgoing shape for at least one full release cycle where feasible, (b) parallel emission or an explicit migration window where both `1.x.x` and `2.0.0` consumers can be supported, (c) every consumer team acknowledging the change before the old version is retired.

Producers stamp every object with the exact `schema_version` they conform to; this is never inferred or omitted. Consumers should reject (route to error handling) any `schema_version` with a MAJOR component they do not explicitly support, and should tolerate — not reject — MINOR and PATCH differences above their own baseline.

The version lineage of this contract is tracked independently from the codebase that produces it: this document itself is the version record, and any change to it is a change to the contract, reviewed and merged the same way an API contract would be, not silently updated alongside an unrelated code change.

---

## 19. Future Compatibility

This contract is designed so that the following future needs require no breaking change:

- **CRM and analytics integration.** `consultation_id` and the fully-structured sections (Sections 7–10) already form a complete, self-contained record suitable for ingestion by a CRM or a BI warehouse. A future integration consumes the `completion` object directly; no new fields are needed for a first-generation CRM sync.
- **Multi-language support.** `conversation.language` exists from `1.0.0` specifically so that adding new supported languages is a value-space addition (new ISO codes), never a shape change.
- **Multi-channel delivery (WhatsApp, Telegram, etc.).** The contract makes no assumption about transport. A new channel is a new producer/consumer pair speaking the same object; `conversation.suggested_replies` and `tone` already accommodate channels with different rendering capabilities by being optional.
- **Additional structured intelligence sections.** A future section (e.g. `competitive_positioning`, `risk_assessment`) is added as a new, nullable, optional top-level key in a MINOR version — existing consumers that don't recognise it simply do not read it, per the additive-evolution principle (Section 2).
- **Multi-agent conversations.** `conversation.role` is already an enum (currently fixed to `"assistant"`) rather than a boolean or implicit value, specifically so that a future scenario with more than one distinct AI persona in a single pipeline does not require restructuring this field — only extending its enum.
- **Workflow action extensibility.** `workflow_actions[].action_type` and `target_system` are enums expected to grow (new automation targets, new trigger types) as MINOR version additions; the trigger-record shape itself (Section 11) does not need to change to accommodate new action types.
- **Deprecation without disruption.** Because every consumer is contractually required (Section 18) to tolerate unrecognised optional fields and MINOR-version additions, this contract can evolve on a faster cadence than any single consumer's release cycle — the frontend, n8n workflows, and FastAPI backend do not need to deploy in lockstep for additive changes to take effect.

---

*End of Consultation Response Contract v1.0.0. This document defines the object exchanged between FastAPI, n8n, and the LLM provider, and is consumed by the Next.js frontend. It does not define implementation, ownership of computation, or internal architecture of any component — see the Backend Engineering Blueprint for that.*