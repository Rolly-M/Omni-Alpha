"""Crypto Microstructure Agent — funding, open interest, on-chain proxies."""
from __future__ import annotations

import random
from datetime import datetime, timezone

from libs.common.constants import ASSET_CRYPTO
from services.agents.base_agent import AgentOutput, BaseAgent


def _mock_crypto_data(symbol: str) -> dict:
    rng = random.Random(symbol + str(datetime.now(timezone.utc).date()))
    return {
        "funding_rate": rng.uniform(-0.03, 0.05),      # % per 8h
        "open_interest_change_24h": rng.uniform(-15, 20),   # %
        "long_short_ratio": rng.uniform(0.8, 2.5),
        "stablecoin_inflow": rng.uniform(-5, 15),      # % change
        "exchange_netflow": rng.uniform(-8, 8),        # negative = more leaving exchange (bullish)
        "fear_greed_index": rng.randint(20, 85),       # 0=fear, 100=greed
        "dominance_btc": rng.uniform(48, 58),          # BTC market cap dominance %
    }


class CryptoMicrostructureAgent(BaseAgent):
    name = "CryptoMicrostructureAgent"

    def _analyze(self, symbol: str, asset_class: str = "crypto", **kwargs) -> AgentOutput:  # type: ignore[override]
        if asset_class != ASSET_CRYPTO and "USDT" not in symbol and "BTC" not in symbol:
            return AgentOutput(
                agent_name=self.name, symbol=symbol, timeframe="microstructure",
                signal_type="NEUTRAL", confidence=40.0, risk_score=20.0,
                thesis="Not a crypto asset — crypto microstructure analysis skipped.",
            )

        d = _mock_crypto_data(symbol)
        bull_score = 0.0
        bear_score = 0.0
        supporting: list[str] = []
        contradicting: list[str] = []

        # Funding rate: high positive = overleveraged longs (bearish)
        if d["funding_rate"] > 0.02:
            bear_score += 20
            contradicting.append(f"Elevated funding rate {d['funding_rate']:.3f}% — overleveraged longs")
        elif d["funding_rate"] < -0.01:
            bull_score += 15
            supporting.append(f"Negative funding rate {d['funding_rate']:.3f}% — shorts paying longs")

        # OI change
        if d["open_interest_change_24h"] > 10:
            if d["long_short_ratio"] > 1.5:
                bear_score += 15
                contradicting.append("OI surge with long crowding — squeeze risk")
            else:
                bull_score += 15
                supporting.append(f"Rising OI +{d['open_interest_change_24h']:.1f}% — fresh capital entering")

        # Exchange netflow: negative = coins leaving exchange = bullish
        if d["exchange_netflow"] < -4:
            bull_score += 20
            supporting.append(f"Exchange netflow negative: {d['exchange_netflow']:.1f}% (HODLing)")
        elif d["exchange_netflow"] > 4:
            bear_score += 20
            contradicting.append(f"Exchange inflow +{d['exchange_netflow']:.1f}% (selling pressure)")

        # Fear/greed
        if d["fear_greed_index"] < 25:
            bull_score += 20
            supporting.append(f"Fear & Greed: Extreme Fear ({d['fear_greed_index']}) — contrarian buy")
        elif d["fear_greed_index"] > 80:
            bear_score += 20
            contradicting.append(f"Fear & Greed: Extreme Greed ({d['fear_greed_index']}) — contrarian sell")

        net = bull_score - bear_score
        if net > 20:
            signal_type = "BUY"
            confidence = min(70.0, 40 + net * 0.8)
        elif net < -20:
            signal_type = "SELL"
            confidence = min(70.0, 40 + abs(net) * 0.8)
        else:
            signal_type = "HOLD"
            confidence = 40.0

        risk_score = 40 + abs(d["funding_rate"]) * 200 + (10 if d["open_interest_change_24h"] > 15 else 0)

        return AgentOutput(
            agent_name=self.name, symbol=symbol, timeframe="microstructure",
            signal_type=signal_type,
            confidence=confidence,
            risk_score=min(100.0, risk_score),
            thesis=(
                f"Crypto microstructure for {symbol}: "
                f"funding={d['funding_rate']:.3f}%, "
                f"OI_chg={d['open_interest_change_24h']:.1f}%, "
                f"FearGreed={d['fear_greed_index']}, "
                f"exchange_netflow={d['exchange_netflow']:.1f}%"
            ),
            supporting_signals=supporting,
            contradicting_signals=contradicting,
            metadata=d,
        )
