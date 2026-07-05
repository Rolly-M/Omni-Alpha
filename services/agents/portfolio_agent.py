"""Portfolio Manager Agent — allocates capital, sizes positions, manages cash."""
from __future__ import annotations

from typing import Dict, List

from libs.common.config import settings
from services.agents.base_agent import AgentOutput, BaseAgent


class PortfolioManagerAgent(BaseAgent):
    name = "PortfolioManagerAgent"

    def _analyze(self, symbol: str, **kwargs) -> AgentOutput:  # type: ignore[override]
        agent_outputs = kwargs.get("agent_outputs", {})
        portfolio_state = kwargs.get("portfolio_state", {})
        risk_verdict = kwargs.get("risk_verdict")
        features = kwargs.get("features")

        strategy_out = agent_outputs.get("StrategyAgent")
        bull_out = agent_outputs.get("BullAgent")
        bear_out = agent_outputs.get("BearAgent")

        if not strategy_out:
            return AgentOutput(
                agent_name=self.name, symbol=symbol, timeframe="portfolio",
                signal_type="HOLD", confidence=50.0, risk_score=50.0,
                thesis="No strategy signal available.",
            )

        signal_type = strategy_out.signal_type
        base_confidence = strategy_out.confidence

        if signal_type not in ("BUY", "SELL"):
            return AgentOutput(
                agent_name=self.name, symbol=symbol, timeframe="portfolio",
                signal_type="HOLD", confidence=50.0, risk_score=30.0,
                thesis=f"No actionable signal for {symbol} (strategy says {signal_type}).",
            )

        # ── Kelly-inspired position sizing ────────────────────────────────
        win_prob = base_confidence / 100
        bull_upside = bull_out.metadata.get("upside_pct", 10.0) if bull_out else 10.0
        bear_downside = bear_out.metadata.get("downside_pct", 8.0) if bear_out else 8.0

        if bear_downside > 0:
            odds = bull_upside / bear_downside
        else:
            odds = 2.0

        kelly_f = win_prob - (1 - win_prob) / max(odds, 0.1)
        kelly_f = max(0.0, kelly_f)
        half_kelly = kelly_f * 0.5   # conservative half-Kelly

        # Apply account type multiplier
        multipliers = {"conservative": 0.5, "balanced": 1.0, "aggressive": 1.5}
        account_mult = multipliers.get(settings.ACCOUNT_TYPE, 1.0)

        raw_size = half_kelly * account_mult
        capped_size = min(settings.MAX_POSITION_SIZE_PCT, max(0.005, raw_size))

        # Apply risk verdict adjustment
        if risk_verdict and risk_verdict.adjusted_size_pct is not None:
            capped_size = min(capped_size, risk_verdict.adjusted_size_pct)

        # Correlation adjustment: if heavily exposed to same sector, reduce
        sector_exposure = portfolio_state.get("sector_exposure", {})
        from libs.common.constants import SECTOR_MAP
        sector = SECTOR_MAP.get(symbol, "Unknown")
        if sector_exposure.get(sector, 0) > settings.MAX_SECTOR_EXPOSURE_PCT * 0.8:
            capped_size *= 0.5

        # Compute stop and target
        current_price = features.current_price if features else 0.0
        atr = features.atr_14 if features else current_price * 0.02
        stop_loss = current_price - 2 * atr if signal_type == "BUY" else current_price + 2 * atr
        take_profit = current_price + 3 * atr if signal_type == "BUY" else current_price - 3 * atr

        # Expected holding period
        tf = kwargs.get("timeframe", "1d")
        holding_map = {"1d": "2-5 days", "1h": "4-12 hours", "4h": "1-3 days", "1w": "2-6 weeks"}
        holding_period = holding_map.get(tf, "1-5 days")

        return AgentOutput(
            agent_name=self.name, symbol=symbol,
            timeframe=kwargs.get("timeframe", "1d"),
            signal_type=signal_type,
            confidence=base_confidence,
            risk_score=bear_out.risk_score if bear_out else 50.0,
            thesis=(
                f"Portfolio allocation for {symbol}: {signal_type} "
                f"size={capped_size*100:.2f}% of portfolio, "
                f"Kelly={kelly_f:.3f} (half={half_kelly:.3f}), "
                f"odds={odds:.2f}x, holding={holding_period}"
            ),
            supporting_signals=[
                f"Position size: {capped_size*100:.2f}% (Kelly-adjusted)",
                f"Stop loss: {stop_loss:.2f}",
                f"Take profit: {take_profit:.2f}",
            ],
            contradicting_signals=[],
            metadata={
                "position_size_pct": round(capped_size, 4),
                "kelly_fraction": round(kelly_f, 4),
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "holding_period": holding_period,
                "sector": sector,
                "win_probability": round(win_prob, 3),
                "expected_odds": round(odds, 2),
            },
        )
