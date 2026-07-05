"""Backtest Lab page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Backtest | OmniAlpha", page_icon="🧪", layout="wide")
st.title("🧪 Backtest Lab")

st.warning(
    "⚠️ **Backtesting caveats:** Results use simulated data and do NOT account for "
    "real market frictions, regulatory changes, or survivorship bias in full. "
    "Past simulated performance is NOT indicative of future results."
)

# Config
with st.form("backtest_form"):
    col1, col2, col3, col4 = st.columns(4)
    symbol = col1.selectbox("Symbol", ["AAPL", "MSFT", "GOOGL", "BTC/USDT", "SPY", "QQQ", "TSLA"])
    timeframe = col2.selectbox("Timeframe", ["1d", "4h", "1h"])
    bars = col3.number_input("Lookback Bars", min_value=50, max_value=2000, value=365, step=50)
    initial = col4.number_input("Initial Equity ($)", value=100_000, step=10_000)
    submitted = st.form_submit_button("▶ Run Backtest", use_container_width=True)

if submitted:
    with st.spinner(f"Backtesting {symbol} on {bars} bars..."):
        try:
            from services.backtest.engine import BacktestEngine
            engine = BacktestEngine(initial_equity=float(initial))
            result = engine.run(symbol=symbol, timeframe=timeframe, lookback_bars=int(bars))

            # KPIs
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Return", f"{result.total_return_pct:+.2f}%")
            c2.metric("Annualised", f"{result.annualized_return_pct:+.2f}%")
            c3.metric("Max Drawdown", f"-{result.max_drawdown_pct:.2f}%")
            c4.metric("Sharpe Ratio", f"{result.sharpe_ratio:.3f}")
            c5.metric("Win Rate", f"{result.win_rate_pct:.1f}%")

            c6, c7, c8 = st.columns(3)
            c6.metric("Total Trades", result.total_trades)
            c7.metric("Profit Factor", f"{result.profit_factor:.3f}")
            c8.metric("Final Equity", f"${result.final_equity:,.2f}")

            # Equity curve
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=result.dates, y=result.equity_curve,
                mode="lines", name="Equity",
                line=dict(color="#00D4AA", width=2),
                fill="tozeroy", fillcolor="rgba(0,212,170,0.08)",
            ))
            fig.add_hline(y=float(initial), line_dash="dash", line_color="gray")
            fig.update_layout(
                title=f"Equity Curve — {symbol}", height=350,
                template="plotly_dark", yaxis_tickprefix="$",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Warnings
            for w in result.warnings:
                st.warning(f"⚠️ {w}")

            # Trade log
            if result.trades:
                st.subheader("Trade Log")
                import pandas as pd
                trade_rows = [
                    {
                        "Entry": t.entry_date.date() if t.entry_date else None,
                        "Exit": t.exit_date.date() if t.exit_date else None,
                        "Direction": t.direction,
                        "Entry Price": round(t.entry_price, 2),
                        "Exit Price": round(t.exit_price, 2) if t.exit_price else None,
                        "P&L": f"${t.pnl:+.2f}",
                        "P&L %": f"{t.pnl_pct:+.2f}%",
                        "Exit Reason": t.exit_reason,
                        "Strategy": t.strategy,
                    }
                    for t in result.trades
                ]
                st.dataframe(pd.DataFrame(trade_rows), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Backtest error: {e}")
