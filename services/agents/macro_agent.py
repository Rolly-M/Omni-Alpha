"""Macro Agent — rates, inflation, central bank, risk-on/risk-off regime."""
from __future__ import annotations

import random
from datetime import datetime, timezone

from services.agents.base_agent import AgentOutput, BaseAgent

# Mock macro state (in live mode, fetch from FRED / alpha vantage / etc.)
def _get_mock_macro() -> dict:
    rng = random.Random(str(datetime.now(timezone.utc).date()))
    return {
        "fed_rate": 5.25 + rng.uniform(-0.25, 0.25),
        "cpi_yoy": 3.2 + rng.uniform(-0.5, 0.5),
        "unemployment": 3.9 + rng.uniform(-0.3, 0.3),
        "vix": 14 + rng.uniform(-3, 12),
        "dxy": 104 + rng.uniform(-2, 2),
        "10y_yield": 4.3 + rng.uniform(-0.3, 0.3),
        "yield_curve_spread": 0.2 + rng.uniform(-0.5, 0.5),   # 10Y - 2Y
        "pmi": 50 + rng.uniform(-4, 6),
        "oil_price": 78 + rng.uniform(-10, 10),
    }


class MacroAgent(BaseAgent):
    name = "MacroAgent"

    def _analyze(self, symbol: str, **kwargs) -> AgentOutput:  # type: ignore[override]
        m = _get_mock_macro()
        bull_score = 0.0
        bear_score = 0.0
        supporting: list[str] = []
        contradicting: list[str] = []

        # VIX — fear gauge
        if m["vix"] < 15:
            bull_score += 20
            supporting.append(f"Low volatility environment: VIX={m['vix']:.1f}")
        elif m["vix"] > 25:
            bear_score += 25
            contradicting.append(f"Elevated fear: VIX={m['vix']:.1f}")

        # Yield curve
        if m["yield_curve_spread"] > 0:
            bull_score += 15
            supporting.append(f"Normal yield curve: spread=+{m['yield_curve_spread']:.2f}%")
        else:
            bear_score += 20
            contradicting.append(f"Inverted yield curve: spread={m['yield_curve_spread']:.2f}%")

        # CPI
        if m["cpi_yoy"] < 2.5:
            bull_score += 15
            supporting.append(f"CPI near target: {m['cpi_yoy']:.1f}%")
        elif m["cpi_yoy"] > 4.5:
            bear_score += 20
            contradicting.append(f"Elevated inflation: CPI {m['cpi_yoy']:.1f}%")

        # PMI
        if m["pmi"] > 52:
            bull_score += 15
            supporting.append(f"Expanding PMI: {m['pmi']:.1f}")
        elif m["pmi"] < 48:
            bear_score += 15
            contradicting.append(f"Contracting PMI: {m['pmi']:.1f}")

        # Fed rate — high rates pressure equities
        if m["fed_rate"] > 5.0:
            bear_score += 10
            contradicting.append(f"High Fed funds rate: {m['fed_rate']:.2f}%")

        net = bull_score - bear_score
        if net > 20:
            regime = "RISK_ON"
            signal_type = "BUY"
            confidence = min(75.0, 45 + net * 0.7)
        elif net < -20:
            regime = "RISK_OFF"
            signal_type = "SELL"
            confidence = min(75.0, 45 + abs(net) * 0.7)
        else:
            regime = "NEUTRAL"
            signal_type = "HOLD"
            confidence = 45.0

        risk_score = 20 + (m["vix"] - 12) * 2 + (20 if m["yield_curve_spread"] < 0 else 0)

        return AgentOutput(
            agent_name=self.name, symbol=symbol, timeframe="macro",
            signal_type=signal_type,
            confidence=confidence,
            risk_score=min(100.0, risk_score),
            thesis=(
                f"Macro backdrop for {symbol}: VIX={m['vix']:.1f}, "
                f"10Y={m['10y_yield']:.2f}%, CPI={m['cpi_yoy']:.1f}%, "
                f"PMI={m['pmi']:.1f}, regime={regime}"
            ),
            supporting_signals=supporting,
            contradicting_signals=contradicting,
            metadata={**m, "regime": regime},
        )
