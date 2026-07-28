# TASC AI & Automation Blueprint v1.0

# Trizen AI Solutions Consultant (TASC)
**Definitive AI & Automation Blueprint**

| Field | Value |
| ---| --- |
| Document ID | TASC-AI-AUTO-001 |
| Version | 1.0 |
| Status | Implementation-ready |
| Product authority | [](https://app.clickup.com/90152654557/docs/2kyr8npx-515) |
| Backend compatibility | [](https://app.clickup.com/90152654557/docs/2kyr8npx-575) |
| Frontend compatibility | [](https://app.clickup.com/90152654557/docs/2kyr8npx-595) |
| Audience | AI engineers, prompt engineers, backend engineers, automation engineers, Claude Code, Cursor |
| Scope | AI consultation intelligence, RAG, structured outputs, qualification, recommendations, and n8n handoff |

* * *
## Architecture reconciliation and binding decisions
The PRD is the source of truth for product behaviour. The Backend Blueprint is the source of truth for backend boundaries and transport contracts. The Frontend Blueprint is the source of truth for presentation and browser state. This document defines intelligence and automation within those boundaries.

| Finding | Binding decision |
| ---| --- |
| The requested framework names ten stages, while the PRD defines six runtime phases: Greeting, Discovery, Exploration, Recommendation, Qualification, Capture and Close. | Use the PRD's six runtime phases as the actual state machine. The requested ten-stage framework is an analytical decomposition mapped onto those six phases, not a new product flow. |
| The requested framework includes AI Readiness, Digital Maturity, Expected ROI, and Business Model. | Extract these as optional enrichment fields when evidence appears. They do not become mandatory discovery questions, new score dimensions, or new panel cards unless already supported by the PRD. |
| The requested brief asks for Confidence Score and Estimated Business Fit. | Keep qualification confidence internal and payload-facing. The visitor panel follows the PRD and frontend blueprint: no separate internal confidence-maths card and no new fit metric. |
| The Backend Blueprint says recommendations are deterministic rules plus evidence, with the model writing rationale. | Preserve this exactly. The model never selects a service, assigns a score, or changes routing. |
| The Backend Blueprint specifies REST endpoints and an SSE response for message turns. | FastAPI remains the only frontend integration point. AI stages emit backend-owned phase events; the browser only renders them. |
| The PRD says n8n is orchestration only. | n8n validates, routes, formats, and delivers. It performs no AI calls, scoring, recommendation, qualification, or business-rule reinterpretation. |
| The Backend Blueprint includes an AutomationPayload with routing flags. | FastAPI computes routing flags. n8n consumes them and executes delivery actions without deriving a competing policy. |

## Normative language
**MUST** is mandatory. **SHOULD** is the default unless a written exception exists. **MAY** is optional. Every implementation task, test, prompt change, and workflow change MUST reference the relevant PRD, Backend Blueprint, or AI rule identifier.

* * *
# 1\. AI Philosophy
## 1.1 Product stance
Nova is a senior pre-sales consultant represented through a conversational interface. The objective is not to answer an endless stream of questions. The objective is to understand a business well enough to give an honest service recommendation, establish whether a human follow-up is worthwhile, and hand that human a reliable briefing.

Nova must move the consultation forward on every turn by doing at least one of four things: filling a meaningful discovery gap, answering a grounded company question, testing a solution hypothesis, or progressing toward qualification and contact capture.
## 1.2 Consultant versus chatbot

| Traditional chatbot behaviour | Nova behaviour |
| ---| --- |
| Waits for arbitrary questions | Leads with a structured discovery objective |
| Treats every message as an isolated prompt | Maintains server-side state and durable slot values |
| Answers from model memory | Answers Trizen questions from retrieved knowledge or defers |
| Makes recommendations from vague similarity | Uses deterministic service mapping plus retrieval evidence |
| Produces a transcript | Produces a validated consultation payload |
| Hides progress | Makes understanding visible through backend snapshots and the Live Analysis Panel |
| Treats confidence as tone | Separates extraction confidence, qualification confidence, and visitor-safe output |
| Optimises for conversation length | Optimises for useful discovery with the fewest necessary turns |

## 1.3 Behavioural laws
1. **Grounded or silent:** factual claims about Trizen, services, proof, pricing bands, process, or timelines require retrieved evidence. Otherwise Nova defers.
2. **One question per turn:** Nova may answer and then ask one discovery question. It must not interrogate with a list.
3. **State before prose:** structured extraction, merge, scoring, recommendation, and phase selection happen before response generation.
4. **Model proposes, code disposes:** model outputs are validated, normalised, constrained, and rejected when they violate business rules.
5. **No commercial invention:** no firm price, delivery commitment, client reference, or capability claim absent from approved knowledge.
6. **Respectful qualification:** budget, authority, and contact are asked after value is established and can be declined.
7. **No silent state changes:** if new evidence changes a recommendation, Nova acknowledges the revision.
8. **Human handoff is a feature:** uncertainty should create a clear consultant follow-up, not a bluff.
## 1.4 Decision ownership

| Decision | Owner |
| ---| --- |
| Intent classification | Model through constrained structured output, with a deterministic fallback |
| Slot extraction | Model through constrained structured output, then deterministic normalisation and merging |
| Next question | Deterministic `QuestionSelector` |
| Retrieval decision | Deterministic intent map and phase rules |
| Retrieved evidence | ChromaDB plus embedding provider |
| Lead score and band | Deterministic qualification engine |
| Service candidate selection and ranking | Deterministic catalogue mapping plus evidence boosts |
| Rationale wording | Model, constrained to selected services and stated pains |
| Executive summary wording | Model from validated state, with deterministic fallback |
| Automation routing | FastAPI-computed payload flags consumed by n8n |

* * *
# 2\. AI Consultant Framework
The requested ten-stage framework is a conceptual decomposition. The runtime implementation uses the six PRD phases shown in the `Runtime phase` column.

| Stage | Runtime phase | Goal | Primary inputs | Outputs | Exit condition | Required information | Conversation strategy |
| ---| ---| ---| ---| ---| ---| ---| --- |
| 1\. Greeting | Greeting | Establish Nova's role and invite the visitor's problem | Session metadata | Static greeting, opening question | First visitor message | None | Warm, concise, no model call |
| 2\. Business Discovery | Discovery | Identify industry, size, pain points, tools, and goals | Visitor message, current slots | Slot deltas, intent, next question | Three or more core slots at confidence 0.6+ or company question | Industry and at least one pain point are preferred | Reflect, then ask the highest-value missing question |
| 3\. Business Understanding | Discovery / Exploration | Build a coherent profile rather than collect disconnected fields | Merged slots, transcript summary | Business profile, contradictions, confidence | Profile is sufficient to test a solution hypothesis | Pain, current process, desired outcome | Use plain business language; avoid premature commercial questions |
| 4\. Pain Point Analysis | Exploration | Clarify process failure, severity, frequency, and impact | Pain points, tools, goals | Specificity, quantified impact, service mappings | At least two usable pain points or a clear single high-impact problem | Pain statement and operational detail | Ask for the bottleneck or measurable consequence |
| 5\. AI Readiness Assessment | Exploration | Determine whether automation or AI is appropriate and feasible | Process repeatability, data availability, tools, maturity | Optional AI readiness and digital maturity fields | Enough evidence for recommendation or a clear non-AI path | Repeatability, data, ownership, constraints | Ask only when it changes the solution hypothesis |
| 6\. Opportunity Identification | Exploration / Recommendation | Identify improvement opportunities without promising outcomes | Pain mappings, goals, evidence | Opportunity hypotheses | Candidate service confidence clears floor | Two pain points and evidence or strong catalogue mapping | Present opportunities as hypotheses, not guarantees |
| 7\. Solution Mapping | Recommendation | Rank one to three Trizen services | Candidate set, evidence, constraints | Ranked recommendation set and rationales | Visitor responds to recommendation | Service fit and stated pain reference | Lead with the problem, then the service, then expected outcome category |
| 8\. Lead Qualification | Qualification | Establish urgency, budget band, authority, and engagement | Timeline, budget, decision role, engagement | Score, band, confidence, next contributor | Commercial slots filled or declined | Timeline and contact are most important for handoff | Explain why the information helps scope follow-up; accept refusal |
| 9\. Consultation Summary | Capture and Close | Give the visitor and consultant a shared understanding | Validated state, score, recommendations | Executive summary and structured summary | Summary validates and contact consent is captured where applicable | Situation, needs, services, qualification, next step | Summarise facts, not hidden reasoning |
| 10\. Automation | Capture and Close | Hand off exactly once to n8n | Validated AutomationPayload | Sheets, email, Telegram actions and acknowledgement | n8n acknowledges or dead-letters | Payload schema, idempotency key | Visitor is not blocked by delivery |

## 2.1 Stage control rules
*   The system MUST skip a stage when the visitor has already supplied its required evidence.
*   The system MUST not ask a question solely to fill an optional enrichment field.
*   A visitor company question can interrupt Discovery or Exploration; Nova answers it, then resumes the highest-value missing discovery slot.
*   A visitor request for a human jumps to Capture and Close without forcing a full discovery sequence.
*   An anti-persona classification terminates qualification and suppresses sales automation.
*   The framework never exposes stage names as internal process jargon. The visitor sees the PRD-approved progress labels: Understanding, Exploring, Recommending, Qualifying, Wrapping up.

* * *
# 3\. Conversation State Machine
## 3.1 Runtime states

| State | Meaning | Allowed actions |
| ---| ---| --- |
| `greeting` | Session created, static greeting available | Accept first visitor message |
| `discovery` | Core business slots being filled | Ask one discovery question, answer grounded questions |
| `exploration` | Pain and opportunity evidence being deepened | Retrieve knowledge, test hypotheses, clarify impact |
| `recommendation` | Ranked services ready to present | Present and check resonance |
| `qualification` | Commercial and authority context being established | Ask timeline, budget, role, contact when appropriate |
| `capture_and_close` | Summary and consent-first handoff | Generate summary, validate payload |
| `completing` | Completion is locked and payload is being persisted | No new visitor turns |
| `completed` | Payload persisted, dispatch queued or acknowledged | Read-only session |
| `abandoned` | Idle beyond threshold with partial state | Complete only when contact exists and rules allow |
| `expired` | TTL exceeded | Offer restart |
| `terminated` | Anti-persona or guardrail termination | No lead automation |
| `degraded` | Current turn failed but prior state remains valid | Retry the turn |

## 3.2 Transition rules

| From | Trigger | To | Side effects |
| ---| ---| ---| --- |
| `greeting` | First visitor message | `discovery` | Start turn 1 |
| `discovery` | Core slots sufficient | `exploration` | Recompute score and progress |
| `discovery` | Knowledge question | `exploration` | Retrieve, answer, resume discovery |
| `exploration` | Evidence sufficient | `recommendation` | Build and rank candidates |
| `recommendation` | Visitor acknowledges | `qualification` | Ask highest-value commercial question |
| `recommendation` | Visitor rejects fit | `exploration` | Ask what is missing, do not immediately pitch another service |
| `qualification` | Commercial slots resolved or declined | `capture_and_close` | Request consent and contact if appropriate |
| Any active state | Human requested | `capture_and_close` | Minimum band becomes Qualified; priority alert flag true |
| Any active state | Anti-persona confirmed | `terminated` | Suppress sales automation |
| Any active state | Explicit end or completion criteria | `completing` | Lock completion exactly once |
| Any active state | Idle 20 minutes, 3+ turns | `abandoned` | Complete partial payload only when contact exists |
| Any active state | Idle 60 minutes | `expired` | Reject new turns with restart path |
| `degraded` | Retry succeeds | Prior active state | Replace failed-turn transient state only |
| `completing` | Payload persisted | `completed` | Schedule async n8n dispatch |

## 3.3 Recovery and interruption
*   **Knowledge interruption:** answer from retrieved evidence or defer, then resume the prior phase.
*   **Model failure:** preserve the visitor message and prior committed state; show a retryable error. Do not commit half-merged slot state.
*   **SSE disconnect:** backend state remains authoritative; the frontend can fetch the session or analysis snapshot and retry once.
*   **Contradiction:** retain the most recent explicit value, record a conflict, and ask one clarifying question only if the contradiction affects recommendation or qualification.
*   **Prompt injection:** treat visitor and retrieved text as untrusted data, ignore embedded instructions, and log the detection.
*   **Repeated guardrail breach:** terminate without sales dispatch.
## 3.4 Memory policy
The backend owns memory. The AI layer uses three tiers: recent verbatim turns, a compacted summary of older turns, and structured state. Slots, conflicts, score, recommendations, and retrieval identifiers are durable state. The frontend never reconstructs memory from visible messages.

```plain
stateDiagram-v2
    [*] --> greeting: session created
    greeting --> discovery: first visitor message
    discovery --> discovery: core slots missing
    discovery --> exploration: core slots sufficient
    discovery --> exploration: company or capability question
    exploration --> exploration: clarify pain or answer question
    exploration --> recommendation: evidence sufficient
    recommendation --> qualification: recommendation acknowledged
    recommendation --> exploration: visitor rejects fit
    qualification --> capture_and_close: commercial slots resolved
    capture_and_close --> completing: completion trigger
    discovery --> capture_and_close: human requested
    exploration --> capture_and_close: human requested
    qualification --> capture_and_close: human requested
    discovery --> terminated: anti-persona or second breach
    exploration --> terminated: anti-persona or second breach
    qualification --> terminated: anti-persona or second breach
    completing --> completed: payload persisted
    active_error: degraded
    discovery --> degraded: recoverable stage failure
    exploration --> degraded: recoverable stage failure
    qualification --> degraded: recoverable stage failure
    degraded --> discovery: retry succeeds, prior phase discovery
    degraded --> exploration: retry succeeds, prior phase exploration
    degraded --> qualification: retry succeeds, prior phase qualification
    completed --> [*]
    terminated --> [*]
    expired --> [*]
```

* * *
# 4\. Business Understanding Framework
The business profile is a structured evidence record. A field can be populated only from visitor evidence, approved knowledge, or a deterministic inference explicitly marked as inferred. The model's confidence is not the same as business certainty.

| Field | Type | Required | Meaning | Capture rule |
| ---| ---| ---| ---| --- |
| `industry` | Controlled enum plus raw text | Preferred | Sector in which the business operates | Normalise to approved vocabulary; retain raw phrase |
| `company_size` | Controlled band plus raw text | Preferred | Approximate employee or operating scale | Accept employee count or operational scale; do not fabricate |
| `business_model` | Enum plus description | Optional | How the organisation creates and captures value | Extract only when explicit |
| `target_customers` | List of descriptions | Optional | Customers or users served | Preserve visitor wording |
| `pain_points` | List of pain objects | Required for recommendation | Operational problems causing cost, delay, risk, or lost growth | Each item gets specificity, impact, and service mapping |
| `current_tools` | List | Optional | Systems used today | Append and deduplicate |
| `manual_processes` | List | Recommended | Repetitive or human-dependent workflows | Capture named process, frequency, and owner when available |
| `growth_stage` | Enum | Optional | Exploring, early, scaling, established, enterprise | Never infer from company size alone |
| `technical_maturity` | Enum | Optional | Ad hoc, developing, standardised, advanced | Evidence from tooling, ownership, deployment, and data practices |
| `budget_band` | Controlled enum | Optional | Indicative available investment band | Ask after value; `undisclosed` and `declined` are valid |
| `timeline` | Controlled enum | Recommended | Desired start or live window | Keep raw date language and normalised band |
| `decision_authority` | Enum | Recommended | Decision maker, influencer, researcher, unknown | Capture explicit role, not title assumptions |
| `urgency` | Enum | Optional | Impact of delay and operational pressure | Derived only when evidence supports it; do not double-count silently |
| `ai_readiness` | Enum plus factors | Optional enrichment | Suitability and readiness for an AI-enabled solution | Derived from repeatability, data, ownership, and process stability |
| `digital_maturity` | Enum plus evidence | Optional enrichment | Broader technology and process maturity | Must not become a new mandatory question |
| `expected_roi` | Structured estimate or raw expectation | Optional | Visitor's stated or quantified expected benefit | Store as expectation, not forecast |
| `confidence` | Per-field 0 to 1 | Required on populated fields | Evidence confidence from extraction and normalisation | Does not equal lead quality |
| `source_turn` | Integer | Required on populated fields | Visitor turn where evidence appeared | Enables auditability |
| `declined` | Boolean | Required | Visitor explicitly declined the field | Terminal for question selection |

## 4.1 Pain point object

| Field | Definition |
| ---| --- |
| `id` | Stable session-local identifier |
| `label` | Concise visitor-grounded description |
| `raw_text` | Original phrase or sentence |
| `specificity` | `vague`, `specific`, or `quantified` |
| `severity` | Optional `low`, `medium`, `high`, `critical`, only when evidenced |
| `frequency` | Optional cadence or volume |
| `impact` | Optional time, cost, headcount, risk, or growth consequence |
| `service_codes` | Deterministic mappings from the catalogue |
| `confidence` | Extraction confidence |
| `source_turn` | Origin turn |

## 4.2 AI readiness factors
AI readiness is an enrichment assessment, not a new product score unless the existing qualification dimensions consume it through configured fit or feasibility logic.

| Factor | Evidence |
| ---| --- |
| Process repeatability | Same steps occur frequently with stable rules |
| Data availability | Required inputs exist in accessible digital systems |
| Data quality | Inputs are sufficiently consistent for automation |
| Process ownership | A person or team can approve and maintain the change |
| Exception rate | Most cases follow a predictable path |
| Integration feasibility | Current tools expose usable interfaces or workflows |
| Change readiness | Stakeholders express willingness and a workable timeline |

The output is `high`, `medium`, `low`, or `unknown`, plus factor-level evidence. It is never represented as a magical percentage.

* * *
# 5\. Lead Qualification Engine
## 5.1 Design stance
This is not BANT. Qualification asks whether there is a meaningful, solvable business problem with enough impact, fit, feasibility, intent, and organisational access to justify human follow-up. The score remains deterministic, explainable, and configuration-driven as required by PRD FR-30 to FR-36.
## 5.2 Dimensions and weights
The existing PRD rubric has six components totalling 100. The requested consulting dimensions map into those components without creating a second competing score.

| Consulting dimension | PRD component | Weight |
| ---| ---| --- |
| Business need | Need clarity | 15 |
| Pain severity and business impact | Need clarity | 10 |
| Operational complexity | Fit | 5 |
| AI readiness and implementation feasibility | Fit | 8 |
| Strategic fit with Trizen services | Fit | 7 |
| Timeline and urgency | Urgency | 15 |
| Budget alignment | Budget | 15 |
| Decision authority | Authority | 10 |
| Engagement and willingness to progress | Engagement | 15 |
| Total |  | 100 |

The implementation may retain the Backend Blueprint's named components `need_clarity`, `fit`, `urgency`, `budget`, `authority`, and `engagement`, while the sub-factors above explain their basis. Do not add a second score called AI readiness score or business fit score.
## 5.3 Scoring rules

| Component | Maximum | Deterministic basis |
| ---| ---| --- |
| Need clarity | 25 | Number, specificity, and quantified impact of pain points |
| Fit | 20 | Service mapping, case coverage, operational complexity, readiness and feasibility evidence |
| Urgency | 15 | Normalised timeline and evidenced cost of delay |
| Budget | 15 | Budget band alignment with indicative engagement shape |
| Authority | 10 | Decision role |
| Engagement | 15 | Substantive turns, company questions, recommendation response, voluntary contact |

Score formula: `clamp(sum(component_scores), 0, 100)`, then apply configured overrides, then assign band. The model never supplies points.
## 5.4 Qualification confidence
`qualification_confidence` is separate from `lead_score`.

`weighted_mean(filled scoring slot confidences) × slot coverage factor`

The confidence is used in internal routing and sales context, not to alter the score. Low confidence means the evidence is thin, not that the visitor is a bad lead.

| Confidence | Meaning |
| ---| --- |
| Below 0.50 | Thin evidence, sales briefing flags review |
| 0.50 to 0.75 | Reasonable evidence |
| Above 0.75 | Strong evidence for normal routing |

## 5.5 Bands and overrides

| Band | Score | Routing meaning |
| ---| ---| --- |
| Cold | 0 to 34 | Early exploration |
| Warm | 35 to 59 | Clear need, weak commercial signal |
| Qualified | 60 to 79 | Strong fit and at least one commercial signal |
| Hot | 80 to 100 | Clear need, fit, urgency, budget and authority |
| Not a lead | Override | Anti-persona or terminated session |

Overrides remain the PRD rules: anti-persona forces `not_a_lead`; explicit human request floors at Qualified; absent contact caps at Warm; fewer than two visitor turns forces Cold; enterprise decision-maker floors at Qualified; abandonment marks partial.

```plain
flowchart TD
    A[Validated business profile and engagement signals] --> B[Compute need clarity]
    B --> C[Compute fit, readiness and feasibility]
    C --> D[Compute urgency]
    D --> E[Compute budget alignment]
    E --> F[Compute authority]
    F --> G[Compute engagement]
    G --> H[Sum and clamp 0-100]
    H --> I[Apply ordered overrides]
    I --> J[Compute qualification confidence]
    J --> K[Assign Cold, Warm, Qualified or Hot]
    K --> L[Identify next score contributor]
    L --> M[Build structured qualification result]
    M --> N{Completion or handoff trigger?}
    N -->|yes| O[Assemble AutomationPayload]
    N -->|no| P[Continue consultation]
```

* * *
# 6\. Recommendation Engine
## 6.1 Responsibility boundary
The recommendation engine selects service codes deterministically. The model may write a rationale for selected codes, but it cannot create, remove, reorder, or rename services.
## 6.2 Algorithm
1. Read validated pain points, goals, industry, company size, budget, and current tools.
2. Map pain signals to candidate service codes using `pain_mapping.yaml`.
3. Drop codes absent from `services.yaml`.
4. Aggregate distinct pain matches and calculate the frequency factor.
5. Add retrieval evidence boost for chunks whose service codes match.
6. Add industry match boost where approved case-study evidence exists.
7. Apply size and budget constraint penalties.
8. Normalise confidence and cap at 0.98.
9. Withhold if fewer than two usable pain points, confidence below 0.6, or phase is too early.
10. Return one to three ranked services.
11. Generate all rationales in one constrained model call.
12. Validate each rationale against stated pain points, banned commercial claims, and public-reference metadata.
13. Substitute a safe template rationale on failure.

`candidate_score = base_weight × pain_frequency_factor + evidence_boost + industry_match_boost − constraint_penalty`
## 6.3 Supporting evidence
Every emitted recommendation carries evidence chunk identifiers internally and in the AutomationPayload. Visitor-facing cards show only the rationale and approved confidence label. Evidence must be sufficient for the claim made: a case-study chunk can support a precedent claim only when `is_public_reference` permits it.
## 6.4 Alternatives
The engine may emit up to three ranked services. A secondary service is an acceptable alternative only when it is independently supported by a mapped pain point or evidence. The model must not invent an alternative because the visitor rejects the primary fit. Rejection returns the conversation to Exploration.
## 6.5 Recommendation invariants
*   No service outside the catalogue.
*   No more than three services.
*   No recommendation below the configured confidence floor.
*   Every rationale references a stated pain or goal.
*   No firm price or delivery date.
*   Changed rankings are acknowledged in the next response.

* * *
# 7\. Knowledge Architecture
## 7.1 Repository structure

```plain
knowledge/
├── manifest.yaml
├── company/
│   ├── about-trizen.md
│   ├── team-and-locations.md
│   └── differentiators.md
├── services/
│   ├── ai-automation.md
│   ├── web-development.md
│   ├── data-engineering.md
│   ├── systems-integration.md
│   ├── cloud-devops.md
│   └── technology-strategy.md
├── industries/
│   ├── logistics.md
│   ├── fintech.md
│   └── approved-industry-patterns.md
├── technology/
│   ├── stack-and-platforms.md
│   └── integration-experience.md
├── faq/
│   ├── general.md
│   ├── engagement.md
│   └── objections.md
├── pricing/
│   └── indicative-bands.md
├── case_studies/
│   ├── logistics-order-automation.md
│   ├── fintech-platform-build.md
│   └── approved-case-study-index.md
├── implementation/
│   ├── discovery-methodology.md
│   ├── delivery-model.md
│   └── quality-and-handover.md
├── qualification/
│   ├── qualification-guidance.md
│   └── disqualification-guidance.md
├── sales_playbook/
│   ├── objection-handling.md
│   └── follow-up-guidance.md
└── glossary.md
```

## 7.2 Document catalogue

| Document family | Purpose | Relationships |
| ---| ---| --- |
| Company | Approved facts about Trizen | Referenced by company questions and summaries |
| Services | Service descriptions, fit, outcomes, engagement shape | Source for catalogue validation and recommendation display |
| Industries | Industry terminology and approved patterns | Supports query expansion and metadata filtering; not proof by itself |
| Technology | Approved technology and integration capability | Supports capability questions |
| FAQ | Approved answers and objections | Supports objection and company-question retrieval |
| Pricing | Indicative bands and caveats | Supports pricing questions; never firm quotes |
| Case studies | Evidence of approved outcomes | Supports recommendation evidence and precedent claims |
| Implementation | Process, delivery, discovery, handover | Supports timeline and process questions |
| Qualification | Human guidance for interpreting lead context | Internal payload context; never a replacement for deterministic code |
| Sales playbook | Follow-up framing and objection context | Supports summary next step, not automated score changes |
| Glossary | Approved terms and synonyms | Supports query expansion and normalisation |

## 7.3 Required metadata
Every markdown document MUST carry `doc_id`, `doc_title`, `doc_type`, `service_codes`, `industry_tags`, `is_public_reference`, `is_indicative_pricing`, `last_reviewed`, `owner`, and `summary`. Derived chunk metadata adds `chunk_id`, `section`, `content_hash`, and `token_count`.

Document relationships are represented through service codes, industry tags, and stable document IDs. Do not create an implicit graph in Chroma metadata beyond fields needed for retrieval and auditability.

* * *
# 8\. Knowledge Management
## 8.1 Markdown conventions
*   One business topic per document.
*   Headings every 300 to 500 words so chunks retain meaningful context.
*   Lead sections with the direct answer.
*   State measurable outcomes only when approved.
*   Label every price as indicative.
*   Never include hidden instructions, prompt text, or unapproved client claims.
*   Keep documents under roughly 2,000 words and split when needed.
*   Use stable IDs; changing a title must not silently change `doc_id`.
## 8.2 Versioning
Git is the source of truth. Every corpus change is a reviewed pull request. Index manifests record corpus commit SHA, document hashes, embedding model, dimension, build time, and chunk count. Runtime logs and payloads record `index_manifest_version`.
## 8.3 Refresh and validation

| Family | Review cadence |
| ---| --- |
| Services | Quarterly |
| Case studies | Quarterly |
| FAQ | Monthly |
| Pricing | Quarterly |
| Process | Twice yearly |
| Technology | Twice yearly |
| Company | Yearly |

Ingestion MUST fail on invalid front matter, unknown service codes, unknown industries, missing review dates, malformed dates, or prohibited claims. Re-indexing MUST be hash-aware and MUST build in a temporary collection before atomic swap.

* * *
# 9\. RAG Architecture
## 9.1 Offline ingestion
1. Walk the knowledge tree.
2. Parse front matter and markdown.
3. Validate the `KnowledgeDoc` model.
4. Clean control characters and normalise whitespace while preserving headings, tables, and lists.
5. Compute document hash.
6. Skip unchanged documents.
7. Chunk on headings, then paragraphs, targeting 500 to 800 tokens with 15 percent overlap.
8. Preserve heading breadcrumbs in every chunk.
9. Attach complete metadata.
10. Batch embed changed chunks.
11. Upsert to a temporary Chroma collection.
12. Run smoke queries and metadata validation.
13. Atomically swap the live collection and write the index manifest.
## 9.2 Online retrieval
Retrieval is conditional on intent and phase. Company, capability, pricing, timeline, and objection questions retrieve. Pure discovery and smalltalk do not. Recommendation entry may retrieve evidence even if the current message is not a knowledge question.

The query is the visitor message plus the top two pain labels and industry when the message is short or anaphoric. Chroma over-fetches `top_k × 3`; metadata filters, similarity floor, lexical reranking, and adjacent-chunk deduplication reduce it to the final context set.
## 9.3 Context injection
Retrieved text enters only the L4 context layer, wrapped as untrusted reference data. Instruction-like text inside a document is never treated as an instruction. Each chunk includes title, section, chunk ID, and metadata needed for the model to understand evidence boundaries.
## 9.4 Citation strategy
Every retrieval event records chunk IDs. The AI layer records the chunk IDs used for each response and carries the union into the consultation payload. Visitor UI does not expose raw citations in MVP. Sales and engineering can trace claims through the payload and logs.

A citation supports a claim only when the chunk contains the relevant fact. A weak similarity score is not a citation. If no chunk clears the floor, enter deferral mode and prohibit factual claims.

```plain
flowchart LR
    A[Markdown source] --> B[Front matter validation]
    B --> C[Cleaning and content hash]
    C --> D{Changed?}
    D -->|no| E[Reuse existing chunks]
    D -->|yes| F[Heading-aware chunking]
    F --> G[Metadata enrichment]
    G --> H[Batch embeddings]
    H --> I[Temporary Chroma collection]
    E --> I
    I --> J[Smoke queries and integrity checks]
    J -->|pass| K[Atomic live index swap]
    J -->|fail| L[Keep existing index]
    K --> M[Intent-based online retrieval]
    M --> N[Query augmentation]
    N --> O[Embedding and over-fetch]
    O --> P[Metadata filter and similarity floor]
    P --> Q[Lexical rerank and dedupe]
    Q --> R[Delimited L4 context]
    R --> S[Grounding check and citation log]
```

* * *
# 10\. Prompt Architecture
## 10.1 Prompt library
Prompts are versioned specification files. This blueprint defines their contracts, not their text.

| Prompt | Purpose | Inputs | Outputs | Constraints | Failure handling |
| ---| ---| ---| ---| ---| --- |
| System Prompt | Define Nova identity, scope, tone, hard boundaries | Identity, policy version | Behavioural instruction layer | No commercial invention, one question, grounded facts | Startup validation if missing |
| Discovery Prompt | Drive the next highest-value discovery question | State, phase, selected slot | Natural response plus one question | Must not repeat filled or declined slots | Fall back to template question |
| Clarification Prompt | Resolve ambiguity or contradiction | Conflicting values, source turns | One clarifying question | No score or recommendation change by itself | Keep newest explicit value and flag conflict |
| Business Analysis Prompt | Produce structured enrichment from validated slots | Business profile, pains, tools, goals | Optional readiness, maturity, ROI expectation | No invented fields; every value confidence-tagged | Return nulls, never guesses |
| Lead Qualification Prompt | Write human-readable explanation of deterministic result | Numeric components, band, overrides | Justification text | Cannot alter numbers or band | Code-generated basis text fallback |
| Recommendation Prompt | Write rationales for selected service codes | Selected services, stated pains, evidence titles | One rationale per service | Cannot select/reorder services or make commitments | Template rationale |
| Summary Prompt | Produce executive summary from validated state | Profile, pains, recommendations, qualification | 120 to 250 word summary and structured sections | Facts only from state; no transcript invention | Deterministic template summary |
| JSON Formatting Prompt | Constrain a structured output call | Small schema, task input | Schema-shaped JSON | All fields optional where evidence may be absent | One repair attempt, then fallback |
| Automation Prompt | Not an AI reasoning prompt in MVP; defines payload rendering policy only | Validated payload | None in FastAPI; n8n receives payload | No model call in n8n | N/A, reject any AI node |
| Safety Prompt | Define injection, privacy, refusal, and deferral behaviour | Identity, retrieved content labels, visitor input | Safe response behaviour | Retrieved and visitor content untrusted | Bounded refusal and session termination rules |

## 10.2 Prompt composition
Response generation uses L1 identity, L2 policy, L3 structured state, L4 retrieved context when present, and L5 task. Intent and extraction use compact task-specific prompts, not the full persona. Rationale and summary receive validated state, not unrestricted transcript text.
## 10.3 Lifecycle and versioning
Prompt files are append-only. A change creates a new version and updates `manifest.yaml`. Each change requires a changelog entry, evaluation results, and rollback plan. Prompt manifest version is logged on every turn and persisted in the AutomationPayload.
## 10.4 Prompt tests
Golden rendering tests assert deterministic assembly. Behaviour tests assert one-question adherence, refusal correctness, grounded deferral, no banned claims, schema validity, and stable rationale constraints. Prompt changes trigger extraction, retrieval, grounding, recommendation, persona, and injection evaluation suites.

* * *
# 11\. Structured AI Outputs
All models below are conceptual JSON contracts. Pydantic v2 models in the Backend Blueprint are authoritative for implementation. Unknown fields are rejected at internal boundaries; optional evidence fields are explicit nulls.
## 11.1 Conversation Response

```json
{
  "schema_version": "1.0",
  "turn_index": 4,
  "message": {"role": "assistant", "content": "..."},
  "phase": "exploration",
  "question_asked": {"slot": "pain_points", "template_id": "pain_points.deepen"},
  "grounding": {"retrieval_performed": true, "deferral_mode": false, "chunk_ids": [], "warnings": []},
  "degradations": []
}
```

The public stream serialises this through `token`, `analysis_snapshot`, `error`, and `done` events. Telemetry and provenance remain internal.
## 11.2 Business Profile

```json
{
  "industry": {"value": "logistics", "raw": "logistics company", "confidence": 0.94, "source_turn": 1, "declined": false},
  "company_size": {"value": "51-200", "raw": "about 180 staff", "confidence": 0.88, "source_turn": 2, "declined": false},
  "business_model": null,
  "target_customers": [],
  "pain_points": [],
  "current_tools": [],
  "manual_processes": [],
  "growth_stage": null,
  "technical_maturity": null,
  "budget_band": null,
  "timeline": null,
  "decision_authority": null,
  "urgency": null,
  "ai_readiness": null,
  "digital_maturity": null,
  "expected_roi": null,
  "conflicts": []
}
```

## 11.3 Lead Qualification

```json
{
  "score": 74,
  "raw_score": 74,
  "band": "qualified",
  "confidence": 0.79,
  "components": [],
  "applied_overrides": [],
  "next_contributor": {"component": "budget", "headroom": 10, "display": "Budget not yet discussed"},
  "justification": "...",
  "disqualified": false,
  "partial": false,
  "ruleset_version": "rs_9c31e0"
}
```

## 11.4 Lead Score

```json
{
  "score": 74,
  "raw_score": 74,
  "components": [
    {"name": "need_clarity", "awarded": 21, "max": 25, "basis": "two specific pain points, one quantified"},
    {"name": "fit", "awarded": 20, "max": 20, "basis": "clear service mapping and evidence"}
  ],
  "overrides": []
}
```

## 11.5 Recommendations

```json
{
  "withheld": false,
  "withheld_reason": null,
  "changed_since_presented": false,
  "items": [
    {
      "service_code": "SVC-AIA",
      "name": "AI Automation and Agents",
      "rank": 1,
      "confidence": 0.87,
      "matched_pain_point_ids": ["pp_01"],
      "evidence_chunk_ids": ["cs-logistics-order-automation#2"],
      "rationale": "...",
      "rationale_source": "model",
      "typical_engagement": "4 to 10 weeks, discovery plus build"
    }
  ]
}
```

## 11.6 Consultation Summary

```json
{
  "executive_summary": "...",
  "word_count": 187,
  "structure": {
    "situation": "...",
    "needs": [],
    "recommended_services": ["SVC-AIA"],
    "qualification": "Qualified, 74",
    "next_step": "Consultant follow-up within one working day"
  },
  "source": "model"
}
```

## 11.7 Automation Payload

```json
{
  "schema_version": "1.0",
  "consultation_id": "01J9XKB2M7QF0R1S2T3U4V5W6X",
  "session_id": "01J9XK7T2ZQ8V3N5B4C6D7E8F9",
  "completion_reason": "criteria_met",
  "partial": false,
  "contact": {"name": "...", "email": "...", "company": "...", "phone": null, "consent": true},
  "business_profile": {},
  "qualification": {},
  "recommendations": [],
  "summary": {},
  "routing": {"send_sales_email": true, "send_telegram_alert": false, "send_visitor_confirmation": true, "append_to_sheet": true, "priority": "follow_up_24h"},
  "conversation": {"turn_count": 9, "transcript_ref": "...", "deferral_count": 1, "grounding_chunk_ids": []},
  "provenance": {"prompt_manifest_version": "...", "ruleset_version": "...", "index_manifest_version": "..."}
}
```

## 11.8 Knowledge Citation

```json
{
  "chunk_id": "cs-logistics-order-automation#2",
  "doc_id": "cs-logistics-order-automation",
  "title": "Northline Logistics order automation",
  "section": "Outcome",
  "similarity": 0.81,
  "claim_types": ["case_study_outcome"],
  "is_public_reference": false,
  "used_in_turn": 4
}
```

## 11.9 Conversation State

```json
{
  "schema_version": "1.0",
  "session_id": "...",
  "status": "active",
  "phase": "exploration",
  "turn_index": 4,
  "messages": [],
  "compacted_summary": null,
  "business_profile": {},
  "qualification": {},
  "recommendations": {},
  "questions_asked": ["industry", "pain_points"],
  "retrieval_log": [],
  "consent": {"granted": false, "granted_at": null},
  "completion": {"consultation_id": null, "reason": null, "completed_at": null}
}
```

## 11.10 Follow-up Questions

```json
{
  "selected_slot": "timeline",
  "question_template_id": "timeline.discovery",
  "reason": "highest_information_gain",
  "question_text": "When are you hoping to have something running?",
  "already_asked": false
}
```

## 11.11 Confidence Analysis

```json
{
  "overall": 0.79,
  "field_confidences": {"industry": 0.94, "company_size": 0.88, "timeline": 0.61},
  "coverage": 0.72,
  "uncertainties": ["decision_authority not established"],
  "effect": "briefing_flag_only"
}
```

Confidence analysis never changes the deterministic score. It explains evidence quality and identifies missing context.

* * *
# 12\. AI Reasoning Pipeline
## 12.1 Normative order

```plain
sequenceDiagram
    autonumber
    participant V as Visitor
    participant O as Orchestrator
    participant G as Guardrails
    participant I as Intent classifier
    participant X as Slot extractor
    participant R as RAG service
    participant Q as Qualification engine
    participant M as Recommendation engine
    participant P as Prompt registry
    participant L as Chat provider
    participant S as Summary generator
    participant A as Payload assembler
    participant N as n8n dispatcher

    V->>O: Visitor message
    O->>G: Validate length, abuse, injection, anti-persona
    G-->>O: Allowed or bounded refusal
    par Understanding
        O->>I: Classify intent
        I->>L: Structured call
        L-->>I: Intent and confidence
    and
        O->>X: Extract slots
        X->>L: Structured call
        L-->>X: Slot deltas
    end
    O->>O: Normalise and merge state
    alt Knowledge intent or recommendation evidence needed
        O->>R: Build query, embed, retrieve, rerank
        R-->>O: Chunks or deferral mode
    end
    O->>Q: Compute deterministic score and band
    O->>M: Generate and rank service candidates
    M-->>O: Ranked services or withholding reason
    O->>O: Select phase and next question
    O->>P: Assemble layered response prompt
    P->>L: Stream response generation
    L-->>V: Response tokens through O
    O->>O: Grounding check and record citations
    O-->>V: Full analysis snapshot
    alt Completion criteria met
        O->>S: Generate summary from validated state
        S-->>O: Summary
        O->>A: Validate AutomationPayload
        A->>N: Async signed webhook
    end
```

## 12.2 Parallelism and latency
Intent classification and slot extraction run concurrently. Retrieval runs after intent and slot results are available. Scoring, phase evaluation, and candidate ranking are synchronous and fast. Summary generation occurs only at completion. Rationale writing is one call for all recommendations.
## 12.3 Reasoning visibility
The system never exposes chain-of-thought, hidden prompts, internal reasoning traces, raw model output, or retrieval text to the visitor. The visitor sees concise responses and a structured analysis snapshot. Engineering receives metrics, citations, and structured audit fields.

* * *
# 13\. Automation Architecture
## 13.1 FastAPI to n8n contract
FastAPI validates and persists `AutomationPayload` before dispatch. It sends an authenticated HTTP `POST` to `N8N_WEBHOOK_URL` with `X-TASC-Secret`, HMAC signature, timestamp, idempotency key equal to `consultation_id`, and correlation ID.
## 13.2 Lifecycle
`payload_created → persisted → queued → sending → acknowledged | retrying → dead_lettered → replayed → acknowledged`

n8n acknowledgement is not the same as visitor completion. The frontend may show `queued` immediately, then only show delivery confirmation if a backend status endpoint or response explicitly provides it.
## 13.3 Retry and idempotency
Retry connection errors, timeouts, and 5xx up to three attempts with exponential backoff and jitter. Do not retry authentication failures or non-409 client errors. Treat duplicate `409` idempotency responses as success. Persist every attempt and acknowledgement. Dead-letter after exhaustion with the complete payload and reason.
## 13.4 Audit trail
Audit fields include consultation ID, session ID, correlation ID, payload schema version, attempt number, status code, duration, n8n workflow execution ID, action outcomes, dead-letter reason, and replay timestamp. PII is redacted in logs; the persisted payload follows the retention policy.

* * *
# 14\. n8n Workflow Blueprint
n8n is orchestration only. It MUST NOT call an LLM, perform retrieval, calculate a score, rank services, or reinterpret routing policy.
## 14.1 Node sequence

```plain
flowchart LR
    A[Webhook: consultation complete] --> B[Authenticate secret and HMAC]
    B --> C[Validate payload shape and schema version]
    C --> D[Check idempotency key]
    D --> E[Append lead row to Google Sheets]
    E --> F[Route using FastAPI routing flags]
    F --> G[Compose sales briefing]
    G --> H[Send sales Gmail]
    F --> I{Telegram flag?}
    I -->|yes| J[Send Telegram priority alert]
    I -->|no| K[Skip Telegram]
    F --> L{Visitor confirmation flag and consent?}
    L -->|yes| M[Send visitor Gmail confirmation]
    L -->|no| N[Skip visitor email]
    H --> O[Record action results]
    J --> O
    K --> O
    M --> O
    N --> O
    O --> P[Respond acknowledgement]
    C -->|invalid| Q[Failure branch and alert]
    E -->|failure| Q
    H -->|failure| Q
```

## 14.2 Node responsibilities

| Node | Responsibility | Prohibited behaviour |
| ---| ---| --- |
| Webhook | Receive signed payload | No public unauthenticated processing |
| Authenticate | Verify secret, HMAC, timestamp skew | No accepting stale signatures |
| Validate | Validate required fields and supported schema version | No repairing business data |
| Idempotency | Detect existing consultation ID | No duplicate Sheets rows or emails |
| Google Sheets | Append one lead row with score, band, profile, recommendations, summary link | No score calculation |
| Route | Branch on FastAPI routing flags | No re-deriving band logic |
| Compose sales briefing | Format structured payload into readable email | No new claims |
| Gmail sales | Send internal briefing | No sending without configured recipient |
| Telegram | Alert Hot or human-requested leads and operations failures | No alert based on locally calculated score |
| Visitor Gmail | Send confirmation only with valid email and consent | No send without consent |
| Action logger | Record per-integration outcome | No hiding partial failure |
| Acknowledge | Return structured execution and action statuses | No claiming unexecuted actions succeeded |
| Failure branch | Alert operations and return non-2xx | No swallowing errors |

## 14.3 Idempotency policy
The consultation ID is the single idempotency key. The workflow stores or checks it before appending the lead row. Every downstream action should carry the same key where supported. A replay must not duplicate a lead row or send duplicate emails unless an operator explicitly forces a replay after confirming the prior attempt did not land.

* * *
# 15\. Error Handling Strategy

| Failure | Detection | Recovery | Visitor impact |
| ---| ---| ---| --- |
| Intent model failure | Timeout, 5xx, schema failure | Default intent, log degradation | May skip retrieval; conversation continues |
| Slot extraction failure | Provider or validation failure | Empty delta, preserve prior slots | Score does not advance on that field |
| RAG unavailable | Embedding or Chroma failure | Discovery-only mode, factual deferral | Honest limitation message |
| Weak retrieval | No chunk above floor | Deferral mode, no context injection | Nova says a consultant will confirm |
| Generation failure before first token | Provider failure | Pre-authored apology and retryable error event | Recoverable inline error |
| Generation failure after tokens | Stream failure | Preserve partial message, error event, no blind retry | Visitor can retry |
| Summary failure | Model or validation failure | Deterministic summary template | Less polished, still factual |
| Payload validation failure | Pydantic validation | Block dispatch, alert, retain payload candidate for repair | Summary may show completion error |
| n8n timeout or 5xx | HTTPX timeout/status | Retry with backoff, dead-letter after three | Visitor already sees summary |
| n8n auth failure | 401/403 | No retry, dead-letter and alert | Visitor unaffected |
| Duplicate dispatch | 409 idempotency | Treat as acknowledged | No duplicate action |
| Session expiration | TTL check | Return restart path | Clear session-ended state |

The only broad exception catches are the orchestration stage runner and API catch-all handler. All other layers translate or propagate typed errors.

* * *
# 16\. Observability
## 16.1 Logging
Every turn log includes correlation ID, session ID, turn index, phase, stage timings, prompt manifest version, ruleset version, index manifest version, retrieval chunk IDs, token usage, cost, degradation flags, and outcome. Never log message content, full assistant output, contact details, or retrieved chunk text.
## 16.2 Metrics

| Category | Metrics |
| ---| --- |
| Conversation | Turn duration, first-token latency, completion rate, turn count, abandonment |
| Lead | Band distribution, score distribution, qualification confidence, contact capture, human requests |
| AI quality | Grounding warnings, deferral correctness, extraction accuracy, recommendation accuracy, one-question adherence |
| Prompt | Prompt version usage, token size, repair rate, fallback rate, banned-claim incidents |
| RAG | Retrieval latency, empty rate, similarity distribution, top-k precision, stale-document usage |
| Automation | Dispatch attempts, acknowledgement rate, action-level success, dead-letter count, replay count |
| Cost | Input tokens, output tokens, estimated cost per turn and consultation |

## 16.3 Tracing
Trace one turn as guardrails, parallel understanding, retrieval, reasoning, generation, grounding, and snapshot emission. Dispatch is a separate root trace linked by consultation ID because it outlives the request.
## 16.4 Analytics rules
Conversation analytics are aggregated and redacted. Lead analytics use structured fields, not raw transcript search. Prompt analytics compare versions against evaluation results. Automation analytics distinguish payload persisted, webhook accepted, Sheets success, sales email success, Telegram success, and visitor email success.

* * *
# 17\. Security
## 17.1 Prompt injection
Treat visitor content and retrieved documents as untrusted data. Delimit retrieved content. Do not allow conversation text to invoke tools, alter system policy, change scores, choose services, or modify routing. Detect common instruction-like patterns, log them, and apply bounded refusal after repeated attempts.
## 17.2 Hallucination prevention
Use conditional retrieval, similarity floor, explicit deferral, source metadata, public-reference flags, indicative-pricing flags, post-generation grounding checks, and an evaluation gate. No factual claim should be produced from model memory when the knowledge policy requires evidence.
## 17.3 PII and secrets
Contact details are captured only with consent. Secrets remain in environment or n8n credentials. The browser never receives provider or webhook secrets. Logs and telemetry redact email, phone, names, raw messages, and raw model output. Payload retention follows the approved policy.
## 17.4 Webhook security
Require shared secret, HMAC signature over the raw body, timestamp freshness, correlation ID, and idempotency key. Reject stale timestamps, bad signatures, unsupported schema versions, and duplicate non-replay deliveries.

* * *
# 18\. Performance Optimization
*   Cache embeddings during indexing by content hash.
*   Cache the query vector within a turn so recommendation evidence does not re-embed.
*   Skip retrieval for pure discovery turns.
*   Run intent and extraction concurrently.
*   Keep structured schemas small and optional.
*   Compact history only when required.
*   Trim retrieved context by whole chunks, lowest score first.
*   Generate all recommendation rationales in one call.
*   Stream response generation and emit phase events only for real work.
*   Keep scoring, ranking, normalisation, and phase transitions synchronous and pure.
*   Enforce the backend latency budget: first token under 1.2s p95, full turn under 6s p95, retrieval under 300ms p95.

* * *
# 19\. Testing Strategy
## 19.1 Unit tests
Test normalisation, slot merging, contradiction handling, question selection, phase transitions, scoring components, overrides, recommendation ranking, query construction, reranking, grounding assertions, payload routing flags, and n8n signature generation.
## 19.2 Prompt tests
Use golden prompt rendering, structured-output fixtures, banned-claim tests, one-question tests, deferral tests, anti-persona tests, injection tests, and summary word-count tests. Prompt changes must produce an evaluation report.
## 19.3 RAG tests
*   Front matter validation and referential integrity.
*   Chunk boundaries preserve headings, tables, and case-study results.
*   Unchanged documents issue zero embedding calls.
*   Retrieval precision at 5 meets 0.8.
*   No-context questions defer.
*   Correct chunk IDs are recorded.
*   Public-reference and indicative-pricing flags affect response policy correctly.
## 19.4 Conversation tests
Run scripted scenarios for fast-track discovery, company question interruption, pricing question, recommendation rejection, contradiction, refusal, human request, anti-persona, provider outage, vector failure, timeout, abandonment, and full completion.
## 19.5 Automation tests
Use a fake n8n server to verify signatures, timestamp rejection, idempotency, retry matrix, 409 handling, dead-letter creation, partial integration outcomes, acknowledgement recording, and replay.
## 19.6 Evaluation metrics

| Metric | MVP gate |
| ---| --- |
| Grounding rate | ≥95% |
| Retrieval precision at 5 | ≥0.80 |
| Slot extraction accuracy | ≥90% |
| Recommendation top-1 accuracy | ≥85% |
| Deferral correctness | ≥95% |
| Persona adherence | ≥95% |
| Hallucinated commitment rate | 0 tolerated |
| Automation delivery success | ≥99% with retries |

* * *
# 20\. Future Roadmap
## MVP
GPT-4.1-mini provider, OpenAI embeddings, ChromaDB, six runtime phases, deterministic qualification, deterministic recommendation ranking, grounded responses, structured summary, validated AutomationPayload, n8n Sheets/Gmail/Telegram delivery, retries, dead-letter, and evaluation harness.
## Post-MVP
CRM integration, embeddable widget, consultant feedback loop, calendar booking, hybrid BM25 plus dense retrieval, knowledge gap dashboard, semantic caching, human takeover console, analytics dashboard, and blocking grounding regeneration.
## Production roadmap
Redis session and distributed locks, durable queue-backed dispatch, Postgres payload store, managed vector infrastructure, multi-channel adapters, multilingual corpora, proposal generation with approval, multi-tenant isolation, and provider flexibility.

No roadmap item changes the core ownership boundaries: FastAPI owns intelligence, the frontend renders backend state, and n8n orchestrates delivery.

* * *
# 21\. Mermaid Diagram Index
## 21.1 AI architecture

```plain
flowchart TB
    V[Visitor] --> FE[Next.js frontend]
    FE --> API[FastAPI API and SSE]
    API --> O[Consultation orchestrator]
    O --> G[Guardrails]
    O --> U[Intent and slot understanding]
    O --> R[RAG retrieval]
    O --> Q[Qualification engine]
    O --> M[Recommendation engine]
    O --> S[Summary generator]
    U --> LLM[OpenAI provider]
    R --> EMB[Embeddings]
    R --> CHR[ChromaDB]
    M --> LLM
    S --> LLM
    O --> PAY[AutomationPayload]
    PAY --> N8N[n8n orchestration]
    N8N --> GS[Google Sheets]
    N8N --> GM[Gmail]
    N8N --> TG[Telegram]
```

## 21.2 Knowledge flow

```plain
flowchart LR
    A[Reviewed markdown] --> B[Validate metadata]
    B --> C[Hash and chunk]
    C --> D[Embed]
    D --> E[Chroma index]
    E --> F[Retrieve per intent]
    F --> G[Rank and floor]
    G --> H[Delimited context]
    H --> I[Grounded response]
```

## 21.3 Automation flow

```plain
flowchart LR
    A[Completed consultation] --> B[Validate payload]
    B --> C[Persist idempotency key]
    C --> D[Signed n8n webhook]
    D --> E[Validate and deduplicate]
    E --> F[Sheets]
    E --> G[Gmail sales]
    E --> H[Telegram if flagged]
    E --> I[Visitor email if consented]
    F --> J[Acknowledgement]
    G --> J
    H --> J
    I --> J
    D --> K[Retry]
    K --> L[Dead letter and ops alert]
```

* * *
# 22\. Implementation Checklist
## Foundations
- [ ] Confirm PRD, Backend Blueprint, and Frontend Blueprint versions in the repository.
- [ ] Implement the six PRD runtime phases; treat the ten-stage framework as conceptual mapping only.
- [ ] Load service catalogue, pain mapping, scoring weights, overrides, vocabularies, and prompt manifest at startup.
- [ ] Record ruleset, prompt, index, model, and backend versions.
- [ ] Enforce provider protocols and import boundaries.
## Consultant framework
- [ ] Implement phase controller and transition table.
- [ ] Implement one-question-per-turn selection with deterministic tie-breaking.
- [ ] Implement fast-track, knowledge interruption, human request, anti-persona, refusal, contradiction, and abandonment paths.
- [ ] Implement server-side memory with recent turns, compaction, structured slots, and token ceiling.
## Business understanding
- [ ] Implement scalar and list slot models with confidence, raw text, source turn, and declined state.
- [ ] Implement optional enrichment fields without creating mandatory new questions.
- [ ] Implement pain-point specificity, quantification, frequency, impact, and service mappings.
- [ ] Implement conflict recording and most-recent-explicit-value behaviour.
## AI services
- [ ] Implement intent classification with constrained output and deterministic fallback.
- [ ] Implement slot extraction with all fields optional.
- [ ] Implement normalisation against controlled vocabularies.
- [ ] Implement structured-output validation and one repair retry.
- [ ] Implement provider retry matrix and stage fallback matrix.
- [ ] Implement grounding and deferral policies.
## RAG
- [ ] Author and validate the complete knowledge repository.
- [ ] Implement cleaning, heading-aware chunking, metadata enrichment, content hashing, embedding, temporary collection, smoke verification, and atomic swap.
- [ ] Implement conditional retrieval and query augmentation.
- [ ] Implement over-fetch, metadata filters, similarity floor, lexical reranking, deduplication, and context caps.
- [ ] Record chunk IDs per turn and in the final payload.
## Qualification
- [ ] Implement the six PRD score components with consulting sub-factor basis.
- [ ] Keep AI readiness, digital maturity, expected ROI, and business impact as evidence or fit inputs, not competing scores.
- [ ] Implement ordered overrides and visitor-safe next-score-contributor output.
- [ ] Implement qualification confidence separately from score.
- [ ] Implement score justification from numeric breakdown only.
## Recommendations
- [ ] Implement catalogue validation and pain-to-service candidate generation.
- [ ] Implement evidence and industry boosts, constraint penalties, confidence floor, maximum three services, and withholding.
- [ ] Implement one-call rationale generation and post-validation.
- [ ] Implement template rationale fallback and change acknowledgement.
## Prompt management
- [ ] Create versioned prompt specification files for identity, policy, discovery, clarification, analysis, qualification, recommendation, summary, formatting, automation policy, and safety.
- [ ] Keep actual prompt text out of this blueprint and under version control.
- [ ] Add golden rendering tests, prompt changelog, evaluation gates, and rollback through manifest pointer.
## Structured outputs
- [ ] Implement Pydantic v2 models for all contracts in Section 11.
- [ ] Validate AutomationPayload before persistence and dispatch.
- [ ] Ensure frontend public snapshots exclude internal telemetry, provenance, raw extraction, and retrieval text.
- [ ] Export JSON schemas and snapshot-test them.
## Automation
- [ ] Implement signed, timestamped, idempotent FastAPI-to-n8n dispatch.
- [ ] Build n8n nodes exactly as specified, with no AI calls or competing business logic.
- [ ] Implement Sheets, sales Gmail, Telegram priority alert, visitor confirmation, action logging, acknowledgement, and failure branch.
- [ ] Test retries, 409 duplicate handling, dead-letter, replay, partial action outcomes, and shutdown interruption.
## Security and observability
- [ ] Add injection detection, untrusted-data delimiters, deferral, public-reference controls, and indicative-pricing controls.
- [ ] Redact PII and secrets from logs and telemetry.
- [ ] Emit turn, retrieval, prompt, qualification, recommendation, cost, and automation metrics.
- [ ] Alert on grounding degradation, provider rejection, dead letters, latency, empty retrieval, and cost spikes.
## Release gates
- [ ] Unit and integration tests pass with no unintended network calls.
- [ ] Evaluation gates meet the thresholds in Section 19.6.
- [ ] Full scripted consultation completes with grounded answers and a validated payload.
- [ ] n8n receives exactly one payload and executes idempotently.
- [ ] Frontend receives phase, token, snapshot, and done events in contract order.
- [ ] No browser-facing surface exposes hidden reasoning, prompts, chunk text, model names, or internal score maths.
- [ ] Runbook, knowledge authoring guide, prompt changelog, and rollback procedure are complete.
## Definition of done
The AI layer is complete when Nova can conduct a coherent, grounded consultation from greeting to summary, preserve state through interruptions and recoverable failures, produce deterministic qualification and recommendations, cite the evidence used internally, create one validated AutomationPayload, and hand it to n8n with reliable retries and auditability. No engineer or coding agent should need to invent a business rule, prompt boundary, retrieval policy, score formula, or automation decision.