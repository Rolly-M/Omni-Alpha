"""Execution Agent — translates portfolio decisions into paper orders."""
from __future__ import annotations

from datetime import datetime, timezone

from libs.common.config import settings
from libs.common.constants import ORDER_MARKET, SIDE_BUY, SIDE_SELL
from services.agents.base_agent import AgentOutput, BaseAgent


class ExecutionAgent(BaseAgent):
    name = "ExecutionAgent"

    def _analyze(self, symbol: str, **kwargs) -> AgentOutput:  # type: ignore[override]
        portfolio_out = kwargs.get("portfolio_out")
        account_state = kwargs.get("account_state", {})

        if not portfolio_out or portfolio_out.signal_type not in ("BUY", "SELL"):
            return AgentOutput(
                agent_name=self.name, symbol=symbol, timeframe="execution",
                signal_type="HOLD", confidence=100.0, risk_score=0.0,
                thesis="No actionable portfolio signal — no order submitted.",
            )

        meta = portfolio_out.metadata
        size_pct = meta.get("position_size_pct", 0.02)
        total_equity = account_state.get("total_equity", settings.INITIAL_BALANCE)
        current_price = account_state.get("current_price", {}).get(symbol, 100.0)

        order_value = total_equity * size_pct
        if current_price > 0:
            quantity = order_value / current_price
        else:
            quantity = 0.0

        side = SIDE_BUY if portfolio_out.signal_type == "BUY" else SIDE_SELL
        slippage = settings.SLIPPAGE_RATE
        commission = settings.COMMISSION_RATE

        # Simulate fill
        if side == SIDE_BUY:
            fill_price = current_price * (1 + slippage)
        else:
            fill_price = current_price * (1 - slippage)

        commission_amount = order_value * commission
        total_cost = order_value + commission_amount

        return AgentOutput(
            agent_name=self.name, symbol=symbol, timeframe="execution",
            signal_type=portfolio_out.signal_type,
            confidence=100.0,
            risk_score=0.0,
            thesis=(
                f"Paper order: {side} {quantity:.4f} {symbol} @ simulated fill {fill_price:.2f}, "
                f"total value ${order_value:.2f}, commission ${commission_amount:.2f}"
            ),
            supporting_signals=[
                f"Order type: {ORDER_MARKET}",
                f"Fill price (simulated): {fill_price:.2f}",
                f"Slippage: {slippage*100:.3f}%",
                f"Commission: ${commission_amount:.2f}",
            ],
            contradicting_signals=[],
            metadata={
                "side": side,
                "order_type": ORDER_MARKET,
                "quantity": round(quantity, 6),
                "estimated_fill_price": round(fill_price, 4),
                "order_value": round(order_value, 2),
                "commission": round(commission_amount, 2),
                "total_cost": round(total_cost, 2),
                "is_paper": True,
                "stop_loss": meta.get("stop_loss"),
                "take_profit": meta.get("take_profit"),
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
