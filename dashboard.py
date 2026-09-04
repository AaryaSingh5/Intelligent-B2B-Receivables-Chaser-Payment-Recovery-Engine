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
    tab_records, tab_audit, tab_compliance = st.tabs([
        "📋 Batch Records",
        "📜 Audit Trail",
        "🛡️ Compliance & Architecture",
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


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    render()
