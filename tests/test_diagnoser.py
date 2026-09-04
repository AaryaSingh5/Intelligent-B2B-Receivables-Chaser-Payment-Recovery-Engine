"""
test_diagnoser.py — Unit Tests for Root-Cause Classifier & Aging Bracket Engine
"""

import unittest

from src.loader import (
    AgingBracket,
    InvoiceRecord,
    PaymentFailureRecord,
    RecordType,
)
from src.diagnoser import diagnose, _classify_aging, ERROR_CODE_MAP


class TestDiagnoser(unittest.TestCase):

    def test_aging_bracket_classification(self):
        """Verify strict aging brackets: Soft (1-15), Moderate (16-30), Escalated (31+)."""
        self.assertEqual(_classify_aging(5), AgingBracket.SOFT)
        self.assertEqual(_classify_aging(15), AgingBracket.SOFT)
        self.assertEqual(_classify_aging(16), AgingBracket.MODERATE)
        self.assertEqual(_classify_aging(30), AgingBracket.MODERATE)
        self.assertEqual(_classify_aging(31), AgingBracket.ESCALATED)
        self.assertEqual(_classify_aging(90), AgingBracket.ESCALATED)

    def test_payment_failure_diagnosis(self):
        """Verify gateway error codes are mapped to clear human-readable root causes."""
        record = PaymentFailureRecord(
            id="PAY-TEST-01",
            type=RecordType.PAYMENT_FAILURE,
            customer_name="Beta Logistics",
            customer_contact="ops@betalogistics.com",
            amount=45000.0,
            error_code="ERR_INSUFFICIENT_FUNDS",
            nudge_count=0,
        )

        diagnosed = diagnose([record])[0]
        self.assertIn("insufficient funds", diagnosed.root_cause.lower())

    def test_unknown_error_code_handling(self):
        """Unknown error codes should have a safe fallback rather than crash."""
        record = PaymentFailureRecord(
            id="PAY-TEST-02",
            type=RecordType.PAYMENT_FAILURE,
            customer_name="Gamma Services",
            customer_contact="support@gammaservices.com",
            amount=12000.0,
            error_code="ERR_CUSTOM_BANK_FAIL",
            nudge_count=0,
        )

        diagnosed = diagnose([record])[0]
        self.assertIn("manual investigation required", diagnosed.root_cause.lower())


if __name__ == "__main__":
    unittest.main()
