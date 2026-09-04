"""
server.py — FastAPI Webhook & Live Automation Server
Intelligent B2B Receivables Chaser & Payment Recovery Engine

Exposes production webhook and REST endpoints:
  • POST /api/receipts/ingest           — Receipt & Invoice ingestion
  • POST /api/webhooks/razorpay         — Razorpay Payment Gateway webhook listener
  • POST /api/webhooks/twilio/whatsapp  — Twilio WhatsApp Inbound message webhook
  • POST /api/automation/sweep          — Trigger autonomous recovery sweep
  • GET  /api/invoices                  — Live SQLite invoice state
  • GET  /api/health                    — Health check & metrics
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.db import get_all_invoices, get_invoice, get_live_metrics, init_db
from src.dispatcher import handle_inbound_whatsapp
from src.gateway import handle_payment_failed, handle_payment_paid, verify_webhook_signature
from src.receipt_parser import parse_and_ingest_receipt
from src.scheduler import run_recovery_sweep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recovery_server")

app = FastAPI(
    title="Revenue Recovery Engine — Automation Server",
    description="Event-Driven Webhook & Autonomous Revenue Recovery Platform for Track 3",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Persistent SQLite database initialized and ready.")


@app.get("/")
def root():
    return {
        "service": "Revenue Recovery Engine — Automation Server",
        "status": "online",
        "version": "2.0.0",
        "track": "Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery",
        "endpoints": {
            "health": "/api/health",
            "invoices": "/api/invoices",
            "receipt_ingest": "/api/receipts/ingest",
            "razorpay_webhook": "/api/webhooks/razorpay",
            "whatsapp_webhook": "/api/webhooks/twilio/whatsapp",
            "run_sweep": "/api/automation/sweep",
        },
    }


@app.get("/api/health")
def health():
    metrics = get_live_metrics()
    return {
        "status": "healthy",
        "database": "sqlite_connected",
        "metrics": metrics,
    }


@app.get("/api/invoices")
def list_invoices():
    return {"invoices": get_all_invoices()}


@app.get("/api/invoices/{invoice_id}")
def get_single_invoice(invoice_id: str):
    inv = get_invoice(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    return inv


class ReceiptIngestRequest(BaseModel):
    id: Optional[str] = None
    customer_name: str
    customer_contact: Optional[str] = ""
    phone: str
    amount: float
    due_date: Optional[str] = None
    aging_days: Optional[int] = 5


@app.post("/api/receipts/ingest")
def ingest_receipt(payload: ReceiptIngestRequest):
    """
    Ingest a new receipt / invoice.
    Automatically generates a Razorpay payment link and creates a tracked record in DB.
    """
    record = parse_and_ingest_receipt(payload.model_dump())
    return {
        "status": "success",
        "message": f"Receipt {record['id']} successfully ingested and scheduled for recovery monitoring.",
        "record": record,
    }


@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request, x_razorpay_signature: Optional[str] = Header(None)):
    """
    Live Razorpay Webhook Endpoint:
      - payment.failed       → Diagnoses error code, generates payment link, dispatches WhatsApp
      - payment_link.paid    → Marks invoice as RECOVERED, sends payment confirmation
      - payment.captured     → Marks invoice as RECOVERED
    """
    body_bytes = await request.body()
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event = data.get("event", "")
    logger.info("[RAZORPAY WEBHOOK] Received event: %s", event)

    # Signature verification (checked if secret configured)
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if secret and x_razorpay_signature:
        if not verify_webhook_signature(body_bytes, x_razorpay_signature, secret):
            raise HTTPException(status_code=400, detail="Invalid HMAC-SHA256 signature")

    if event == "payment.failed":
        result = handle_payment_failed(data)
        return {"status": "processed", "event": event, "result": result}
    elif event in ("payment_link.paid", "payment.captured"):
        result = handle_payment_paid(data)
        return {"status": "processed", "event": event, "result": result}
    else:
        return {"status": "acknowledged", "event": event, "message": "Event received and recorded"}


@app.post("/api/webhooks/twilio/whatsapp")
async def twilio_whatsapp_webhook(request: Request):
    """
    Inbound Twilio WhatsApp Webhook:
    Receives customer WhatsApp replies, uses NLP to detect promise-to-pay dates,
    pauses escalation, and returns an automated WhatsApp confirmation.
    """
    form = {}
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            form = await request.json()
        except Exception:
            pass
    else:
        try:
            form_data = await request.form()
            form = dict(form_data)
        except Exception:
            pass

    from_number = form.get("From") or form.get("phone") or form.get("from") or ""
    message_body = form.get("Body") or form.get("message") or form.get("body") or ""

    if not from_number or not message_body:
        raise HTTPException(status_code=400, detail="Missing 'From' or 'Body' in webhook payload")

    logger.info("[TWILIO WEBHOOK] Inbound WhatsApp from %s: '%s'", from_number, message_body)
    result = handle_inbound_whatsapp(from_number=from_number, message_body=message_body)

    # Return standard TwiML or JSON
    twiml_resp = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Message>{result.get("auto_reply")}</Message></Response>'
    )
    return Response(content=twiml_resp, media_type="application/xml")


@app.post("/api/automation/sweep")
def trigger_sweep(dry_run: bool = True, background_tasks: BackgroundTasks = BackgroundTasks()):
    """
    Run the autonomous recovery sweep:
    Checks promise expirations, advances aging, enforces stopping rules, and dispatches notices.
    """
    summary = run_recovery_sweep(dry_run=dry_run)
    return {
        "status": "sweep_completed",
        "summary": summary,
    }


if __name__ == "__main__":
    port = int(os.getenv("FASTAPI_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

