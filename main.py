#!/usr/bin/env python3
"""
main.py — CLI Entry Point
Intelligent B2B Receivables Chaser & Payment Recovery Engine

Runs the full pipeline end-to-end:
  Loader → Diagnoser → Guards → Orchestrator → Logger → Evaluator

Usage:
    python main.py
    python main.py --data path/to/custom_batch.json
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows to support emoji & box-drawing characters
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure the package root is importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.loader import load_records, RecoveryStatus
from src.diagnoser import diagnose
from src.guards import enforce_guards
from src.orchestrator import generate_messages
from src.logger import write_audit_log
from src.evaluator import compute_metrics, print_metrics_report


# ─── Pretty Console Helpers ─────────────────────────────────────────────────

_BANNER = r"""
╔══════════════════════════════════════════════════════════════════════╗
║      🏦  Intelligent B2B Receivables Chaser                        ║
║          & Payment Recovery Engine                                 ║
║                                                                    ║
║      Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

def _step(label: str, detail: str = "") -> None:
    """Print a styled pipeline step."""
    suffix = f" — {detail}" if detail else ""
    print(f"  ▸ {label}{suffix}")


def _section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")


# ─── Main Pipeline ──────────────────────────────────────────────────────────

def main(data_path: Path | None = None) -> None:
    print(_BANNER)
    start = time.perf_counter()

    # ── 1. Load ──────────────────────────────────────────────────────────
    _section("① LOADING RECORDS")
    records = load_records(data_path)
    _step("Records loaded", f"{len(records)} records from synthetic batch")
    invoice_count = sum(1 for r in records if r.type.value == "b2b_invoice")
    payment_count = len(records) - invoice_count
    _step("Breakdown", f"{invoice_count} B2B invoices, {payment_count} payment failures")

    # ── 2. Diagnose ──────────────────────────────────────────────────────
    _section("② DIAGNOSING ROOT CAUSES & AGING BRACKETS")
    records = diagnose(records)
    for r in records:
        tag = r.aging_bracket.value if r.aging_bracket else r.error_code
        _step(r.id, f"{r.customer_name} → {tag}")

    # ── 3. Guard Enforcement ─────────────────────────────────────────────
    _section("③ ENFORCING POLICY GUARDS")
    records = enforce_guards(records)
    for r in records:
        if r.status == RecoveryStatus.PROMISE_TRACKED:
            _step(r.id, f"⏸  PROMISE_TRACKED — paused until {r.promise_date}")
        elif r.status == RecoveryStatus.MAX_RETRIES_REACHED:
            _step(r.id, f"⛔ MAX_RETRIES_REACHED — no further nudges")
        else:
            _step(r.id, f"✅ Cleared for messaging")

    # ── 4. Orchestrate Messages ──────────────────────────────────────────
    _section("④ GENERATING RECOVERY MESSAGES")
    records = generate_messages(records)
    for r in records:
        # Truncate message preview to first line
        preview = (r.recovery_message or "").split("\n")[0][:80]
        _step(r.id, f"[{r.status.value}] {preview}…")

    # ── 5. Audit Log ─────────────────────────────────────────────────────
    _section("⑤ WRITING AUDIT LOG")
    log_path = write_audit_log(records)
    _step("Audit log written", str(log_path))

    # ── 6. Evaluate & Report ─────────────────────────────────────────────
    _section("⑥ METRICS & SUMMARY REPORT")
    metrics = compute_metrics(records)
    report_path = Path(__file__).resolve().parent / "logs" / "metrics_report.md"
    print_metrics_report(metrics, output_path=report_path)
    _step("Metrics report saved", str(report_path))

    elapsed = time.perf_counter() - start
    print(f"\n{'═' * 70}")
    print(f"  ✅  Pipeline completed in {elapsed:.2f}s")
    print(f"{'═' * 70}\n")


# ─── CLI Argument Parsing ───────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Intelligent B2B Receivables Chaser & Payment Recovery Engine",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path to a custom JSON batch file (default: data/synthetic_batch.json)",
    )
    args = parser.parse_args()
    main(data_path=args.data)
