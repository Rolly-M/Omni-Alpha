"""Portfolio page — positions, P&L, equity curve detail."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Portfolio | OmniAlpha", page_icon="💼", layout="wide")
st.title("💼 Portfolio Overview")

# KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Equity", "$102,300", "+$2,300")
c2.metric("Cash", "$87,000 (85%)")
c3.metric("Positions Value", "$15,300 (15%)")
c4.metric("Max Drawdown", "1.2%", "-0.3%")

st.markdown("---")

# Positions table
st.subheader("Open Positions")
positions = pd.DataFrame([
    {"Symbol": "AAPL", "Class": "Stock", "Qty": 25.0, "Avg Cost": 183.40,
     "Current": 185.20, "Market Value": 4630.0, "Unreal. P&L": "+$45.00", "P&L %": "+0.98%"},
    {"Symbol": "MSFT", "Class": "Stock", "Qty": 10.0, "Avg Cost": 415.00,
     "Current": 422.10, "Market Value": 4221.0, "Unreal. P&L": "+$71.00", "P&L %": "+1.71%"},
    {"Symbol": "BTC/USDT", "Class": "Crypto", "Qty": 0.05, "Avg Cost": 67500.0,
     "Current": 68200.0, "Market Value": 3410.0, "Unreal. P&L": "+$35.00", "P&L %": "+1.04%"},
])
st.dataframe(positions, use_container_width=True, hide_index=True)

# Allocation pie
col_pie, col_curve = st.columns(2)
with col_pie:
    st.subheader("Allocation")
    labels = ["Cash", "AAPL", "MSFT", "BTC/USDT"]
    values = [87_000, 4_630, 4_221, 3_410]
    fig = px.pie(names=labels, values=values, hole=0.4,
                 color_discrete_sequence=px.colors.sequential.Teal)
    fig.update_layout(height=300, template="plotly_dark", margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

with col_curve:
    st.subheader("Daily P&L History")
    rng = np.random.default_rng(7)
    daily_pnl = rng.normal(120, 400, 30)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq="D")
    colors = ["#00D4AA" if v > 0 else "#FF4444" for v in daily_pnl]
    fig = go.Figure(go.Bar(x=dates, y=daily_pnl, marker_color=colors))
    fig.update_layout(height=300, template="plotly_dark", margin=dict(l=0, r=0, t=10, b=0),
                      yaxis_tickprefix="$")
    st.plotly_chart(fig, use_container_width=True)

# Performance metrics
st.markdown("---")
st.subheader("Performance Metrics")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Sharpe Ratio", "1.42")
m2.metric("Sortino", "1.85")
m3.metric("Win Rate", "58.3%")
m4.metric("Profit Factor", "1.65")
m5.metric("Avg Win", "+2.1%")
m6.metric("Avg Loss", "-1.3%")
