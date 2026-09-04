"""
test_pipeline.py — End-to-End Batch Pipeline & Evaluator Integration Tests
Track 3: 'Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail.'
"""

import unittest
from pathlib import Path

from src.loader import load_records
from src.diagnoser import diagnose
from src.guards import enforce_guards
from src.orchestrator import generate_messages
from src.evaluator import compute_metrics

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_batch.json"


class TestFullPipeline(unittest.TestCase):

    def test_end_to_end_batch_pipeline(self):
        """Run the full 6-stage pipeline and verify zero boundary violations."""
        self.assertTrue(DATA_PATH.exists(), f"Synthetic batch data missing at {DATA_PATH}")

        # 1. Load
        records = load_records(DATA_PATH)
        self.assertGreater(len(records), 0, "No records loaded from batch")

        # 2. Diagnose
        diagnosed = diagnose(records)
        self.assertEqual(len(diagnosed), len(records))

        # 3. Guard
        guarded = enforce_guards(diagnosed)
        self.assertEqual(len(guarded), len(records))

        # 4. Orchestrate
        orchestrated = generate_messages(guarded)
        self.assertEqual(len(orchestrated), len(records))

        # 5. Evaluate
        metrics = compute_metrics(orchestrated)

        # Core Track 3 Invariants:
        self.assertEqual(metrics.boundary_violations, 0, "Boundary violations MUST be strictly 0")
        self.assertGreater(metrics.total_revenue_at_risk, 0)
        self.assertGreater(metrics.total_recovered_or_promised, 0)
        self.assertGreater(metrics.recovery_rate_pct, 50.0, "Expected recovery rate > 50%")
        self.assertEqual(metrics.total_records, len(records))


if __name__ == "__main__":
    unittest.main()
