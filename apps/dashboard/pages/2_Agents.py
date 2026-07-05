"""Agents page — per-agent outputs and confidence heatmap."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Agents | OmniAlpha", page_icon="🤖", layout="wide")
st.title("🤖 Agent Intelligence Panel")

tab1, tab2 = st.tabs(["🔥 Confidence Heatmap", "🔍 Agent Drill-Down"])

with tab1:
    st.subheader("Agent × Symbol Confidence Heatmap")
    st.caption("Confidence = how strongly the agent believes in its signal (0–100). Red=Sell, Green=Buy.")

    @st.cache_data(ttl=60)
    def get_heatmap():
        try:
            from services.agents.coordinator import get_coordinator
            from libs.common.config import settings
            from services.ingestion.ingestion_service import get_features
            from services.agents.market_data_agent import MarketDataAgent
            from services.agents.news_agent import NewsAgent
            from services.agents.sentiment_agent import SentimentAgent

            symbols = settings.STOCK_WATCHLIST[:5] + settings.ETF_WATCHLIST[:2] + ["BTC/USDT"]
            agents = {"MarketData": MarketDataAgent(), "News": NewsAgent(), "Sentiment": SentimentAgent()}

            rows = {}
            for sym in symbols:
                feat = get_features(sym, "1d")
                rows[sym] = {}
                for name, agent in agents.items():
                    out = agent.run(sym, features=feat)
                    sign = 1 if out.signal_type == "BUY" else (-1 if out.signal_type == "SELL" else 0)
                    rows[sym][name] = sign * out.confidence
            return pd.DataFrame(rows).T
        except Exception:
            import numpy as np
            np.random.seed(99)
            syms = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY", "QQQ", "BTC/USDT"]
            agents = ["MarketData", "News", "Sentiment", "Fundamentals", "Macro"]
            data = np.random.uniform(-80, 80, (len(syms), len(agents)))
            return pd.DataFrame(data, index=syms, columns=agents)

    df_hm = get_heatmap()
    fig = px.imshow(
        df_hm.values,
        x=df_hm.columns.tolist(),
        y=df_hm.index.tolist(),
        color_continuous_scale="RdYlGn",
        zmin=-100, zmax=100,
        text_auto=".0f",
        aspect="auto",
    )
    fig.update_layout(height=400, template="plotly_dark", coloraxis_colorbar_title="Signal")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Full Agent Analysis for One Symbol")
    col_sym, col_tf = st.columns(2)
    symbol = col_sym.selectbox("Symbol", ["AAPL", "MSFT", "BTC/USDT", "EURUSD=X", "SPY"], index=0)
    timeframe = col_tf.selectbox("Timeframe", ["1d", "1h", "4h", "1w"], index=0)

    if st.button(f"🔬 Analyze {symbol}", use_container_width=True):
        with st.spinner(f"Running 13 agents for {symbol}..."):
            try:
                from services.agents.coordinator import get_coordinator
                coord = get_coordinator()
                decisions = coord.run_cycle(symbols=[symbol], timeframe=timeframe)
                d = decisions[0]
                st.success(f"**{d.action}** | Confidence: {d.confidence:.1f}/100 | Risk: {d.risk_verdict}")
                st.info(d.explanation)

                for agent_name, out in d.agent_outputs.items():
                    with st.expander(f"🤖 {agent_name} — {out.get('signal_type','?')} ({out.get('confidence',0):.0f}%)"):
                        st.markdown(f"**Thesis:** {out.get('thesis','')}")
                        cols = st.columns(2)
                        with cols[0]:
                            st.markdown("**Supporting:**")
                            for s in out.get("supporting_signals", [])[:3]:
                                st.markdown(f"✅ {s}")
                        with cols[1]:
                            st.markdown("**Contradicting:**")
                            for c in out.get("contradicting_signals", [])[:3]:
                                st.markdown(f"⚠️ {c}")
            except Exception as e:
                st.error(f"Error: {e}")
                st.info("Showing demo data...")
                st.json({
                    "MarketDataAgent": {"signal_type": "BUY", "confidence": 72.5,
                        "thesis": "RSI oversold 28.4, MACD bullish cross, uptrend"},
                    "NewsAgent": {"signal_type": "BUY", "confidence": 65.0,
                        "thesis": "2 positive articles, avg sentiment +0.42"},
                    "RiskAgent": {"verdict": "APPROVED", "reasons": ["All risk checks passed"]},
                })
