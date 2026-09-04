# 🏦 Intelligent B2B Receivables Chaser & Payment Recovery Engine

> **Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery**

A production-ready, local-first Python CLI engine that automates B2B receivables chasing and payment failure recovery with bounded safety, complete audit trails, and measured metrics.

🌐 **Live Cloud App**: [https://intelligent-b2b-receivables-chaser-payment-recovery-engine-7jm.streamlit.app/](https://intelligent-b2b-receivables-chaser-payment-recovery-engine-7jm.streamlit.app/)  
📖 **[View the Complete Visual Walkthrough with UI Screenshots (WALKTHROUGH.md)](./WALKTHROUGH.md)**

---

## 🎯 What It Does

This engine bridges three official Razorpay buildathon example tracks into a single unified, event-driven, production-ready platform:

| Capability | Real-World Implementation |
|---|---|
| **🧾 Receipt Ingestion & Aging Engine** | Automated receipt ingestion, due date aging classification, and instant payment link generation |
| **💳 Razorpay Payment Gateway & Webhooks** | Generates dynamic Razorpay Payment Links; listens to `payment.failed` (root-cause diagnosis & instant recovery link) and `payment_link.paid` (auto-resolution) |
| **💬 Two-Way WhatsApp Recovery Loop** | Dispatches WhatsApp reminders with Razorpay checkout links; ingests incoming replies via Twilio webhook, extracts promise dates with NLP regex, and auto-pauses nudges |
| **⏰ Autonomous Recovery Sweep Engine** | Background scheduler monitoring promise deadlines, advancing aging brackets, and enforcing 2-nudge stopping rules |
| **🗄️ Thread-Safe SQLite Persistence** | Production-ready ACID storage (`data/recovery_engine.db`) for invoices, payment attempts, WhatsApp messages, and audit trail |
| **🌐 FastAPI Webhook Server & Dashboard** | High-performance async REST API on port 8000 + 5-tab executive Streamlit dashboard with **Live Automation Center** |

---

## 📂 Project Structure

```
revenue_recovery_engine/
│
├── data/
│   ├── synthetic_batch.json      # 37 mock records (invoices + payment failures)
│   └── recovery_engine.db        # SQLite database (invoices, attempts, messages, audit)
│
├── src/
│   ├── __init__.py
│   ├── db.py                     # SQLite persistence layer with thread-safe pooling
│   ├── gateway.py                # Razorpay SDK client, payment link minting & webhooks
│   ├── receipt_parser.py         # Receipt ingestion, aging classification, link creation
│   ├── dispatcher.py             # Twilio WhatsApp two-way messaging & NLP promise parser
│   ├── scheduler.py              # Autonomous recovery sweep & promise expiration checker
│   ├── loader.py                 # Ingestion & normalization into Pydantic models
│   ├── diagnoser.py              # Root-cause classifier & aging bracket engine
│   ├── guards.py                 # Bounded policy gates & stopping rules
│   ├── orchestrator.py           # Contextual recovery message generator
│   ├── logger.py                 # Immutable audit trail writer
│   └── evaluator.py              # Metrics aggregation & markdown report generator
│
├── logs/
│   ├── recovery_audit.log        # Generated at runtime — complete audit trail
│   └── metrics_report.md         # Generated at runtime — metrics summary
│
├── .env.example                  # Template for API keys & configuration
├── requirements.txt              # Pinned Python dependencies
├── README.md                     # Comprehensive documentation
├── server.py                     # FastAPI webhook & automation server (Port 8000)
├── dashboard.py                  # Streamlit Executive Dashboard & Live Automation Center (Port 8501)
└── main.py                       # CLI entry point — runs the batch pipeline
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ installed
- `pip` available on PATH

### Setup & Run

```bash
# 1. Navigate to the engine directory
cd revenue_recovery_engine

# 2. (Optional) Create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Copy and configure environment
cp .env.example .env

# 5. Launch the FastAPI Webhook & Automation Server (Port 8000)
python server.py

# 6. Launch the Streamlit Executive Dashboard & Live Automation Center (Port 8501)
streamlit run dashboard.py

# 7. Run the CLI batch processor directly
python main.py

# 8. Run CLI with WhatsApp dispatch simulation
python main.py --dispatch

# 9. Run automated unit test suite (13 unit tests)
python -m unittest discover tests/
```

## 🌐 Live Streamlit Cloud Deployment

The executive dashboard is live on Streamlit Community Cloud:

👉 **[Launch RECOVER.AI Live Dashboard](https://intelligent-b2b-receivables-chaser-payment-recovery-engine-7jm.streamlit.app/)**

- **Instant Browser Access**: No local installation or environment configuration required.
- **Full Interactive Capabilities**: Review the 37-record batch, test the authentic dark-mode WhatsApp device simulator, ingest new receipts, trigger simulated Razorpay webhooks, and inspect the real-time SQLite database.
- **Autonomous & Self-Contained**: Operates in standalone simulation mode with deterministic standard payment links, safe sandbox WhatsApp messaging, and zero cloud latency.

---

## ⚡ Real-World Event-Driven Automation

The engine operates as a fully reactive, automated platform that connects invoice receipts, live payment links, automated webhooks, and customer messaging loops in real time:

```
                  ┌──────────────────────┐
                  │   Receipt Ingestion  │
                  │ (PDF / JSON / Scan)  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Dynamic Razorpay     │
                  │ Payment Link Minted  │
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌──────────────────────────┐      ┌──────────────────────────┐
│   Outbound Recovery Msg  │      │  Payment Gateway Event   │
│   (WhatsApp / Email)     │      │   (Razorpay Webhook)     │
└───────────┬──────────────┘      └───────────┬──────────────┘
            │                                 │
            ▼                                 │
┌──────────────────────────┐                  │
│ Customer Replies via WA  │                  │
│ ("Will pay by Friday")   │                  │
└───────────┬──────────────┘                  │
            │                                 │
            ▼                                 │
┌──────────────────────────┐                  │
│  Twilio Inbound Webhook  │                  │
│  + NLP Regex Extractor   │                  │
└───────────┬──────────────┘                  │
            │                                 │
            ▼                                 ▼
┌────────────────────────────────────────────────────────────┐
│              Autonomous Recovery Sweep Engine              │
│  - Pauses nudges on promise commitment                     │
│  - Re-triggers escalation when promise expires             │
│  - On payment.failed: Diagnoses root cause & resends link  │
│  - On payment_link.paid: Marks RESOLVED & closes ticket   │
│  - Enforces hard 2-nudge stopping rules & audit logging    │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ Thread-Safe SQLite DB    │
              │ + Streamlit Live Center  │
              └──────────────────────────┘
```

### FastAPI Endpoints (`http://localhost:8000`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Healthcheck & system status (uptime, active records, DB connectivity) |
| `GET` | `/api/invoices` | List all tracked invoices with status, aging bracket, and promise state |
| `POST` | `/api/receipts/ingest` | Ingest new receipt, compute aging, classify bracket, and mint Razorpay link |
| `POST` | `/api/webhooks/razorpay` | Razorpay webhook listener (`payment.failed` root-cause, `payment_link.paid` auto-resolve) with HMAC verification |
| `POST` | `/api/webhooks/twilio/whatsapp` | Twilio inbound webhook: receives customer replies, extracts promise dates via NLP, pauses escalation |
| `POST` | `/api/automation/sweep` | Triggers background recovery sweep across all active invoices |

Interactive Swagger documentation is available at `http://localhost:8000/docs`.

---

## 🔧 Pipeline Architecture

The engine processes records through a strict, sequential 7-stage pipeline:

```
┌──────────┐    ┌───────────┐    ┌────────┐    ┌──────────────┐    ┌────────┐    ┌───────────┐    ┌────────────┐
│  LOADER  │───▶│ DIAGNOSER │───▶│ GUARDS │───▶│ ORCHESTRATOR │───▶│ LOGGER │───▶│ EVALUATOR │───▶│ DISPATCHER │
└──────────┘    └───────────┘    └────────┘    └──────────────┘    └────────┘    └───────────┘    └────────────┘
  Ingest &        Root-cause      Policy         Message            Audit          Metrics &        WhatsApp
  validate        analysis +      enforcement    generation         trail          markdown         delivery
  JSON data       aging brackets  & stopping     (tone-matched)     (append-only)  report           (Twilio API)
```

### Stage Details

| Stage | Module | Responsibility |
|-------|--------|---------------|
| **① Load** | `loader.py` | Parse JSON → Pydantic models with full validation |
| **② Diagnose** | `diagnoser.py` | Map error codes to root causes; classify aging brackets |
| **③ Guard** | `guards.py` | Enforce max-nudge stop, compliance tone gate, promise pause |
| **④ Orchestrate** | `orchestrator.py` | Generate contextual messages matching tone to aging/status |
| **⑤ Log** | `logger.py` | Write immutable audit entries to `recovery_audit.log` |
| **⑥ Evaluate** | `evaluator.py` | Compute & print recovery metrics as a Markdown table |
| **⑦ Dispatch** | `dispatcher.py` | Deliver recovery messages via WhatsApp (Twilio API / dry-run) |

---

## 🛡️ Bounded Safety & Compliance

Every messaging action is strictly bounded by three safety gates:

### 1. Stopping Rule
- **Limit**: Maximum 2 nudges per record (`MAX_NUDGES = 2`)
- **Action**: Records with `nudge_count >= 2` are set to `MAX_RETRIES_REACHED` — no further automated messages

### 2. Compliance Rule
- **Limit**: No aggressive or legal collection language on invoices under 30 days overdue
- **Action**: Aging bracket determines message tone (Soft → Moderate → Escalated only after 31+ days)

### 3. Promise-to-Pay Pause
- **Trigger**: NLP regex parser detects commitment phrases in customer replies (e.g., "Will pay by Friday")
- **Action**: Record status set to `PROMISE_TRACKED`, all nudges paused, follow-up date extracted and logged

---

## 📊 Sample Output

After running `python main.py`, you'll see:

```
## 🏦 Revenue Recovery Engine — Run Summary

| Metric                       |          Value |
|------------------------------|----------------|
| 📊 Total Records Processed   |             37 |
| 💰 Total Revenue at Risk      | ₹7,598,900.00 |
| ✅ Recovered / Promised       | ₹5,301,400.00 |
| 📈 Recovery Rate              |        69.76%  |
| 🚫 Boundary Violations        |             0  |

### Status Breakdown

| Status Breakdown              | Count |
|-------------------------------|-------|
| 📤 Nudges Sent                |    16 |
| 🤝 Promises Tracked (Paused)  |    11 |
| ⛔ Max Retries Reached         |     6 |
| ⏳ Pending / Unactioned        |     4 |

> ✅ **All boundary & compliance checks passed — 0 violations.**
```

---

## 📝 Audit Trail

Every decision is logged to `logs/recovery_audit.log` with full context:

```
========================================================================
  Timestamp       : 2026-09-04T15:30:00+00:00
  Record ID       : INV-002
  Type            : b2b_invoice
  Customer        : NovaByte Solutions
  Amount (₹)      : 340,000.00
  Aging Bracket   : Soft (1-15 days)
  Nudge Count     : 1
  Status          : PROMISE_TRACKED
  Root Cause      : Invoice overdue by 12 day(s) — classified as Soft (1-15 days).
  Promise Date    : 2026-09-09
  Customer Reply  : Will clear this by Tuesday
  Boundary Viols  : 0
  Recovery Message:
    | Hi NovaByte Solutions,
    | Thank you for your commitment to settle INV-002 (₹340,000.00) by ...
========================================================================
```

---

## 🧪 Error Codes Supported

| Error Code | Root Cause | Recommended Action |
|-----------|-----------|-------------------|
| `ERR_GATEWAY_TIMEOUT` | Gateway timed out | Auto-retry |
| `ERR_INSUFFICIENT_FUNDS` | Insufficient funds | Nudge to top up |
| `ERR_CARD_EXPIRED` | Card expired | Prompt card update |
| `ERR_BANK_DECLINED` | Bank declined | Contact bank |
| `ERR_NETWORK_ERROR` | Network failure | Auto-retry |
| `ERR_AUTHENTICATION_FAILED` | 3DS/OTP failed | Reattempt auth |
| `ERR_DUPLICATE_TRANSACTION` | Duplicate detected | Verify original |

---

## 💬 WhatsApp Delivery via Twilio (Live & Simulation)

The engine includes active WhatsApp messaging capabilities powered by the Twilio API for WhatsApp, built with strict financial safety guardrails:

### Safety Architecture
- **Dry-Run by Default**: Unless `ENABLE_LIVE_WHATSAPP=true` is explicitly set in `.env`, the dispatcher operates in dry-run simulation mode — drafting, validating, and logging messages without incurring API charges or sending unsolicited messages.
- **Strict Recipient Allowlist**: In live mode, messages will **only** be dispatched to phone numbers declared in `ALLOWED_RECIPIENTS` (comma-separated E.164 format in `.env`), preventing accidental customer messaging during demos.
- **Max-Retries Auto-Block**: Records in `MAX_RETRIES_REACHED` status are automatically intercepted and blocked from dispatch.
- **Rate-Limiting Throttle**: Automatic 0.5s pause between sends to comply with WhatsApp messaging thresholds.

### Setup Instructions

1. **Sign up for Twilio**: Create a free sandbox account at [twilio.com](https://www.twilio.com).
2. **Join WhatsApp Sandbox**: Follow the prompt in Twilio Console to text the join code to `+14155238886`.
3. **Configure `.env`**:
   ```env
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_WHATSAPP_NUMBER=+14155238886
   ENABLE_LIVE_WHATSAPP=true
   ALLOWED_RECIPIENTS=+919876543210
   ```
4. **Send live or simulated messages**:
   ```bash
   # Dry-run simulation (no keys needed):
   python main.py --dispatch

   # Live WhatsApp delivery (requires .env configuration):
   python main.py --dispatch --live-whatsapp
   ```
5. **Interactive UI**: Open `dashboard.py` in your browser, head to the **💬 WhatsApp Dispatch** tab, select any record, enter your number, and test single or batch message dispatch interactively!

---

## 🖥️ Streamlit Executive Dashboard & Visual Walkthrough

> **Live Deployment**: [https://intelligent-b2b-receivables-chaser-payment-recovery-engine-7jm.streamlit.app/](https://intelligent-b2b-receivables-chaser-payment-recovery-engine-7jm.streamlit.app/)  
> **Detailed Illustrated Guide**: [WALKTHROUGH.md](./WALKTHROUGH.md)

Launch locally with `streamlit run dashboard.py` (available at `http://localhost:8501`). Designed as an executive control room inspired by **Stripe Sigma, Linear, and Mercury**:

### 1. 📊 Executive Overview & Interactive Financial Analytics
![Executive Overview & KPI Cards](./docs/assets/fintech_hero_kpis.png)
- **Top Executive Branding Bar**: Live system health badges (`● FASTAPI 8000 ONLINE`, `RAZORPAY LINK GATEWAY`, `SQLITE PERSISTED`, `0 VIOLATIONS`).
- **5 Hero KPI Cards**: Revenue at Risk (`₹79.2L`), Secured & Promised (`₹59.4L`), Recovery Velocity (`75.0%`), Active Interventions (`31`), and Guardrail Violations (`0`).
- **Plotly Visualizations**: Area spline recovery curve, aging risk exposure donut chart, and 75% recovery velocity gauge.

### 2. 💬 WhatsApp Recovery Console & Device Preview
![WhatsApp Device Preview](./docs/assets/fintech_whatsapp_mockup.png)
- **Authentic WhatsApp Mockup**: Dark-mode device canvas with customer avatar, verified WhatsApp Business badge, and timestamped outbound/inbound chat bubbles.
- **Embedded Razorpay Payment Links**: Outbound bubbles embed live payment link cards (`https://rzp.io/l/...`) and blue double-check delivery receipts (`✓✓`).

### 3. ⚡ Live Automation & Webhook Control Center
![Live Automation Center](./docs/assets/fintech_automation_center.png)
- **Receipt Ingestion Studio**: Ingest invoices with real-time aging calculation and instant link creation.
- **Two-Way Inbound Simulator**: Test customer replies (*"Will pay by Friday"*) with instant NLP date extraction pausing reminders.
- **Razorpay Webhooks**: Single-click triggers for `payment.failed` and `payment_link.paid`.
- **Live SQLite Database Stream**: Real-time table view reflecting database state changes dynamically.

📖 **For high-resolution screenshots and video recordings of all 5 tabs, see [WALKTHROUGH.md](./WALKTHROUGH.md).**

## 🧪 Automated Test Suite

The engine includes an automated unit test suite with 13 unit tests covering bounded stopping rules, compliance tone gates, promise NLP date extraction, and Razorpay HMAC signature verification:

```bash
python -m unittest discover tests/
```

| Test Module | Coverage | Status |
|---|---|---|
| `tests/test_guards.py` | Stopping Rule (`MAX_NUDGES=2`), 30-Day Compliance Tone Gate, Promise-to-Pay Pause | ✅ Pass |
| `tests/test_diagnoser.py` | Aging cohort classification (Soft/Moderate/Escalated), Gateway error mappings | ✅ Pass |
| `tests/test_nlp.py` | Colloquial temporal extraction ("next Friday", "tomorrow"), non-commitment filter | ✅ Pass |
| `tests/test_gateway.py` | Deterministic/live link minting, HMAC-SHA256 signature verification, paid webhooks | ✅ Pass |
| `tests/test_pipeline.py` | End-to-end 6-stage batch run on 37 synthetic records, zero boundary violations | ✅ Pass |

---

## 🏗️ System Architecture & AI Judgment

For detailed engineering decisions, data flow diagrams, and a defense of where deterministic logic was chosen over non-deterministic AI to prevent financial liability, view:

👉 **[docs/architecture.md](./docs/architecture.md)**

---

## ⚠️ Known Limitations & Honest Failure Modes

As emphasized in the Razorpay Buildathon engineering criteria, production-minded software must honestly account for edge cases and limitations:

1. **Colloquial & Ambiguous Promise Dates**:
   - *Limitation*: The regex NLP engine extracts deterministic temporal anchors (e.g. *"by Friday"*, *"next Tuesday"*, *"tomorrow afternoon"*). Highly ambiguous replies like *"will pay once our client clears our pending invoice"* do not contain a concrete date.
   - *Mitigation*: The engine gracefully falls back to classifying the message as a general inquiry, logs the reply to the audit trail, and maintains the existing reminder schedule without erroneously freezing the debt.
2. **Twilio WhatsApp Sandboxing & Rate Limits**:
   - *Limitation*: The Twilio WhatsApp sandbox requires recipient numbers to opt-in with a join code. Outbound dispatch is throttled with a 0.5s pause to prevent carrier rate-limiting.
   - *Mitigation*: The dispatcher defaults to dry-run sandbox simulation mode unless `ENABLE_LIVE_WHATSAPP=true` is explicitly configured, protecting against accidental spam or API billing.
3. **Webhook Idempotency & Network Partitions**:
   - *Limitation*: If network instability drops a webhook delivery between Razorpay and the local FastAPI server, events could be delayed.
   - *Mitigation*: The autonomous recovery sweep engine (`src/scheduler.py`) periodically scans the SQLite database to reconcile state independently of incoming webhooks.
4. **ERP Accounting Sync**:
   - *Limitation*: Current release ingests via JSON payloads, REST API (`/api/receipts/ingest`), and Streamlit UI. Native bidirectional syncing with Tally Prime or Zoho Books is slated for the Phase 2 production roadmap.

---

## 📜 License

Built for the Razorpay AI Buildathon 2026. For demonstration and competition purposes.


---

## 👥 Team

Intelligent B2B Receivables Chaser & Payment Recovery Engine — Razorpay AI Buildathon 2026, Track 3: AI Revenue Recovery.
