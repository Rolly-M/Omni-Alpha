"""Fundamentals Agent — valuation, earnings, balance-sheet quality."""
from __future__ import annotations

import random
from datetime import datetime, timezone

from libs.common.constants import ASSET_CRYPTO, ASSET_FOREX, SECTOR_MAP
from services.agents.base_agent import AgentOutput, BaseAgent

# Static fundamental profiles for demo (real mode would call financials API)
_FUND_PROFILES: dict[str, dict] = {
    "AAPL": {"pe": 28.5, "pb": 45.0, "roe": 150.0, "debt_equity": 1.8, "revenue_growth": 4.5},
    "MSFT": {"pe": 35.0, "pb": 15.0, "roe": 42.0, "debt_equity": 0.4, "revenue_growth": 17.0},
    "GOOGL": {"pe": 26.0, "pb": 6.5, "roe": 25.0, "debt_equity": 0.1, "revenue_growth": 15.0},
    "AMZN": {"pe": 55.0, "pb": 8.0, "roe": 18.0, "debt_equity": 0.8, "revenue_growth": 12.0},
    "TSLA": {"pe": 65.0, "pb": 10.0, "roe": 18.0, "debt_equity": 0.2, "revenue_growth": 3.0},
    "NVDA": {"pe": 65.0, "pb": 35.0, "roe": 90.0, "debt_equity": 0.4, "revenue_growth": 122.0},
    "META": {"pe": 25.0, "pb": 7.0, "roe": 34.0, "debt_equity": 0.1, "revenue_growth": 27.0},
    "SPY": {"pe": 22.0, "pb": 4.5, "roe": 18.0, "debt_equity": 0.0, "revenue_growth": 8.0},
    "QQQ": {"pe": 30.0, "pb": 6.0, "roe": 20.0, "debt_equity": 0.0, "revenue_growth": 14.0},
}

_SECTOR_PE_MEDIANS: dict[str, float] = {
    "Technology": 28.0, "Communication Services": 20.0,
    "Consumer Discretionary": 30.0, "ETF": 22.0,
}


class FundamentalsAgent(BaseAgent):
    name = "FundamentalsAgent"

    def _analyze(self, symbol: str, **kwargs) -> AgentOutput:  # type: ignore[override]
        from libs.common.constants import SECTOR_MAP, ASSET_CRYPTO, ASSET_FOREX

        asset_class = kwargs.get("asset_class", "stock")
        if asset_class in (ASSET_CRYPTO, ASSET_FOREX):
            return AgentOutput(
                agent_name=self.name, symbol=symbol, timeframe="fundamental",
                signal_type="NEUTRAL", confidence=40.0, risk_score=30.0,
                thesis=f"Fundamental analysis not applicable for {asset_class} asset {symbol}.",
            )

        profile = _FUND_PROFILES.get(symbol)
        if profile is None:
            rng = random.Random(symbol)
            profile = {
                "pe": rng.uniform(15, 60),
                "pb": rng.uniform(1.5, 20),
                "roe": rng.uniform(8, 40),
                "debt_equity": rng.uniform(0.1, 2.0),
                "revenue_growth": rng.uniform(-5, 30),
            }

        sector = SECTOR_MAP.get(symbol, "Technology")
        sector_pe = _SECTOR_PE_MEDIANS.get(sector, 25.0)

        bull_score = 0.0
        bear_score = 0.0
        supporting: list[str] = []
        contradicting: list[str] = []

        # P/E vs sector
        if profile["pe"] < sector_pe * 0.85:
            bull_score += 20
            supporting.append(f"Undervalued vs sector: P/E {profile['pe']:.1f} < sector median {sector_pe:.1f}")
        elif profile["pe"] > sector_pe * 1.30:
            bear_score += 20
            contradicting.append(f"Premium valuation: P/E {profile['pe']:.1f} > 130% of sector median")

        # Revenue growth
        if profile["revenue_growth"] > 20:
            bull_score += 20
            supporting.append(f"Strong revenue growth: {profile['revenue_growth']:.1f}%")
        elif profile["revenue_growth"] < 0:
            bear_score += 20
            contradicting.append(f"Declining revenue: {profile['revenue_growth']:.1f}%")

        # ROE
        if profile["roe"] > 25:
            bull_score += 15
            supporting.append(f"High ROE: {profile['roe']:.1f}%")
        elif profile["roe"] < 10:
            bear_score += 15
            contradicting.append(f"Low ROE: {profile['roe']:.1f}%")

        # Leverage
        if profile["debt_equity"] > 2.0:
            bear_score += 15
            contradicting.append(f"High leverage: D/E {profile['debt_equity']:.1f}")
        elif profile["debt_equity"] < 0.3:
            bull_score += 10
            supporting.append(f"Clean balance sheet: D/E {profile['debt_equity']:.1f}")

        net = bull_score - bear_score
        if net > 15:
            signal_type = "BUY"
            confidence = min(75.0, 45 + net * 0.8)
        elif net < -15:
            signal_type = "SELL"
            confidence = min(75.0, 45 + abs(net) * 0.8)
        else:
            signal_type = "HOLD"
            confidence = 45.0

        return AgentOutput(
            agent_name=self.name, symbol=symbol, timeframe="fundamental",
            signal_type=signal_type,
            confidence=confidence,
            risk_score=min(80.0, 20 + bear_score * 0.6),
            thesis=(
                f"Fundamental review of {symbol} ({sector} sector): "
                f"P/E={profile['pe']:.1f}, ROE={profile['roe']:.1f}%, "
                f"RevGrowth={profile['revenue_growth']:.1f}%, D/E={profile['debt_equity']:.2f}"
            ),
            supporting_signals=supporting,
            contradicting_signals=contradicting,
            metadata={**profile, "sector": sector, "sector_pe": sector_pe},
        )
