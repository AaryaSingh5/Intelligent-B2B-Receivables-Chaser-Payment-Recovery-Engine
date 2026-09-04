"""
evaluator.py — Metrics Aggregation & Markdown Report Generator
Computes the key recovery metrics and prints a polished Markdown summary
table to the terminal (and optionally writes to a file).

Metrics computed:
  • Total Records Processed
  • Total Revenue at Risk (₹)
  • Total Money Recovered / Secured via Promises (₹)
  • Recovery Rate (%)
  • Boundary Violations (target: 0)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from tabulate import tabulate

from .loader import RecoveryRecord, RecoveryStatus


# ─── Metrics Data Class ─────────────────────────────────────────────────────

@dataclass
class RecoveryMetrics:
    total_records: int = 0
    total_revenue_at_risk: float = 0.0
    total_recovered_or_promised: float = 0.0
    recovery_rate_pct: float = 0.0
    boundary_violations: int = 0

    # Breakdown
    nudges_sent: int = 0
    promises_tracked: int = 0
    max_retries_reached: int = 0
    pending: int = 0


# ─── Computation ─────────────────────────────────────────────────────────────

def compute_metrics(records: List[RecoveryRecord]) -> RecoveryMetrics:
    """Aggregate metrics across all processed records."""
    m = RecoveryMetrics()
    m.total_records = len(records)

    for r in records:
        m.total_revenue_at_risk += r.amount
        m.boundary_violations += len(r.boundary_violations)

        if r.status == RecoveryStatus.NUDGE_SENT:
            m.nudges_sent += 1
            m.total_recovered_or_promised += r.amount

        elif r.status == RecoveryStatus.PROMISE_TRACKED:
            m.promises_tracked += 1
            m.total_recovered_or_promised += r.amount

        elif r.status == RecoveryStatus.MAX_RETRIES_REACHED:
            m.max_retries_reached += 1
            # Not counted as recovered

        elif r.status == RecoveryStatus.RECOVERED:
            m.total_recovered_or_promised += r.amount

        else:
            m.pending += 1

    if m.total_revenue_at_risk > 0:
        m.recovery_rate_pct = round(
            (m.total_recovered_or_promised / m.total_revenue_at_risk) * 100, 2
        )

    return m


# ─── Markdown Report ────────────────────────────────────────────────────────

def print_metrics_report(metrics: RecoveryMetrics, output_path: Optional[Path] = None) -> str:
    """
    Format and print a polished Markdown metrics summary table.
    Optionally writes the report to a file.  Returns the report string.
    """
    summary_rows = [
        ["📊 Total Records Processed", f"{metrics.total_records}"],
        ["💰 Total Revenue at Risk", f"₹{metrics.total_revenue_at_risk:,.2f}"],
        ["✅ Recovered / Promised", f"₹{metrics.total_recovered_or_promised:,.2f}"],
        ["📈 Recovery Rate", f"{metrics.recovery_rate_pct}%"],
        ["🚫 Boundary Violations", f"{metrics.boundary_violations}"],
    ]

    breakdown_rows = [
        ["📤 Nudges Sent", f"{metrics.nudges_sent}"],
        ["🤝 Promises Tracked (Paused)", f"{metrics.promises_tracked}"],
        ["⛔ Max Retries Reached", f"{metrics.max_retries_reached}"],
        ["⏳ Pending / Unactioned", f"{metrics.pending}"],
    ]

    summary_table = tabulate(
        summary_rows,
        headers=["Metric", "Value"],
        tablefmt="github",
        colalign=("left", "right"),
    )

    breakdown_table = tabulate(
        breakdown_rows,
        headers=["Status Breakdown", "Count"],
        tablefmt="github",
        colalign=("left", "right"),
    )

    report_lines = [
        "",
        "## 🏦 Revenue Recovery Engine — Run Summary",
        "",
        summary_table,
        "",
        "### Status Breakdown",
        "",
        breakdown_table,
        "",
    ]

    # Boundary violations health check
    if metrics.boundary_violations == 0:
        report_lines.append("> ✅ **All boundary & compliance checks passed — 0 violations.**")
    else:
        report_lines.append(
            f"> ⚠️  **{metrics.boundary_violations} boundary violation(s) detected — "
            f"review audit log for details.**"
        )

    report_lines.append("")

    report = "\n".join(report_lines)

    # Print to terminal
    print(report)

    # Optionally persist
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

    return report
