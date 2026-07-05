"""Audit log page — immutable decision trail."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Audit | OmniAlpha", page_icon="📋", layout="wide")
st.title("📋 Immutable Audit Log")
st.caption("All agent decisions, orders, risk events, and system actions are logged here. Rows are never edited or deleted.")

# Filter controls
col1, col2, col3 = st.columns(3)
event_filter = col1.multiselect("Event Type", ["AGENT_SIGNAL", "RISK_APPROVED", "RISK_REJECTED",
    "ORDER_SUBMITTED", "ORDER_FILLED", "KILL_SWITCH_TRIGGERED", "CYCLE_STARTED", "CYCLE_COMPLETE"],
    default=[])
severity_filter = col2.multiselect("Severity", ["INFO", "WARN", "ERROR", "CRITICAL"], default=[])
symbol_filter = col3.text_input("Symbol (optional)")

audit_data = pd.DataFrame([
    {"Time": "2024-12-04 10:00:00", "Event": "CYCLE_STARTED", "Actor": "coordinator",
     "Symbol": "—", "Severity": "INFO", "Summary": "Analysis cycle started for 17 symbols"},
    {"Time": "2024-12-04 10:00:03", "Event": "AGENT_SIGNAL", "Actor": "MarketDataAgent",
     "Symbol": "AAPL", "Severity": "INFO", "Summary": "BUY signal — RSI=28.4 oversold, MACD bullish cross"},
    {"Time": "2024-12-04 10:00:03", "Event": "AGENT_SIGNAL", "Actor": "NewsAgent",
     "Symbol": "AAPL", "Severity": "INFO", "Summary": "BUY — 2 positive articles, sentiment=+0.42"},
    {"Time": "2024-12-04 10:00:04", "Event": "RISK_APPROVED", "Actor": "RiskAgent",
     "Symbol": "AAPL", "Severity": "INFO", "Summary": "APPROVED — all risk checks passed"},
    {"Time": "2024-12-04 10:00:04", "Event": "ORDER_SUBMITTED", "Actor": "ExecutionAgent",
     "Symbol": "AAPL", "Severity": "INFO", "Summary": "BUY 25 AAPL @ $183.40 paper order"},
    {"Time": "2024-12-04 10:00:05", "Event": "ORDER_FILLED", "Actor": "PaperBroker",
     "Symbol": "AAPL", "Severity": "INFO", "Summary": "BUY 25 AAPL filled @ $183.49 commission=$4.59"},
    {"Time": "2024-12-04 10:00:06", "Event": "RISK_REJECTED", "Actor": "RiskAgent",
     "Symbol": "TSLA", "Severity": "WARN", "Summary": "REJECTED — ATR=4.2% exceeds high-vol threshold"},
    {"Time": "2024-12-04 10:00:07", "Event": "AGENT_SIGNAL", "Actor": "CryptoMicrostructureAgent",
     "Symbol": "BTC/USDT", "Severity": "INFO", "Summary": "BUY — negative funding rate, exchange outflow bullish"},
    {"Time": "2024-12-04 10:00:10", "Event": "CYCLE_COMPLETE", "Actor": "coordinator",
     "Symbol": "—", "Severity": "INFO", "Summary": "Cycle: 3 BUY, 1 SELL, 13 HOLD, 2 REJECTED"},
])

# Apply filters
filtered = audit_data.copy()
if event_filter:
    filtered = filtered[filtered["Event"].isin(event_filter)]
if severity_filter:
    filtered = filtered[filtered["Severity"].isin(severity_filter)]
if symbol_filter:
    filtered = filtered[filtered["Symbol"].str.upper() == symbol_filter.upper()]

def color_severity(row):
    if row["Severity"] == "CRITICAL":
        return ["background-color: #550000"] * len(row)
    elif row["Severity"] == "WARN":
        return ["background-color: #333300"] * len(row)
    return [""] * len(row)

st.dataframe(
    filtered.style.apply(color_severity, axis=1),
    use_container_width=True, hide_index=True,
)

st.caption(f"Showing {len(filtered)} of {len(audit_data)} log entries")
