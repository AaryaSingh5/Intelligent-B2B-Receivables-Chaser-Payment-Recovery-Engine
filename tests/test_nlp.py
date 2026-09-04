"""
test_nlp.py — Unit Tests for Promise-to-Pay NLP Regex Entity Extraction
"""

import unittest
from datetime import datetime

from src.guards import extract_promise_date


class TestPromiseNLP(unittest.TestCase):

    def test_extract_promise_date_formats(self):
        """Test extraction across varied colloquial commitment phrases."""
        test_cases = [
            ("Will pay by Friday", True),
            ("Payment will be done by next Monday", True),
            ("Will clear this by Tuesday afternoon", True),
            ("Going to settle by tomorrow", True),
            ("Updating card details, will pay by Friday", True),
        ]

        for text, should_match in test_cases:
            res = extract_promise_date(text)
            if should_match:
                self.assertIsNotNone(res, f"Failed to extract promise from: '{text}'")
                # Ensure extracted string is ISO date format YYYY-MM-DD
                datetime.strptime(res, "%Y-%m-%d")

    def test_non_commitment_replies_return_none(self):
        """Conversational inquiries without commitment must NOT pause follow-ups."""
        non_commitments = [
            "Can you please resend the invoice copy?",
            "What is the billing address on this?",
            "We have not received the goods yet.",
            "Please speak to our accounts manager.",
            "",
            None,
        ]

        for text in non_commitments:
            self.assertIsNone(extract_promise_date(text), f"False positive on: '{text}'")


if __name__ == "__main__":
    unittest.main()
