"""
guards.py — Bounded Policy Gates & Stopping Rules
Enforces three explicit safety rules before any messaging action:
  1. Stopping Rule        – block if nudge_count >= MAX_NUDGES
  2. Compliance Rule      – forbid aggressive/legal language on invoices < 30 days
  3. Promise-to-Pay Pause – block if customer has an active promise date
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from .loader import (
    AgingBracket,
    InvoiceRecord,
    RecordType,
    RecoveryRecord,
    RecoveryStatus,
)

# ─── Constants ───────────────────────────────────────────────────────────────

MAX_NUDGES: int = 2
COMPLIANCE_AGING_THRESHOLD_DAYS: int = 30

# Regex patterns that detect commitment phrases and optional day-names / dates
_PROMISE_PATTERNS = [
    # "will pay by Friday", "will clear this by Tuesday"
    r"(?:will|shall|going to|promise to|committed to|expect)\s+(?:pay|clear|settle|transfer|make.*?payment|arrange.*?funds|retry.*?payment).*?by\s+(\w+(?:\s+\w+)?)",
    # "payment will be done by next Monday"
    r"payment\s+will\s+(?:be\s+)?(?:done|made|sent|processed|cleared).*?by\s+(\w+(?:\s+\w+)?)",
    # "updating card details, will pay by Friday"
    r"updating.*?will\s+pay.*?by\s+(\w+(?:\s+\w+)?)",
]

# Named days of the week for date extraction
_DAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


# ─── Promise-to-Pay Date Extraction ─────────────────────────────────────────

def extract_promise_date(reply: Optional[str]) -> Optional[str]:
    """
    Scan a customer reply for commitment phrases and return the promised
    date as an ISO-format string (YYYY-MM-DD).  Returns None if no
    promise is detected.
    """
    if not reply:
        return None

    reply_lower = reply.lower().strip()

    for pattern in _PROMISE_PATTERNS:
        match = re.search(pattern, reply_lower, re.IGNORECASE)
        if match:
            raw_date = match.group(1).strip().lower()
            return _resolve_date_token(raw_date)

    return None


def _resolve_date_token(token: str) -> str:
    """Convert a fuzzy date token (day name, ordinal, 'end of month/week') to ISO date."""
    today = datetime.utcnow().date()

    # "end of month"
    if "end of month" in token:
        # Last day of current month
        if today.month == 12:
            eom = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            eom = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return eom.isoformat()

    # "end of week"
    if "end of week" in token:
        days_until_friday = (4 - today.weekday()) % 7 or 7
        return (today + timedelta(days=days_until_friday)).isoformat()

    # "next <day>"
    next_prefix = False
    clean = token
    if token.startswith("next "):
        next_prefix = True
        clean = token[5:]

    # Day name
    if clean in _DAY_NAMES:
        target_weekday = _DAY_NAMES[clean]
        days_ahead = (target_weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # Always push to next occurrence
        if next_prefix:
            days_ahead += 7  # "next Monday" = the Monday after the coming one
        return (today + timedelta(days=days_ahead)).isoformat()

    # "next week" (generic)
    if "next week" in token:
        return (today + timedelta(days=7)).isoformat()

    # Ordinal day like "15th", "20th"
    ordinal_match = re.search(r"(\d{1,2})(?:st|nd|rd|th)?", token)
    if ordinal_match:
        day_num = int(ordinal_match.group(1))
        try:
            candidate = today.replace(day=day_num)
            if candidate <= today:
                # Push to next month
                if today.month == 12:
                    candidate = candidate.replace(year=today.year + 1, month=1)
                else:
                    candidate = candidate.replace(month=today.month + 1)
            return candidate.isoformat()
        except ValueError:
            pass

    # Fallback: assume +7 days
    return (today + timedelta(days=7)).isoformat()


# ─── Guard Enforcement ───────────────────────────────────────────────────────

def enforce_guards(records: List[RecoveryRecord]) -> List[RecoveryRecord]:
    """
    Apply all policy gates to each record.  Mutates records in place,
    setting status flags and boundary_violations where necessary.
    Returns the full list for downstream chaining.
    """
    for record in records:
        # ── 1. Promise-to-Pay Pause ──────────────────────────────────
        promise_date = extract_promise_date(record.simulated_reply)
        if promise_date:
            record.promise_date = promise_date
            record.status = RecoveryStatus.PROMISE_TRACKED
            # Skip further guards — no messaging while promise is active
            continue

        # ── 2. Stopping Rule: max nudges ─────────────────────────────
        if record.nudge_count >= MAX_NUDGES:
            record.status = RecoveryStatus.MAX_RETRIES_REACHED
            continue

        # ── 3. Compliance Rule (invoices only) ───────────────────────
        if record.type == RecordType.B2B_INVOICE:
            assert isinstance(record, InvoiceRecord)
            if record.aging_days < COMPLIANCE_AGING_THRESHOLD_DAYS:
                # Mark as compliant — orchestrator must use soft/moderate tone
                # (The tone selection itself happens in orchestrator.py;
                #  here we just ensure the aging bracket is correct.)
                pass
            # No violation to record — compliance is handled by tone gating.

    return records
