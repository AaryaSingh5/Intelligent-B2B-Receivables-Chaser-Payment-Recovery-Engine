"""
test_gateway.py — Unit Tests for Razorpay Payment Link Generation & Webhooks
"""

import hashlib
import hmac
import unittest

from src.gateway import (
    create_payment_link,
    verify_webhook_signature,
    handle_payment_failed,
    handle_payment_paid,
)


class TestGateway(unittest.TestCase):

    def test_create_payment_link_deterministic(self):
        """Link generation must return a valid payment link URL and ID."""
        link = create_payment_link(
            invoice_id="INV-UNIT-01",
            amount=75000.0,
            customer_name="Alpha Tech",
            phone="+919876543210",
        )
        self.assertIn("short_url", link)
        self.assertTrue(link["short_url"].startswith("https://rzp.io/"))
        self.assertEqual(link["amount"], 75000.0)

    def test_hmac_webhook_signature_verification(self):
        """Verify HMAC-SHA256 signature algorithm against known secret and body."""
        secret = "test_webhook_secret_12345"
        body = b'{"event":"payment.failed","payload":{}}'
        valid_signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        # Valid signature must pass
        self.assertTrue(verify_webhook_signature(body, valid_signature, secret=secret))

        # Tampered signature must fail
        self.assertFalse(verify_webhook_signature(body, "tampered_signature_xyz", secret=secret))

    def test_handle_payment_paid_webhook(self):
        """payment_link.paid event must resolve the payment and return success."""
        event_data = {
            "event": "payment_link.paid",
            "payload": {
                "payment_link": {
                    "entity": {
                        "id": "plink_test_99",
                        "amount": 5000000,  # 50,000 INR in paise
                        "notes": {"invoice_id": "INV-UNIT-PAID"},
                    }
                }
            }
        }
        res = handle_payment_paid(event_data)
        self.assertIn(res["status"], ["success", "resolved"])
        self.assertEqual(res["invoice_id"], "INV-UNIT-PAID")


if __name__ == "__main__":
    unittest.main()
