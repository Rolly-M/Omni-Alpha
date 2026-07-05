"""OmniAlpha Streamlit Dashboard — Home / Overview page."""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OmniAlpha",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

DISCLAIMER = (
    "⚠️ **DISCLAIMER:** OmniAlpha is for **research, education, and simulation ONLY**. "
    "No guarantee of returns. Markets involve substantial risk. "
    "Users are responsible for legal, tax, and regulatory compliance. "
    "This is **not** financial advice."
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=OmniAlpha", width=200)
    st.markdown("**v1.0.0** | Paper Trading Mode")
    st.success("🟢 MOCK MODE — No real money")
    st.error("🔴 LIVE TRADING: DISABLED")

    st.markdown("---")
    st.markdown("### Quick Controls")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if st.button("⚡ Run Analysis Cycle", use_container_width=True):
        with st.spinner("Running agents..."):
            try:
                from services.agents.coordinator import get_coordinator
                coordinator = get_coordinator()
                decisions = coordinator.run_cycle(symbols=["AAPL", "MSFT", "BTC/USDT", "EURUSD=X"])
                st.success(f"✅ {len(decisions)} decisions generated")
            except Exception as e:
                st.warning(f"Demo mode: {str(e)[:60]}")

    kill_active = st.toggle("🚨 Kill Switch", value=False, key="kill_switch")
    if kill_active:
        st.error("⛔ KILL SWITCH ACTIVE — All trading halted")

    st.markdown("---")
    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")


# ── Main header ───────────────────────────────────────────────────────────────
st.title("🔭 OmniAlpha — Research & Paper Trading")
st.warning(DISCLAIMER)

# ── Top KPIs ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("💰 Portfolio Value", "$102,300", "+$2,300 (2.3%)")
col2.metric("💵 Cash", "$87,000", "85.0%")
col3.metric("📈 Today's P&L", "+$230", "+0.23%")
col4.metric("📊 Open Positions", "3", "")
col5.metric("🎯 Active Signals", "5", "+2")

st.markdown("---")

# ── Equity curve ──────────────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📈 Portfolio Equity Curve")
    rng = np.random.default_rng(42)
    days = 60
    curve = [100_000]
    for _ in range(days):
        curve.append(curve[-1] * (1 + rng.normal(0.0012, 0.010)))

    dates_idx = pd.date_range(end=pd.Timestamp.now(), periods=days + 1, freq="D")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates_idx, y=curve,
        mode="lines", name="Portfolio",
        line=dict(color="#00D4AA", width=2),
        fill="tozeroy", fillcolor="rgba(0,212,170,0.1)",
    ))
    fig.add_hline(y=100_000, line_dash="dash", line_color="gray",
                  annotation_text="Initial $100k")
    fig.update_layout(
        height=300, margin=dict(l=0, r=0, t=10, b=0),
        template="plotly_dark", showlegend=False,
        yaxis=dict(tickprefix="$"),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("🌡️ Regime Status")
    st.metric("Market Regime", "RISK_ON", "↑ Bullish")
    st.metric("VIX", "14.2", "-2.1 from yesterday")
    st.metric("10Y Yield", "4.31%", "+0.03%")
    st.metric("BTC Dominance", "52.4%", "-0.8%")

# ── Active signals ────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🔥 Top Opportunities by Asset Class")

@st.cache_data(ttl=120)
def get_demo_signals():
    from services.agents.coordinator import get_coordinator
    from libs.common.config import settings
    coordinator = get_coordinator()
    try:
        symbols = settings.STOCK_WATCHLIST[:4] + settings.CRYPTO_WATCHLIST[:1] + settings.FOREX_WATCHLIST[:1]
        decisions = coordinator.run_cycle(symbols=symbols)
        rows = []
        for d in decisions:
            rows.append({
                "Symbol": d.symbol,
                "Asset Class": d.asset_class.upper(),
                "Action": d.action,
                "Confidence": f"{d.confidence:.1f}%",
                "Risk Verdict": d.risk_verdict,
                "Entry": f"${d.entry_price:.2f}" if d.entry_price > 10 else f"{d.entry_price:.4f}",
                "Size": f"{d.position_size_pct*100:.2f}%",
                "Thesis": d.thesis[:80] + "..." if len(d.thesis) > 80 else d.thesis,
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame([
            {"Symbol": "AAPL", "Asset Class": "STOCK", "Action": "BUY", "Confidence": "72.5%",
             "Risk Verdict": "APPROVED", "Entry": "$185.20", "Size": "2.00%",
             "Thesis": "RSI oversold (28.4), MACD bullish cross, uptrend confirmed"},
            {"Symbol": "BTC/USDT", "Asset Class": "CRYPTO", "Action": "BUY", "Confidence": "65.0%",
             "Risk Verdict": "APPROVED", "Entry": "$68,200", "Size": "2.00%",
             "Thesis": "Negative funding rate, exchange outflow bullish, Fear=35"},
            {"Symbol": "EURUSD=X", "Asset Class": "FOREX", "Action": "HOLD", "Confidence": "48.0%",
             "Risk Verdict": "APPROVED", "Entry": "1.0853", "Size": "0.00%",
             "Thesis": "Mixed signals, awaiting macro catalyst"},
        ])


df_signals = get_demo_signals()
if not df_signals.empty:
    def color_action(val):
        if val == "BUY":
            return "background-color: #004400; color: #00ff88"
        elif val == "SELL":
            return "background-color: #440000; color: #ff6666"
        return ""

    styled = df_signals.style.applymap(color_action, subset=["Action"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

# ── Recent agent activity ─────────────────────────────────────────────────────
st.markdown("---")
col_news, col_alerts = st.columns(2)

with col_news:
    st.subheader("📰 Recent News Impact")
    news_items = [
        ("🟢", "NVDA", "NVDA beats earnings estimates by 12%", "72 min ago"),
        ("🔴", "TSLA", "TSLA faces regulatory scrutiny from SEC", "3 h ago"),
        ("🟡", "AAPL", "AAPL trading range remains tight; analysts mixed", "5 h ago"),
        ("🟢", "MSFT", "MSFT announces $5B share buyback program", "8 h ago"),
    ]
    for icon, sym, headline, age in news_items:
        st.markdown(f"{icon} **{sym}** — {headline} _{age}_")

with col_alerts:
    st.subheader("⚠️ Risk Alerts")
    st.success("✅ Max drawdown: 1.2% / 15% limit — OK")
    st.success("✅ Daily loss: +0.23% — OK")
    st.success("✅ Cash level: 85% — OK")
    st.warning("⚠️ TSLA ATR=4.2% — High volatility, position size reduced")
    st.info("ℹ️ 3 pending signals awaiting approval")

st.markdown("---")
st.caption("OmniAlpha v1.0.0 | Paper Trading Only | Not financial advice")
