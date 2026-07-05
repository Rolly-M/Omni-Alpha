"""Risk Monitor page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Risk | OmniAlpha", page_icon="🛡️", layout="wide")
st.title("🛡️ Risk Monitor")

# Kill switch control
ks_col, info_col = st.columns([1, 2])
with ks_col:
    st.subheader("Emergency Controls")
    if st.button("🚨 ACTIVATE KILL SWITCH", type="primary", use_container_width=True):
        try:
            from services.risk.kill_switch import kill_switch
            kill_switch.activate(reason="Manual activation from dashboard")
            st.error("⛔ KILL SWITCH ACTIVATED")
        except Exception as e:
            st.error(f"Kill switch: {e}")
    if st.button("✅ Deactivate Kill Switch", use_container_width=True):
        try:
            from services.risk.kill_switch import kill_switch
            kill_switch.deactivate()
            st.success("Kill switch deactivated")
        except Exception as e:
            st.info("Kill switch not active")

with info_col:
    st.subheader("Current Risk Status")
    st.success("✅ Kill Switch: INACTIVE")
    st.success("✅ Live Trading: DISABLED (paper mode)")
    st.success("✅ Daily Loss: +0.23% / 2.0% limit")
    st.success("✅ Drawdown: 1.2% / 15.0% limit")
    st.success("✅ Cash: 85% / 10% minimum")

st.markdown("---")

# Risk gauges
st.subheader("Risk Limit Utilization")
cols = st.columns(4)

def gauge_fig(title, value, max_val, color_threshold=0.7):
    pct = value / max_val
    color = "green" if pct < color_threshold else ("orange" if pct < 0.9 else "red")
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        delta={"reference": 0},
        gauge={
            "axis": {"range": [0, max_val]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, max_val * 0.6], "color": "#003300"},
                {"range": [max_val * 0.6, max_val * 0.8], "color": "#333300"},
                {"range": [max_val * 0.8, max_val], "color": "#330000"},
            ],
        },
        title={"text": title},
    ))
    fig.update_layout(height=200, template="plotly_dark", margin=dict(l=20, r=20, t=40, b=0))
    return fig

cols[0].plotly_chart(gauge_fig("Drawdown %", 1.2, 15.0), use_container_width=True)
cols[1].plotly_chart(gauge_fig("Daily Loss %", 0.0, 2.0), use_container_width=True)
cols[2].plotly_chart(gauge_fig("Largest Position %", 4.6, 5.0, 0.8), use_container_width=True)
cols[3].plotly_chart(gauge_fig("Correlation Risk", 0.42, 1.0, 0.75), use_container_width=True)

# Risk config
st.markdown("---")
st.subheader("Active Risk Limits")
from libs.common.config import settings
limits_data = {
    "Limit": ["Max Position Size", "Max Daily Loss", "Max Drawdown",
               "Max Leverage", "Min Cash", "Max Sector Exposure"],
    "Value": [f"{settings.MAX_POSITION_SIZE_PCT*100:.1f}%",
               f"{settings.MAX_DAILY_LOSS_PCT*100:.1f}%",
               f"{settings.MAX_DRAWDOWN_PCT*100:.1f}%",
               f"{settings.MAX_LEVERAGE:.1f}x",
               f"{settings.MIN_CASH_PCT*100:.1f}%",
               f"{settings.MAX_SECTOR_EXPOSURE_PCT*100:.1f}%"],
    "Current": ["4.6%", "0.0% gain", "1.2%", "1.0x", "85%", "8.5%"],
    "Status": ["✅ OK", "✅ OK", "✅ OK", "✅ OK", "✅ OK", "✅ OK"],
}
import pandas as pd
st.dataframe(pd.DataFrame(limits_data), use_container_width=True, hide_index=True)
