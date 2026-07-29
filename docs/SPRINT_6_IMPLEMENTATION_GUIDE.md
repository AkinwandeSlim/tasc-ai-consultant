# Sprint 6 Architecture
## AI Automation Integration

Version: 1.1

Status: Approved

---

# Objective

Sprint 6 transforms the existing consultation platform into a complete AI Automation solution that satisfies the internship assignment requirements.

The objective is **NOT** to redesign the current application.

Instead, Sprint 6 extends the existing architecture by introducing:

- n8n as the orchestration and automation layer
- An LLM as the consultation intelligence engine

The existing frontend and FastAPI backend remain intact.

---

# Architecture Philosophy

The platform follows strict separation of responsibilities.

```
Frontend
      │
      ▼
FastAPI Backend
      │
      ▼
n8n Workflow
      │
      ▼
LLM + Business Integrations
```

Core principles:

- The frontend never communicates directly with an LLM.
- The frontend never communicates directly with Google services.
- FastAPI remains the application server.
- n8n owns AI orchestration and business automation.
- The LLM is responsible for conversational reasoning, not application logic.

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
                  FastAPI Backend
                          │
               Validation & Sessions
                          │
                    HTTP Webhook
                          │
                          ▼
                    n8n Workflow
        ┌──────────────────────────────────────┐
        │                                      │
        │      AI Consultation Orchestrator    │
        │                                      │
        └──────────────────────────────────────┘
                          │
                          ▼
                   OpenAI / Gemini
                          │
                          ▼
            Consultation Response Object
     (Natural Conversation + Structured Intelligence)
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
    Google Sheets                     Gmail
          │                               │
          └───────────────┬───────────────┘
                          ▼
                  Return Consultation
                          │
                          ▼
                     FastAPI Backend
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

Responsible for:

- REST API contracts
- Session management
- Request validation
- Error handling
- Calling n8n
- Returning responses
- Future authentication

FastAPI is **not responsible for AI reasoning**.

---

## n8n

n8n becomes the AI Automation Engine.

Responsibilities:

- Receive consultation requests
- Manage workflow orchestration
- Invoke the LLM
- Supply system prompts
- Pass conversation history
- Trigger business automations
- Update Google Sheets
- Send notification emails
- Return a structured Consultation Response Object

---

## LLM

The LLM is the Consultation Intelligence Engine.

Responsibilities include:

- Understanding business context
- Holding a natural conversation
- Asking follow-up questions
- Extracting structured business information
- Updating the consultation state
- Assessing AI readiness
- Evaluating lead quality
- Generating implementation recommendations
- Producing professional business responses

The LLM never communicates directly with the frontend.

It always returns a structured Consultation Response Object to n8n.

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

1. User opens the consultation platform.

↓

2. Frontend starts a consultation session.

↓

3. User submits a message.

↓

4. FastAPI validates the request.

↓

5. FastAPI forwards the request to the n8n webhook.

↓

6. n8n prepares the consultation context.

↓

7. n8n invokes the LLM.

↓

8. The LLM conducts the consultation, understands the user's business, asks follow-up questions when needed, updates the structured business profile, and returns a Consultation Response Object.

↓

9. n8n executes required workflow actions.

Examples:

- Update Google Sheets
- Send internal notification
- Send follow-up email

↓

10. n8n returns the Consultation Response Object.

↓

11. FastAPI returns the response.

↓

12. Frontend updates:

- Conversation
- Business Profile
- Lead Qualification
- Recommendations
- Consultation Progress
- Dashboard Cards

---

# Consultation Response Contract

Every LLM response must return a **Consultation Response Object**.

The object combines conversational output with structured intelligence.

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

Sprint 6 requires:

✅ OpenAI or Gemini

✅ n8n

✅ Google Sheets

✅ Gmail

These satisfy the internship assignment requirements.

---

# Existing Qualification Engine

The deterministic qualification engine remains part of the repository.

For Sprint 6:

- The LLM becomes the primary consultation engine.
- The deterministic engine remains available for future validation, auditing, or hybrid AI workflows.

This preserves the existing engineering investment while enabling more natural AI conversations.

---

# Future Enhancements

The following are intentionally excluded from Sprint 6:

- RAG
- Vector Database
- Streaming Responses
- Redis
- Authentication
- Multi-user Sessions
- Voice Support
- WhatsApp
- Slack
- CRM Integrations

These can be introduced in future versions without changing the current architecture.

---

# Success Criteria

Sprint 6 is complete when:

✅ Frontend communicates with FastAPI

✅ FastAPI calls n8n

✅ n8n invokes an LLM

✅ The LLM conducts a natural business consultation

✅ The LLM returns a valid Consultation Response Object

✅ Google Sheets is updated automatically

✅ Gmail notifications are sent when required

✅ The Business Intelligence dashboard updates after every response

✅ The AI asks intelligent follow-up questions when information is missing

✅ Recommendations are generated naturally based on the conversation

No additional architectural changes should be introduced after Sprint 6 begins.