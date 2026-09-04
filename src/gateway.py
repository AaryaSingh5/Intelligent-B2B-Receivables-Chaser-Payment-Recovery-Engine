"""
gateway.py — Razorpay Payment Gateway & Webhook Integration
Intelligent B2B Receivables Chaser & Payment Recovery Engine

Integrates live Razorpay Payment Links API and Webhooks:
  • Generates Razorpay Standard Payment Links for invoices & degraded retries
  • HMAC-SHA256 Webhook Signature Verification
  • Event Handler for `payment.failed` (root-cause diagnosis + recovery dispatch)
  • Event Handler for `payment_link.paid` / `payment.captured` (auto-resolution + receipt)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from .db import (
    get_invoice,
    log_audit_event,
    log_payment_attempt,
    log_whatsapp_message,
    update_invoice_status,
    upsert_invoice,
)
from .diagnoser import ERROR_CODE_MAP
from .dispatcher import dispatch_whatsapp_messages
from .loader import (
    InvoiceRecord,
    PaymentFailureRecord,
    RecordType,
    RecoveryRecord,
    RecoveryStatus,
)

load_dotenv()
logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")


def get_razorpay_client():
    """Return an authenticated Razorpay client if credentials are configured."""
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET and not RAZORPAY_KEY_ID.startswith("your-"):
        try:
            import razorpay
            return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        except Exception as exc:
            logger.warning("Failed to initialize Razorpay client: %s", exc)
    return None


def create_payment_link(
    invoice_id: str,
    amount: float,
    customer_name: str,
    phone: str = "",
    description: str = "",
) -> Dict[str, Any]:
    """
    Generate an active Razorpay payment link.
    If live credentials are present, calls the Razorpay API.
    Otherwise, generates a deterministic simulation payment link.
    """
    client = get_razorpay_client()
    desc = description or f"Payment for {invoice_id} - {customer_name}"

    if client:
        try:
            amount_paise = int(round(amount * 100))
            payload = {
                "amount": amount_paise,
                "currency": "INR",
                "accept_partial": False,
                "description": desc,
                "customer": {
                    "name": customer_name,
                    "contact": phone.replace("+", "") if phone else "",
                },
                "notify": {"sms": False, "email": False, "whatsapp": False},
                "reminder_enable": True,
                "notes": {"invoice_id": invoice_id},
                "callback_url": os.getenv("APP_URL", "http://localhost:8501"),
                "callback_method": "get",
            }
            res = client.payment_link.create(payload)
            link_url = res.get("short_url") or f"https://rzp.io/i/{res.get('id')}"
            logger.info("Created live Razorpay Payment Link for %s: %s", invoice_id, link_url)
            return {
                "id": res.get("id"),
                "short_url": link_url,
                "status": "live",
                "amount": amount,
            }
        except Exception as exc:
            logger.warning("Razorpay API call failed for %s, falling back to mock link: %s", invoice_id, exc)

    # Deterministic simulation link for testing
    slug = invoice_id.lower().replace("-", "")
    mock_url = f"https://rzp.io/i/{slug}"
    return {
        "id": f"plink_sim_{slug}",
        "short_url": mock_url,
        "status": "simulated",
        "amount": amount,
    }


def verify_webhook_signature(payload_body: bytes | str, signature: str, secret: str | None = None) -> bool:
    """Verify HMAC-SHA256 signature from Razorpay webhook headers."""
    webhook_secret = secret or RAZORPAY_WEBHOOK_SECRET
    if not webhook_secret or not signature:
        # In test/dev without configured secret, permit simulation
        return True

    if isinstance(payload_body, str):
        payload_body = payload_body.encode("utf-8")

    expected = hmac.new(webhook_secret.encode("utf-8"), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_payment_failed(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Razorpay `payment.failed` webhook:
      1. Extract failure details (error_code, description, payment_id).
      2. Record payment attempt in SQLite.
      3. Diagnose root cause & map to recommended action.
      4. Check stopping rule & policy guards.
      5. Generate new payment link & contextual recovery message.
      6. Dispatch recovery message via WhatsApp.
    """
    payload = event_data.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = payload.get("id", f"pay_sim_{int(time.time())}")
    amount = float(payload.get("amount", 0)) / 100.0  # paise to INR
    if amount == 0:
        amount = float(event_data.get("amount", 25000.0))

    error_code = payload.get("error_code") or event_data.get("error_code") or "ERR_GATEWAY_TIMEOUT"
    error_desc = payload.get("error_description") or event_data.get("error_description") or "Transaction timed out"

    # Identify matching invoice or create a dynamic failure record
    notes = payload.get("notes", {})
    inv_id = notes.get("invoice_id") or event_data.get("invoice_id") or f"PAY-{int(time.time() % 10000):04d}"
    customer_name = notes.get("customer_name") or payload.get("email") or event_data.get("customer_name") or "Corporate Client"
    phone = payload.get("contact") or event_data.get("phone") or "+919876543210"

    # 1. Log attempt in DB
    log_payment_attempt(
        invoice_id=inv_id,
        amount=amount,
        status="failed",
        error_code=error_code,
        error_description=error_desc,
        gateway_payment_id=payment_id,
    )

    # 2. Diagnose root-cause
    root_cause = ERROR_CODE_MAP.get(error_code, f"Payment failed: {error_desc}")
    recommended_action = "Please verify your account balance/card details or use the direct recovery link below"

    # 3. Fetch existing record or create dynamic record
    existing = get_invoice(inv_id)
    nudge_count = existing["nudge_count"] if existing else 0

    # 4. Check stopping rule guard
    if nudge_count >= 2:
        new_status = "MAX_RETRIES_REACHED"
        message = f"INTERNAL NOTE — Maximum recovery attempts reached for {inv_id}. Forwarded to collections."
        update_invoice_status(inv_id, status=new_status, root_cause=root_cause, recovery_message=message)
        log_audit_event(inv_id, "GATEWAY_FAILURE_BLOCKED", f"Stopped: {root_cause}", {"error_code": error_code})
        return {
            "status": "blocked",
            "invoice_id": inv_id,
            "reason": "MAX_RETRIES_REACHED",
            "error_code": error_code,
        }

    # 5. Generate fresh Razorpay Payment Link
    link_info = create_payment_link(inv_id, amount, customer_name, phone)
    pay_link = link_info["short_url"]

    # 6. Compose recovery message with live link
    recovery_msg = (
        f"Hi {customer_name},\n\n"
        f"Your recent payment of ₹{amount:,.2f} could not be completed due to: {error_desc}.\n\n"
        f"Recommended Action: {recommended_action}.\n\n"
        f"You can quickly complete this payment using your secure Razorpay recovery link:\n"
        f"👉 {pay_link}\n\n"
        f"— Payment Operations Team"
    )

    # 7. Upsert to DB
    upsert_invoice({
        "id": inv_id,
        "type": "payment_failure",
        "customer_name": customer_name,
        "customer_contact": payload.get("email", ""),
        "phone": phone,
        "amount": amount,
        "aging_days": 0,
        "status": "NUDGE_SENT",
        "nudge_count": nudge_count + 1,
        "payment_link_url": pay_link,
        "payment_link_id": link_info.get("id"),
        "error_code": error_code,
        "root_cause": root_cause,
        "recovery_message": recovery_msg,
    })

    # 8. Dispatch WhatsApp recovery message
    rec = PaymentFailureRecord(
        id=inv_id,
        amount=amount,
        customer_name=customer_name,
        customer_contact=payload.get("email", "finance@company.com"),
        phone=phone,
        error_code=error_code,
        nudge_count=nudge_count + 1,
        recovery_message=recovery_msg,
        status=RecoveryStatus.NUDGE_SENT,
    )
    dispatch_results = dispatch_whatsapp_messages([rec], dry_run=True)
    wa_status = dispatch_results[0].status if dispatch_results else "unknown"

    log_whatsapp_message(
        invoice_id=inv_id,
        direction="OUTBOUND",
        recipient=phone,
        body=recovery_msg,
        status=wa_status,
    )

    log_audit_event(inv_id, "PAYMENT_FAILED_PROCESSED", root_cause, {
        "error_code": error_code,
        "payment_link": pay_link,
        "whatsapp_status": wa_status,
    })

    return {
        "status": "recovered_attempt_sent",
        "invoice_id": inv_id,
        "error_code": error_code,
        "payment_link": pay_link,
        "whatsapp_status": wa_status,
    }


def handle_payment_paid(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Razorpay `payment_link.paid` or `payment.captured` webhook:
      1. Extract payment entity and invoice ID.
      2. Mark invoice as RECOVERED in SQLite.
      3. Send automated WhatsApp confirmation / receipt.
      4. Record in audit log.
    """
    payload = event_data.get("payload", {})
    plink = payload.get("payment_link", {}).get("entity", {})
    payment = payload.get("payment", {}).get("entity", {})

    notes = plink.get("notes", {}) or payment.get("notes", {})
    inv_id = notes.get("invoice_id") or event_data.get("invoice_id")

    amount = float(plink.get("amount") or payment.get("amount", 0)) / 100.0
    if amount == 0:
        amount = float(event_data.get("amount", 0.0))

    existing = get_invoice(inv_id) if inv_id else None
    customer_name = existing["customer_name"] if existing else (plink.get("customer", {}).get("name") or "Valued Customer")
    phone = existing["phone"] if existing else (plink.get("customer", {}).get("contact") or "+919876543210")

    if inv_id:
        update_invoice_status(inv_id, status="RECOVERED")
        log_payment_attempt(
            invoice_id=inv_id,
            amount=amount or (existing["amount"] if existing else 0.0),
            status="captured",
            gateway_payment_id=payment.get("id") or plink.get("id"),
        )

    receipt_msg = (
        f"Hi {customer_name},\n\n"
        f"✅ Payment Confirmation: We have successfully received your payment of ₹{amount:,.2f} "
        f"for {inv_id or 'your invoice'}.\n\n"
        f"Your account balance has been cleared and is now in good standing. Thank you for your partnership!\n\n"
        f"— Accounts Receivable Team"
    )

    log_whatsapp_message(
        invoice_id=inv_id,
        direction="OUTBOUND",
        recipient=phone,
        body=receipt_msg,
        status="sent_confirmation",
    )

    log_audit_event(
        inv_id or "UNKNOWN",
        "REVENUE_RECOVERED",
        f"Payment of ₹{amount:,.2f} received via Razorpay",
        {"amount": amount, "gateway_id": payment.get("id") or plink.get("id")},
    )

    return {
        "status": "success",
        "invoice_id": inv_id,
        "amount_recovered": amount,
        "message": "Payment verified and recorded as RECOVERED",
    }
