# 🎬 AegisPay — Buildathon Video Pitch Script

**Track 3: AI Revenue Recovery (Razorpay AI Buildathon 2026)**

This document contains a suggested choreography and narration script for recording the demo video of the AegisPay Revenue Recovery Engine.

---

## ⏱️ Video Structure (2-3 Minutes)

*   **0:00 - 0:30** Introduction & The Problem
*   **0:30 - 1:00** The Backend Architecture (APIs & Safety Rules)
*   **1:00 - 2:00** The Live Demo (Tab 5 - Live Automation Center)
*   **2:00 - 2:30** Conclusion & Why It Matters

---

## 🗣️ Narration Script & Actions

### 1. Introduction (0:00 - 0:30)
**[Visual]** Start on the Executive Dashboard (Tab 1: Executive Overview & Analytics) showing the charts and KPIs.
**[Audio]** 
> *"Hello judges, welcome to AegisPay, our submission for Track 3: AI Revenue Recovery.*
> *We've built an autonomous, event-driven engine that chases B2B receivables and handles payment failures without human intervention.*
> *As you can see on our dashboard, it continuously monitors at-risk capital, enforces compliance to prevent spam, and acts as a central nervous system for revenue recovery."*

### 2. The AI & Architecture (0:30 - 1:00)
**[Visual]** Switch to Tab 2 (Receivables Portfolio) or Tab 4 (Compliance & Audit Ledger). Scroll through the Audit log.
**[Audio]**
> *"Under the hood, we have a FastAPI backend powering a 7-stage sequential pipeline.* 
> *Instead of relying on non-deterministic AI for everything, we built strict financial guardrails. We enforce a hard 2-nudge stopping rule, and we only escalate tone on invoices older than 30 days to protect customer relationships.*
> *Every single decision is logged immutably in our SQLite audit trail."*

### 3. The Live Demo (1:00 - 2:00) 
*(This is the most critical part where you prove the system works in real-time.)*

**[Visual]** Switch to Tab 5 (Live Automation Center). Focus on the "Instant Receipt Ingestion Studio". Fill out the form or use the default values and click "Ingest Receipt & Mint Payment Link".
**[Audio]**
> *"To prove the pipeline works live, let's use our Live Automation Center. First, we ingest a new invoice. Instantly, the engine calculates the aging risk and uses the Razorpay API to mint a live, dynamic payment link."*

**[Visual]** Move down to the "Two-Way WhatsApp Inbound Simulator". Select a preset reply like *"Checking with finance team, will settle by Friday"* and hit process.
**[Audio]**
> *"Here is where our AI comes in. If a customer replies to our automated WhatsApp reminder with a promise to pay, our NLP engine steps in. It extracts the exact promise date from natural language, logs it, and automatically pauses any further reminders so we don't spam the customer."*

**[Visual]** Move to the "Razorpay Webhooks" section. Click "Fire Paid Webhook". Point to the bottom where the Real-Time Database updates.
**[Audio]**
> *"Finally, we simulate Razorpay webhooks. When an invoice is paid or fails, the webhook hits our backend, diagnoses the root cause, and autonomously closes the recovery loop by updating our database in real-time."*

### 4. Conclusion (2:00 - 2:30)
**[Visual]** Switch back to Tab 1 (Dashboard) or end on the AegisPay logo.
**[Audio]**
> *"By combining Razorpay's API, Twilio's WhatsApp gateway, and our bounded AI NLP engine, AegisPay removes the manual operational overhead of collections.*
> *It's a production-ready, safe, and autonomous Revenue Recovery Engine. Thank you!"*

---

### 💡 Why emphasize Tab 5 in the video?
*   **It proves it's real:** It demonstrates that your API integrations (Razorpay, Twilio) and AI NLP logic actually function live, rather than just being mock data.
*   **Visualizes the backend:** Your project does heavy background work (webhooks, state machines). Tab 5 makes those invisible backend processes tangible and easy for judges to understand in a 2-minute window.
