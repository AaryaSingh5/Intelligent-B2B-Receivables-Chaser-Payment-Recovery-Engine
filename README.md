# 🏦 Intelligent B2B Receivables Chaser & Payment Recovery Engine

> **Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery**

A production-ready, local-first Python CLI engine that automates B2B receivables chasing and payment failure recovery with bounded safety, complete audit trails, and measured metrics.

---

## 🎯 What It Does

This engine bridges three official Razorpay buildathon example tracks into a single unified pipeline:

| Track | Capability |
|-------|-----------|
| **B2B Receivables Chaser** | Escalating workflows from gentle reminders → firm follow-ups → escalation notices based on invoice aging |
| **Payment Degradation Root-Cause Analysis** | Parses gateway error codes (timeouts, insufficient funds, expired cards, etc.) into actionable root causes |
| **Promise-to-Pay Tracker** | Extracts commitment dates from customer replies, pauses escalation, and schedules follow-up checks |
| **💬 WhatsApp Dispatch (Twilio)** | Live or simulated multi-channel WhatsApp recovery dispatch with allowlist protection & rate limiting |

---

## 📂 Project Structure

```
revenue_recovery_engine/
│
├── data/
│   └── synthetic_batch.json      # 37 mixed mock records (invoices + payment failures)
│
├── src/
│   ├── __init__.py
│   ├── loader.py                 # Ingestion & normalization into Pydantic models
│   ├── diagnoser.py              # Root-cause classifier & aging bracket engine
│   ├── guards.py                 # Bounded policy gates & stopping rules
│   ├── orchestrator.py           # Contextual recovery message generator
│   ├── dispatcher.py             # Twilio WhatsApp message dispatcher with safety gates
│   ├── logger.py                 # Immutable audit trail writer
│   └── evaluator.py              # Metrics aggregation & markdown report generator
│
├── logs/
│   ├── recovery_audit.log        # Generated at runtime — complete audit trail
│   └── metrics_report.md         # Generated at runtime — metrics summary
│
├── .env.example                  # Template for API keys & configuration
├── requirements.txt              # Pinned Python dependencies
├── README.md                     # This file
└── main.py                       # CLI entry point — runs the full pipeline
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

# 5. Run the engine (CLI)
python main.py

# 6. Run with WhatsApp simulation / dry-run dispatch
python main.py --dispatch

# 7. Run with live WhatsApp dispatch via Twilio (requires .env credentials)
python main.py --dispatch --live-whatsapp

# 8. Launch the Streamlit Executive Dashboard
streamlit run dashboard.py
```

### Custom Data

```bash
python main.py --data path/to/your_batch.json
```

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

## 📜 License

Built for the Razorpay AI Buildathon 2026. For demonstration and competition purposes.


---

## 👥 Team

Intelligent B2B Receivables Chaser & Payment Recovery Engine — Razorpay AI Buildathon 2026, Track 3: AI Revenue Recovery.
