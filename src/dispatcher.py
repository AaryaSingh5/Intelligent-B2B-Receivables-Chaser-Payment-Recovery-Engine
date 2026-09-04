"""
dispatcher.py -- WhatsApp Message Dispatcher (Twilio)
Intelligent B2B Receivables Chaser & Payment Recovery Engine

Dispatches recovery messages to customers via WhatsApp using the
Twilio API for WhatsApp (WhatsApp Business sandbox or production).

Safety Architecture (Buildathon Compliant):
  * DRY_RUN mode (default)  -- Logs intent; NO real API calls made.
  * ENABLE_LIVE_WHATSAPP     -- Must be explicitly set to "true" in .env
                               to allow live network requests.
  * Recipient allowlist      -- Only sends to numbers in ALLOWED_RECIPIENTS
                               (comma-separated in .env) when in live mode.
  * Message length cap       -- Truncates at 1600 chars (WhatsApp limit).
  * Records blocked states   -- MAX_RETRIES_REACHED records are never sent.

Environment Variables Required (live mode only):
    TWILIO_ACCOUNT_SID       -- Your Twilio Account SID (starts with "AC")
    TWILIO_AUTH_TOKEN        -- Your Twilio Auth Token
    TWILIO_WHATSAPP_NUMBER   -- Twilio WhatsApp sender (e.g. +14155238886)
    ENABLE_LIVE_WHATSAPP     -- Set to "true" to enable real sends (default: false)
    ALLOWED_RECIPIENTS       -- Comma-separated allowlist of E.164 numbers

Usage:
    from src.dispatcher import dispatch_whatsapp_messages
    results = dispatch_whatsapp_messages(records, dry_run=True)
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

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


def _get_recipient(record: RecoveryRecord) -> str | None:
    phone = getattr(record, "phone", None)
    if not phone:
        return None
    cleaned = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def _send_via_twilio(account_sid, auth_token, from_number, to_number, body):
    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            body=body,
            from_=f"whatsapp:{from_number}",
            to=f"whatsapp:{to_number}",
        )
        return msg.sid, None
    except ImportError:
        return "error", "Twilio SDK not installed. Run: pip install twilio"
    except Exception as exc:
        return "error", str(exc)


def dispatch_whatsapp_messages(
    records: List[RecoveryRecord],
    dry_run: bool = True,
    target_record_id: str | None = None,
) -> List[DispatchResult]:
    config = _load_config()
    if not config["live_enabled"]:
        dry_run = True

    if not dry_run:
        missing = [k for k in ("account_sid", "auth_token") if not config[k]]
        if missing:
            raise ValueError(
                f"Live WhatsApp dispatch requires: {', '.join(missing)}. "
                "Set them in your .env file."
            )

    results: List[DispatchResult] = []

    for record in records:
        if target_record_id and record.id != target_record_id:
            continue

        if record.status == RecoveryStatus.MAX_RETRIES_REACHED:
            results.append(DispatchResult(
                record_id=record.id,
                customer_name=record.customer_name,
                recipient_number="N/A",
                status="skipped",
                error="MAX_RETRIES_REACHED -- dispatch blocked by guardrail",
            ))
            logger.info("[DISPATCHER] Skipped %s -- MAX_RETRIES_REACHED", record.id)
            continue

        if not record.recovery_message:
            results.append(DispatchResult(
                record_id=record.id,
                customer_name=record.customer_name,
                recipient_number="N/A",
                status="skipped",
                error="No recovery message generated",
            ))
            continue

        recipient = _get_recipient(record)
        if not recipient:
            results.append(DispatchResult(
                record_id=record.id,
                customer_name=record.customer_name,
                recipient_number="N/A",
                status="skipped",
                error="No phone number on record",
                message_preview=(record.recovery_message or "")[:80],
            ))
            logger.info("[DISPATCHER] Skipped %s -- no phone number", record.id)
            continue

        body = _truncate(record.recovery_message)
        preview = body[:100].replace("\n", " ") + ("..." if len(body) > 100 else "")

        if dry_run:
            results.append(DispatchResult(
                record_id=record.id,
                customer_name=record.customer_name,
                recipient_number=recipient,
                status="simulated",
                message_preview=preview,
            ))
            logger.info("[DISPATCHER] [DRY RUN] Would send to %s (%s): %s",
                        record.customer_name, recipient, preview)
            continue

        # Live mode -- allowlist guard
        if config["allowed_list"] and recipient not in config["allowed_list"]:
            results.append(DispatchResult(
                record_id=record.id,
                customer_name=record.customer_name,
                recipient_number=recipient,
                status="skipped",
                error=f"Recipient {recipient} not in ALLOWED_RECIPIENTS allowlist",
                message_preview=preview,
            ))
            logger.warning("[DISPATCHER] Allowlist block: %s (%s)", record.id, recipient)
            continue

        sid, err = _send_via_twilio(
            account_sid=config["account_sid"],
            auth_token=config["auth_token"],
            from_number=config["from_number"],
            to_number=recipient,
            body=body,
        )

        if err:
            results.append(DispatchResult(
                record_id=record.id,
                customer_name=record.customer_name,
                recipient_number=recipient,
                status="error",
                error=err,
                message_preview=preview,
            ))
            logger.error("[DISPATCHER] Send failed for %s: %s", record.id, err)
        else:
            results.append(DispatchResult(
                record_id=record.id,
                customer_name=record.customer_name,
                recipient_number=recipient,
                status="sent",
                message_sid=sid,
                message_preview=preview,
            ))
            logger.info("[DISPATCHER] Sent to %s (%s) -- SID: %s",
                        record.customer_name, recipient, sid)

        time.sleep(SEND_DELAY_SECONDS)

    return results


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
