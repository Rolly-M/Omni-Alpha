"""Sandbox script — simulates one full trading day with live output.

Run: python scripts/run_sandbox_day.py [--verbose]
"""
import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.common.config import settings
from libs.common.logger import configure_logging, get_logger
from services.agents.coordinator import Coordinator
from services.execution.paper_broker import PaperBroker

configure_logging()
log = get_logger("sandbox")


def run_sandbox(verbose: bool = False):
    print("\n" + "="*60)
    print("  OmniAlpha — Sandbox Trading Day Simulation")
    print("  ⚠  PAPER TRADING ONLY — No real money")
    print("="*60 + "\n")

    coordinator = Coordinator()
    broker = PaperBroker(partial_fill_probability=0.05)

    symbols = settings.STOCK_WATCHLIST[:4] + settings.CRYPTO_WATCHLIST[:2] + settings.FOREX_WATCHLIST[:1]
    portfolio_state = {
        "cash_pct": 0.85,
        "daily_pnl_pct": 0.0,
        "drawdown_pct": 0.0,
        "sector_exposure": {},
    }
    account_state = {
        "total_equity": settings.INITIAL_BALANCE,
        "current_price": {},
    }

    print(f"📊 Analysing {len(symbols)} instruments: {', '.join(symbols)}\n")

    # Run 3 cycles (morning, midday, close)
    sessions = ["09:30 (Open)", "12:00 (Midday)", "15:30 (Close)"]
    all_orders = []

    for session in sessions:
        print(f"\n{'─'*50}")
        print(f"🕐 Session: {session}")
        print("─"*50)

        decisions = coordinator.run_cycle(
            symbols=symbols,
            timeframe="1d",
            portfolio_state=portfolio_state,
            account_state=account_state,
        )

        orders_this_session = 0
        for d in decisions:
            status_icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(d.action, "⚪")
            verdict_icon = "✅" if d.risk_verdict == "APPROVED" else "❌"

            print(f"\n  {status_icon} {d.symbol:12} | {d.action:4} | Conf: {d.confidence:5.1f}% "
                  f"| Risk: {verdict_icon}{d.risk_verdict}")

            if verbose:
                print(f"     Thesis: {d.thesis[:80]}...")
                if d.supporting_signals:
                    print(f"     ✅ {d.supporting_signals[0][:70]}")
                if d.contradicting_signals:
                    print(f"     ⚠️  {d.contradicting_signals[0][:70]}")

            # Submit paper order for approved buy/sell signals
            if d.action in ("BUY", "SELL") and d.risk_verdict in ("APPROVED", "REDUCE_SIZE"):
                price = d.entry_price
                order_value = settings.INITIAL_BALANCE * d.position_size_pct
                qty = order_value / price if price > 0 else 0

                order = broker.submit(
                    symbol=d.symbol,
                    side=d.action,
                    quantity=qty,
                    market_price=price,
                    stop_loss=d.stop_loss,
                    take_profit=d.take_profit,
                )
                orders_this_session += 1
                all_orders.append(order)

                fill_icon = "📋" if order.status == "FILLED" else ("⚠️" if order.status == "PARTIAL_FILL" else "❌")
                print(f"     {fill_icon} Paper order: {order.status} "
                      f"{'@ $' + str(round(order.average_fill_price, 2)) if order.average_fill_price else '(rejected)'}"
                      f" | Commission: ${order.commission:.2f}")

        print(f"\n  📊 Session summary: {orders_this_session} orders submitted")
        time.sleep(0.5)  # Small pause between sessions

    # End of day summary
    print(f"\n{'='*60}")
    print("📈 END OF DAY SUMMARY")
    print("="*60)

    filled = [o for o in all_orders if o.status in ("FILLED", "PARTIAL_FILL")]
    rejected = [o for o in all_orders if o.status == "REJECTED"]
    total_commission = sum(o.commission for o in filled)
    total_slippage = sum(o.slippage for o in filled)

    print(f"  Total orders:      {len(all_orders)}")
    print(f"  Filled:            {len(filled)}")
    print(f"  Rejected:          {len(rejected)}")
    print(f"  Total commission:  ${total_commission:.2f}")
    print(f"  Total slippage:    ${total_slippage:.2f}")
    print(f"\n  ✅ Simulation complete. No real money used.")
    print(f"  📋 See the Audit Log for full decision trail.")
    print("="*60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniAlpha Sandbox Day")
    parser.add_argument("--verbose", action="store_true", help="Show agent thesis details")
    args = parser.parse_args()
    run_sandbox(verbose=args.verbose)
