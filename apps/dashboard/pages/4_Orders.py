"""Orders page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Orders | OmniAlpha", page_icon="📄", layout="wide")
st.title("📄 Order Book")
st.info("All orders are **paper orders** (is_paper=True). No real money is moved.")

status_filter = st.multiselect("Status Filter", ["FILLED", "PARTIAL_FILL", "REJECTED", "PENDING"],
                                default=["FILLED", "PARTIAL_FILL", "REJECTED"])

orders = pd.DataFrame([
    {"Order ID": "ord-001", "Symbol": "AAPL", "Side": "BUY", "Qty": 25.0,
     "Type": "MARKET", "Status": "FILLED", "Fill Price": 183.40, "Commission": 4.59,
     "Slippage": 0.92, "Paper": True, "Time": "2024-12-01 14:32"},
    {"Order ID": "ord-002", "Symbol": "MSFT", "Side": "BUY", "Qty": 10.0,
     "Type": "MARKET", "Status": "FILLED", "Fill Price": 415.10, "Commission": 4.15,
     "Slippage": 0.83, "Paper": True, "Time": "2024-12-02 09:45"},
    {"Order ID": "ord-003", "Symbol": "BTC/USDT", "Side": "BUY", "Qty": 0.05,
     "Type": "MARKET", "Status": "FILLED", "Fill Price": 67_500.0, "Commission": 3.38,
     "Slippage": 16.88, "Paper": True, "Time": "2024-12-03 16:20"},
    {"Order ID": "ord-004", "Symbol": "NVDA", "Side": "BUY", "Qty": 5.0,
     "Type": "MARKET", "Status": "PARTIAL_FILL", "Fill Price": 895.0, "Commission": 2.24,
     "Slippage": 1.12, "Paper": True, "Time": "2024-12-04 10:05"},
    {"Order ID": "ord-005", "Symbol": "TSLA", "Side": "SELL", "Qty": 15.0,
     "Type": "MARKET", "Status": "REJECTED", "Fill Price": None, "Commission": 0,
     "Slippage": 0, "Paper": True, "Time": "2024-12-04 10:06"},
])

if status_filter:
    orders = orders[orders["Status"].isin(status_filter)]

def highlight_status(row):
    if row["Status"] == "FILLED":
        return ["background-color: #003300"] * len(row)
    elif row["Status"] == "REJECTED":
        return ["background-color: #440000"] * len(row)
    elif row["Status"] == "PARTIAL_FILL":
        return ["background-color: #333300"] * len(row)
    return [""] * len(row)

st.dataframe(orders.style.apply(highlight_status, axis=1), use_container_width=True, hide_index=True)

# Stats
total_commission = orders[orders["Status"].isin(["FILLED","PARTIAL_FILL"])]["Commission"].sum()
total_slippage = orders[orders["Status"].isin(["FILLED","PARTIAL_FILL"])]["Slippage"].sum()
c1, c2, c3 = st.columns(3)
c1.metric("Total Commission Paid", f"${total_commission:.2f}")
c2.metric("Total Slippage Cost", f"${total_slippage:.2f}")
c3.metric("Rejected Orders", len(orders[orders["Status"]=="REJECTED"]))
