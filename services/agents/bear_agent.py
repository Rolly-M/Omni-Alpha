"""Bear Agent — constructs the strongest possible case AGAINST a trade."""
from __future__ import annotations

from typing import Dict

from services.agents.base_agent import AgentOutput, BaseAgent


class BearAgent(BaseAgent):
    name = "BearAgent"

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

        all_risks: list[str] = []
        risk_sum = 0.0
        sell_count = 0
        n_agents = max(1, len(agent_outputs))

        for name, out in agent_outputs.items():
            risk_sum += out.risk_score
            all_risks.extend(out.contradicting_signals)
            if out.signal_type == "SELL":
                sell_count += 1

        avg_risk = risk_sum / n_agents

        # Downside estimation
        downside_pct = 0.0
        if features:
            if features.volatility_regime == "HIGH":
                downside_pct += features.atr_pct * 5
            if features.rsi_14 > 70:
                downside_pct += 8.0
            if features.trend_label == "DOWNTREND":
                downside_pct += 12.0
            downside_pct += abs(features.return_20d) * 0.3 if features.return_20d < 0 else 3.0

        downside_pct = max(3.0, min(40.0, downside_pct + avg_risk * 0.1))
        stop_loss = entry_price * (1 - downside_pct / 100 * 0.5) if entry_price > 0 else 0

        top_risks = sorted(set(all_risks), key=len)[:5]
        if not top_risks:
            top_risks = [
                "No trade is without risk — execution cost and timing uncertainty",
                "Market conditions can change faster than analysis",
            ]

        thesis = (
            f"BEAR CASE for {symbol}: "
            f"{sell_count}/{n_agents} agents are bearish. "
            f"Estimated downside: -{downside_pct:.1f}%. "
            f"Avg risk score across agents: {avg_risk:.1f}/100. "
            f"Key risk: {top_risks[0] if top_risks else 'elevated uncertainty'}."
        )

        confidence = min(85.0, avg_risk * 0.6 + sell_count / n_agents * 40)

        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            timeframe=kwargs.get("timeframe", "1d"),
            signal_type="SELL",
            confidence=confidence,
            risk_score=avg_risk,
            thesis=thesis,
            supporting_signals=top_risks,     # "supporting" for the BEAR case
            contradicting_signals=[],
            metadata={
                "downside_pct": round(downside_pct, 1),
                "suggested_stop": round(stop_loss, 2),
                "bearish_agents": sell_count,
                "total_agents": n_agents,
                "avg_risk_score": round(avg_risk, 1),
            },
        )
