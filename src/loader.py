"""
loader.py — Ingestion & Normalization
Reads synthetic_batch.json and normalises each record into strongly-typed
Pydantic models ready for downstream processing.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, validator


# ─── Enums ───────────────────────────────────────────────────────────────────

class RecordType(str, Enum):
    B2B_INVOICE = "b2b_invoice"
    PAYMENT_FAILURE = "payment_failure"


class RecoveryStatus(str, Enum):
    PENDING = "PENDING"
    NUDGE_SENT = "NUDGE_SENT"
    MAX_RETRIES_REACHED = "MAX_RETRIES_REACHED"
    PROMISE_TRACKED = "PROMISE_TRACKED"
    RECOVERED = "RECOVERED"
    ESCALATED = "ESCALATED"


class AgingBracket(str, Enum):
    SOFT = "Soft (1-15 days)"
    MODERATE = "Moderate (16-30 days)"
    ESCALATED = "Escalated (31+ days)"


# ─── Models ──────────────────────────────────────────────────────────────────

class BaseRecord(BaseModel):
    """Fields shared by every record."""
    id: str
    type: RecordType
    amount: float = Field(..., gt=0, description="Amount in INR")
    customer_name: str
    customer_contact: str
    phone: Optional[str] = None
    nudge_count: int = Field(default=0, ge=0)
    simulated_reply: Optional[str] = None

    # Populated by the pipeline
    status: RecoveryStatus = RecoveryStatus.PENDING
    root_cause: Optional[str] = None
    aging_bracket: Optional[AgingBracket] = None
    recovery_message: Optional[str] = None
    promise_date: Optional[str] = None
    boundary_violations: List[str] = Field(default_factory=list)


class InvoiceRecord(BaseRecord):
    """B2B overdue invoice with aging information."""
    type: Literal[RecordType.B2B_INVOICE] = RecordType.B2B_INVOICE
    aging_days: int = Field(..., ge=0)
    error_code: Optional[str] = None  # Not applicable, always None


class PaymentFailureRecord(BaseRecord):
    """Degraded / failed payment with a gateway error code."""
    type: Literal[RecordType.PAYMENT_FAILURE] = RecordType.PAYMENT_FAILURE
    error_code: str
    aging_days: Optional[int] = None  # Not applicable, always None


# Convenience union type
RecoveryRecord = Union[InvoiceRecord, PaymentFailureRecord]


# ─── Loader ──────────────────────────────────────────────────────────────────

def load_records(data_path: Optional[Path] = None) -> List[RecoveryRecord]:
    """
    Load and validate records from the synthetic batch JSON file.

    Returns a list of strongly-typed Pydantic model instances.
    Raises FileNotFoundError or json.JSONDecodeError on bad input.
    """
    if data_path is None:
        data_path = Path(__file__).resolve().parent.parent / "data" / "synthetic_batch.json"

    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    raw: list = json.loads(data_path.read_text(encoding="utf-8"))

    records: List[RecoveryRecord] = []
    for entry in raw:
        record_type = entry.get("type")
        if record_type == RecordType.B2B_INVOICE.value:
            records.append(InvoiceRecord(**entry))
        elif record_type == RecordType.PAYMENT_FAILURE.value:
            records.append(PaymentFailureRecord(**entry))
        else:
            raise ValueError(f"Unknown record type '{record_type}' in record {entry.get('id')}")

    return records
