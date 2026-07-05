"""Training Simulator — step-by-step fake-balance trading practice."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Training | OmniAlpha", page_icon="🎓", layout="wide")
st.title("🎓 Training Simulator")
st.info(
    "Practice trading with **fake money** ($100,000 virtual balance). "
    "All trades are simulated. No real money is involved."
)

# Session state for simulator
if "sim_balance" not in st.session_state:
    st.session_state.sim_balance = 100_000.0
    st.session_state.sim_equity_curve = [100_000.0]
    st.session_state.sim_trades = []
    st.session_state.sim_positions = {}

st.sidebar.markdown("### 💰 Simulator Balance")
account_type = st.sidebar.selectbox("Account Profile", ["Conservative", "Balanced", "Aggressive"])
balance = st.session_state.sim_balance
st.sidebar.metric("Virtual Cash", f"${balance:,.2f}")

if st.sidebar.button("🔄 Reset Simulator", type="secondary"):
    st.session_state.sim_balance = 100_000.0
    st.session_state.sim_equity_curve = [100_000.0]
    st.session_state.sim_trades = []
    st.session_state.sim_positions = {}
    st.rerun()

# Config multipliers
profile_multipliers = {"Conservative": 0.02, "Balanced": 0.05, "Aggressive": 0.10}
size_pct = profile_multipliers[account_type]

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📊 Get Signal & Trade")
    symbol = st.selectbox("Choose Symbol", ["AAPL", "MSFT", "GOOGL", "AMZN", "BTC/USDT", "EURUSD=X", "SPY"])

    if st.button(f"🔍 Analyze {symbol} — Run All 13 Agents", use_container_width=True):
        with st.spinner("Running agents..."):
            try:
                from services.agents.coordinator import get_coordinator
                coord = get_coordinator()
                decisions = coord.run_cycle(symbols=[symbol])
                d = decisions[0]
                st.session_state.last_decision = d
                st.success(f"**{d.action}** | Confidence {d.confidence:.1f}% | Risk: {d.risk_verdict}")
                st.code(d.explanation, language="")
            except Exception as e:
                import random
                rng = random.Random(symbol)
                st.session_state.last_decision = type("D", (), {
                    "action": rng.choice(["BUY", "HOLD", "BUY", "SELL"]),
                    "confidence": rng.uniform(55, 80),
                    "entry_price": rng.uniform(150, 500),
                    "risk_verdict": "APPROVED",
                    "explanation": f"Demo: {symbol} showing technical setup.",
                })()
                st.info(f"Demo signal: **{st.session_state.last_decision.action}** at ${st.session_state.last_decision.entry_price:.2f}")

    if "last_decision" in st.session_state:
        d = st.session_state.last_decision
        if d.action in ("BUY", "SELL") and d.risk_verdict == "APPROVED":
            trade_val = st.session_state.sim_balance * size_pct
            col_b, col_s = st.columns(2)
            with col_b:
                if st.button(f"✅ Execute {d.action} ({size_pct*100:.0f}% = ${trade_val:,.0f})",
                              use_container_width=True, type="primary"):
                    price = d.entry_price
                    commission = trade_val * 0.001
                    qty = (trade_val - commission) / price
                    pnl_sim = np.random.normal(trade_val * 0.008, trade_val * 0.015)
                    st.session_state.sim_balance += pnl_sim - commission
                    st.session_state.sim_equity_curve.append(st.session_state.sim_balance)
                    st.session_state.sim_trades.append({
                        "Symbol": symbol, "Action": d.action,
                        "Price": round(price, 2), "Value": round(trade_val, 2),
                        "P&L": round(pnl_sim, 2), "Commission": round(commission, 2),
                    })
                    st.success(f"Simulated fill! P&L: ${pnl_sim:+.2f}")
                    st.rerun()

with col_right:
    st.subheader("📈 Equity Curve")
    curve = st.session_state.sim_equity_curve
    fig = go.Figure(go.Scatter(
        y=curve, mode="lines+markers",
        line=dict(color="#00D4AA"), marker=dict(size=4),
    ))
    fig.update_layout(
        height=250, template="plotly_dark",
        yaxis_tickprefix="$",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    pnl = st.session_state.sim_balance - 100_000
    st.metric("Simulated P&L", f"${pnl:+,.2f}", f"{pnl/100_000*100:+.2f}%")

# Trade history
if st.session_state.sim_trades:
    st.subheader("📋 Trade History (Simulated)")
    st.dataframe(pd.DataFrame(st.session_state.sim_trades), use_container_width=True, hide_index=True)
