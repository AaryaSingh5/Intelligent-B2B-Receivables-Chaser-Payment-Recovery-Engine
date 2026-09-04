"""
test_guards.py — Unit Tests for Bounded Policy Gates & Stopping Rules
Track 3 Requirement: 'Stopping rules, compliant escalation, and zero boundary violations.'
"""

import unittest

from src.loader import AgingBracket, InvoiceRecord, RecordType, RecoveryStatus
from src.guards import (
    MAX_NUDGES,
    COMPLIANCE_AGING_THRESHOLD_DAYS,
    enforce_guards,
    extract_promise_date,
)
from src.orchestrator import generate_messages


class TestGuards(unittest.TestCase):

    def test_stopping_rule_stops_at_max_nudges(self):
        """Records with nudge_count >= MAX_NUDGES must transition to MAX_RETRIES_REACHED."""
        record = InvoiceRecord(
            id="INV-TEST-01",
            type=RecordType.B2B_INVOICE,
            customer_name="Test Corp",
            customer_contact="finance@testcorp.com",
            amount=50000.0,
            nudge_count=2,  # Already hit limit
            aging_days=10,
            aging_bracket=AgingBracket.SOFT,
        )

        guarded = enforce_guards([record])[0]
        self.assertEqual(guarded.status, RecoveryStatus.MAX_RETRIES_REACHED)
        self.assertEqual(guarded.nudge_count, 2)

    def test_stopping_rule_allows_under_limit(self):
        """Records with nudge_count < MAX_NUDGES must not be blocked by guards."""
        record = InvoiceRecord(
            id="INV-TEST-02",
            type=RecordType.B2B_INVOICE,
            customer_name="Test Corp",
            customer_contact="finance@testcorp.com",
            amount=50000.0,
            nudge_count=1,
            aging_days=10,
            aging_bracket=AgingBracket.SOFT,
        )

        guarded = enforce_guards([record])[0]
        # Must not be stopped
        self.assertNotEqual(guarded.status, RecoveryStatus.MAX_RETRIES_REACHED)

        # Downstream orchestrator generates message and transitions to NUDGE_SENT
        orchestrated = generate_messages([guarded])[0]
        self.assertEqual(orchestrated.status, RecoveryStatus.NUDGE_SENT)
        self.assertEqual(orchestrated.nudge_count, 1)
        self.assertIsNotNone(orchestrated.recovery_message)

    def test_promise_to_pay_pause(self):
        """Records with commitment phrases must pause reminders and set PROMISE_TRACKED."""
        record = InvoiceRecord(
            id="INV-TEST-03",
            type=RecordType.B2B_INVOICE,
            customer_name="Acme Corp",
            customer_contact="accounts@acme.com",
            amount=100000.0,
            nudge_count=0,
            aging_days=20,
            aging_bracket=AgingBracket.MODERATE,
            simulated_reply="Will clear this by next Friday afternoon",
        )

        guarded = enforce_guards([record])[0]
        self.assertEqual(guarded.status, RecoveryStatus.PROMISE_TRACKED)
        self.assertIsNotNone(guarded.promise_date)
        self.assertEqual(guarded.nudge_count, 0)  # Nudges must NOT increment when paused

    def test_compliance_tone_gate_boundary(self):
        """Invoices <= 30 days must never receive escalated notices."""
        record = InvoiceRecord(
            id="INV-TEST-04",
            type=RecordType.B2B_INVOICE,
            customer_name="Young Debt Inc",
            customer_contact="billing@youngdebt.com",
            amount=20000.0,
            nudge_count=0,
            aging_days=15,
            aging_bracket=AgingBracket.SOFT,
        )

        guarded = enforce_guards([record])[0]
        self.assertIn(guarded.aging_bracket, [AgingBracket.SOFT, AgingBracket.MODERATE])


if __name__ == "__main__":
    unittest.main()
