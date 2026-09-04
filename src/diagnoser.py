"""
diagnoser.py — Root-Cause Classifier & Aging Bracket Engine
Maps gateway error codes to human-readable root causes for payment failures,
and assigns aging brackets (Soft / Moderate / Escalated) for B2B invoices.
"""

from __future__ import annotations

from typing import List

from .loader import (
    AgingBracket,
    InvoiceRecord,
    PaymentFailureRecord,
    RecordType,
    RecoveryRecord,
)

# ─── Error-Code → Root-Cause Mapping ────────────────────────────────────────

ERROR_CODE_MAP: dict[str, str] = {
    "ERR_GATEWAY_TIMEOUT": (
        "Payment gateway timed out before receiving a response from the "
        "acquiring bank. Likely a transient infrastructure issue — safe to retry."
    ),
    "ERR_INSUFFICIENT_FUNDS": (
        "Customer's account had insufficient funds at the time of charge. "
        "Recommend nudging the customer to top up and retry."
    ),
    "ERR_CARD_EXPIRED": (
        "The card on file has expired. Customer must update their payment "
        "instrument before a successful charge can occur."
    ),
    "ERR_BANK_DECLINED": (
        "Issuing bank declined the transaction without a specific sub-code. "
        "May indicate risk flags or account restrictions on the customer's side."
    ),
    "ERR_NETWORK_ERROR": (
        "A network-level failure occurred between the payment gateway and the "
        "bank network. Transient — automatic retry is recommended."
    ),
    "ERR_AUTHENTICATION_FAILED": (
        "3-D Secure / OTP authentication failed or was abandoned by the "
        "customer. They should be prompted to reattempt with correct credentials."
    ),
    "ERR_DUPLICATE_TRANSACTION": (
        "A duplicate transaction was detected by the gateway's idempotency "
        "layer. Verify whether the original transaction succeeded before retrying."
    ),
}

UNKNOWN_ERROR_ROOT_CAUSE = (
    "Unrecognised error code. Manual investigation required — "
    "escalate to the payments-ops team."
)


# ─── Aging Bracket Classifier ───────────────────────────────────────────────

def _classify_aging(aging_days: int) -> AgingBracket:
    """Return the aging bracket for a given number of overdue days."""
    if aging_days <= 15:
        return AgingBracket.SOFT
    elif aging_days <= 30:
        return AgingBracket.MODERATE
    else:
        return AgingBracket.ESCALATED


# ─── Public API ──────────────────────────────────────────────────────────────

def diagnose(records: List[RecoveryRecord]) -> List[RecoveryRecord]:
    """
    Enrich every record with diagnostic metadata:
      • Payment failures  → root_cause (from error code map)
      • B2B invoices      → aging_bracket + descriptive root_cause
    """
    for record in records:
        if record.type == RecordType.PAYMENT_FAILURE:
            assert isinstance(record, PaymentFailureRecord)
            record.root_cause = ERROR_CODE_MAP.get(
                record.error_code, UNKNOWN_ERROR_ROOT_CAUSE
            )

        elif record.type == RecordType.B2B_INVOICE:
            assert isinstance(record, InvoiceRecord)
            bracket = _classify_aging(record.aging_days)
            record.aging_bracket = bracket
            record.root_cause = (
                f"Invoice overdue by {record.aging_days} day(s) — "
                f"classified as {bracket.value}."
            )

    return records
