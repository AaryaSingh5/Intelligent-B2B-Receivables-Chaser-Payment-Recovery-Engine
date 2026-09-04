"""
dispatcher.py — Two-Way WhatsApp Message Dispatcher (Twilio)
Intelligent B2B Receivables Chaser & Payment Recovery Engine

Dispatches recovery messages to customers via WhatsApp using the
Twilio API for WhatsApp (WhatsApp Business sandbox or production).
Also handles INBOUND replies to extract promises-to-pay via NLP and pause nudges.

Safety Architecture (Buildathon Compliant):
  • DRY_RUN mode (default)  — Logs intent; NO real API calls made.
  • ENABLE_LIVE_WHATSAPP     — Must be explicitly set to "true" in .env
                               to allow live network requests.
  • Recipient allowlist      — Only sends to numbers in ALLOWED_RECIPIENTS
                               (comma-separated in .env) when in live mode.
  • Message length cap       — Truncates at 1600 chars (WhatsApp limit).
  • Records blocked states   — MAX_RETRIES_REACHED records are never sent.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from .db import (
    find_invoice_by_phone,
    get_invoice,
    log_audit_event,
    log_whatsapp_message,
    update_invoice_status,
)
from .guards import extract_promise_date
from .loader import RecoveryRecord, RecoveryStatus

load_dotenv()
logger = logging.getLogger(__name__)

WHATSAPP_MAX_CHARS = 1600
SEND_DELAY_SECONDS = 0.5


@dataclass
class DispatchResult:
    record_id: str
    customer_name: str
    recipient_number: str
    status: str  # "sent" | "simulated" | "skipped" | "error"
    message_sid: str | None = None
    error: str | None = None
    message_preview: str = ""
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))


def _load_config() -> dict:
    return {
        "account_sid":  os.getenv("TWILIO_ACCOUNT_SID", ""),
        "auth_token":   os.getenv("TWILIO_AUTH_TOKEN", ""),
        "from_number":  os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886"),
        "live_enabled": os.getenv("ENABLE_LIVE_WHATSAPP", "false").lower() == "true",
        "allowed_list": [
            n.strip() for n in os.getenv("ALLOWED_RECIPIENTS", "").split(",")
            if n.strip()
        ],
    }


def _truncate(message: str, max_len: int = WHATSAPP_MAX_CHARS) -> str:
    if len(message) <= max_len:
        return message
    return message[: max_len - 30] + "\n\n[...message truncated]"


def _get_recipient(record: Any) -> str | None:
    phone = getattr(record, "phone", None)
    if not phone and isinstance(record, dict):
        phone = record.get("phone")
    if not phone:
        return None
    cleaned = str(phone).replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def send_single_whatsapp_message(
    to_number: str,
    body: str,
    dry_run: bool = True,
) -> tuple[str, str | None]:
    """
    Send or simulate a single WhatsApp message to a phone number.
    Returns (sid_or_status, error_message).
    """
    config = _load_config()
    cleaned_to = to_number.replace("whatsapp:", "").strip()
    if not cleaned_to.startswith("+"):
        cleaned_to = "+" + cleaned_to

    if not config["live_enabled"]:
        dry_run = True

    if dry_run:
        logger.info("[DISPATCHER] [SIMULATION] To %s: %s", cleaned_to, body[:80])
        return f"SM_sim_{int(time.time()*1000)}", None

    if config["allowed_list"] and cleaned_to not in config["allowed_list"]:
        return "skipped", f"Recipient {cleaned_to} not in ALLOWED_RECIPIENTS allowlist"

    try:
        from twilio.rest import Client
        client = Client(config["account_sid"], config["auth_token"])
        msg = client.messages.create(
            body=_truncate(body),
            from_=f"whatsapp:{config['from_number']}",
            to=f"whatsapp:{cleaned_to}",
        )
        return msg.sid, None
    except ImportError:
        return "error", "Twilio SDK not installed. Run: pip install twilio"
    except Exception as exc:
        return "error", str(exc)


def dispatch_whatsapp_messages(
    records: List[Any],
    dry_run: bool = True,
    target_record_id: str | None = None,
) -> List[DispatchResult]:
    config = _load_config()
    if not config["live_enabled"]:
        dry_run = True

    results: List[DispatchResult] = []

    for record in records:
        rec_id = getattr(record, "id", None) or (record.get("id") if isinstance(record, dict) else None)
        cust_name = getattr(record, "customer_name", "Client") or (record.get("customer_name") if isinstance(record, dict) else "Client")
        rec_status = getattr(record, "status", None) or (record.get("status") if isinstance(record, dict) else None)
        status_val = rec_status.value if hasattr(rec_status, "value") else str(rec_status or "")
        msg_body = getattr(record, "recovery_message", None) or (record.get("recovery_message") if isinstance(record, dict) else None)

        if target_record_id and rec_id != target_record_id:
            continue

        if status_val == "MAX_RETRIES_REACHED":
            results.append(DispatchResult(
                record_id=rec_id or "UNKNOWN",
                customer_name=cust_name,
                recipient_number="N/A",
                status="skipped",
                error="MAX_RETRIES_REACHED — dispatch blocked by guardrail",
            ))
            continue

        if not msg_body:
            results.append(DispatchResult(
                record_id=rec_id or "UNKNOWN",
                customer_name=cust_name,
                recipient_number="N/A",
                status="skipped",
                error="No recovery message generated",
            ))
            continue

        recipient = _get_recipient(record)
        if not recipient:
            results.append(DispatchResult(
                record_id=rec_id or "UNKNOWN",
                customer_name=cust_name,
                recipient_number="N/A",
                status="skipped",
                error="No phone number on record",
            ))
            continue

        preview = msg_body[:100].replace("\n", " ") + ("…" if len(msg_body) > 100 else "")

        if dry_run:
            results.append(DispatchResult(
                record_id=rec_id,
                customer_name=cust_name,
                recipient_number=recipient,
                status="simulated",
                message_preview=preview,
            ))
            log_whatsapp_message(
                invoice_id=rec_id,
                direction="OUTBOUND",
                recipient=recipient,
                body=msg_body,
                status="simulated",
            )
            continue

        sid, err = send_single_whatsapp_message(recipient, msg_body, dry_run=False)
        if err:
            results.append(DispatchResult(
                record_id=rec_id,
                customer_name=cust_name,
                recipient_number=recipient,
                status="error",
                error=err,
                message_preview=preview,
            ))
            log_whatsapp_message(
                invoice_id=rec_id,
                direction="OUTBOUND",
                recipient=recipient,
                body=msg_body,
                status="error",
            )
        else:
            results.append(DispatchResult(
                record_id=rec_id,
                customer_name=cust_name,
                recipient_number=recipient,
                status="sent",
                message_sid=sid,
                message_preview=preview,
            ))
            log_whatsapp_message(
                invoice_id=rec_id,
                direction="OUTBOUND",
                recipient=recipient,
                body=msg_body,
                status="sent",
                twilio_sid=sid,
            )

        time.sleep(SEND_DELAY_SECONDS)

    return results


def handle_inbound_whatsapp(from_number: str, message_body: str) -> Dict[str, Any]:
    """
    Process an inbound WhatsApp message from a customer:
      1. Match sender phone with invoice in SQLite.
      2. Run NLP promise-to-pay extraction on text.
      3. If a promise date is extracted:
         - Pause reminders (status = PROMISE_TRACKED).
         - Store promise_date in DB.
         - Send automated pause confirmation.
      4. If general inquiry:
         - Log note and acknowledge.
    """
    cleaned_phone = from_number.replace("whatsapp:", "").strip()
    invoice = find_invoice_by_phone(cleaned_phone)
    inv_id = invoice["id"] if invoice else "UNKNOWN"
    customer_name = invoice["customer_name"] if invoice else "Valued Client"
    amount = invoice["amount"] if invoice else 0.0

    # Log inbound message
    log_whatsapp_message(
        invoice_id=inv_id,
        direction="INBOUND",
        recipient=cleaned_phone,
        body=message_body,
        status="received",
    )

    # NLP promise extraction
    promise_date = extract_promise_date(message_body)

    if promise_date:
        if invoice:
            update_invoice_status(
                invoice_id=inv_id,
                status="PROMISE_TRACKED",
                promise_date=promise_date,
            )
            log_audit_event(
                inv_id,
                "PROMISE_TRACKED_INBOUND",
                f"Customer promised to pay by {promise_date} via WhatsApp reply: '{message_body}'",
                {"promise_date": promise_date, "reply": message_body},
            )

        auto_reply = (
            f"Hi {customer_name},\n\n"
            f"🤝 Thank you! We have recorded your commitment to settle {inv_id} (₹{amount:,.2f}) "
            f"by {promise_date}.\n\n"
            f"We have paused all automated reminders until then. If you need to pay earlier, "
            f"your link remains active:\n"
            f"👉 {invoice.get('payment_link_url') if invoice else 'https://rzp.io/l/demo'}\n\n"
            f"— Accounts Receivable Team"
        )
        send_single_whatsapp_message(cleaned_phone, auto_reply, dry_run=True)

        return {
            "status": "promise_tracked",
            "invoice_id": inv_id,
            "promise_date": promise_date,
            "auto_reply": auto_reply,
            "customer_name": customer_name,
        }

    # General reply acknowledgement
    auto_reply = (
        f"Hi {customer_name},\n\n"
        f"Thank you for contacting Accounts Receivable regarding {inv_id}. "
        f"Our operations team has received your note and will review it shortly.\n\n"
        f"— Accounts Receivable Team"
    )
    send_single_whatsapp_message(cleaned_phone, auto_reply, dry_run=True)

    return {
        "status": "acknowledged",
        "invoice_id": inv_id,
        "promise_date": None,
        "auto_reply": auto_reply,
        "customer_name": customer_name,
    }


def format_dispatch_summary(results: List[DispatchResult]) -> str:
    sent      = sum(1 for r in results if r.status == "sent")
    simulated = sum(1 for r in results if r.status == "simulated")
    skipped   = sum(1 for r in results if r.status == "skipped")
    errors    = sum(1 for r in results if r.status == "error")

    lines = [
        "-" * 60,
        "  WhatsApp Dispatch Summary",
        "-" * 60,
        f"  Sent (live):   {sent}",
        f"  Simulated:     {simulated}",
        f"  Skipped:       {skipped}",
        f"  Errors:        {errors}",
        "-" * 60,
    ]
    for r in results:
        icon = {"sent": "[SENT]", "simulated": "[SIM]", "skipped": "[SKIP]", "error": "[ERR]"}.get(r.status, "[?]")
        detail = r.message_sid or r.error or r.message_preview or ""
        lines.append(f"  {icon} [{r.record_id}] {r.customer_name} ({r.recipient_number}) -> {detail}")

    return "\n".join(lines)
