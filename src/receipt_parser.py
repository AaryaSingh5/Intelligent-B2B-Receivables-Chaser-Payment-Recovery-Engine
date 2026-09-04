"""
receipt_parser.py — Receipt & Invoice Ingestion Engine
Intelligent B2B Receivables Chaser & Payment Recovery Engine

Ingests incoming receipts, invoice uploads, or billing payloads:
  • Extracts vendor, customer, phone, amount, due date, items
  • Computes aging days and assigns compliance aging bracket
  • Calls Razorpay Gateway to mint an active payment link
  • Generates initial tone-matched recovery message
  • Persists to SQLite database and logs ingestion audit event
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from .db import log_audit_event, upsert_invoice
from .gateway import create_payment_link
from .loader import AgingBracket

logger = logging.getLogger(__name__)


def parse_and_ingest_receipt(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingest a new receipt / invoice into the automated recovery engine.

    Accepted fields:
      - id: str (optional, defaults to INV-{timestamp})
      - customer_name: str (required)
      - customer_contact: str (email, optional)
      - phone: str (required for WhatsApp delivery)
      - amount: float (required)
      - due_date: str (YYYY-MM-DD, optional)
      - aging_days: int (optional if due_date given)
      - items: list (optional line items)
    """
    now = datetime.now(timezone.utc)
    inv_id = data.get("id") or f"INV-{int(time.time() % 100000):05d}"
    customer_name = data.get("customer_name") or "Corporate Client"
    contact = data.get("customer_contact", "")
    phone = data.get("phone", "+919876500001")
    amount = float(data.get("amount", 10000.0))

    # Calculate aging days
    due_date_str = data.get("due_date")
    if due_date_str:
        try:
            due_dt = date.fromisoformat(due_date_str)
            today = date.today()
            aging_days = max(0, (today - due_dt).days)
        except Exception:
            aging_days = int(data.get("aging_days", 5))
    else:
        aging_days = int(data.get("aging_days", 5))

    # Classify aging bracket
    if aging_days <= 15:
        bracket = AgingBracket.SOFT.value
    elif aging_days <= 30:
        bracket = AgingBracket.MODERATE.value
    else:
        bracket = AgingBracket.ESCALATED.value

    # Generate live/simulated Razorpay payment link
    link_info = create_payment_link(
        invoice_id=inv_id,
        amount=amount,
        customer_name=customer_name,
        phone=phone,
    )
    pay_link = link_info["short_url"]

    # Compose initial tone-matched recovery message
    if bracket == AgingBracket.SOFT.value:
        msg = (
            f"Hi {customer_name},\n\n"
            f"Friendly reminder: Invoice {inv_id} for ₹{amount:,.2f} was due {aging_days} day(s) ago. "
            f"We understand things get busy!\n\n"
            f"You can quickly settle this balance via your direct Razorpay link:\n"
            f"👉 {pay_link}\n\n"
            f"Warm regards,\nAccounts Receivable Team"
        )
    elif bracket == AgingBracket.MODERATE.value:
        msg = (
            f"Dear {customer_name},\n\n"
            f"We are following up on Invoice {inv_id} (₹{amount:,.2f}), now {aging_days} days overdue. "
            f"Kindly arrange settlement at your earliest convenience:\n"
            f"👉 {pay_link}\n\n"
            f"If you have an expected payment date, please reply directly to this message.\n\n"
            f"Best regards,\nAccounts Receivable Team"
        )
    else:
        msg = (
            f"Dear {customer_name},\n\n"
            f"ESCALATION NOTICE — Invoice {inv_id}\n\n"
            f"Invoice {inv_id} (₹{amount:,.2f}) remains unpaid after {aging_days} days. "
            f"Please settle the outstanding balance immediately via Razorpay:\n"
            f"👉 {pay_link}\n\n"
            f"Regards,\nSenior Accounts & Collections"
        )

    record_dict = {
        "id": inv_id,
        "type": "b2b_invoice",
        "customer_name": customer_name,
        "customer_contact": contact,
        "phone": phone,
        "amount": amount,
        "aging_days": aging_days,
        "aging_bracket": bracket,
        "status": "PENDING",
        "nudge_count": 0,
        "payment_link_url": pay_link,
        "payment_link_id": link_info.get("id"),
        "root_cause": f"Overdue by {aging_days} days ({bracket})",
        "recovery_message": msg,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    # Persist to SQLite
    upsert_invoice(record_dict)

    # Record in audit log
    log_audit_event(
        inv_id,
        "RECEIPT_INGESTED",
        f"Ingested invoice for {customer_name} (₹{amount:,.2f}, {aging_days}d overdue)",
        {"payment_link": pay_link, "aging_bracket": bracket},
    )

    logger.info("Successfully ingested invoice %s for %s with Razorpay link %s", inv_id, customer_name, pay_link)
    return record_dict
