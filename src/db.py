"""
db.py — Persistent SQLite Database Layer
Intelligent B2B Receivables Chaser & Payment Recovery Engine

Provides ACID-compliant persistent storage for:
  • Invoices & Payment Failure Records
  • Gateway Payment Attempts & Failure Diagnostics
  • Two-Way WhatsApp Outbound / Inbound Message Logs
  • Immutable Audit Trail Events
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "recovery_engine.db"
SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_batch.json"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_contact TEXT,
            phone TEXT,
            amount REAL NOT NULL,
            aging_days INTEGER DEFAULT 0,
            aging_bracket TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            nudge_count INTEGER NOT NULL DEFAULT 0,
            payment_link_url TEXT,
            payment_link_id TEXT,
            promise_date TEXT,
            simulated_reply TEXT,
            root_cause TEXT,
            recovery_message TEXT,
            error_code TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payment_attempts (
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            amount REAL NOT NULL,
            gateway_payment_id TEXT,
            error_code TEXT,
            error_description TEXT,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );

        CREATE TABLE IF NOT EXISTS whatsapp_messages (
            id TEXT PRIMARY KEY,
            invoice_id TEXT,
            direction TEXT NOT NULL,
            recipient TEXT NOT NULL,
            body TEXT NOT NULL,
            twilio_sid TEXT,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            record_id TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            payload TEXT
        );
        """)

    count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    if count == 0 and SEED_PATH.exists():
        _seed_initial_data(conn)
    conn.close()


def _seed_initial_data(conn: sqlite3.Connection) -> None:
    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except Exception:
        return

    now = datetime.now(timezone.utc).isoformat()
    records_to_insert = []
    for item in data:
        inv_id = item.get("id")
        rec_type = item.get("type", "b2b_invoice")
        name = item.get("customer_name", "Unknown")
        contact = item.get("customer_contact", "")
        phone = item.get("phone", "")
        amount = float(item.get("amount", 0.0))
        aging = int(item.get("aging_days", 0)) if "aging_days" in item and item["aging_days"] is not None else 0
        nudge_count = int(item.get("nudge_count", 0))
        reply = item.get("simulated_reply")
        error_code = item.get("error_code")

        records_to_insert.append((
            inv_id, rec_type, name, contact, phone, amount, aging,
            None, "PENDING", nudge_count, None, None, None,
            reply, None, None, error_code, now, now
        ))

    with conn:
        conn.executemany("""
        INSERT OR IGNORE INTO invoices (
            id, type, customer_name, customer_contact, phone, amount, aging_days,
            aging_bracket, status, nudge_count, payment_link_url, payment_link_id,
            promise_date, simulated_reply, root_cause, recovery_message, error_code,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records_to_insert)


def get_all_invoices(db_path: Path | None = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM invoices ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_invoice(invoice_id: str, db_path: Path | None = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def find_invoice_by_phone(phone: str, db_path: Path | None = None) -> Optional[Dict[str, Any]]:
    cleaned = phone.replace("whatsapp:", "").replace("+", "").replace(" ", "")
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM invoices WHERE status != 'RECOVERED' ORDER BY updated_at DESC").fetchall()
    conn.close()
    for r in rows:
        rec_phone = (r["phone"] or "").replace("+", "").replace(" ", "")
        if rec_phone and (rec_phone in cleaned or cleaned in rec_phone):
            return dict(r)
    return None


def upsert_invoice(data: Dict[str, Any], db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute("""
        INSERT INTO invoices (
            id, type, customer_name, customer_contact, phone, amount, aging_days,
            aging_bracket, status, nudge_count, payment_link_url, payment_link_id,
            promise_date, simulated_reply, root_cause, recovery_message, error_code,
            created_at, updated_at
        ) VALUES (
            :id, :type, :customer_name, :customer_contact, :phone, :amount, :aging_days,
            :aging_bracket, :status, :nudge_count, :payment_link_url, :payment_link_id,
            :promise_date, :simulated_reply, :root_cause, :recovery_message, :error_code,
            :created_at, :updated_at
        )
        ON CONFLICT(id) DO UPDATE SET
            customer_name = excluded.customer_name,
            phone = COALESCE(excluded.phone, invoices.phone),
            amount = excluded.amount,
            aging_days = excluded.aging_days,
            aging_bracket = COALESCE(excluded.aging_bracket, invoices.aging_bracket),
            status = excluded.status,
            nudge_count = excluded.nudge_count,
            payment_link_url = COALESCE(excluded.payment_link_url, invoices.payment_link_url),
            payment_link_id = COALESCE(excluded.payment_link_id, invoices.payment_link_id),
            promise_date = COALESCE(excluded.promise_date, invoices.promise_date),
            simulated_reply = COALESCE(excluded.simulated_reply, invoices.simulated_reply),
            root_cause = COALESCE(excluded.root_cause, invoices.root_cause),
            recovery_message = COALESCE(excluded.recovery_message, invoices.recovery_message),
            error_code = COALESCE(excluded.error_code, invoices.error_code),
            updated_at = excluded.updated_at
        """, {
            "id": data.get("id"),
            "type": data.get("type", "b2b_invoice"),
            "customer_name": data.get("customer_name", "Unknown"),
            "customer_contact": data.get("customer_contact", ""),
            "phone": data.get("phone", ""),
            "amount": float(data.get("amount", 0.0)),
            "aging_days": int(data.get("aging_days", 0)),
            "aging_bracket": data.get("aging_bracket"),
            "status": data.get("status", "PENDING"),
            "nudge_count": int(data.get("nudge_count", 0)),
            "payment_link_url": data.get("payment_link_url"),
            "payment_link_id": data.get("payment_link_id"),
            "promise_date": data.get("promise_date"),
            "simulated_reply": data.get("simulated_reply"),
            "root_cause": data.get("root_cause"),
            "recovery_message": data.get("recovery_message"),
            "error_code": data.get("error_code"),
            "created_at": data.get("created_at", now),
            "updated_at": now,
        })
    conn.close()


def update_invoice_status(
    invoice_id: str,
    status: str,
    nudge_increment: int = 0,
    promise_date: str | None = None,
    payment_link_url: str | None = None,
    recovery_message: str | None = None,
    root_cause: str | None = None,
    db_path: Path | None = None,
) -> None:
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute("""
        UPDATE invoices SET
            status = ?,
            nudge_count = nudge_count + ?,
            promise_date = COALESCE(?, promise_date),
            payment_link_url = COALESCE(?, payment_link_url),
            recovery_message = COALESCE(?, recovery_message),
            root_cause = COALESCE(?, root_cause),
            updated_at = ?
        WHERE id = ?
        """, (status, nudge_increment, promise_date, payment_link_url, recovery_message, root_cause, now, invoice_id))
    conn.close()


def log_payment_attempt(
    invoice_id: str,
    amount: float,
    status: str,
    error_code: str | None = None,
    error_description: str | None = None,
    gateway_payment_id: str | None = None,
    db_path: Path | None = None,
) -> str:
    attempt_id = f"ATT-{int(time.time() * 1000)}"
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
        INSERT INTO payment_attempts (
            id, invoice_id, amount, gateway_payment_id, error_code, error_description, status, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (attempt_id, invoice_id, amount, gateway_payment_id, error_code, error_description, status, now))
    conn.close()
    return attempt_id


def log_whatsapp_message(
    invoice_id: str | None,
    direction: str,
    recipient: str,
    body: str,
    status: str,
    twilio_sid: str | None = None,
    db_path: Path | None = None,
) -> str:
    msg_id = f"MSG-{int(time.time() * 1000)}"
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
        INSERT INTO whatsapp_messages (
            id, invoice_id, direction, recipient, body, twilio_sid, status, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, invoice_id, direction, recipient, body, twilio_sid, status, now))
    conn.close()
    return msg_id


def log_audit_event(
    record_id: str,
    action: str,
    detail: str = "",
    payload: Dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    payload_str = json.dumps(payload) if payload else None
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
        INSERT INTO audit_log (timestamp, record_id, action, detail, payload)
        VALUES (?, ?, ?, ?, ?)
        """, (now, record_id, action, detail, payload_str))
    conn.close()


def get_live_metrics(db_path: Path | None = None) -> Dict[str, Any]:
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM invoices").fetchall()
    conn.close()

    total_records = len(rows)
    total_revenue_at_risk = sum(r["amount"] for r in rows)
    recovered_or_promised = sum(
        r["amount"] for r in rows if r["status"] in ("RECOVERED", "PROMISE_TRACKED")
    )
    recovery_rate = (recovered_or_promised / total_revenue_at_risk * 100) if total_revenue_at_risk > 0 else 0.0

    nudges_sent = sum(1 for r in rows if r["status"] == "NUDGE_SENT")
    promises_tracked = sum(1 for r in rows if r["status"] == "PROMISE_TRACKED")
    max_retries = sum(1 for r in rows if r["status"] == "MAX_RETRIES_REACHED")
    recovered = sum(1 for r in rows if r["status"] == "RECOVERED")
    pending = sum(1 for r in rows if r["status"] == "PENDING")

    return {
        "total_records": total_records,
        "total_revenue_at_risk": total_revenue_at_risk,
        "total_recovered_or_promised": recovered_or_promised,
        "recovery_rate_pct": round(recovery_rate, 2),
        "nudges_sent": nudges_sent,
        "promises_tracked": promises_tracked,
        "max_retries_reached": max_retries,
        "recovered": recovered,
        "pending": pending,
    }
