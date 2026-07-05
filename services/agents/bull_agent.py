"""Bull Agent — constructs the strongest possible case FOR a trade."""
from __future__ import annotations

from typing import Dict, List

from services.agents.base_agent import AgentOutput, BaseAgent


class BullAgent(BaseAgent):
    name = "BullAgent"

    def _analyze(
        self,
        symbol: str,
        agent_outputs: Dict[str, AgentOutput] = None,
        features=None,
        entry_price: float = 0.0,
        **kwargs,
    ) -> AgentOutput:  # type: ignore[override]
        if agent_outputs is None:
            agent_outputs = {}

        # Gather all bull evidence from analyst agents
        all_supporting: list[str] = []
        confidence_sum = 0.0
        buy_confidence_sum = 0.0
        buy_count = 0

        for name, out in agent_outputs.items():
            if out.signal_type in ("BUY", "NEUTRAL") and out.confidence > 40:
                all_supporting.extend(out.supporting_signals)
                confidence_sum += out.confidence
                if out.signal_type == "BUY":
                    buy_confidence_sum += out.confidence
                    buy_count += 1

        # Price targets based on features
        upside_pct = 0.0
        if features:
            # Target: at least to 52-week high, or 10% if near high
            if features.pct_from_52w_high < -10:
                upside_pct = abs(features.pct_from_52w_high)
            else:
                upside_pct = 10.0
            # Extra upside from momentum
            if features.return_20d > 0:
                upside_pct += features.return_20d * 0.5

        upside_pct = min(50.0, max(5.0, upside_pct))
        price_target = entry_price * (1 + upside_pct / 100) if entry_price > 0 else 0

        # Build bull thesis
        n_agents = max(1, len(agent_outputs))
        avg_bull_confidence = buy_confidence_sum / max(1, buy_count)
        top_signals = sorted(set(all_supporting), key=len)[:5]

        if not top_signals:
            top_signals = ["Market regime supports this trade", "Risk/reward profile is acceptable"]

        thesis = (
            f"BULL CASE for {symbol}: "
            f"{buy_count}/{n_agents} agents are bullish. "
            f"Projected upside: +{upside_pct:.1f}% "
            f"({'target: $' + str(round(price_target, 2)) if price_target > 0 else ''}). "
            f"Strongest factors: {top_signals[0] if top_signals else 'multiple signals align'}."
        )

        # Bull confidence is capped at 85 — we never express 100% certainty
        confidence = min(85.0, avg_bull_confidence * 0.9 + buy_count / n_agents * 20)

        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            timeframe=kwargs.get("timeframe", "1d"),
            signal_type="BUY",
            confidence=confidence,
            risk_score=20.0,  # bull agent is inherently optimistic on risk
            thesis=thesis,
            supporting_signals=top_signals,
            contradicting_signals=[],
            metadata={
                "upside_pct": round(upside_pct, 1),
                "price_target": round(price_target, 2),
                "bullish_agents": buy_count,
                "total_agents": n_agents,
                "avg_bull_confidence": round(avg_bull_confidence, 1),
            },
        )
