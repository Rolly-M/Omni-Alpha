"""Reflection Agent — reviews past decisions, scores agent accuracy, learns lessons."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from services.agents.base_agent import AgentOutput, BaseAgent


class ReflectionAgent(BaseAgent):
    """Periodically reviews completed trades and measures which agents contributed
    to good/bad outcomes. Writes lessons to the audit log but never auto-deploys
    parameter changes without human approval.
    """
    name = "ReflectionAgent"

    def _analyze(self, symbol: str, **kwargs) -> AgentOutput:  # type: ignore[override]
        completed_trades = kwargs.get("completed_trades", [])
        return self.reflect(completed_trades)

    def reflect(self, completed_trades: List[dict]) -> AgentOutput:
        if not completed_trades:
            return AgentOutput(
                agent_name=self.name, symbol="PORTFOLIO", timeframe="reflection",
                signal_type="NEUTRAL", confidence=60.0, risk_score=20.0,
                thesis="No completed trades to review yet.",
            )

        agent_pnl_contribution: Dict[str, float] = {}
        winning_trades = 0
        losing_trades = 0
        total_pnl = 0.0

        for trade in completed_trades:
            pnl_pct = trade.get("pnl_pct", 0.0)
            total_pnl += pnl_pct
            if pnl_pct > 0:
                winning_trades += 1
            else:
                losing_trades += 1

            # Attribute contribution
            for agent_name, conf in trade.get("agent_confidences", {}).items():
                signal = trade.get("agent_signals", {}).get(agent_name, "HOLD")
                trade_direction = trade.get("direction", "BUY")
                # If agent agreed with profitable trade: positive contribution
                contribution = 0.0
                if signal == trade_direction:
                    contribution = pnl_pct * (conf / 100)
                else:
                    contribution = -pnl_pct * (conf / 100) * 0.5

                agent_pnl_contribution[agent_name] = (
                    agent_pnl_contribution.get(agent_name, 0.0) + contribution
                )

        win_rate = winning_trades / max(1, len(completed_trades)) * 100
        avg_pnl = total_pnl / max(1, len(completed_trades))

        # Top contributing and worst agents
        sorted_agents = sorted(agent_pnl_contribution.items(), key=lambda x: x[1], reverse=True)
        top_agents = [f"{name}: +{v:.2f}%" for name, v in sorted_agents[:3] if v > 0]
        poor_agents = [f"{name}: {v:.2f}%" for name, v in sorted_agents if v < 0]

        lessons: list[str] = []
        if win_rate < 40:
            lessons.append("Win rate below 40%: review entry criteria and trend filters")
        if poor_agents:
            lessons.append(f"Agents to review: {', '.join([a.split(':')[0] for a in poor_agents[:2]])}")
        if avg_pnl > 0:
            lessons.append(f"Positive avg P&L {avg_pnl:.2f}%: current approach is working")

        return AgentOutput(
            agent_name=self.name, symbol="PORTFOLIO", timeframe="reflection",
            signal_type="NEUTRAL",
            confidence=70.0,
            risk_score=20.0,
            thesis=(
                f"Reflection over {len(completed_trades)} trades: "
                f"win_rate={win_rate:.1f}%, avg_pnl={avg_pnl:.2f}%. "
                f"Lessons: {lessons[0] if lessons else 'No critical issues found.'}"
            ),
            supporting_signals=top_agents or ["No completed winning trades yet"],
            contradicting_signals=poor_agents[:3],
            metadata={
                "total_trades": len(completed_trades),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 1),
                "avg_pnl_pct": round(avg_pnl, 3),
                "agent_contributions": {k: round(v, 3) for k, v in sorted_agents},
                "lessons": lessons,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
