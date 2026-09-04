"""
scheduler.py — Autonomous Revenue Recovery Scheduler & Sweep Daemon
Intelligent B2B Receivables Chaser & Payment Recovery Engine

Executes continuous, bounded recovery cycles:
  • Evaluates Promise Expiration (auto-resumes when promised date lapses without payment)
  • Updates Aging Days and tone brackets (Soft → Moderate → Escalated)
  • Enforces Stopping Rule (Hard stop at nudge_count >= 2)
  • Autonomous Dispatch of tone-matched WhatsApp notices with live Razorpay payment links
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List

from .db import (
    get_all_invoices,
    log_audit_event,
    update_invoice_status,
)
from .dispatcher import dispatch_whatsapp_messages
from .gateway import create_payment_link
from .guards import COMPLIANCE_AGING_THRESHOLD_DAYS, MAX_NUDGES
from .loader import AgingBracket

logger = logging.getLogger(__name__)


def run_recovery_sweep(dry_run: bool = True) -> Dict[str, Any]:
    """
    Execute a full autonomous recovery evaluation sweep across all records in SQLite.
    Can be run periodically via background timer, cron, or API call.
    """
    invoices = get_all_invoices()
    today = date.today()

    evaluated_count = len(invoices)
    nudges_dispatched = 0
    promises_checked = 0
    promises_expired = 0
    stopped_max = 0
    records_to_dispatch = []

    for inv in invoices:
        inv_id = inv["id"]
        status = inv["status"]
        nudge_count = inv["nudge_count"]
        promise_date_str = inv["promise_date"]

        # ── 1. Skip already recovered invoices ───────────────────────
        if status == "RECOVERED":
            continue

        # ── 2. Promise-to-Pay Check ─────────────────────────────────
        if status == "PROMISE_TRACKED":
            promises_checked += 1
            if promise_date_str:
                try:
                    p_date = date.fromisoformat(promise_date_str)
                    if today > p_date:
                        # Promise date has elapsed without payment — auto-resume recovery!
                        promises_expired += 1
                        update_invoice_status(
                            invoice_id=inv_id,
                            status="PENDING",
                            root_cause=f"Promise expired on {promise_date_str} without payment receipt. Resuming recovery.",
                        )
                        log_audit_event(
                            inv_id,
                            "PROMISE_EXPIRED",
                            f"Promise date {promise_date_str} passed. Re-opened for collection follow-up.",
                        )
                        status = "PENDING"
                except Exception:
                    pass

            if status == "PROMISE_TRACKED":
                # Still within promise window — keep paused
                continue

        # ── 3. Stopping Rule Enforcement ────────────────────────────
        if nudge_count >= MAX_NUDGES:
            if status != "MAX_RETRIES_REACHED":
                update_invoice_status(
                    invoice_id=inv_id,
                    status="MAX_RETRIES_REACHED",
                    root_cause=f"Stopping rule enforced: reached {nudge_count} nudges.",
                )
                log_audit_event(
                    inv_id,
                    "MAX_RETRIES_ENFORCED",
                    f"Automated messaging blocked after {nudge_count} attempts. Flagged for manual AR review.",
                )
                stopped_max += 1
            continue

        # ── 4. Eligible for Automated Recovery Dispatch ─────────────
        # Ensure active Razorpay payment link exists
        pay_link = inv.get("payment_link_url")
        if not pay_link or "sim" in pay_link:
            link_info = create_payment_link(
                invoice_id=inv_id,
                amount=inv["amount"],
                customer_name=inv["customer_name"],
                phone=inv.get("phone", ""),
            )
            pay_link = link_info["short_url"]

        # Evaluate aging bracket
        aging_days = inv["aging_days"]
        if aging_days <= 15:
            bracket = AgingBracket.SOFT.value
            body = (
                f"Hi {inv['customer_name']},\n\n"
                f"Gentle reminder: Invoice {inv_id} for ₹{inv['amount']:,.2f} is currently overdue ({aging_days} days). "
                f"Please settle at your convenience via Razorpay:\n"
                f"👉 {pay_link}\n\n"
                f"Reply with an expected date if you need assistance.\n"
                f"— Accounts Receivable"
            )
        elif aging_days <= COMPLIANCE_AGING_THRESHOLD_DAYS:
            bracket = AgingBracket.MODERATE.value
            body = (
                f"Dear {inv['customer_name']},\n\n"
                f"We are following up on overdue Invoice {inv_id} (₹{inv['amount']:,.2f}), now {aging_days} days past due. "
                f"Please settle directly via your secure link:\n"
                f"👉 {pay_link}\n\n"
                f"Warm regards,\nAccounts Receivable Team"
            )
        else:
            bracket = AgingBracket.ESCALATED.value
            body = (
                f"Dear {inv['customer_name']},\n\n"
                f"ESCALATION NOTICE — Invoice {inv_id}\n\n"
                f"Balance of ₹{inv['amount']:,.2f} is {aging_days} days overdue. Immediate payment is required:\n"
                f"👉 {pay_link}\n\n"
                f"Senior Accounts & Collections"
            )

        # Update message & bracket in DB
        update_invoice_status(
            invoice_id=inv_id,
            status="NUDGE_SENT",
            nudge_increment=1,
            payment_link_url=pay_link,
            recovery_message=body,
            root_cause=f"Overdue by {aging_days} days ({bracket})",
        )

        inv_record = dict(inv)
        inv_record["recovery_message"] = body
        inv_record["status"] = "NUDGE_SENT"
        inv_record["payment_link_url"] = pay_link
        records_to_dispatch.append(inv_record)
        nudges_dispatched += 1

    # Dispatch messages (dry-run or live)
    if records_to_dispatch:
        dispatch_whatsapp_messages(records_to_dispatch, dry_run=dry_run)

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_evaluated": evaluated_count,
        "nudges_dispatched": nudges_dispatched,
        "promises_checked": promises_checked,
        "promises_expired": promises_expired,
        "stopped_max_retries": stopped_max,
        "dry_run": dry_run,
    }

    log_audit_event(
        "AUTOMATION_ENGINE",
        "SWEEP_COMPLETED",
        f"Sweep finished: {nudges_dispatched} nudges sent, {promises_expired} promises expired",
        summary,
    )

    logger.info("Autonomous recovery sweep complete: %s", summary)
    return summary
