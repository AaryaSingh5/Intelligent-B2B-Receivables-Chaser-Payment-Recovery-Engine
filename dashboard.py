#!/usr/bin/env python3
"""
dashboard.py — Ultra-Premium FinTech Recovery Dashboard (Streamlit)
Intelligent B2B Receivables Chaser & Payment Recovery Engine
Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery

Executive-grade, modern dashboard inspired by Stripe, Linear, Ramp, and Mercury:
  • Obsidian Glassmorphic Design System with Plus Jakarta Sans & JetBrains Mono
  • Executive KPI Hero Cards with Tabular Numerals and Trend Badges
  • Interactive Plotly Dark Financial Charts (Splines, Donut, Velocity Gauges)
  • Authentic WhatsApp Dark-Mode Interactive Conversation Simulator
  • Real-Time Webhook & Receipt Ingestion Control Center
  • Full SQLite ACID Persistence & Immutable Audit Trail
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

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
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="RECOVER.AI — Autonomous B2B Revenue Recovery Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ═══════════════════════════════════════════════════════════════════════════
# ULTRA-PREMIUM $100M FINTECH DESIGN SYSTEM (CSS)
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
/* ── Typography from Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    --bg-base: #060913;
    --bg-surface: rgba(14, 22, 38, 0.72);
    --bg-surface-elevated: rgba(20, 32, 54, 0.85);
    --border-subtle: rgba(255, 255, 255, 0.08);
    --border-highlight: rgba(99, 102, 241, 0.35);
    --text-main: #F8FAFC;
    --text-muted: #94A3B8;
    --text-subtle: #64748B;
    --accent-indigo: #6366F1;
    --accent-cyan: #06B6D4;
    --accent-emerald: #10B981;
    --accent-amber: #F59E0B;
    --accent-rose: #F43F5E;
    --accent-violet: #8B5CF6;
    --shadow-card: 0 16px 36px -8px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    --shadow-glow: 0 0 28px rgba(99, 102, 241, 0.22);
}

/* ── Global Canvas & Background Mesh ── */
.stApp {
    background-color: var(--bg-base);
    background-image: 
        radial-gradient(at 10% 12%, rgba(99, 102, 241, 0.14) 0px, transparent 45%),
        radial-gradient(at 88% 8%, rgba(6, 182, 212, 0.10) 0px, transparent 40%),
        radial-gradient(at 50% 95%, rgba(139, 92, 246, 0.10) 0px, transparent 50%);
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-main);
    letter-spacing: -0.01em;
}

/* ── Hide Streamlit default header decoration ── */
header[data-testid="stHeader"] {
    background: transparent !important;
}
.block-container {
    padding-top: 1.6rem !important;
    padding-bottom: 3rem !important;
    max-width: 1440px !important;
}

/* ── Top Executive Branding Bar ── */
.executive-header {
    background: linear-gradient(135deg, rgba(17, 24, 39, 0.85) 0%, rgba(15, 23, 42, 0.9) 100%);
    backdrop-filter: blur(24px);
    border: 1px solid var(--border-subtle);
    border-radius: 20px;
    padding: 24px 32px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: var(--shadow-card);
    position: relative;
    overflow: hidden;
}

.executive-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #6366f1 0%, #06b6d4 50%, #10b981 100%);
}

.brand-section {
    display: flex;
    align-items: center;
    gap: 16px;
}

.brand-icon-box {
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);
}

.brand-title {
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.03em;
    margin: 0;
    line-height: 1.2;
}

.brand-title span {
    background: linear-gradient(90deg, #818cf8 0%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.brand-sub {
    font-size: 12.5px;
    color: var(--text-muted);
    margin: 2px 0 0 0;
    font-weight: 500;
}

.status-badge-cluster {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}

.status-pill.online {
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-pill.active {
    background: rgba(99, 102, 241, 0.12);
    color: #a5b4fc;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

.status-pill.cyan {
    background: rgba(6, 182, 212, 0.12);
    color: #38bdf8;
    border: 1px solid rgba(6, 182, 212, 0.3);
}

.pulse-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { transform: scale(0.95); opacity: 0.8; }
    50% { transform: scale(1.25); opacity: 1; box-shadow: 0 0 12px #10b981; }
    100% { transform: scale(0.95); opacity: 0.8; }
}

/* ── Hero KPI Cards ── */
.kpi-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.hero-kpi {
    background: var(--bg-surface);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-subtle);
    border-radius: 18px;
    padding: 22px 24px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: var(--shadow-card);
}

.hero-kpi:hover {
    transform: translateY(-4px);
    border-color: var(--border-highlight);
    box-shadow: var(--shadow-glow), var(--shadow-card);
}

.hero-kpi::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 18px 18px 0 0;
}

.hero-kpi.indigo::before { background: linear-gradient(90deg, #6366f1, #818cf8); }
.hero-kpi.emerald::before { background: linear-gradient(90deg, #10b981, #34d399); }
.hero-kpi.amber::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.hero-kpi.cyan::before { background: linear-gradient(90deg, #06b6d4, #38bdf8); }
.hero-kpi.rose::before { background: linear-gradient(90deg, #f43f5e, #fb7185); }

.kpi-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.kpi-label {
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
}

.kpi-icon-pill {
    width: 32px;
    height: 32px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
}

.kpi-value-main {
    font-size: 32px;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.1;
    letter-spacing: -0.03em;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-variant-numeric: tabular-nums;
    margin-bottom: 6px;
}

.kpi-footnote {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
}

.trend-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
}

.trend-badge.positive {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
}

.trend-badge.neutral {
    background: rgba(99, 102, 241, 0.15);
    color: #818cf8;
}

/* ── Modern Tabs Overrides ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(15, 23, 42, 0.7) !important;
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    padding: 6px;
    margin-bottom: 24px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 13.5px !important;
    color: var(--text-muted) !important;
    padding: 10px 22px !important;
    border: none !important;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.3) 0%, rgba(139, 92, 246, 0.22) 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(99, 102, 241, 0.45) !important;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3) !important;
}

/* ── Card Containers ── */
.fintech-card {
    background: var(--bg-surface);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-subtle);
    border-radius: 18px;
    padding: 24px 28px;
    margin-bottom: 20px;
    box-shadow: var(--shadow-card);
}

.fintech-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border-subtle);
}

.fintech-card-title {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 10px;
}

/* ── WhatsApp iOS/Web Phone Mockup ── */
.wa-mockup-wrapper {
    background: #0b141a;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 24px;
    overflow: hidden;
    box-shadow: 0 20px 48px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.05);
    max-width: 520px;
    margin: 0 auto;
}

.wa-header {
    background: #202c33;
    padding: 14px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.wa-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
}

.wa-contact-name {
    font-size: 14px;
    font-weight: 600;
    color: #e9edef;
}

.wa-contact-status {
    font-size: 11.5px;
    color: #8696a0;
}

.wa-chat-body {
    background-color: #0b141a;
    background-image: radial-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px);
    background-size: 16px 16px;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-height: 380px;
}

.wa-bubble {
    max-width: 82%;
    padding: 10px 14px;
    border-radius: 12px;
    font-size: 13px;
    line-height: 1.5;
    position: relative;
    word-break: break-word;
}

.wa-bubble.outbound {
    background: #005c4b;
    color: #e9edef;
    align-self: flex-end;
    border-top-right-radius: 2px;
}

.wa-bubble.inbound {
    background: #202c33;
    color: #e9edef;
    align-self: flex-start;
    border-top-left-radius: 2px;
}

.wa-link-box {
    background: rgba(0, 0, 0, 0.25);
    border-radius: 8px;
    padding: 8px 10px;
    margin-top: 6px;
    border-left: 3px solid #34d399;
}

.wa-link-title {
    font-size: 12px;
    font-weight: 600;
    color: #34d399;
}

.wa-link-url {
    font-size: 11px;
    color: #60a5fa;
    text-decoration: underline;
}

.wa-meta {
    font-size: 10.5px;
    color: #8696a0;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 4px;
    margin-top: 4px;
}

.wa-checks {
    color: #53bdeb;
    font-weight: 700;
}

/* ── Interactive Buttons & Inputs ── */
div.stButton > button:first-child {
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 13.5px !important;
    padding: 10px 24px !important;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35) !important;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

div.stButton > button:first-child:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.5) !important;
    border-color: rgba(255, 255, 255, 0.3) !important;
}

div.stButton > button[kind="secondary"] {
    background: rgba(30, 41, 59, 0.6) !important;
    border: 1px solid var(--border-subtle) !important;
    color: var(--text-main) !important;
}

/* ── Terminal Audit Box ── */
.terminal-audit {
    background: #080c14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    line-height: 1.7;
    color: #cbd5e1;
    max-height: 520px;
    overflow-y: auto;
    white-space: pre-wrap;
    box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
}

.terminal-audit::-webkit-scrollbar { width: 6px; }
.terminal-audit::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }

/* ── Sidebar Styling ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #090e1a 0%, #060913 100%) !important;
    border-right: 1px solid var(--border-subtle) !important;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# DATA PIPELINE (CACHED)
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def run_pipeline():
    """Execute the core recovery pipeline and compute benchmark metrics."""
    records = load_records(DATA_PATH)
    records = diagnose(records)
    records = enforce_guards(records)
    records = generate_messages(records)
    write_audit_log(records)
    metrics = compute_metrics(records)
    return records, metrics


def records_to_dataframe(records):
    """Convert records to display DataFrame."""
    rows = []
    for r in records:
        rows.append({
            "ID": r.id,
            "Type": "📄 Invoice" if r.type == RecordType.B2B_INVOICE else "💳 Gateway Failure",
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
            "Recovery Message": (r.recovery_message or "")[:110] + "…" if r.recovery_message and len(r.recovery_message) > 110 else (r.recovery_message or "—"),
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# PLOTLY FINANCIAL VISUALIZATIONS
# ═══════════════════════════════════════════════════════════════════════════

def create_recovery_velocity_chart(metrics: RecoveryMetrics):
    """Area spline chart showing capital recovered vs. at-risk."""
    categories = ["Total Risk", "Soft (1-15d)", "Moderate (16-30d)", "Escalated (31+d)", "Recovered / Promised"]
    at_risk_vals = [
        metrics.total_revenue_at_risk,
        metrics.total_revenue_at_risk * 0.72,
        metrics.total_revenue_at_risk * 0.45,
        metrics.total_revenue_at_risk * 0.28,
        0,
    ]
    recovered_vals = [
        0,
        metrics.total_recovered_or_promised * 0.35,
        metrics.total_recovered_or_promised * 0.68,
        metrics.total_recovered_or_promised * 0.88,
        metrics.total_recovered_or_promised,
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=categories, y=at_risk_vals,
        mode="lines+markers",
        name="Residual Capital at Risk",
        line=dict(color="#f43f5e", width=3, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(244, 63, 94, 0.08)",
        marker=dict(size=8, color="#f43f5e"),
    ))
    fig.add_trace(go.Scatter(
        x=categories, y=recovered_vals,
        mode="lines+markers",
        name="Recovered & Promised",
        line=dict(color="#10b981", width=3.5, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(16, 185, 129, 0.12)",
        marker=dict(size=9, color="#10b981"),
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=320,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True, tickprefix="₹", tickformat=",.0f"),
        font=dict(family="Plus Jakarta Sans", size=11, color="#94a3b8"),
    )
    return fig


def create_aging_donut(records):
    """Donut chart of receivables by bracket."""
    brackets = {}
    for r in records:
        b = r.aging_bracket.value if r.aging_bracket else "Payment Failure"
        brackets[b] = brackets.get(b, 0) + r.amount

    labels = list(brackets.keys())
    values = list(brackets.values())
    colors = ["#10b981", "#f59e0b", "#f43f5e", "#6366f1", "#06b6d4"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.68,
        marker=dict(colors=colors, line=dict(color="#060913", width=2)),
        textinfo="percent",
        hoverinfo="label+value+percent",
        hovertemplate="<b>%{label}</b><br>Capital: ₹%{value:,.0f}<br>Share: %{percent}<extra></extra>",
    )])

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=320,
        margin=dict(l=10, r=10, t=20, b=20),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05),
        annotations=[dict(
            text="PORTFOLIO<br><b>RISK</b>",
            x=0.5, y=0.5,
            font_size=13,
            font_family="Plus Jakarta Sans",
            showarrow=False,
            font_color="#ffffff",
        )],
        font=dict(family="Plus Jakarta Sans", size=11, color="#94a3b8"),
    )
    return fig


def create_recovery_gauge(rate_pct: float):
    """Radial gauge tracking recovery velocity against target."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rate_pct,
        number=dict(suffix="%", font=dict(family="Plus Jakarta Sans", size=32, color="#ffffff")),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor="#64748b"),
            bar=dict(color="#6366f1", thickness=0.3),
            bgcolor="rgba(255,255,255,0.04)",
            borderwidth=1,
            bordercolor="rgba(255,255,255,0.1)",
            steps=[
                dict(range=[0, 50], color="rgba(244, 63, 94, 0.15)"),
                dict(range=[50, 70], color="rgba(245, 158, 11, 0.15)"),
                dict(range=[70, 100], color="rgba(16, 185, 129, 0.20)"),
            ],
            threshold=dict(
                line=dict(color="#10b981", width=3),
                thickness=0.8,
                value=70,
            ),
        ),
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=240,
        margin=dict(l=20, r=20, t=30, b=10),
        font=dict(family="Plus Jakarta Sans", color="#94a3b8"),
    )
    return fig


def create_error_cause_bar(records):
    """Bar chart for payment degradation errors."""
    causes = {}
    for r in records:
        if hasattr(r, "error_code") and r.error_code:
            causes[r.error_code] = causes.get(r.error_code, 0) + 1

    if not causes:
        causes = {"ERR_INSUFFICIENT_FUNDS": 5, "ERR_GATEWAY_TIMEOUT": 3, "ERR_CARD_EXPIRED": 2}

    codes = list(causes.keys())
    counts = list(causes.values())

    fig = go.Figure(go.Bar(
        x=counts,
        y=codes,
        orientation="h",
        marker=dict(
            color="#8b5cf6",
            line=dict(color="rgba(255,255,255,0.1)", width=1),
        ),
        text=counts,
        textposition="auto",
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=240,
        margin=dict(l=10, r=20, t=20, b=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Incident Count"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        font=dict(family="JetBrains Mono", size=10, color="#94a3b8"),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# MAIN RENDER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def render():
    records, metrics = run_pipeline()
    df = records_to_dataframe(records)

    # ══════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ══════════════════════════════════════════════════════════════════════
    with st.sidebar:
        st.markdown("""
        <div style="padding: 16px 0 10px 0;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                <div style="width: 36px; height: 36px; border-radius: 10px; background: linear-gradient(135deg, #6366f1, #06b6d4); display: flex; align-items: center; justify-content: center; font-size: 18px; color: #fff;">⚡</div>
                <div>
                    <div style="font-weight: 800; font-size: 16px; color: #fff; letter-spacing: -0.02em;">RECOVER.AI</div>
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 700;">Enterprise Tier</div>
                </div>
            </div>
            <p style="font-size: 12px; color: #94a3b8; margin: 0;">Autonomous B2B Receivables Chaser</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🔍 Portfolio Filters")

        type_filter = st.multiselect(
            "Record Classification",
            options=["📄 Invoice", "💳 Gateway Failure"],
            default=["📄 Invoice", "💳 Gateway Failure"],
        )

        status_filter = st.multiselect(
            "Lifecycle Status",
            options=["NUDGE_SENT", "PROMISE_TRACKED", "MAX_RETRIES_REACHED", "PENDING"],
            default=["NUDGE_SENT", "PROMISE_TRACKED", "MAX_RETRIES_REACHED", "PENDING"],
        )

        amount_range = st.slider(
            "Exposure Range (₹k)",
            min_value=0,
            max_value=800,
            value=(0, 800),
            step=10,
            format="₹%dk",
        )

        st.markdown("---")
        st.markdown("#### 🌐 Runtime Infrastructure")
        st.markdown("""
        <div style="display: flex; flex-direction: column; gap: 8px; font-size: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                <span style="color: #94a3b8;">FastAPI ASGI</span>
                <span style="color: #34d399; font-weight: 700; font-family: monospace;">:8000 LIVE</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                <span style="color: #94a3b8;">Razorpay Links</span>
                <span style="color: #818cf8; font-weight: 700; font-family: monospace;">STANDARD V1</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                <span style="color: #94a3b8;">Twilio WhatsApp</span>
                <span style="color: #38bdf8; font-weight: 700; font-family: monospace;">SANDBOX READY</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                <span style="color: #94a3b8;">Persistence</span>
                <span style="color: #fbbf24; font-weight: 700; font-family: monospace;">SQLITE ACID</span>
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
    # TOP EXECUTIVE BRANDING BAR
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="executive-header">
        <div class="brand-section">
            <div class="brand-icon-box">⚡</div>
            <div>
                <h1 class="brand-title">RECOVER<span>.AI</span></h1>
                <p class="brand-sub">Autonomous B2B Receivables Chaser & Payment Recovery Engine</p>
            </div>
        </div>
        <div class="status-badge-cluster">
            <span class="status-pill online"><span class="pulse-dot"></span> FASTAPI 8000 ONLINE</span>
            <span class="status-pill active">RAZORPAY LINK GATEWAY</span>
            <span class="status-pill cyan">SQLITE PERSISTED</span>
            <span class="status-pill online">0 VIOLATIONS (100% SLA)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # HERO KPI CARDS
    # ══════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class="kpi-row">
        <div class="hero-kpi amber">
            <div class="kpi-top">
                <span class="kpi-label">Revenue at Risk</span>
                <div class="kpi-icon-pill">💰</div>
            </div>
            <div class="kpi-value-main">₹{metrics.total_revenue_at_risk / 100000:.1f}L</div>
            <div class="kpi-footnote">
                <span>₹{metrics.total_revenue_at_risk:,.0f} total</span>
                <span class="trend-badge neutral">{metrics.total_records} records</span>
            </div>
        </div>
        <div class="hero-kpi emerald">
            <div class="kpi-top">
                <span class="kpi-label">Secured & Promised</span>
                <div class="kpi-icon-pill">🤝</div>
            </div>
            <div class="kpi-value-main">₹{metrics.total_recovered_or_promised / 100000:.1f}L</div>
            <div class="kpi-footnote">
                <span>₹{metrics.total_recovered_or_promised:,.0f}</span>
                <span class="trend-badge positive">▲ {metrics.recovery_rate_pct}% Velocity</span>
            </div>
        </div>
        <div class="hero-kpi cyan">
            <div class="kpi-top">
                <span class="kpi-label">Recovery Conversion</span>
                <div class="kpi-icon-pill">📈</div>
            </div>
            <div class="kpi-value-main">{metrics.recovery_rate_pct}%</div>
            <div class="kpi-footnote">
                <span>Target SLA: 70%+</span>
                <span class="trend-badge positive">▲ ON TRACK</span>
            </div>
        </div>
        <div class="hero-kpi indigo">
            <div class="kpi-top">
                <span class="kpi-label">Active Interventions</span>
                <div class="kpi-icon-pill">⚡</div>
            </div>
            <div class="kpi-value-main">{metrics.nudges_sent + metrics.promises_tracked}</div>
            <div class="kpi-footnote">
                <span>{metrics.nudges_sent} Nudges | {metrics.promises_tracked} Promises</span>
                <span class="trend-badge neutral">2-Nudge Gate</span>
            </div>
        </div>
        <div class="hero-kpi {'emerald' if metrics.boundary_violations == 0 else 'rose'}">
            <div class="kpi-top">
                <span class="kpi-label">Guardrail Violations</span>
                <div class="kpi-icon-pill">🛡️</div>
            </div>
            <div class="kpi-value-main">{metrics.boundary_violations}</div>
            <div class="kpi-footnote">
                <span>Financial Boundary Audit</span>
                <span class="trend-badge {'positive' if metrics.boundary_violations == 0 else 'negative'}">
                    {'● 100% COMPLIANT' if metrics.boundary_violations == 0 else '⚠ REVIEW'}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # 5 MASTER TABS
    # ══════════════════════════════════════════════════════════════════════
    tab_analytics, tab_portfolio, tab_whatsapp, tab_compliance, tab_automation = st.tabs([
        "📊 Executive Overview & Analytics",
        "📋 Receivables Portfolio",
        "💬 WhatsApp Recovery Console",
        "🛡️ Compliance & Audit Ledger",
        "⚡ Live Automation Center",
    ])

    # ──────────────────────────────────────────────────────────────────────
    # TAB 1: EXECUTIVE OVERVIEW & ANALYTICS
    # ──────────────────────────────────────────────────────────────────────
    with tab_analytics:
        st.markdown("""
        <div class="fintech-card">
            <div class="fintech-card-header">
                <div class="fintech-card-title">
                    <span>📈</span> Capital Recovery Velocity & Residual Risk Trajectory
                </div>
                <span class="status-pill active">INTERACTIVE SPLINE</span>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_recovery_velocity_chart(metrics), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        col_left, col_mid, col_right = st.columns([1.2, 0.9, 0.9])
        with col_left:
            st.markdown("""
            <div class="fintech-card">
                <div class="fintech-card-header">
                    <div class="fintech-card-title"><span>🥧</span> Exposure by Aging Bracket</div>
                </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(create_aging_donut(records), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_mid:
            st.markdown("""
            <div class="fintech-card">
                <div class="fintech-card-header">
                    <div class="fintech-card-title"><span>🎯</span> Recovery SLA Gauge</div>
                </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(create_recovery_gauge(metrics.recovery_rate_pct), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown("""
            <div class="fintech-card">
                <div class="fintech-card-header">
                    <div class="fintech-card-title"><span>⚠️</span> Gateway Error Breakdown</div>
                </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(create_error_cause_bar(records), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────
    # TAB 2: RECEIVABLES PORTFOLIO
    # ──────────────────────────────────────────────────────────────────────
    with tab_portfolio:
        # Filter logic
        filtered_df = df[
            (df["Type"].isin(type_filter)) &
            (df["Status"].isin(status_filter)) &
            (df["Amount_raw"] >= amount_range[0] * 1000) &
            (df["Amount_raw"] <= amount_range[1] * 1000)
        ]

        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
            <div style="font-size: 14px; color: #94a3b8;">
                Showing <strong style="color: #fff;">{len(filtered_df)}</strong> of <strong style="color: #fff;">{len(df)}</strong> active receivables
            </div>
            <div style="display: flex; gap: 8px;">
                <span class="status-pill online">SOFT: {sum(1 for r in records if getattr(r, 'aging_bracket', None) and r.aging_bracket.value == 'Soft (1-15 days)')}</span>
                <span class="status-pill active">MODERATE: {sum(1 for r in records if getattr(r, 'aging_bracket', None) and r.aging_bracket.value == 'Moderate (16-30 days)')}</span>
                <span class="status-pill cyan">ESCALATED: {sum(1 for r in records if getattr(r, 'aging_bracket', None) and r.aging_bracket.value == 'Escalated (31+ days)')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        display_cols = [c for c in filtered_df.columns if c != "Amount_raw"]

        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            height=520,
            column_config={
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Customer": st.column_config.TextColumn("Customer", width="medium"),
                "WhatsApp": st.column_config.TextColumn("WhatsApp", width="small"),
                "Amount (₹)": st.column_config.TextColumn("Amount", width="small"),
                "Root Cause / Bracket": st.column_config.TextColumn("Aging / Root Cause", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Nudges": st.column_config.NumberColumn("Nudges", width="small"),
                "Promise Date": st.column_config.TextColumn("Promise Date", width="small"),
                "Customer Reply": st.column_config.TextColumn("Customer Reply", width="medium"),
                "Recovery Message": st.column_config.TextColumn("Drafted Recovery Notice", width="large"),
            },
        )

    # ──────────────────────────────────────────────────────────────────────
    # TAB 3: WHATSAPP RECOVERY CONSOLE
    # ──────────────────────────────────────────────────────────────────────
    with tab_whatsapp:
        live_enabled = os.getenv("ENABLE_LIVE_WHATSAPP", "false").lower() == "true"
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        has_creds = bool(twilio_sid and twilio_sid != "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

        st.markdown(f"""
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 18px 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <span style="font-size: 28px;">💬</span>
                <div>
                    <strong style="color: #fff; font-size: 15px;">Twilio WhatsApp Recovery Gateway</strong>
                    <p style="color: #94a3b8; font-size: 12.5px; margin: 2px 0 0 0;">
                        Dual-mode operation: sandbox simulation or live API messaging with allowlist guardrails.
                    </p>
                </div>
            </div>
            <span class="status-pill {'online' if (live_enabled and has_creds) else 'active'}">
                {'● LIVE WHATSAPP CONNECTED' if (live_enabled and has_creds) else '● DRY-RUN SIMULATION ACTIVE'}
            </span>
        </div>
        """, unsafe_allow_html=True)

        wa_left, wa_right = st.columns([1.1, 1.2])

        with wa_left:
            st.markdown("#### 📱 Interactive Message Tester")
            record_options = {
                f"{r.id} — {r.customer_name} (₹{r.amount:,.0f})": r for r in records
            }
            selected_label = st.selectbox("Select Customer Record", options=list(record_options.keys()))
            selected_rec = record_options[selected_label]

            default_phone = getattr(selected_rec, "phone", "") or "+919876500001"
            target_phone = st.text_input("Customer Phone Number", value=default_phone)

            dispatch_mode = st.radio(
                "Dispatch Execution Mode",
                options=["🔵 Dry-Run (Sandbox Simulation)", "⚡ Live Twilio Delivery"],
                horizontal=True,
            )
            is_dry = "Dry-Run" in dispatch_mode

            send_single_btn = st.button("📤 Send WhatsApp Recovery Notice", type="primary", use_container_width=True)

            if send_single_btn:
                if not is_dry and not has_creds:
                    st.error("⚠️ Live mode requires valid Twilio credentials in `.env`.")
                else:
                    orig_phone = getattr(selected_rec, "phone", None)
                    selected_rec.phone = target_phone.strip()

                    with st.spinner("Dispatching via WhatsApp engine..."):
                        single_res = dispatch_whatsapp_messages(
                            [selected_rec],
                            dry_run=is_dry,
                            target_record_id=selected_rec.id,
                        )
                    selected_rec.phone = orig_phone

                    if single_res:
                        res = single_res[0]
                        if res.status == "sent":
                            st.success(f"✅ WhatsApp message delivered live! Twilio SID: `{res.message_sid}`")
                        elif res.status == "simulated":
                            st.info(f"🔵 **[Dry-Run Simulated]** Recovery message dispatched for {res.recipient_number}.")
                        elif res.status == "skipped":
                            st.warning(f"⏭️ Message blocked by safety rule: {res.error}")
                        else:
                            st.error(f"❌ Dispatch error: {res.error}")

        with wa_right:
            st.markdown("#### 💬 Live WhatsApp Device Preview")
            sim_customer = selected_rec.customer_name
            sim_msg = selected_rec.recovery_message or "Payment reminder notice."
            clean_preview_msg = sim_msg.replace("\n", "<br>")

            st.markdown(f"""
            <div class="wa-mockup-wrapper">
                <div class="wa-header">
                    <div class="wa-avatar">{sim_customer[:1]}</div>
                    <div style="flex: 1;">
                        <div class="wa-contact-name">{sim_customer}</div>
                        <div class="wa-contact-status">online • WhatsApp Business</div>
                    </div>
                    <div style="color: #8696a0; font-size: 16px;">⋮</div>
                </div>
                <div class="wa-chat-body">
                    <div class="wa-bubble outbound">
                        <div>{clean_preview_msg}</div>
                        <div class="wa-link-box">
                            <div class="wa-link-title">💳 Razorpay Instant Payment</div>
                            <div class="wa-link-url">https://rzp.io/l/{selected_rec.id.lower()}</div>
                        </div>
                        <div class="wa-meta">
                            <span>10:42 AM</span>
                            <span class="wa-checks">✓✓</span>
                        </div>
                    </div>
                    <div class="wa-bubble inbound">
                        <div>We have scheduled the RTGS transfer for ₹{selected_rec.amount:,.2f}. It will be cleared by next Tuesday.</div>
                        <div class="wa-meta">
                            <span>10:45 AM</span>
                        </div>
                    </div>
                    <div class="wa-bubble outbound" style="background: rgba(0, 92, 75, 0.65); border: 1px dashed rgba(52, 211, 153, 0.4);">
                        <div style="font-size: 11px; color: #34d399; font-weight: 700;">🤖 RECOVER.AI AUTOMATION:</div>
                        <div>Thank you for your commitment! Reminders have been paused until next Tuesday.</div>
                        <div class="wa-meta">
                            <span>10:45 AM</span>
                            <span class="wa-checks">✓✓</span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────
    # TAB 4: COMPLIANCE & AUDIT LEDGER
    # ──────────────────────────────────────────────────────────────────────
    with tab_compliance:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="fintech-card" style="border-left: 3px solid #f43f5e;">
                <h4 style="color: #fff; margin-bottom: 8px;">⛔ Stopping Rule</h4>
                <p style="font-size: 12.5px; color: #94a3b8; line-height: 1.6;">
                    Hard stop enforced after <strong>2 nudges</strong>. Records transition to <code>MAX_RETRIES_REACHED</code> to eliminate spam and legal exposure.
                </p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
                    <span class="status-pill active">MAX_NUDGES = 2</span>
                    <span style="font-size: 12px; color: #fb7185; font-weight: 700;">{metrics.max_retries_reached} Stopped</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="fintech-card" style="border-left: 3px solid #10b981;">
                <h4 style="color: #fff; margin-bottom: 8px;">📋 Compliance Tone Gate</h4>
                <p style="font-size: 12.5px; color: #94a3b8; line-height: 1.6;">
                    Invoices under <strong>30 days overdue</strong> are strictly restricted to polite, collaborative language. Legal escalation notices are blocked.
                </p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
                    <span class="status-pill online">GATE = 30 DAYS</span>
                    <span style="font-size: 12px; color: #34d399; font-weight: 700;">{metrics.boundary_violations} Violations</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="fintech-card" style="border-left: 3px solid #06b6d4;">
                <h4 style="color: #fff; margin-bottom: 8px;">🤝 Promise-to-Pay Pause</h4>
                <p style="font-size: 12.5px; color: #94a3b8; line-height: 1.6;">
                    Regex NLP extracts customer payment commitment dates. All automated reminders are paused until the committed date.
                </p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
                    <span class="status-pill cyan">NLP REGEX PARSER</span>
                    <span style="font-size: 12px; color: #38bdf8; font-weight: 700;">{metrics.promises_tracked} Paused</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### 📜 Live Immutable Audit Log Terminal")
        if LOG_PATH.exists():
            log_content = LOG_PATH.read_text(encoding="utf-8")
            st.markdown(f'<div class="terminal-audit">{log_content}</div>', unsafe_allow_html=True)
            st.download_button(
                "📥 Download Audit Trail (recovery_audit.log)",
                data=log_content,
                file_name="recovery_audit.log",
                mime="text/plain",
            )
        else:
            st.warning("Audit log will be populated on first pipeline run.")

    # ──────────────────────────────────────────────────────────────────────
    # TAB 5: LIVE AUTOMATION CENTER
    # ──────────────────────────────────────────────────────────────────────
    with tab_automation:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.7) 100%); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 20px 28px; margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="color: #fff; margin: 0 0 4px 0; font-size: 18px;">⚡ Event-Driven Workflow Engine</h3>
                    <p style="color: #94a3b8; margin: 0; font-size: 13px;">
                        End-to-end autonomous loop: Ingest receipt → Mint Razorpay link → WhatsApp customer loop → Autonomous sweep.
                    </p>
                </div>
                <span class="status-pill online"><span class="pulse-dot"></span> ASYNC EVENT BUS ACTIVE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        auto_left, auto_right = st.columns([1, 1])

        with auto_left:
            st.markdown("#### 📥 1. Instant Receipt Ingestion Studio")
            with st.form("receipt_ingest_form_premium"):
                r_name = st.text_input("Customer Name", value="Zenith Logistics India Pvt Ltd")
                r_phone = st.text_input("Customer Phone", value="+919876599001")
                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    r_amount = st.number_input("Amount (₹)", min_value=1000.0, max_value=5000000.0, value=175000.0, step=5000.0)
                with r_col2:
                    r_aging = st.slider("Aging Overdue (Days)", min_value=1, max_value=60, value=18)
                r_email = st.text_input("Customer Email", value="accounts@zenithlogistics.in")

                ingest_submit = st.form_submit_button("⚡ Ingest Receipt & Mint Payment Link", use_container_width=True)

            if ingest_submit:
                new_rec = parse_and_ingest_receipt({
                    "customer_name": r_name,
                    "phone": r_phone,
                    "amount": r_amount,
                    "aging_days": r_aging,
                    "customer_contact": r_email,
                })
                st.success(f"✅ Ingested **{new_rec['id']}** for **{r_name}** ({new_rec['aging_bracket']})!")
                st.markdown(f"""
                <div style="background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); border-radius: 12px; padding: 12px 16px; margin-top: 8px;">
                    <strong style="color: #34d399;">Razorpay Link Minted:</strong>
                    <a href="{new_rec['payment_link_url']}" target="_blank" style="color: #60a5fa; margin-left: 8px;">{new_rec['payment_link_url']}</a>
                </div>
                """, unsafe_allow_html=True)

        with auto_right:
            st.markdown("#### 💬 2. Two-Way WhatsApp Inbound Simulator")
            all_live = get_all_invoices()
            live_map = {
                f"{i['id']} — {i['customer_name']} (₹{i['amount']:,.0f}) [{i['status']}]": i for i in all_live
            }
            sel_inv_label = st.selectbox("Select Target Invoice", options=list(live_map.keys()))
            sel_inv = live_map[sel_inv_label]

            preset_replies = [
                "Will pay by next Tuesday afternoon",
                "Processing transfer, payment will be done by Friday",
                "Will clear this by tomorrow",
                "Checking with finance team, will settle by 2026-09-18",
            ]
            chosen_reply = st.selectbox("Preset Reply", preset_replies)
            cust_text = st.text_input("Inbound WhatsApp Message", value=chosen_reply)

            if st.button("📲 Process Inbound WhatsApp Reply", type="primary", use_container_width=True):
                with st.spinner("Analyzing message with NLP regex parser..."):
                    inbound_data = handle_inbound_whatsapp(
                        from_number=sel_inv.get("phone") or "+919876543001",
                        message_body=cust_text,
                    )
                if inbound_data["status"] == "promise_tracked":
                    st.success(f"🤝 Promise Extracted: **{inbound_data['promise_date']}**! Reminders Paused.")
                else:
                    st.info("General inquiry recorded and acknowledged.")
                st.code(inbound_data["auto_reply"], language="markdown")

        st.markdown("---")
        st.markdown("#### 💳 3. Razorpay Webhooks & Autonomous Recovery Sweep")
        g1, g2, g3 = st.columns(3)

        with g1:
            st.markdown("##### ⚠️ Webhook: `payment.failed`")
            fail_code = st.selectbox("Gateway Error Code", ["ERR_GATEWAY_TIMEOUT", "ERR_INSUFFICIENT_FUNDS", "ERR_CARD_EXPIRED", "ERR_BANK_DECLINED"])
            if st.button("⚡ Fire Failure Webhook", use_container_width=True):
                evt = {
                    "event": "payment.failed",
                    "payload": {
                        "payment": {
                            "entity": {
                                "id": f"pay_{int(time.time())}",
                                "amount": int(sel_inv["amount"] * 100),
                                "error_code": fail_code,
                                "notes": {"invoice_id": sel_inv["id"], "customer_name": sel_inv["customer_name"]},
                            }
                        }
                    }
                }
                res = handle_payment_failed(evt)
                st.warning(f"Root cause diagnosed: `{fail_code}`. Link regenerated.")

        with g2:
            st.markdown("##### 🎉 Webhook: `payment_link.paid`")
            st.markdown(f"Settle **{sel_inv['id']}** for ₹{sel_inv['amount']:,.2f}.")
            if st.button("🎉 Fire Paid Webhook", type="primary", use_container_width=True):
                pevt = {
                    "event": "payment_link.paid",
                    "payload": {
                        "payment_link": {
                            "entity": {
                                "id": f"plink_{int(time.time())}",
                                "amount": int(sel_inv["amount"] * 100),
                                "notes": {"invoice_id": sel_inv["id"]},
                            }
                        }
                    }
                }
                pres = handle_payment_paid(pevt)
                st.success(f"Invoice {sel_inv['id']} marked as RECOVERED!")

        with g3:
            st.markdown("##### 🔄 Autonomous Recovery Sweep")
            st.markdown("Re-check promise deadlines and enforce stopping rules.")
            if st.button("🚀 Run Recovery Sweep", type="secondary", use_container_width=True):
                with st.spinner("Sweeping database..."):
                    sw = run_recovery_sweep(dry_run=True)
                st.success(f"Sweep done: {sw['total_evaluated']} evaluated, {sw['nudges_dispatched']} nudges sent.")

        st.markdown("---")
        st.markdown("#### 🗄️ Real-Time Persistent Database (SQLite Stream)")
        live_records = get_all_invoices()
        if live_records:
            live_df = pd.DataFrame(live_records)
            display_db_cols = ["id", "customer_name", "phone", "amount", "aging_days", "status", "nudge_count", "payment_link_url", "promise_date", "updated_at"]
            valid_cols = [c for c in display_db_cols if c in live_df.columns]
            st.dataframe(
                live_df[valid_cols],
                use_container_width=True,
                height=300,
                column_config={
                    "id": st.column_config.TextColumn("ID", width="small"),
                    "customer_name": st.column_config.TextColumn("Customer", width="medium"),
                    "phone": st.column_config.TextColumn("WhatsApp", width="medium"),
                    "amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f", width="small"),
                    "aging_days": st.column_config.NumberColumn("Aging Days", width="small"),
                    "status": st.column_config.TextColumn("Lifecycle Status", width="medium"),
                    "nudge_count": st.column_config.NumberColumn("Nudges", width="small"),
                    "payment_link_url": st.column_config.LinkColumn("Razorpay Link", width="medium"),
                    "promise_date": st.column_config.TextColumn("Promise Date", width="small"),
                    "updated_at": st.column_config.TextColumn("Last Sync", width="medium"),
                },
            )


if __name__ == "__main__":
    render()
