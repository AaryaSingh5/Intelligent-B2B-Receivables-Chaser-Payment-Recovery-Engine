"""
orchestrator.py — Contextual Recovery Message Generator
Produces the appropriate outbound communication for each record based on
its type, aging bracket, guard status, and root cause.

Message tiers for B2B invoices:
  • Soft (1-15 days)   → Gentle payment reminder
  • Moderate (16-30d)  → Firm follow-up
  • Escalated (31+ d)  → Formal escalation notice

Payment failures receive tailored retry / update prompts based on the
diagnosed root cause.

Records in PROMISE_TRACKED or MAX_RETRIES_REACHED states receive
appropriate hold / closure messages instead of collection nudges.
"""

from __future__ import annotations

from typing import List

from .loader import (
    AgingBracket,
    InvoiceRecord,
    PaymentFailureRecord,
    RecordType,
    RecoveryRecord,
    RecoveryStatus,
)


# ─── Invoice Message Templates ──────────────────────────────────────────────

_INVOICE_TEMPLATES: dict[AgingBracket, str] = {
    AgingBracket.SOFT: (
        "Hi {name},\n\n"
        "This is a friendly reminder that Invoice {id} for ₹{amount:,.2f} "
        "was due {days} day(s) ago. We understand things can slip through — "
        "could you kindly arrange payment at your earliest convenience?\n\n"
        "If you've already initiated the transfer, please disregard this note.\n\n"
        "Warm regards,\nAccounts Receivable Team"
    ),
    AgingBracket.MODERATE: (
        "Dear {name},\n\n"
        "We are following up on Invoice {id} (₹{amount:,.2f}), now overdue "
        "by {days} days. As per our payment terms, we kindly request immediate "
        "attention to this outstanding balance.\n\n"
        "Please share an expected payment date or reach out if there are "
        "any concerns we can help resolve.\n\n"
        "Best regards,\nAccounts Receivable Team"
    ),
    AgingBracket.ESCALATED: (
        "Dear {name},\n\n"
        "ESCALATION NOTICE — Invoice {id}\n\n"
        "Despite prior communications, Invoice {id} (₹{amount:,.2f}) remains "
        "unpaid after {days} days. This matter has been escalated internally.\n\n"
        "We strongly urge you to settle this balance within 5 business days "
        "to avoid further collection procedures. Please contact us immediately "
        "to discuss a resolution.\n\n"
        "Regards,\nSenior Accounts & Collections"
    ),
}


# ─── Payment Failure Message Templates ───────────────────────────────────────

_PAYMENT_TEMPLATES: dict[str, str] = {
    "ERR_GATEWAY_TIMEOUT": (
        "Hi {name},\n\n"
        "Your recent payment of ₹{amount:,.2f} could not be processed due to "
        "a gateway timeout (a temporary infrastructure issue). We will "
        "automatically retry the transaction shortly.\n\n"
        "No action is required from your side at this time.\n\n"
        "— Payment Operations"
    ),
    "ERR_INSUFFICIENT_FUNDS": (
        "Hi {name},\n\n"
        "Your payment of ₹{amount:,.2f} was declined because of insufficient "
        "funds in the linked account. Please ensure adequate balance and "
        "retry the payment, or update your payment method.\n\n"
        "— Payment Operations"
    ),
    "ERR_CARD_EXPIRED": (
        "Hi {name},\n\n"
        "The card linked to your account has expired, which caused your "
        "₹{amount:,.2f} payment to fail. Please update your card details "
        "in your account settings and retry.\n\n"
        "— Payment Operations"
    ),
    "ERR_BANK_DECLINED": (
        "Hi {name},\n\n"
        "Your bank declined the ₹{amount:,.2f} transaction. This may be due "
        "to internal risk flags or account restrictions. We recommend "
        "contacting your bank for clarification, then retrying the payment.\n\n"
        "— Payment Operations"
    ),
    "ERR_NETWORK_ERROR": (
        "Hi {name},\n\n"
        "A network error prevented your ₹{amount:,.2f} payment from "
        "completing. This is typically transient — we will retry "
        "automatically. No action needed from your end.\n\n"
        "— Payment Operations"
    ),
    "ERR_AUTHENTICATION_FAILED": (
        "Hi {name},\n\n"
        "Your ₹{amount:,.2f} payment failed because 3-D Secure / OTP "
        "authentication was not completed. Please reattempt the payment "
        "and ensure you complete the verification step.\n\n"
        "— Payment Operations"
    ),
    "ERR_DUPLICATE_TRANSACTION": (
        "Hi {name},\n\n"
        "A duplicate transaction was detected for ₹{amount:,.2f}. Our "
        "system blocked the second attempt to protect you. Please verify "
        "whether the original payment succeeded before retrying.\n\n"
        "— Payment Operations"
    ),
}

_PAYMENT_GENERIC = (
    "Hi {name},\n\n"
    "Your payment of ₹{amount:,.2f} encountered an unexpected error. "
    "Our team is investigating. We will reach out with next steps shortly.\n\n"
    "— Payment Operations"
)


# ─── Hold / Closure Messages ────────────────────────────────────────────────

_PROMISE_HOLD_MSG = (
    "Hi {name},\n\n"
    "Thank you for your commitment to settle {id} (₹{amount:,.2f}) by "
    "{promise_date}. We have paused further reminders and will follow up "
    "after the promised date if payment has not been received.\n\n"
    "— Accounts Receivable Team"
)

_MAX_RETRIES_MSG = (
    "INTERNAL NOTE — {id}\n\n"
    "Maximum nudge limit reached for {name} (₹{amount:,.2f}). "
    "No further automated messages will be sent. Record has been flagged "
    "for manual review by the collections team."
)


# ─── Public API ──────────────────────────────────────────────────────────────

def generate_messages(records: List[RecoveryRecord]) -> List[RecoveryRecord]:
    """
    Generate the appropriate recovery / hold message for every record
    based on its current status, type, and diagnosis.
    """
    for record in records:
        # ── Promise-tracked: pause message ───────────────────────────
        if record.status == RecoveryStatus.PROMISE_TRACKED:
            record.recovery_message = _PROMISE_HOLD_MSG.format(
                name=record.customer_name,
                id=record.id,
                amount=record.amount,
                promise_date=record.promise_date or "TBD",
            )
            continue

        # ── Max retries reached: internal hold note ──────────────────
        if record.status == RecoveryStatus.MAX_RETRIES_REACHED:
            record.recovery_message = _MAX_RETRIES_MSG.format(
                name=record.customer_name,
                id=record.id,
                amount=record.amount,
            )
            continue

        # ── B2B Invoice: tone matches aging bracket ──────────────────
        if record.type == RecordType.B2B_INVOICE:
            assert isinstance(record, InvoiceRecord)
            template = _INVOICE_TEMPLATES.get(
                record.aging_bracket, _INVOICE_TEMPLATES[AgingBracket.SOFT]
            )
            record.recovery_message = template.format(
                name=record.customer_name,
                id=record.id,
                amount=record.amount,
                days=record.aging_days,
            )
            record.status = RecoveryStatus.NUDGE_SENT
            continue

        # ── Payment Failure: root-cause-aware retry prompt ───────────
        if record.type == RecordType.PAYMENT_FAILURE:
            assert isinstance(record, PaymentFailureRecord)
            template = _PAYMENT_TEMPLATES.get(record.error_code, _PAYMENT_GENERIC)
            record.recovery_message = template.format(
                name=record.customer_name,
                amount=record.amount,
            )
            record.status = RecoveryStatus.NUDGE_SENT
            continue

    return records
