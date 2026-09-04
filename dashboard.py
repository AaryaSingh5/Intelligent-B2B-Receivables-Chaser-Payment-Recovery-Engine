#!/usr/bin/env python3
"""
dashboard.py — Executive Recovery Dashboard (Streamlit)
Intelligent B2B Receivables Chaser & Payment Recovery Engine

A premium, real-time executive dashboard displaying:
  • Top-level KPI cards
  • Interactive filterable batch record table
  • Live immutable audit trail viewer
  • Compliance & architecture breakdown panel

Usage:
    streamlit run dashboard.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

# ── Ensure src is importable ────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.loader import load_records, RecordType, RecoveryStatus
from src.diagnoser import diagnose
from src.guards import enforce_guards
from src.orchestrator import generate_messages
from src.logger import write_audit_log
from src.evaluator import compute_metrics, RecoveryMetrics
from src.dispatcher import dispatch_whatsapp_messages, DispatchResult, handle_inbound_whatsapp
from src.db import get_all_invoices, get_live_metrics, init_db
from src.gateway import create_payment_link, handle_payment_failed, handle_payment_paid
from src.receipt_parser import parse_and_ingest_receipt
from src.scheduler import run_recovery_sweep

# ── Paths ───────────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).resolve().parent / "data" / "synthetic_batch.json"
LOG_PATH = Path(__file__).resolve().parent / "logs" / "recovery_audit.log"


# ═══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & GLOBAL STYLES
# ═══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Revenue Recovery Engine — Dashboard",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Premium CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Import premium font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── Root variables ── */
:root {
    --bg-primary: #0a0e1a;
    --bg-card: #111827;
    --bg-card-hover: #1a2340;
    --border-subtle: rgba(99, 102, 241, 0.15);
    --border-glow: rgba(99, 102, 241, 0.4);
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-indigo: #6366f1;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-rose: #f43f5e;
    --accent-cyan: #06b6d4;
    --accent-violet: #8b5cf6;
    --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%);
    --gradient-emerald: linear-gradient(135deg, #059669 0%, #10b981 100%);
    --gradient-amber: linear-gradient(135deg, #d97706 0%, #f59e0b 100%);
    --gradient-rose: linear-gradient(135deg, #e11d48 0%, #f43f5e 100%);
    --gradient-cyan: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
    --shadow-lg: 0 10px 40px rgba(0, 0, 0, 0.4);
    --shadow-glow: 0 0 30px rgba(99, 102, 241, 0.15);
}

/* ── Global overrides ── */
.stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ── Sidebar styling ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1729 0%, #111827 100%);
    border-right: 1px solid var(--border-subtle);
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li {
    color: var(--text-secondary);
}

/* ── KPI Card styling ── */
.kpi-container {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}

.kpi-card {
    background: linear-gradient(145deg, #111827 0%, #1a2340 100%);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 24px 28px;
    flex: 1;
    min-width: 200px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: var(--shadow-lg);
}

.kpi-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
}

.kpi-card:hover {
    transform: translateY(-4px);
    border-color: var(--border-glow);
    box-shadow: var(--shadow-glow), var(--shadow-lg);
}

.kpi-card.indigo::before { background: var(--gradient-primary); }
.kpi-card.emerald::before { background: var(--gradient-emerald); }
.kpi-card.amber::before { background: var(--gradient-amber); }
.kpi-card.cyan::before { background: var(--gradient-cyan); }
.kpi-card.rose::before { background: var(--gradient-rose); }

.kpi-icon {
    font-size: 28px;
    margin-bottom: 8px;
    display: block;
}

.kpi-label {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: var(--text-muted);
    margin-bottom: 6px;
}

.kpi-value {
    font-size: 32px;
    font-weight: 800;
    color: var(--text-primary);
    line-height: 1.1;
    margin-bottom: 4px;
}

.kpi-sub {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
}

/* ── Section headers ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 32px 0 16px 0;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-subtle);
}

.section-header h2 {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
}

.section-header .badge {
    background: rgba(99, 102, 241, 0.15);
    color: var(--accent-indigo);
    font-size: 11px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 0.5px;
}

/* ── Status badges ── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
}

.status-nudge { background: rgba(6, 182, 212, 0.15); color: #22d3ee; }
.status-promise { background: rgba(16, 185, 129, 0.15); color: #34d399; }
.status-max { background: rgba(244, 63, 94, 0.15); color: #fb7185; }
.status-pending { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

/* ── Compliance card ── */
.compliance-card {
    background: linear-gradient(145deg, #111827 0%, #1a2340 100%);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: var(--shadow-lg);
    transition: all 0.3s ease;
}

.compliance-card:hover {
    border-color: var(--border-glow);
}

.compliance-card h3 {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 8px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

.compliance-card p {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
    margin: 0;
}

.compliance-card .rule-tag {
    display: inline-block;
    background: rgba(99, 102, 241, 0.12);
    color: var(--accent-indigo);
    font-size: 11px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 12px;
    margin-top: 8px;
}

/* ── Audit log viewer ── */
.audit-viewer {
    background: #0d1117;
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 20px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    font-size: 12px;
    line-height: 1.7;
    color: #c9d1d9;
    max-height: 600px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.3);
}

.audit-viewer::-webkit-scrollbar {
    width: 6px;
}
.audit-viewer::-webkit-scrollbar-track {
    background: #0d1117;
}
.audit-viewer::-webkit-scrollbar-thumb {
    background: #30363d;
    border-radius: 3px;
}

/* ── Pipeline flow diagram ── */
.pipeline-flow {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    flex-wrap: wrap;
    padding: 20px;
    margin: 16px 0;
}

.pipeline-node {
    background: linear-gradient(145deg, #1a2340 0%, #1e293b 100%);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 12px 20px;
    text-align: center;
    min-width: 120px;
    transition: all 0.3s ease;
}

.pipeline-node:hover {
    border-color: var(--accent-indigo);
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.2);
    transform: translateY(-2px);
}

.pipeline-node .node-icon {
    font-size: 22px;
    display: block;
    margin-bottom: 4px;
}

.pipeline-node .node-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-primary);
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

.pipeline-arrow {
    color: var(--accent-indigo);
    font-size: 20px;
    opacity: 0.6;
}

/* ── Data table overrides ── */
.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
}

/* ── Header banner ── */
.header-banner {
    background: linear-gradient(135deg, #1a1a3e 0%, #111827 40%, #0f172a 100%);
    border: 1px solid var(--border-subtle);
    border-radius: 20px;
    padding: 32px 40px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-lg);
}

.header-banner::after {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
    pointer-events: none;
}

.header-banner h1 {
    font-size: 28px;
    font-weight: 800;
    color: var(--text-primary);
    margin: 0 0 6px 0;
    letter-spacing: -0.5px;
}

.header-banner .subtitle {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-secondary);
    margin: 0;
}

.header-banner .track-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(99, 102, 241, 0.15);
    color: var(--accent-indigo);
    font-size: 11px;
    font-weight: 700;
    padding: 5px 14px;
    border-radius: 20px;
    margin-top: 12px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

/* ── Metric delta pill ── */
.delta-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
}
.delta-pill.positive { background: rgba(16, 185, 129, 0.15); color: #34d399; }
.delta-pill.zero { background: rgba(99, 102, 241, 0.12); color: #a5b4fc; }
.delta-pill.negative { background: rgba(244, 63, 94, 0.15); color: #fb7185; }

/* ── Tab styling ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(17, 24, 39, 0.5);
    border-radius: 12px;
    padding: 4px;
    border: 1px solid var(--border-subtle);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.3px;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# DATA PIPELINE (cached)
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def run_pipeline():
    """Execute the full recovery pipeline and return processed records + metrics."""
    records = load_records(DATA_PATH)
    records = diagnose(records)
    records = enforce_guards(records)
    records = generate_messages(records)
    write_audit_log(records)
    metrics = compute_metrics(records)
    return records, metrics


def records_to_dataframe(records):
    """Convert processed records to a display-ready DataFrame."""
    rows = []
    for r in records:
        row = {
            "ID": r.id,
            "Type": "📄 Invoice" if r.type == RecordType.B2B_INVOICE else "💳 Payment",
            "Customer": r.customer_name,
            "WhatsApp": getattr(r, "phone", None) or "—",
            "Amount (₹)": f"₹{r.amount:,.2f}",
            "Amount_raw": r.amount,
            "Root Cause / Bracket": (
                r.aging_bracket.value if r.aging_bracket
                else (r.error_code if hasattr(r, "error_code") and r.error_code else "N/A")
            ),
            "Status": r.status.value,
            "Nudges": r.nudge_count,
            "Promise Date": r.promise_date or "—",
            "Customer Reply": r.simulated_reply or "—",
            "Recovery Message": (r.recovery_message or "")[:120] + "…" if r.recovery_message and len(r.recovery_message) > 120 else (r.recovery_message or "—"),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def get_status_html(status: str) -> str:
    """Return a styled HTML badge for a status string."""
    css_map = {
        "NUDGE_SENT": ("📤", "status-nudge"),
        "PROMISE_TRACKED": ("🤝", "status-promise"),
        "MAX_RETRIES_REACHED": ("⛔", "status-max"),
        "PENDING": ("⏳", "status-pending"),
    }
    icon, cls = css_map.get(status, ("•", "status-pending"))
    return f'<span class="status-badge {cls}">{icon} {status}</span>'


# ═══════════════════════════════════════════════════════════════════════════
# RENDER DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

def render():
    # ── Run pipeline ─────────────────────────────────────────────────────
    records, metrics = run_pipeline()
    df = records_to_dataframe(records)

    # ══════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ══════════════════════════════════════════════════════════════════════
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding: 20px 0 10px 0;">
            <span style="font-size: 42px;">🏦</span>
            <h2 style="font-size: 17px; font-weight: 800; color: #f1f5f9; margin: 8px 0 2px 0; letter-spacing: -0.3px;">Revenue Recovery</h2>
            <p style="font-size: 12px; color: #64748b; margin: 0;">AI-Powered Engine</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("#### 🔧 Filters")

        type_filter = st.multiselect(
            "Record Type",
            options=["📄 Invoice", "💳 Payment"],
            default=["📄 Invoice", "💳 Payment"],
        )

        status_filter = st.multiselect(
            "Status",
            options=["NUDGE_SENT", "PROMISE_TRACKED", "MAX_RETRIES_REACHED", "PENDING"],
            default=["NUDGE_SENT", "PROMISE_TRACKED", "MAX_RETRIES_REACHED", "PENDING"],
        )

        amount_range = st.slider(
            "Amount Range (₹ thousands)",
            min_value=0,
            max_value=800,
            value=(0, 800),
            step=10,
            format="₹%dk",
        )

        st.markdown("---")

        # Pipeline diagram in sidebar
        st.markdown("#### ⚙️ Pipeline Stages")
        st.markdown("""
        <div style="padding: 8px 0;">
            <div style="display: flex; align-items: center; gap: 10px; margin: 6px 0; padding: 8px 12px; background: rgba(99,102,241,0.08); border-radius: 8px; border-left: 3px solid #6366f1;">
                <span style="font-size: 16px;">📥</span>
                <span style="font-size: 12px; font-weight: 600; color: #e2e8f0;">① Loader</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px; margin: 6px 0; padding: 8px 12px; background: rgba(6,182,212,0.08); border-radius: 8px; border-left: 3px solid #06b6d4;">
                <span style="font-size: 16px;">🔍</span>
                <span style="font-size: 12px; font-weight: 600; color: #e2e8f0;">② Diagnoser</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px; margin: 6px 0; padding: 8px 12px; background: rgba(244,63,94,0.08); border-radius: 8px; border-left: 3px solid #f43f5e;">
                <span style="font-size: 16px;">🛡️</span>
                <span style="font-size: 12px; font-weight: 600; color: #e2e8f0;">③ Guards</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px; margin: 6px 0; padding: 8px 12px; background: rgba(139,92,246,0.08); border-radius: 8px; border-left: 3px solid #8b5cf6;">
                <span style="font-size: 16px;">💬</span>
                <span style="font-size: 12px; font-weight: 600; color: #e2e8f0;">④ Orchestrator</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px; margin: 6px 0; padding: 8px 12px; background: rgba(245,158,11,0.08); border-radius: 8px; border-left: 3px solid #f59e0b;">
                <span style="font-size: 16px;">📝</span>
                <span style="font-size: 12px; font-weight: 600; color: #e2e8f0;">⑤ Logger</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px; margin: 6px 0; padding: 8px 12px; background: rgba(16,185,129,0.08); border-radius: 8px; border-left: 3px solid #10b981;">
                <span style="font-size: 16px;">📊</span>
                <span style="font-size: 12px; font-weight: 600; color: #e2e8f0;">⑥ Evaluator</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(
            '<p style="font-size: 11px; color: #475569; text-align: center;">'
            'Razorpay AI Buildathon 2026<br/>Track 3: AI Revenue Recovery'
            '</p>',
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════════════
    # HEADER BANNER
    # ══════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class="header-banner">
        <h1>🏦 Revenue Recovery Engine</h1>
        <p class="subtitle">Intelligent B2B Receivables Chaser & Payment Degradation Recovery</p>
        <span class="track-badge">🏆 Track 3 — AI Revenue Recovery</span>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # KPI CARDS
    # ══════════════════════════════════════════════════════════════════════
    violations_cls = "emerald" if metrics.boundary_violations == 0 else "rose"
    violations_icon = "✅" if metrics.boundary_violations == 0 else "⚠️"

    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card indigo">
            <span class="kpi-icon">📊</span>
            <div class="kpi-label">Total Records</div>
            <div class="kpi-value">{metrics.total_records}</div>
            <div class="kpi-sub">{metrics.nudges_sent + metrics.promises_tracked} actioned</div>
        </div>
        <div class="kpi-card amber">
            <span class="kpi-icon">💰</span>
            <div class="kpi-label">Revenue at Risk</div>
            <div class="kpi-value">₹{metrics.total_revenue_at_risk / 100000:.1f}L</div>
            <div class="kpi-sub">₹{metrics.total_revenue_at_risk:,.0f}</div>
        </div>
        <div class="kpi-card emerald">
            <span class="kpi-icon">✅</span>
            <div class="kpi-label">Recovered / Promised</div>
            <div class="kpi-value">₹{metrics.total_recovered_or_promised / 100000:.1f}L</div>
            <div class="kpi-sub">₹{metrics.total_recovered_or_promised:,.0f}</div>
        </div>
        <div class="kpi-card cyan">
            <span class="kpi-icon">📈</span>
            <div class="kpi-label">Recovery Rate</div>
            <div class="kpi-value">{metrics.recovery_rate_pct}%</div>
            <div class="kpi-sub">
                <span class="delta-pill positive">▲ Target: 70%+</span>
            </div>
        </div>
        <div class="kpi-card {violations_cls}">
            <span class="kpi-icon">{violations_icon}</span>
            <div class="kpi-label">Boundary Violations</div>
            <div class="kpi-value">{metrics.boundary_violations}</div>
            <div class="kpi-sub">
                <span class="delta-pill {"zero" if metrics.boundary_violations == 0 else "negative"}">
                    {"● All checks passed" if metrics.boundary_violations == 0 else "⚠ Review required"}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Status breakdown mini-cards ──────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📤 Nudges Sent", metrics.nudges_sent)
    with col2:
        st.metric("🤝 Promises Tracked", metrics.promises_tracked)
    with col3:
        st.metric("⛔ Max Retries", metrics.max_retries_reached)
    with col4:
        st.metric("⏳ Pending", metrics.pending)

    # ══════════════════════════════════════════════════════════════════════
    # TABBED CONTENT
    # ══════════════════════════════════════════════════════════════════════
    tab_records, tab_audit, tab_compliance, tab_whatsapp, tab_automation = st.tabs([
        "📋 Batch Records",
        "📜 Audit Trail",
        "🛡️ Compliance & Architecture",
        "💬 WhatsApp Dispatch",
        "⚡ Live Automation Center",
    ])

    # ── TAB 1: Interactive Batch Record Table ────────────────────────────
    with tab_records:
        st.markdown("""
        <div class="section-header">
            <h2>📋 Batch Record Explorer</h2>
            <span class="badge">INTERACTIVE</span>
        </div>
        """, unsafe_allow_html=True)

        # Apply filters
        filtered_df = df[
            (df["Type"].isin(type_filter)) &
            (df["Status"].isin(status_filter)) &
            (df["Amount_raw"] >= amount_range[0] * 1000) &
            (df["Amount_raw"] <= amount_range[1] * 1000)
        ]

        st.markdown(
            f'<p style="font-size: 13px; color: #94a3b8; margin-bottom: 12px;">'
            f'Showing <strong style="color: #f1f5f9;">{len(filtered_df)}</strong> of '
            f'<strong style="color: #f1f5f9;">{len(df)}</strong> records '
            f'(use sidebar filters to refine)</p>',
            unsafe_allow_html=True,
        )

        # Display columns (drop raw amount)
        display_cols = [c for c in filtered_df.columns if c != "Amount_raw"]

        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            height=500,
            column_config={
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Customer": st.column_config.TextColumn("Customer", width="medium"),
                "WhatsApp": st.column_config.TextColumn("WhatsApp", width="small"),
                "Amount (₹)": st.column_config.TextColumn("Amount", width="small"),
                "Root Cause / Bracket": st.column_config.TextColumn("Root Cause / Bracket", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Nudges": st.column_config.NumberColumn("Nudges", width="small"),
                "Promise Date": st.column_config.TextColumn("Promise", width="small"),
                "Customer Reply": st.column_config.TextColumn("Reply", width="medium"),
                "Recovery Message": st.column_config.TextColumn("Message Preview", width="large"),
            },
        )

        # ── Breakdown charts ────────────────────────────────────────────
        st.markdown("---")
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("##### 📊 Records by Status")
            status_counts = df["Status"].value_counts()
            st.bar_chart(status_counts, color="#6366f1")

        with chart_col2:
            st.markdown("##### 💰 Revenue by Status (₹)")
            revenue_by_status = df.groupby("Status")["Amount_raw"].sum()
            st.bar_chart(revenue_by_status, color="#10b981")

    # ── TAB 2: Live Audit Trail Viewer ───────────────────────────────────
    with tab_audit:
        st.markdown("""
        <div class="section-header">
            <h2>📜 Immutable Audit Trail</h2>
            <span class="badge">LIVE LOG VIEWER</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<p style="font-size: 13px; color: #94a3b8; margin-bottom: 16px;">'
            'Every decision, state transition, root cause diagnosis, and message payload is logged '
            'sequentially to <code style="background: rgba(99,102,241,0.12); color: #a5b4fc; '
            'padding: 2px 8px; border-radius: 4px;">logs/recovery_audit.log</code> — '
            'proving full transparency and compliance.</p>',
            unsafe_allow_html=True,
        )

        # Search / filter for audit log
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            audit_search = st.text_input(
                "🔍 Search audit log",
                placeholder="Search by Record ID, customer name, status...",
                label_visibility="collapsed",
            )
        with search_col2:
            tail_lines = st.selectbox("Lines", [50, 100, 200, 500, "All"], index=1)

        if LOG_PATH.exists():
            log_content = LOG_PATH.read_text(encoding="utf-8")

            # Apply search filter
            if audit_search:
                lines = log_content.splitlines()
                matched_sections = []
                in_section = False
                current_section = []

                for line in lines:
                    if line.startswith("=" * 20):
                        if in_section and any(audit_search.lower() in l.lower() for l in current_section):
                            matched_sections.extend(current_section)
                            matched_sections.append(line)
                        current_section = [line]
                        in_section = True
                    elif in_section:
                        current_section.append(line)

                # Catch last section
                if in_section and any(audit_search.lower() in l.lower() for l in current_section):
                    matched_sections.extend(current_section)

                log_content = "\n".join(matched_sections) if matched_sections else "No matching entries found."
            else:
                # Tail the log
                if tail_lines != "All":
                    lines = log_content.splitlines()
                    log_content = "\n".join(lines[-int(tail_lines):])

            st.markdown(
                f'<div class="audit-viewer">{log_content}</div>',
                unsafe_allow_html=True,
            )

            # Log stats
            total_entries = log_content.count("Record ID")
            st.markdown(
                f'<p style="font-size: 12px; color: #64748b; margin-top: 8px; text-align: right;">'
                f'📄 Log file: {LOG_PATH.name} &nbsp;|&nbsp; '
                f'📏 {LOG_PATH.stat().st_size:,} bytes &nbsp;|&nbsp; '
                f'📝 {total_entries} entries shown</p>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("⚠️ Audit log file not found. Run `python main.py` first to generate it.")

    # ── TAB 3: Compliance & Architecture Panel ───────────────────────────
    with tab_compliance:
        st.markdown("""
        <div class="section-header">
            <h2>🛡️ Compliance & Safety Architecture</h2>
            <span class="badge">GUARDRAILS</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<p style="font-size: 13px; color: #94a3b8; margin-bottom: 24px;">'
            'Every messaging action is <strong style="color: #f1f5f9;">strictly bounded</strong> '
            'by three layered safety gates, ensuring compliance, preventing spam, and respecting '
            'active customer commitments.</p>',
            unsafe_allow_html=True,
        )

        # Three compliance cards
        rule_col1, rule_col2, rule_col3 = st.columns(3)

        with rule_col1:
            st.markdown(f"""
            <div class="compliance-card">
                <h3>⛔ Stopping Rule</h3>
                <p>
                    If a record's <strong>nudge_count ≥ 2</strong>, all further automated
                    messaging is <strong>blocked</strong>. The record is set to
                    <code>MAX_RETRIES_REACHED</code> and flagged for manual review.
                </p>
                <span class="rule-tag">MAX_NUDGES = 2</span>
                <br/><br/>
                <p style="font-size: 12px;">
                    <strong style="color: #fb7185;">Records stopped:</strong> {metrics.max_retries_reached}
                </p>
            </div>
            """, unsafe_allow_html=True)

        with rule_col2:
            st.markdown(f"""
            <div class="compliance-card">
                <h3>📋 Compliance Gate</h3>
                <p>
                    Invoices under <strong>30 days overdue</strong> are strictly limited to
                    <strong>Soft</strong> or <strong>Moderate</strong> tone. Aggressive legal
                    collection language and escalation notices are forbidden.
                </p>
                <span class="rule-tag">THRESHOLD = 30 DAYS</span>
                <br/><br/>
                <p style="font-size: 12px;">
                    <strong style="color: #34d399;">Violations:</strong> {metrics.boundary_violations}
                </p>
            </div>
            """, unsafe_allow_html=True)

        with rule_col3:
            st.markdown(f"""
            <div class="compliance-card">
                <h3>🤝 Promise-to-Pay Pause</h3>
                <p>
                    When a customer reply contains a commitment phrase (e.g., "Will pay by Friday"),
                    the NLP parser extracts the date and sets <code>PROMISE_TRACKED</code>.
                    <strong>All nudges are paused</strong> until the promised date.
                </p>
                <span class="rule-tag">NLP REGEX PARSER</span>
                <br/><br/>
                <p style="font-size: 12px;">
                    <strong style="color: #34d399;">Promises paused:</strong> {metrics.promises_tracked}
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Pipeline Architecture Diagram
        st.markdown("""
        <div class="section-header">
            <h2>⚙️ Pipeline Architecture</h2>
            <span class="badge">6-STAGE SEQUENTIAL</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="pipeline-flow">
            <div class="pipeline-node">
                <span class="node-icon">📥</span>
                <span class="node-label">Loader</span>
            </div>
            <span class="pipeline-arrow">→</span>
            <div class="pipeline-node">
                <span class="node-icon">🔍</span>
                <span class="node-label">Diagnoser</span>
            </div>
            <span class="pipeline-arrow">→</span>
            <div class="pipeline-node">
                <span class="node-icon">🛡️</span>
                <span class="node-label">Guards</span>
            </div>
            <span class="pipeline-arrow">→</span>
            <div class="pipeline-node">
                <span class="node-icon">💬</span>
                <span class="node-label">Orchestrator</span>
            </div>
            <span class="pipeline-arrow">→</span>
            <div class="pipeline-node">
                <span class="node-icon">📝</span>
                <span class="node-label">Logger</span>
            </div>
            <span class="pipeline-arrow">→</span>
            <div class="pipeline-node">
                <span class="node-icon">📊</span>
                <span class="node-label">Evaluator</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Aging bracket reference
        st.markdown("---")
        st.markdown("""
        <div class="section-header">
            <h2>📐 Aging Bracket Reference</h2>
            <span class="badge">TONE MAPPING</span>
        </div>
        """, unsafe_allow_html=True)

        age_col1, age_col2, age_col3 = st.columns(3)
        with age_col1:
            st.markdown("""
            <div class="compliance-card" style="border-left: 3px solid #10b981;">
                <h3>🟢 Soft (1–15 days)</h3>
                <p>Gentle, polite payment reminder. Assumes good faith — customer may have
                simply overlooked the invoice.</p>
                <span class="rule-tag" style="background: rgba(16,185,129,0.12); color: #10b981;">
                    GENTLE REMINDER
                </span>
            </div>
            """, unsafe_allow_html=True)
        with age_col2:
            st.markdown("""
            <div class="compliance-card" style="border-left: 3px solid #f59e0b;">
                <h3>🟡 Moderate (16–30 days)</h3>
                <p>Firm but professional follow-up. Requests immediate attention and asks for
                an expected payment date.</p>
                <span class="rule-tag" style="background: rgba(245,158,11,0.12); color: #f59e0b;">
                    FIRM FOLLOW-UP
                </span>
            </div>
            """, unsafe_allow_html=True)
        with age_col3:
            st.markdown("""
            <div class="compliance-card" style="border-left: 3px solid #f43f5e;">
                <h3>🔴 Escalated (31+ days)</h3>
                <p>Formal escalation notice. Mentions internal escalation and urges settlement
                within 5 business days.</p>
                <span class="rule-tag" style="background: rgba(244,63,94,0.12); color: #f43f5e;">
                    ESCALATION NOTICE
                </span>
            </div>
            """, unsafe_allow_html=True)

        # Error code reference table
        st.markdown("---")
        st.markdown("""
        <div class="section-header">
            <h2>🔧 Error Code Reference</h2>
            <span class="badge">PAYMENT FAILURES</span>
        </div>
        """, unsafe_allow_html=True)

        error_data = pd.DataFrame([
            {"Error Code": "ERR_GATEWAY_TIMEOUT", "Root Cause": "Gateway timed out", "Action": "🔄 Auto-retry", "Severity": "🟡 Medium"},
            {"Error Code": "ERR_INSUFFICIENT_FUNDS", "Root Cause": "Insufficient funds", "Action": "📤 Nudge to top up", "Severity": "🟠 High"},
            {"Error Code": "ERR_CARD_EXPIRED", "Root Cause": "Card expired", "Action": "💳 Prompt card update", "Severity": "🟠 High"},
            {"Error Code": "ERR_BANK_DECLINED", "Root Cause": "Bank declined", "Action": "🏦 Contact bank", "Severity": "🔴 Critical"},
            {"Error Code": "ERR_NETWORK_ERROR", "Root Cause": "Network failure", "Action": "🔄 Auto-retry", "Severity": "🟡 Medium"},
            {"Error Code": "ERR_AUTHENTICATION_FAILED", "Root Cause": "3DS/OTP failed", "Action": "🔐 Reattempt auth", "Severity": "🟠 High"},
            {"Error Code": "ERR_DUPLICATE_TRANSACTION", "Root Cause": "Duplicate detected", "Action": "🔍 Verify original", "Severity": "🟢 Low"},
        ])

        st.dataframe(
            error_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Error Code": st.column_config.TextColumn("Error Code", width="medium"),
                "Root Cause": st.column_config.TextColumn("Root Cause", width="medium"),
                "Action": st.column_config.TextColumn("Recommended Action", width="medium"),
                "Severity": st.column_config.TextColumn("Severity", width="small"),
            },
        )

    # ── TAB 4: WhatsApp Dispatch Panel ───────────────────────────────────
    with tab_whatsapp:
        st.markdown("""
        <div class="section-header">
            <h2>💬 WhatsApp Dispatch via Twilio</h2>
            <span class="badge">TWILIO API</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<p style="font-size: 13px; color: #94a3b8; margin-bottom: 20px;">'
            'Send recovery messages directly to customers via <strong style="color: #f1f5f9;">WhatsApp</strong> '
            'using the Twilio API. By default this runs in <strong style="color: #34d399;">Dry-Run / Simulation</strong> '
            'mode — no real messages are sent. Set <code style="background: rgba(99,102,241,0.12); '
            'color: #a5b4fc; padding: 2px 8px; border-radius: 4px;">ENABLE_LIVE_WHATSAPP=true</code> '
            'in your <code style="background: rgba(99,102,241,0.12); color: #a5b4fc; padding: 2px 8px; '
            'border-radius: 4px;">.env</code> file to enable live delivery.</p>',
            unsafe_allow_html=True,
        )

        import os
        live_enabled = os.getenv("ENABLE_LIVE_WHATSAPP", "false").lower() == "true"
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        has_creds = bool(twilio_sid and twilio_sid != "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

        # Status indicator
        if live_enabled and has_creds:
            st.markdown("""
            <div style="background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3);
                        border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; display: flex;
                        align-items: center; gap: 12px;">
                <span style="font-size: 24px;">✅</span>
                <div>
                    <strong style="color: #34d399; font-size: 14px;">Live Mode Active</strong>
                    <p style="color: #94a3b8; font-size: 12px; margin: 2px 0 0 0;">
                        Twilio credentials detected. Messages will be delivered to ALLOWED_RECIPIENTS.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.2);
                        border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; display: flex;
                        align-items: center; gap: 12px;">
                <span style="font-size: 24px;">🔵</span>
                <div>
                    <strong style="color: #a5b4fc; font-size: 14px;">Dry-Run / Simulation Mode</strong>
                    <p style="color: #94a3b8; font-size: 12px; margin: 2px 0 0 0;">
                        No real messages will be sent. Add Twilio credentials to .env and set
                        ENABLE_LIVE_WHATSAPP=true to enable live delivery.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Setup guide expander
        with st.expander("📖 WhatsApp Setup Guide (click to expand)"):
            st.markdown("""
            ### How to Enable Live WhatsApp Delivery

            **Step 1 — Create a Twilio Account**
            - Sign up free at [twilio.com](https://www.twilio.com) (no credit card needed for sandbox)

            **Step 2 — Join the WhatsApp Sandbox**
            - In Twilio Console → Messaging → Try it out → Send a WhatsApp message
            - Send the join code from your phone to `+14155238886`

            **Step 3 — Add credentials to `.env`**
            ```
            TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            TWILIO_AUTH_TOKEN=your_auth_token
            TWILIO_WHATSAPP_NUMBER=+14155238886
            ENABLE_LIVE_WHATSAPP=true
            ALLOWED_RECIPIENTS=+919876543210,+919123456789
            ```

            **Step 4 — Allowlist your numbers**
            - Add your target phone numbers (E.164 format e.g. `+919876543210`) to `ALLOWED_RECIPIENTS`
            - Only these numbers will receive messages (hard safety guardrail)

            > **Note:** The Twilio sandbox requires recipients to opt-in by texting the join code first.
            > For production, upgrade to a Twilio WhatsApp Business approved sender.
            """)

        st.markdown("---")

        # ── SECTION 1: Single Record Interactive Test ─────────────────────────
        st.markdown("### 📱 Test Single WhatsApp Dispatch")
        st.markdown(
            '<p style="font-size: 13px; color: #94a3b8; margin-bottom: 16px;">'
            'Select any record from the batch, preview its tone-matched message, and send a test message '
            'to your own WhatsApp number or the record recipient.</p>',
            unsafe_allow_html=True,
        )

        test_col1, test_col2 = st.columns([1, 1])

        with test_col1:
            record_options = {
                f"{r.id} — {r.customer_name} (₹{r.amount:,.0f})": r for r in records
            }
            selected_label = st.selectbox(
                "Select Customer Record",
                options=list(record_options.keys()),
                index=0,
            )
            selected_rec = record_options[selected_label]

            default_phone = getattr(selected_rec, "phone", "") or "+919876500001"
            custom_phone = st.text_input(
                "Recipient WhatsApp Number (E.164 format)",
                value=default_phone,
                help="Include country code, e.g. +919876543210. Must be joined to Twilio Sandbox for sandbox testing.",
            )

            test_mode = st.radio(
                "Single Test Mode",
                options=["🔵 Dry-Run (Simulate)", "⚡ Live Send"],
                horizontal=True,
                key="single_test_mode",
            )
            single_is_dry = "Dry-Run" in test_mode

            send_single_btn = st.button("📤 Send Test WhatsApp", type="primary", use_container_width=True)

        with test_col2:
            st.markdown(
                '<div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">'
                'MESSAGE PAYLOAD PREVIEW:</div>',
                unsafe_allow_html=True,
            )
            st.code(selected_rec.recovery_message or "No message generated.", language="markdown")

            status_color = "#34d399" if selected_rec.status.value in ("NUDGE_SENT", "PROMISE_TRACKED") else "#fb7185"
            st.markdown(
                f'<p style="font-size: 12px; color: #64748b;">Record Status: '
                f'<strong style="color: {status_color};">{selected_rec.status.value}</strong> &nbsp;|&nbsp; '
                f'Nudge Count: <strong>{selected_rec.nudge_count}/2</strong></p>',
                unsafe_allow_html=True,
            )

        if send_single_btn:
            if not single_is_dry and not has_creds:
                st.error("⚠️ Live send requires Twilio credentials in `.env`.")
            else:
                # Temporarily attach test phone if customized
                orig_phone = getattr(selected_rec, "phone", None)
                selected_rec.phone = custom_phone.strip()

                with st.spinner("Dispatching WhatsApp message..."):
                    single_res = dispatch_whatsapp_messages(
                        [selected_rec],
                        dry_run=single_is_dry,
                        target_record_id=selected_rec.id,
                    )
                selected_rec.phone = orig_phone

                if single_res:
                    res = single_res[0]
                    if res.status == "sent":
                        st.success(f"✅ WhatsApp message delivered live! Twilio SID: `{res.message_sid}`")
                    elif res.status == "simulated":
                        st.info(f"🔵 **[Dry-Run Simulated]** WhatsApp message validated & queued for {res.recipient_number}. Message length: {len(selected_rec.recovery_message or '')} chars.")
                    elif res.status == "skipped":
                        st.warning(f"⏭️ Message blocked by safety guard: {res.error}")
                    else:
                        st.error(f"❌ Dispatch error: {res.error}")

        st.markdown("---")

        # ── SECTION 2: Batch Dispatch ─────────────────────────────────────────
        st.markdown("### 📦 Batch WhatsApp Dispatch")
        st.markdown(
            '<p style="font-size: 13px; color: #94a3b8; margin-bottom: 16px;">'
            'Process the entire batch of 37 records simultaneously with guardrail safety.</p>',
            unsafe_allow_html=True,
        )

        wa_col1, wa_col2 = st.columns([3, 1])
        with wa_col1:
            dispatch_mode = st.radio(
                "Batch Dispatch Mode",
                options=["🔵 Dry-Run (Simulation)", "⚡ Live Send"],
                horizontal=True,
                help="Dry-Run logs intent without making API calls. Live Send requires Twilio credentials.",
            )
        with wa_col2:
            dispatch_all = st.button(
                "💬 Run Batch Dispatch",
                type="secondary",
                use_container_width=True,
                help="Dispatch WhatsApp messages for all eligible records",
            )

        is_dry_run = "Dry-Run" in dispatch_mode

        if dispatch_all:
            if not is_dry_run and not has_creds:
                st.error(
                    "⚠️ Live mode requires Twilio credentials. "
                    "Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN to your .env and restart the dashboard."
                )
            else:
                with st.spinner("Dispatching WhatsApp messages..."):
                    results = dispatch_whatsapp_messages(records, dry_run=is_dry_run)

                # Summary metrics
                sent = sum(1 for r in results if r.status == "sent")
                simulated = sum(1 for r in results if r.status == "simulated")
                skipped = sum(1 for r in results if r.status == "skipped")
                errors = sum(1 for r in results if r.status == "error")

                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("✅ Sent (Live)", sent)
                mc2.metric("🔵 Simulated", simulated)
                mc3.metric("⏭️ Skipped", skipped)
                mc4.metric("❌ Errors", errors)

                st.markdown("---")

                # Results table
                result_rows = []
                for r in results:
                    status_icon = {
                        "sent": "✅ Sent",
                        "simulated": "🔵 Simulated",
                        "skipped": "⏭️ Skipped",
                        "error": "❌ Error",
                    }.get(r.status, r.status)
                    result_rows.append({
                        "Record ID": r.record_id,
                        "Customer": r.customer_name,
                        "Recipient": r.recipient_number,
                        "Status": status_icon,
                        "SID / Detail": r.message_sid or r.error or r.message_preview or "—",
                        "Timestamp": r.timestamp,
                    })

                result_df = pd.DataFrame(result_rows)
                st.dataframe(
                    result_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Record ID": st.column_config.TextColumn("Record ID", width="small"),
                        "Customer": st.column_config.TextColumn("Customer", width="medium"),
                        "Recipient": st.column_config.TextColumn("WhatsApp Number", width="medium"),
                        "Status": st.column_config.TextColumn("Status", width="small"),
                        "SID / Detail": st.column_config.TextColumn("SID / Detail", width="large"),
                        "Timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
                    },
                )

                if is_dry_run:
                    st.info(
                        "🔵 This was a **Dry-Run**. Switch to **⚡ Live Send** and add Twilio credentials "
                        "to your `.env` to deliver real messages."
                    )
                else:
                    st.success(
                        f"✅ Live dispatch complete — {sent} messages sent via Twilio WhatsApp."
                    )

    # ── TAB 5: Live Automation Center ──────────────────────────────────
    with tab_automation:
        st.markdown("""
        <div class="section-header">
            <h2>⚡ Live Automation & Webhook Control Center</h2>
            <span class="badge">EVENT-DRIVEN WORKFLOW</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<p style="font-size: 13px; color: #94a3b8; margin-bottom: 24px;">'
            'An end-to-end autonomous event loop connecting <strong style="color: #f1f5f9;">Receipt Ingestion</strong>, '
            '<strong style="color: #6366f1;">Razorpay Payment Links & Webhooks</strong>, '
            '<strong style="color: #10b981;">Two-Way WhatsApp NLP</strong>, and '
            '<strong style="color: #06b6d4;">Persistent SQLite Database</strong> in real time.</p>',
            unsafe_allow_html=True,
        )

        # ── Architecture Status Indicators ──────────────────────────────
        auto_col1, auto_col2, auto_col3 = st.columns(3)
        with auto_col1:
            st.markdown("""
            <div class="compliance-card" style="border-left: 3px solid #6366f1;">
                <h3 style="font-size: 14px;">🌐 FastAPI Webhook Server</h3>
                <p style="font-size: 12px; margin: 4px 0 0 0;">
                    Port: <code>8000</code> &nbsp;|&nbsp; Endpoints: <code>/api/webhooks/razorpay</code>, <code>/api/webhooks/twilio/whatsapp</code>
                </p>
                <span class="rule-tag" style="background: rgba(99,102,241,0.15); color: #818cf8; margin-top: 8px;">
                    FASTAPI ASGI ACTIVE
                </span>
            </div>
            """, unsafe_allow_html=True)

        with auto_col2:
            st.markdown("""
            <div class="compliance-card" style="border-left: 3px solid #10b981;">
                <h3 style="font-size: 14px;">💳 Razorpay Gateway Engine</h3>
                <p style="font-size: 12px; margin: 4px 0 0 0;">
                    Live standard payment links (UPI, Cards, Netbanking) with HMAC-SHA256 verification.
                </p>
                <span class="rule-tag" style="background: rgba(16,185,129,0.15); color: #34d399; margin-top: 8px;">
                    RAZORPAY STANDARD LINKS
                </span>
            </div>
            """, unsafe_allow_html=True)

        with auto_col3:
            st.markdown("""
            <div class="compliance-card" style="border-left: 3px solid #06b6d4;">
                <h3 style="font-size: 14px;">🤝 Two-Way WhatsApp NLP</h3>
                <p style="font-size: 12px; margin: 4px 0 0 0;">
                    Inbound customer reply interceptor extracts promise date and auto-pauses reminders.
                </p>
                <span class="rule-tag" style="background: rgba(6,182,212,0.15); color: #22d3ee; margin-top: 8px;">
                    TWILIO INBOUND + NLP
                </span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # ── WORKBENCH 1: Instant Receipt Ingestion Studio ──────────────
        st.markdown("### 📥 1. Ingest Receipt & Auto-Mint Razorpay Link")
        st.markdown(
            '<p style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">'
            'Add a new overdue B2B receipt/invoice. The engine instantly computes aging, assigns the compliance bracket, '
            'creates a Razorpay Payment Link, and drafts the contextual recovery notice.</p>',
            unsafe_allow_html=True,
        )

        with st.form("receipt_ingest_form", clear_on_submit=False):
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                new_cust_name = st.text_input("Customer Name", value="Zenith Logistics India Pvt Ltd")
                new_cust_phone = st.text_input("Customer Phone (E.164)", value="+919876599001")
            with rc2:
                new_amount = st.number_input("Invoice Amount (₹)", min_value=1000.0, max_value=5000000.0, value=175000.0, step=5000.0)
                new_aging = st.slider("Aging Days Overdue", min_value=1, max_value=60, value=18)
            with rc3:
                new_contact = st.text_input("Customer Contact Email", value="accounts@zenithlogistics.in")
                ingest_btn = st.form_submit_button("⚡ Ingest Receipt & Mint Payment Link", type="primary", use_container_width=True)

        if ingest_btn:
            new_record = parse_and_ingest_receipt({
                "customer_name": new_cust_name,
                "phone": new_cust_phone,
                "amount": new_amount,
                "aging_days": new_aging,
                "customer_contact": new_contact,
            })
            st.success(
                f"✅ Receipt **{new_record['id']}** ingested for **{new_cust_name}**! "
                f"Assigned bracket: `{new_record['aging_bracket']}`."
            )
            st.markdown(f"""
            <div style="background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.3);
                        border-radius: 10px; padding: 14px 18px; margin: 12px 0;">
                <strong style="color: #34d399;">🔗 Razorpay Payment Link Generated:</strong>
                <a href="{new_record['payment_link_url']}" target="_blank" style="color: #60a5fa; font-weight: 600; margin-left: 8px;">
                    {new_record['payment_link_url']}
                </a>
            </div>
            """, unsafe_allow_html=True)
            st.code(new_record["recovery_message"], language="markdown")

        st.markdown("---")

        # ── WORKBENCH 2: Two-Way WhatsApp Customer Reply Simulator ─────
        st.markdown("### 💬 2. Two-Way WhatsApp Conversation Simulator")
        st.markdown(
            '<p style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">'
            'Simulate an incoming WhatsApp reply from a customer. The engine runs regex NLP to detect commitment dates, '
            'transitions the invoice to <code style="color: #34d399;">PROMISE_TRACKED</code>, and sends an automated confirmation.</p>',
            unsafe_allow_html=True,
        )

        all_live_invoices = get_all_invoices()
        live_options = {
            f"{i['id']} — {i['customer_name']} (₹{i['amount']:,.0f}) [{i['status']}]": i for i in all_live_invoices
        }

        wa_sim_col1, wa_sim_col2 = st.columns([1, 1])
        with wa_sim_col1:
            selected_inv_label = st.selectbox("Select Target Invoice", options=list(live_options.keys()), key="wa_sim_select")
            selected_inv = live_options[selected_inv_label]

            sample_replies = [
                "Will pay by next Tuesday afternoon",
                "Processing transfer, payment will be done by Friday",
                "Will clear this by tomorrow",
                "Checking with my finance team, will settle by 2026-09-18",
                "Already initiated NEFT transfer",
            ]
            selected_sample = st.selectbox("Preset Customer Replies (or type custom below)", sample_replies)
            custom_reply = st.text_input("Customer WhatsApp Message", value=selected_sample)

            sim_reply_btn = st.button("📲 Receive WhatsApp Reply", type="primary", use_container_width=True)

        with wa_sim_col2:
            if sim_reply_btn and custom_reply:
                with st.spinner("Processing inbound WhatsApp message..."):
                    inbound_res = handle_inbound_whatsapp(
                        from_number=selected_inv.get("phone") or "+919876543001",
                        message_body=custom_reply,
                    )

                if inbound_res["status"] == "promise_tracked":
                    st.success(
                        f"🤝 Promise Extracted: **{inbound_res['promise_date']}**! "
                        f"Invoice **{inbound_res['invoice_id']}** transitioned to **PROMISE_TRACKED**."
                    )
                else:
                    st.info(f"ℹ️ Inbound note acknowledged for **{inbound_res['invoice_id']}**.")

                st.markdown(
                    '<div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px;">'
                    'AUTOMATED BOT CONFIRMATION DISPATCHED:</div>',
                    unsafe_allow_html=True,
                )
                st.code(inbound_res["auto_reply"], language="markdown")
            else:
                st.markdown(
                    '<div style="background: rgba(17,24,39,0.5); border: 1px dashed rgba(99,102,241,0.2); '
                    'border-radius: 8px; padding: 24px; text-align: center; color: #64748b; font-size: 13px;">'
                    'Click "📲 Receive WhatsApp Reply" to test real-time promise extraction and auto-reply.'
                    '</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("---")

        # ── WORKBENCH 3: Razorpay Webhook Simulator ────────────────────
        st.markdown("### 💳 3. Razorpay Payment Gateway Webhook Simulator")
        st.markdown(
            '<p style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">'
            'Trigger real-time gateway webhook events. Observe how the engine diagnoses root causes on payment failures '
            'or marks invoices as <code style="color: #34d399;">RECOVERED</code> on payment success.</p>',
            unsafe_allow_html=True,
        )

        gw_col1, gw_col2 = st.columns([1, 1])
        with gw_col1:
            st.markdown("##### ⚠️ Simulate Payment Failure (`payment.failed`)")
            fail_error_code = st.selectbox(
                "Gateway Error Code",
                ["ERR_GATEWAY_TIMEOUT", "ERR_INSUFFICIENT_FUNDS", "ERR_CARD_EXPIRED", "ERR_BANK_DECLINED", "ERR_NETWORK_ERROR"],
            )
            trigger_fail_btn = st.button("⚡ Fire `payment.failed` Webhook", type="secondary", use_container_width=True)

            if trigger_fail_btn:
                fail_event = {
                    "event": "payment.failed",
                    "payload": {
                        "payment": {
                            "entity": {
                                "id": f"pay_live_{int(time.time())}",
                                "amount": int(selected_inv["amount"] * 100),
                                "error_code": fail_error_code,
                                "error_description": f"Transaction rejected with {fail_error_code}",
                                "contact": selected_inv.get("phone", "+919876543210"),
                                "notes": {
                                    "invoice_id": selected_inv["id"],
                                    "customer_name": selected_inv["customer_name"],
                                },
                            }
                        }
                    }
                }
                fail_res = handle_payment_failed(fail_event)
                st.warning(
                    f"⚠️ Failure diagnosed: **{fail_error_code}**! "
                    f"Generated recovery link: `{fail_res.get('payment_link')}`"
                )

        with gw_col2:
            st.markdown("##### ✅ Simulate Payment Success (`payment_link.paid`)")
            st.markdown(
                f'<p style="font-size: 12px; color: #94a3b8;">Settle invoice '
                f'<strong>{selected_inv["id"]}</strong> for ₹{selected_inv["amount"]:,.2f}.</p>',
                unsafe_allow_html=True,
            )
            trigger_paid_btn = st.button("🎉 Fire `payment_link.paid` Webhook", type="primary", use_container_width=True)

            if trigger_paid_btn:
                paid_event = {
                    "event": "payment_link.paid",
                    "payload": {
                        "payment_link": {
                            "entity": {
                                "id": f"plink_live_{int(time.time())}",
                                "amount": int(selected_inv["amount"] * 100),
                                "notes": {"invoice_id": selected_inv["id"]},
                            }
                        }
                    }
                }
                paid_res = handle_payment_paid(paid_event)
                st.success(
                    f"🎉 Revenue Secured! Invoice **{selected_inv['id']}** marked as **RECOVERED**. "
                    f"Automated receipt dispatched via WhatsApp."
                )

        st.markdown("---")

        # ── WORKBENCH 4: Autonomous Recovery Sweep ──────────────────────
        st.markdown("### 🔄 4. Autonomous Recovery Engine Sweep")
        st.markdown(
            '<p style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">'
            'Executes the periodic scheduler sweep: evaluates promise deadlines (auto-unpausing expired promises), '
            'advances overdue aging, enforces stopping rules, and triggers queued recovery notices.</p>',
            unsafe_allow_html=True,
        )

        sweep_col1, sweep_col2 = st.columns([3, 1])
        with sweep_col1:
            st.markdown(
                '<p style="font-size: 13px; color: #e2e8f0; margin-top: 6px;">'
                'Scheduled daemon runs continuously in background. Click to run an immediate on-demand sweep.</p>',
                unsafe_allow_html=True,
            )
        with sweep_col2:
            sweep_btn = st.button("🚀 Run Recovery Sweep", type="primary", use_container_width=True)

        if sweep_btn:
            with st.spinner("Executing autonomous recovery sweep..."):
                sweep_result = run_recovery_sweep(dry_run=True)
            st.success(
                f"✅ Sweep completed: **{sweep_result['total_evaluated']}** records evaluated, "
                f"**{sweep_result['nudges_dispatched']}** nudges actioned, "
                f"**{sweep_result['stopped_max_retries']}** stopped by guardrails."
            )

        # ── Live SQLite Database Stream ────────────────────────────────
        st.markdown("---")
        st.markdown("### 🗄️ Live Database Records (SQLite)")
        live_db_data = get_all_invoices()
        live_df = pd.DataFrame(live_db_data)
        if not live_df.empty:
            cols_to_show = ["id", "customer_name", "phone", "amount", "aging_days", "status", "nudge_count", "payment_link_url", "promise_date", "updated_at"]
            available_cols = [c for c in cols_to_show if c in live_df.columns]
            st.dataframe(
                live_df[available_cols],
                use_container_width=True,
                height=350,
                column_config={
                    "id": st.column_config.TextColumn("ID", width="small"),
                    "customer_name": st.column_config.TextColumn("Customer", width="medium"),
                    "phone": st.column_config.TextColumn("WhatsApp", width="medium"),
                    "amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f", width="small"),
                    "aging_days": st.column_config.NumberColumn("Aging (d)", width="small"),
                    "status": st.column_config.TextColumn("Status", width="medium"),
                    "nudge_count": st.column_config.NumberColumn("Nudges", width="small"),
                    "payment_link_url": st.column_config.LinkColumn("Razorpay Link", width="medium"),
                    "promise_date": st.column_config.TextColumn("Promise Date", width="small"),
                    "updated_at": st.column_config.TextColumn("Last Updated", width="medium"),
                },
            )


if __name__ == "__main__":
    render()
