"""Strategy Agent — selects and scores multiple strategies based on regime."""
from __future__ import annotations

from typing import Dict, List

from services.agents.base_agent import AgentOutput, BaseAgent


_STRATEGIES = {
    "trend_following": {
        "description": "Ride the trend until it bends",
        "favorable_regime": ["UPTREND", "RISK_ON"],
        "unfavorable_regime": ["HIGH_VOLATILITY", "DOWNTREND"],
    },
    "mean_reversion": {
        "description": "Fade extremes back to mean",
        "favorable_regime": ["NEUTRAL", "LOW_VOLATILITY"],
        "unfavorable_regime": ["TRENDING"],
    },
    "momentum": {
        "description": "Buy recent winners, short losers",
        "favorable_regime": ["UPTREND", "RISK_ON"],
        "unfavorable_regime": ["VOLATILE"],
    },
    "breakout": {
        "description": "Enter on volume-confirmed breakouts",
        "favorable_regime": ["SQUEEZE_BREAKOUT"],
        "unfavorable_regime": ["BEAR"],
    },
    "news_event": {
        "description": "Capitalize on high-impact news events",
        "favorable_regime": ["ANY"],
        "unfavorable_regime": [],
    },
    "crypto_momentum": {
        "description": "Crypto-specific momentum / reversal",
        "favorable_regime": ["CRYPTO_BULL"],
        "unfavorable_regime": ["CRYPTO_BEAR"],
    },
}


class StrategyAgent(BaseAgent):
    name = "StrategyAgent"

    def _analyze(
        self,
        symbol: str,
        agent_outputs: Dict[str, AgentOutput] = None,
        features=None,
        **kwargs,
    ) -> AgentOutput:  # type: ignore[override]
        if agent_outputs is None:
            agent_outputs = {}

        md = agent_outputs.get("MarketDataAgent")
        macro = agent_outputs.get("MacroAgent")
        crypto = agent_outputs.get("CryptoMicrostructureAgent")

        # Determine active regime signals
        regime_tags: list[str] = []
        if md:
            regime_tags.append(md.metadata.get("trend_label", "NEUTRAL"))
            if md.metadata.get("atr_pct", 0) > 3:
                regime_tags.append("HIGH_VOLATILITY")
            if md.metadata.get("bb_squeeze") == "SQUEEZE_BREAKOUT":
                regime_tags.append("SQUEEZE_BREAKOUT")
        if macro:
            regime_tags.append(macro.metadata.get("regime", "NEUTRAL"))
        if crypto:
            regime_tags.append("CRYPTO_BULL" if crypto.signal_type == "BUY" else "CRYPTO_BEAR")

        # Score strategies
        strategy_scores: Dict[str, float] = {}
        for strat_name, strat in _STRATEGIES.items():
            score = 0.0
            for tag in regime_tags:
                if tag in strat["favorable_regime"] or "ANY" in strat["favorable_regime"]:
                    score += 20
                if tag in strat["unfavorable_regime"]:
                    score -= 15
            strategy_scores[strat_name] = max(0.0, score)

        best_strategy = max(strategy_scores, key=lambda k: strategy_scores[k])
        best_score = strategy_scores[best_strategy]

        # Aggregate signal direction from all agent outputs
        buy_votes = sum(1 for o in agent_outputs.values() if o.signal_type == "BUY")
        sell_votes = sum(1 for o in agent_outputs.values() if o.signal_type == "SELL")
        total_votes = max(1, len(agent_outputs))

        if buy_votes / total_votes > 0.55:
            signal_type = "BUY"
            confidence = min(85.0, 40 + buy_votes / total_votes * 60 + best_score * 0.3)
        elif sell_votes / total_votes > 0.55:
            signal_type = "SELL"
            confidence = min(85.0, 40 + sell_votes / total_votes * 60 + best_score * 0.3)
        else:
            signal_type = "HOLD"
            confidence = 40.0

        avg_risk = sum(o.risk_score for o in agent_outputs.values()) / max(1, len(agent_outputs))

        active_strategies = [k for k, v in strategy_scores.items() if v > 30]

        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            timeframe=kwargs.get("timeframe", "1d"),
            signal_type=signal_type,
            confidence=confidence,
            risk_score=min(100.0, avg_risk),
            thesis=(
                f"Strategy selection for {symbol}: active strategies={active_strategies}, "
                f"best={best_strategy} (score={best_score:.0f}), "
                f"votes: BUY={buy_votes} SELL={sell_votes} out of {total_votes} agents"
            ),
            supporting_signals=[
                f"Best strategy: {best_strategy} — {_STRATEGIES[best_strategy]['description']}",
                f"Agent consensus: {buy_votes}/{total_votes} BUY votes",
            ],
            contradicting_signals=[
                f"Sell votes: {sell_votes}/{total_votes}",
            ] if sell_votes > 0 else [],
            metadata={
                "strategy_scores": {k: round(v, 1) for k, v in strategy_scores.items()},
                "best_strategy": best_strategy,
                "active_strategies": active_strategies,
                "regime_tags": regime_tags,
                "buy_votes": buy_votes,
                "sell_votes": sell_votes,
                "total_agents": total_votes,
            },
        )
