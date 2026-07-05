"""Risk Agent — veto authority. Enforces all risk limits before any order is proposed."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from libs.common.config import settings
from libs.common.constants import RISK_APPROVED, RISK_REJECTED, RISK_REDUCE
from services.agents.base_agent import AgentOutput, BaseAgent


@dataclass
class RiskVerdict:
    verdict: str           # APPROVED / REJECTED / REDUCE_SIZE
    reasons: List[str]
    adjusted_size_pct: Optional[float] = None
    kill_switch_triggered: bool = False


class RiskAgent(BaseAgent):
    name = "RiskAgent"

    def _analyze(self, symbol: str, **kwargs) -> AgentOutput:  # type: ignore[override]
        verdict = self.evaluate(
            symbol=symbol,
            proposed_size_pct=kwargs.get("proposed_size_pct", 0.02),
            agent_outputs=kwargs.get("agent_outputs", {}),
            portfolio_state=kwargs.get("portfolio_state", {}),
            features=kwargs.get("features"),
        )
        signal_type = "HOLD" if verdict.verdict in (RISK_REJECTED, RISK_REDUCE) else "BUY"
        risk_score = 80.0 if verdict.verdict == RISK_REJECTED else 40.0

        return AgentOutput(
            agent_name=self.name, symbol=symbol,
            timeframe=kwargs.get("timeframe", "1d"),
            signal_type=signal_type,
            confidence=90.0,
            risk_score=risk_score,
            thesis=f"Risk verdict: {verdict.verdict}. Reasons: {'; '.join(verdict.reasons)}",
            supporting_signals=verdict.reasons if verdict.verdict == RISK_APPROVED else [],
            contradicting_signals=verdict.reasons if verdict.verdict != RISK_APPROVED else [],
            metadata={"verdict": verdict.verdict, "reasons": verdict.reasons,
                      "adjusted_size_pct": verdict.adjusted_size_pct},
        )

    def evaluate(
        self,
        symbol: str,
        proposed_size_pct: float,
        agent_outputs: Dict[str, AgentOutput] = None,
        portfolio_state: dict = None,
        features=None,
    ) -> RiskVerdict:
        if agent_outputs is None:
            agent_outputs = {}
        if portfolio_state is None:
            portfolio_state = {}

        reasons: list[str] = []
        approved = True
        adjusted_size = proposed_size_pct

        # ── Kill switch check ─────────────────────────────────────────────
        if settings.KILL_SWITCH_ENABLED:
            return RiskVerdict(
                verdict=RISK_REJECTED,
                reasons=["KILL SWITCH is active — all new orders blocked."],
                kill_switch_triggered=True,
            )

        # ── Live trading guard ────────────────────────────────────────────
        if settings.LIVE_TRADING_ENABLED:
            reasons.append("WARN: Live trading is enabled — paper mode override not active.")

        # ── Position size limit ───────────────────────────────────────────
        max_pos = settings.MAX_POSITION_SIZE_PCT
        if proposed_size_pct > max_pos:
            adjusted_size = max_pos
            reasons.append(f"Position capped at {max_pos*100:.1f}% (requested {proposed_size_pct*100:.1f}%)")

        # ── Max daily loss ────────────────────────────────────────────────
        daily_pnl_pct = portfolio_state.get("daily_pnl_pct", 0.0)
        if daily_pnl_pct < -settings.MAX_DAILY_LOSS_PCT:
            approved = False
            reasons.append(
                f"Daily loss limit reached: {daily_pnl_pct*100:.1f}% < -{settings.MAX_DAILY_LOSS_PCT*100:.1f}%"
            )

        # ── Max drawdown circuit breaker ──────────────────────────────────
        drawdown = portfolio_state.get("drawdown_pct", 0.0)
        if drawdown > settings.MAX_DRAWDOWN_PCT:
            approved = False
            reasons.append(
                f"Max drawdown breached: {drawdown*100:.1f}% > {settings.MAX_DRAWDOWN_PCT*100:.1f}%"
            )

        # ── Cash minimum ─────────────────────────────────────────────────
        cash_pct = portfolio_state.get("cash_pct", 1.0)
        if cash_pct - adjusted_size < settings.MIN_CASH_PCT:
            required_reduction = cash_pct - settings.MIN_CASH_PCT
            if required_reduction <= 0:
                approved = False
                reasons.append(f"Insufficient cash: {cash_pct*100:.1f}% available, need >{settings.MIN_CASH_PCT*100:.1f}%")
            else:
                adjusted_size = required_reduction
                reasons.append(f"Size reduced to preserve {settings.MIN_CASH_PCT*100:.1f}% cash floor")

        # ── High volatility filter ────────────────────────────────────────
        if features and features.volatility_regime == "HIGH":
            if adjusted_size > max_pos * 0.5:
                adjusted_size = max_pos * 0.5
                reasons.append(f"High volatility: position halved (ATR={features.atr_pct:.1f}%)")

        # ── High risk score aggregation ───────────────────────────────────
        if agent_outputs:
            avg_risk = sum(o.risk_score for o in agent_outputs.values()) / len(agent_outputs)
            if avg_risk > 75:
                approved = False
                reasons.append(f"Aggregate risk score too high: {avg_risk:.1f}/100")
            elif avg_risk > 60:
                adjusted_size = min(adjusted_size, max_pos * 0.5)
                reasons.append(f"Elevated risk score {avg_risk:.1f}: size halved")

        # ── Fat-finger limit ─────────────────────────────────────────────
        if adjusted_size > 0.20:
            approved = False
            reasons.append(f"Fat-finger: proposed size {adjusted_size*100:.1f}% exceeds 20% hard cap")

        if not reasons:
            reasons.append("All risk checks passed.")

        if not approved:
            return RiskVerdict(verdict=RISK_REJECTED, reasons=reasons)

        # Size was adjusted but approved
        if abs(adjusted_size - proposed_size_pct) > 0.001:
            return RiskVerdict(
                verdict=RISK_REDUCE, reasons=reasons, adjusted_size_pct=adjusted_size
            )

        return RiskVerdict(verdict=RISK_APPROVED, reasons=reasons, adjusted_size_pct=adjusted_size)
