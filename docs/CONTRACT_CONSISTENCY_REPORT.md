# Contract Consistency Report

**Document ID:** TASC-CONSISTENCY-001
**Status:** Diagnostic — does not modify, reconcile, or resolve any existing document
**Scope:** Compares field-level terminology for the Consultation Response Object across four existing documents

This report does not choose a correct version of any field. It records where each document's own text disagrees with the others, so that reconciliation can happen against the actual implemented FastAPI/Pydantic models rather than against any of these design documents in isolation — no document reviewed here has visibility into the implementation, so none of them can be treated as self-evidently authoritative over the others.

---

## Table of Contents

1. [Documents Compared](#1-documents-compared)
2. [Method](#2-method)
3. [Top-Level Envelope Differences](#3-top-level-envelope-differences)
4. [Conversation Section Differences](#4-conversation-section-differences)
5. [Business Profile Section Differences](#5-business-profile-section-differences)
6. [AI Readiness Section Differences](#6-ai-readiness-section-differences)
7. [Lead Qualification Section Differences](#7-lead-qualification-section-differences)
8. [Recommendations Section Differences](#8-recommendations-section-differences)
9. [Workflow Actions Section Differences](#9-workflow-actions-section-differences)
10. [Metadata Section Differences](#10-metadata-section-differences)
11. [Stage / Phase Terminology Differences](#11-stage--phase-terminology-differences)
12. [Fields Referenced by Only One Document](#12-fields-referenced-by-only-one-document)
13. [Summary of Findings](#13-summary-of-findings)
14. [Recommendation](#14-recommendation)

---

## 1. Documents Compared

| Document | Location | What it contains regarding the response object |
|---|---|---|
| Consultation Response Contract | `docs/CONSULTATION_RESPONSE_CONTRACT.md` | A full field-by-field JSON schema, presented as the authoritative contract |
| Sprint 6 Architecture | `docs/SPRINT_6_ARCHITECTURE.md` (uploaded as `SPRINT_6_IMPLEMENTATION_GUIDE.md`) | One worked JSON example under "Consultation Response Contract," presented as the shape the deterministic engine produces |
| Consultation State Machine | `docs/CONSULTATION_STATE_MACHINE.md` | No standalone schema; per-stage "Expected Dashboard Updates" entries that name specific fields and paths |
| System Architecture | `docs/SYSTEM_ARCHITECTURE.md` | No independent field definitions; Section 7 contains a note flagging that the Sprint 6 Architecture example and the Contract disagree, quoting a subset of the disagreement |

## 2. Method

Each subsection below lists a concept (e.g. "the qualification band"), then shows, verbatim where possible, how each document names or shapes that concept, and where it appears (section/field path). A blank cell means the document does not reference that concept at all — this is recorded as an absence, not treated as agreement or disagreement. Every row is marked **Requires implementation verification** — this report does not conclude which version reflects (or should reflect) the actual code.

## 3. Top-Level Envelope Differences

| Field | Consultation Response Contract | Sprint 6 Architecture example | Consultation State Machine | System Architecture |
|---|---|---|---|---|
| `schema_version` | Present, required (§4, §15) | Not present in the example | Not referenced | Not referenced |
| `response_id` | Present, required (§4, §15) | Not present | Not referenced | Not referenced |
| `session_id` | Present, required (§4, §15) | Not present | Not referenced | Not referenced |
| `consultation_id` | Present, nullable (§4, §5) | Not present | Not referenced | Not referenced |
| `turn_index` | Present, required, monotonic (§3, §5, §14) | Not present | Referenced indirectly via "turn" language in stage descriptions (e.g. "turn 2"), no field path given | Not referenced |
| `response_type` | Present, enum of 7 values: `greeting`, `discovery`, `clarification`, `qualification`, `recommendation`, `completion`, `error` (§3, §5) | Not present as a top-level field; closest analogue is `conversation.stage` (§ below) | Defines 9 internal stages: Greeting, Discovery, Business Understanding, Pain Point Analysis, AI Readiness Assessment, Lead Qualification, Recommendation, Summary, Completion (§4) — explicitly internal, "never exposed to the visitor" | Not defined; Section 9 references "the consultation lifecycle" generically, deferring to the State Machine |
| `assistant_message` vs `conversation.message` | Nested: `conversation.message` (§6) | Top-level field: `assistant_message` (worked example) | References "the natural-language reply" conceptually, no explicit JSON path given | Not defined |
| `error` (top-level object) | Present, nullable, populated on `response_type: "error"` (§4, §17) | Not present in the example | Not referenced | Not defined |

**Requires implementation verification.**

## 4. Conversation Section Differences

| Field | Contract | Sprint 6 Architecture example | State Machine | System Architecture |
|---|---|---|---|---|
| `conversation.message` | Present (§6) | Absent — message content is at top-level `assistant_message` instead | Not specified as a field path | Not defined |
| `conversation.stage` | Not present — Contract uses top-level `response_type` instead | Present, e.g. `"DISCOVERY"` (worked example) | Uses internal stage names (Greeting, Discovery, Business Understanding, etc.) — not shown as tied to a specific field path | Section 7 note names `conversation.stage` when quoting the Sprint 6 example |
| `conversation.should_continue` | Not present anywhere in the Contract | Present, boolean (worked example) | Not referenced | Not defined |
| `conversation.completion_percentage` | Not present under `conversation`; Contract instead defines `metadata.completeness` (§12) | Present, e.g. `35` (worked example) | References `metadata.completeness` (e.g. Greeting stage: "`metadata.completeness: 0`") and, separately, a `conversation_progress.stage` concept (§ below) — neither matches `conversation.completion_percentage` exactly | Not defined |
| `conversation.next_question` | Not present; Contract instead defines `conversation.follow_up_question` (§6) | Present (worked example) | Not referenced by exact field path | Not defined |
| `conversation.tone`, `conversation.suggested_replies`, `conversation.language` | All present (§6) | None of the three appear in the worked example | Not referenced | Not defined |
| `conversation_progress` (as an object) | Not present anywhere in the Contract's field tables | Not present | Referenced repeatedly (e.g. "`conversation_progress.stage` moves to..."), implying a field that does not appear in the Contract | Not defined |

**Requires implementation verification.**

## 5. Business Profile Section Differences

| Field | Contract | Sprint 6 Architecture example | State Machine | System Architecture |
|---|---|---|---|---|
| Value representation | Every leaf field wrapped in a "value envelope": `{value, raw_text, confidence, status, captured_at_turn}` (§7) | Plain scalar values, e.g. `"industry": "Logistics"` — no envelope, no confidence, no status | References "industry chip," "business_size chip" and per-field `confidence`/`status`-like behavior conceptually (e.g. "confirmed," "inferred," "declined" are used in Section 6 of the State Machine document), but does not show a JSON shape | Not defined |
| `pain_points` | Array of objects: `{description, category, severity, confidence, captured_at_turn}` (§7) | Array of plain strings, e.g. `["Manual inventory management"]` | Referenced as a list, "newest first" — no object shape given | Not defined |
| `goals` | Field name used (§7) | Field named `business_goals` instead | Not referenced by exact field name | Not defined |
| `current_tools` | Field name used (§7) | Field named `current_systems` instead | Not referenced by exact field name | Not defined |
| `budget` / `timeline` | **Not present** in the Contract's `business_profile` field table (§7) at all — these concepts appear only implicitly via `lead_qualification`-adjacent slots in other TASC documents outside this comparison scope | Present directly under `business_profile`: `"budget": null`, `"timeline": null` | Referenced as gathered during the "Lead Qualification" stage (§4.6), not tied to `business_profile` | Not defined |
| `decision_maker` | Present as `decision_maker` (envelope-wrapped) (§7) | Present as `decision_maker` (plain value, `null` in example) | Referenced as "decision role," gathered in "Business Understanding" (§4.3) | Not defined |
| `completeness_percentage` | Present under `business_profile` (§7) | Not present under `business_profile` — closest analogue is `conversation.completion_percentage`, a different field path entirely | Not referenced by exact field path | Not defined |

**Requires implementation verification.**

## 6. AI Readiness Section Differences

| Item | Contract | Sprint 6 Architecture example | State Machine | System Architecture |
|---|---|---|---|---|
| `ai_readiness` section (entire) | Present as a full top-level section: `digital_maturity_level`, `current_automation_level`, `data_infrastructure_status`, `ai_readiness_score`, `readiness_factors`, `blockers`, `opportunities` (§8) | **Absent from the worked JSON example entirely** — though "Assess AI readiness" is listed as a Consultation Philosophy goal in prose elsewhere in the same document | Present conceptually as its own consultation stage ("AI Readiness Assessment," §4.5) with matching field names (`ai_readiness`, `ai_readiness_score`) referenced in "Expected Dashboard Updates" | Not defined independently |

This is the largest single structural gap found: one document (Sprint 6 Architecture) states the goal in prose but its own worked example does not include the section at all, while two other documents (Contract, State Machine) define and reference it as a first-class part of the object.

**Requires implementation verification.**

## 7. Lead Qualification Section Differences

| Field | Contract | Sprint 6 Architecture example | State Machine | System Architecture |
|---|---|---|---|---|
| Banding field name | `band`, enum `cold`/`warm`/`qualified`/`hot`/`not_a_lead` (§9) | `level`, value shown as `"Warm"` (capitalized, different casing convention) | References `lead_qualification.band` and `lead_qualification.score` by these exact names (e.g. Lead Qualification stage, §4.6) | Section 7 note quotes `lead_qualification.level`/`confidence` when describing the Sprint 6 example |
| `confidence` at the qualification level | **Not present** — Contract's `lead_qualification` object has no `confidence` field (confidence appears elsewhere, e.g. per-recommendation and per-business-profile-field) (§9) | Present: `"confidence": 0.82` | Not referenced | Section 7 note quotes it as part of the discrepancy |
| `raw_score` | Present (§9, §11.4 of related documents) | Not present | Not referenced by exact field name | Not defined |
| `score_breakdown` | Present, object with 6 named components (§9) | Not present | Referenced ("`lead_qualification.score`, `score_breakdown`, and `band` become fully computed," §4.6) — matches Contract's naming | Not defined |
| `qualification_status` | Present, object with 6 checklist keys: `business_context_understood`, `challenges_identified`, `solution_matched`, `timeline_established`, `budget_discussed`, `contact_captured` (§9) | Not present | Present, same 6 keys referenced by the same names across multiple stages (§4.3, §4.4, §4.8) | Not defined |
| `overrides_applied`, `justification` | Both present (§9) | Neither present | Not referenced | Not defined |

**Requires implementation verification.**

## 8. Recommendations Section Differences

| Field | Contract | Sprint 6 Architecture example | State Machine | System Architecture |
|---|---|---|---|---|
| Service identifier | `service_id` + `service_name` (two fields) (§10) | `service` (single field, e.g. `"Inventory Automation"`) | References "`recommended_services`" and "`recommendations[]`" generically, no field-level breakdown | Not defined |
| Priority representation | `priority_rank`, integer, unique ordering (§10) | `priority`, string value (e.g. `"High"`) | Not referenced by exact field name | Not defined |
| Rationale field name | `rationale` (§10) | `reason` | Not referenced by exact field name | Not defined |
| `confidence` | Present, float 0.0–0.98 (§10) | **Not present** in the worked example at all | Referenced as "confidence tiers" (§4.7: "confidence tiers" visible on the dashboard) — implies a confidence value exists, consistent with the Contract, not the Sprint 6 example | Not defined |
| `supporting_evidence_refs` | Present (§10) | Not present | Not referenced | Not defined |
| Max count | 3 (§10, consistent with Sprint 6 Architecture's prose: "max 3") | Not shown in the single-item worked example, but stated in prose elsewhere in the same document ("max 3") | Not referenced with a specific number | Not defined |

**Requires implementation verification.**

## 9. Workflow Actions Section Differences

| Aspect | Contract | Sprint 6 Architecture example | State Machine | System Architecture |
|---|---|---|---|---|
| Data shape | Array of trigger-record objects: `{action_type, target_system, trigger_condition, idempotency_key, status, payload_ref}` (§11) | A single flat object of three booleans: `{save_to_google_sheets, notify_sales, send_followup_email}` | References `workflow_actions[]` as an array populating at completion (§4.9) — array shape matches Contract, not the Sprint 6 example | Section 7 note quotes `workflow_actions.save_to_google_sheets` (boolean) as part of the discrepancy |
| `idempotency_key` | Present, required on every action (§11) | Not present in any form | Not referenced | Not defined |
| Action typing | Enum `action_type` distinguishing `log_lead`, `send_notification_email`, `schedule_followup`, `update_crm_record`, `trigger_human_handoff`, `none` (§11) | No action-type enum — each automation target is its own boolean flag instead | Not referenced by exact field name | Not defined |

This is a structural (not just naming) difference: one document represents workflow actions as a list of records, the other as a flat set of boolean flags. These are not reconcilable by a field rename alone.

**Requires implementation verification.**

## 10. Metadata Section Differences

| Field | Contract | Sprint 6 Architecture example | State Machine | System Architecture |
|---|---|---|---|---|
| Fields present | `model_provider`, `model_name`, `prompt_version`, `latency_ms`, `token_usage`, `correlation_id`, `environment`, `completeness`, `generated_at` (9 fields) (§12) | `model`, `timestamp` (2 fields) | References `metadata.completeness` specifically (§4.1, §4.9), consistent with the Contract's field name | Not defined |
| Model identification | Split across `model_provider` + `model_name` | Single combined `model` field (e.g. `"gpt-4.1"`) | Not referenced | Not defined |
| Timestamp field name | `generated_at` | `timestamp` | Not referenced | Not defined |

**Requires implementation verification.**

## 11. Stage / Phase Terminology Differences

| Concept | Contract | Sprint 6 Architecture | State Machine | System Architecture |
|---|---|---|---|---|
| Number of distinct stages/phases | 7 `response_type` values | 1 example value shown (`DISCOVERY`); full enum not specified anywhere in the document | 9 internal stages | Defers to State Machine, does not assert a count |
| Whether stage is visitor-facing / API-facing | `response_type` is a top-level API field, implicitly consumer-facing | `conversation.stage` is a field within the response object, implicitly consumer-facing | Explicitly states internal stages are **never exposed** to the visitor and are for internal reasoning only (§2, principle 1) | Not addressed |
| Mapping between the three stage schemes | Not defined in any document | — | — | Section 7 note observes the naming mismatch but does not attempt a mapping |

Whether `response_type` (Contract), `conversation.stage` (Sprint 6 example), and the State Machine's 9 internal stages are meant to be the same concept at different granularities, or genuinely separate concepts (one API-facing, one internal), is not established by any of the four documents.

**Requires implementation verification.**

## 12. Fields Referenced by Only One Document

For completeness, the following fields appear in exactly one of the four documents, with no corresponding reference (matching or conflicting) in any other:

| Field | Appears only in |
|---|---|
| `schema_version`, `response_id`, `session_id`, `consultation_id`, `turn_index`, `error` (top-level object) | Consultation Response Contract |
| `conversation.should_continue` | Sprint 6 Architecture example |
| `conversation_progress` (as a named object) | Consultation State Machine |
| The Section 7 discrepancy note itself (a meta-reference, not a field) | System Architecture |

**Requires implementation verification.**

## 13. Summary of Findings

- The Consultation Response Contract and the Consultation State Machine are largely — though not perfectly — consistent with each other in field naming (`band`, `qualification_status`, `ai_readiness`, `ai_readiness_score`, `metadata.completeness`, `workflow_actions[]` as an array all match across both documents).
- The Sprint 6 Architecture document's own worked example diverges from both of the above on nearly every section: top-level envelope fields, the conversation object's shape, business profile field names and value representation, the entire `ai_readiness` section (absent), qualification field names and an added `confidence` field, recommendation field names and a missing `confidence` field, and — most structurally — `workflow_actions` represented as flat booleans rather than an array of records.
- System Architecture introduces no new field definitions; it only quotes a subset of the Sprint 6 Architecture / Contract disagreement in its Section 7 note.
- No document in this comparison has visibility into the actual FastAPI/Pydantic implementation. It is therefore not possible, from these four documents alone, to determine which naming convention, if any, matches what the code currently returns.

## 14. Recommendation

The final Consultation Response Object contract should be reconciled against the **implemented FastAPI/Pydantic models**, via code review, rather than by further comparison of these design documents against one another. Each row in this report marked **Requires implementation verification** should be checked against the actual response model(s) in the codebase, and the authoritative field name/shape recorded from that source — not selected by preference among the four documents compared here.

This report makes no recommendation as to which document's version of any field is correct, and modifies none of the four documents it compares.