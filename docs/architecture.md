# 🏗️ System Architecture & Engineering Design Decisions
> **RECOVER.AI — Intelligent B2B Receivables Chaser & Payment Recovery Engine**  
> Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery

---

## 1. Executive Summary & Design Philosophy

In modern B2B commerce and checkout workflows, revenue leakage rarely happens in a single catastrophic event. Instead, revenue silently slips away through two major leakage points:
1. **Corporate Receivables Aging**: B2B invoices that pass their net-30/60 due dates without proactive follow-up.
2. **Checkout Payment Degradation**: Payment attempts failing due to transient timeouts, insufficient funds, expired cards, or authentication drops.

Most merchants handle this with either **manual finance team follow-ups** (slow, expensive, inconsistently applied) or **static blanket email blasts** (unresponsive to customer context, risk damaging high-value client relationships).

**RECOVER.AI** solves this by implementing an autonomous, event-driven agentic closed loop:  
`Detect → Diagnose → Decide → Execute → Verify`

---

## 2. Component Architecture & Event Flow

```
                                  ┌───────────────────────────────┐
                                  │   Receipt & Invoice Source    │
                                  │ (PDF / JSON / ERP Ingestion)  │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │   1. Receipt Parser & Aging   │
                                  │    Calculates aging bracket   │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐ ┌───────────────────────────────┐
│   Razorpay Webhook Callback   │ │   2. Root-Cause Diagnoser     │ │  Twilio Inbound WhatsApp Reply│
│  (payment.failed / paid)      │─┼─▶   Maps error codes &        │◀┼─ ("Will pay next Friday")     │
└───────────────────────────────┘ │   aging cohorts               │ └───────────────────────────────┘
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │   3. Bounded Policy Guards    │
                                  │   - Stopping Rule (Max 2)     │
                                  │   - 30-Day Compliance Gate    │
                                  │   - Promise-to-Pay Pause      │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │   4. Contextual Orchestrator  │
                                  │   Tone-matched recovery copy  │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │  5. Dispatcher & Payment Links│
                                  │  - Dynamic Razorpay links     │
                                  │  - Twilio WhatsApp engine     │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │ 6. Dual Persistence & Audit   │
                                  │ - recovery_audit.log (append) │
                                  │ - recovery_engine.db (SQLite) │
                                  └───────────────────────────────┘
```

---

## 3. Defense of "AI Judgment": Where AI Belongs vs. Deterministic Rules

Razorpay's Buildathon evaluation explicitly grades **"AI Judgment"**:
> *"Did you use AI where it genuinely adds value? Or did you force-fit a model where a simple if-else would work?"*

In high-stakes financial operations, non-deterministic AI models must **never** be given unbounded control over money, retry frequency, or compliance thresholds. 

| System Component | Engineering Decision | Rationale |
|---|---|---|
| **Retry & Nudge Stopping Rules** | **Deterministic Rule (`MAX_NUDGES = 2`)** | Financial spam and customer harassment carry strict legal liability. A deterministic state machine guarantees a hard stop with **zero hallucination risk**. |
| **Compliance Tone Gating** | **Deterministic Gate (`Threshold = 30 Days`)** | Indian commercial norms and fair debt collection practices strictly forbid aggressive legal notices on fresh invoices (<30 days). A hard rule enforces this boundary unconditionally. |
| **Customer Promise Extraction** | **Regex / NLP Pattern Parser** | Human WhatsApp replies are unstructured, colloquial, and diverse (*"Will clear this by Tuesday afternoon"*, *"Payment will be done by Friday"*). Entity extraction is ideal here to extract temporal commitments without risking hallucinations. |
| **Recovery Message Drafting** | **Contextual Template Engine + Optional LLM** | Guarantees brand consistency, compliant phrasing, and deterministic placeholder population (invoice ID, exact INR amount, Razorpay checkout URL). |
| **HMAC Webhook Verification** | **Deterministic Cryptographic Hashing** | SHA-256 HMAC verification guarantees that only authenticated Razorpay gateway callbacks can trigger invoice state transitions. |

---

## 4. Bounded Policy Guards & Stopping Rules

The engine implements three strict financial safety gates before any message or money action:

### Gate 1: Max-Nudge Stopping Rule
- **Threshold**: Exactly 2 nudges (`MAX_NUDGES = 2`).
- **Behavior**: Any record with `nudge_count >= 2` transitions to `MAX_RETRIES_REACHED`.
- **Enforcement**: All outbound messaging is automatically intercepted and blocked. An internal hold note is generated for human credit-control review.

### Gate 2: Compliance Tone Gate
- **Threshold**: 30 days overdue.
- **Behavior**: Invoices with `aging_days < 30` are restricted to `Soft` (1–15d) or `Moderate` (16–30d) tone. Formal escalation notices are strictly blocked until day 31+.

### Gate 3: Promise-to-Pay Pause
- **Trigger**: Inbound customer replies containing commitment phrases.
- **Behavior**: Transitions invoice to `PROMISE_TRACKED`, records the ISO promise deadline, pauses all future automated reminders, and sends an automated acknowledgement with the active payment link.

---

## 5. Failure Modes, Edge Cases & Recovery Mechanisms

Real-world engineering requires anticipating failures:

| Potential Failure Point | Impact | Engine Recovery & Mitigation |
|---|---|---|
| **Twilio API Downtime or Rate Limits** | Outbound WhatsApp delivery fails or times out. | Dispatcher catches HTTP/API exceptions, records status as `error` in SQLite without incrementing customer `nudge_count`, and queues for background retry. |
| **Ambiguous Customer Reply** | Customer texts *"Will pay once our client clears our cheque"*. | Regex NLP fails to find a deterministic date token. Fallback: flags reply as a general inquiry, sends receipt acknowledgement, and maintains existing reminder schedule. |
| **Duplicate Webhook Delivery** | Razorpay fires duplicate `payment_link.paid` events. | Database queries invoice status before execution; if already `RESOLVED`, idempotency check discards duplicate processing. |
| **Unrecognized Gateway Error Code** | Bank returns an undocumented proprietary error code. | Diagnoser maps uncatalogued codes to `UNKNOWN_ERROR_ROOT_CAUSE`, logs an ops alert, and recommends human payment-ops investigation rather than guessing. |

---

## 6. Scalability & Production Roadmap

1. **Enterprise Database**: Migrate SQLite to AWS Aurora PostgreSQL with connection pooling.
2. **Distributed Queue**: Decouple dispatch loops using Celery with Redis for asynchronous rate-limited WhatsApp throughput.
3. **ERP Integrations**: Webhook connectors for Tally Prime, Zoho Books, and SAP for automatic bi-directional ledger reconciliation.
