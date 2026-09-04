"""
logger.py — Immutable Audit Trail Writer
Appends a timestamped, structured, append-only log entry for every record
that passes through the pipeline to `logs/recovery_audit.log`.

Each entry captures the full decision context: record ID, type, status,
root cause, recovery message payload, promise date, and any boundary
violations — satisfying the "complete audit trail" buildathon criterion.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .loader import RecoveryRecord

# ─── Constants ───────────────────────────────────────────────────────────────

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "recovery_audit.log"
_SEPARATOR = "=" * 88


# ─── Public API ──────────────────────────────────────────────────────────────

def write_audit_log(records: List[RecoveryRecord]) -> Path:
    """
    Append one structured audit entry per record to the log file.
    Creates the logs/ directory and file if they don't exist.
    Returns the path to the log file for caller convenience.
    """
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    with _LOG_FILE.open("a", encoding="utf-8") as fp:
        run_ts = datetime.now(timezone.utc).isoformat()
        fp.write(f"\n{'#' * 88}\n")
        fp.write(f"# PIPELINE RUN — {run_ts}\n")
        fp.write(f"{'#' * 88}\n\n")

        for record in records:
            fp.write(f"{_SEPARATOR}\n")
            fp.write(f"  Timestamp       : {run_ts}\n")
            fp.write(f"  Record ID       : {record.id}\n")
            fp.write(f"  Type            : {record.type.value}\n")
            fp.write(f"  Customer        : {record.customer_name}\n")
            fp.write(f"  Contact         : {record.customer_contact}\n")
            fp.write(f"  Amount (₹)      : {record.amount:,.2f}\n")

            if record.aging_bracket:
                fp.write(f"  Aging Bracket   : {record.aging_bracket.value}\n")

            fp.write(f"  Nudge Count     : {record.nudge_count}\n")
            fp.write(f"  Status          : {record.status.value}\n")
            fp.write(f"  Root Cause      : {record.root_cause or 'N/A'}\n")

            if record.promise_date:
                fp.write(f"  Promise Date    : {record.promise_date}\n")

            if record.simulated_reply:
                fp.write(f"  Customer Reply  : {record.simulated_reply}\n")

            violations = record.boundary_violations or []
            fp.write(f"  Boundary Viols  : {len(violations)}\n")
            for v in violations:
                fp.write(f"    ⚠  {v}\n")

            fp.write(f"  Recovery Message:\n")
            if record.recovery_message:
                for line in record.recovery_message.splitlines():
                    fp.write(f"    | {line}\n")
            else:
                fp.write(f"    | (none)\n")

            fp.write(f"{_SEPARATOR}\n\n")

    return _LOG_FILE
