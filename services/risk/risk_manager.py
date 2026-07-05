"""Global risk manager — monitors portfolio-level risk in real time."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from libs.common.config import settings
from libs.common.logger import get_logger

log = get_logger("risk_manager")


@dataclass
class RiskAlert:
    level: str           # INFO / WARN / CRITICAL
    code: str
    message: str
    value: float
    threshold: float
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RiskManager:
    """Portfolio-level risk monitoring. Emits alerts and can trigger circuit breakers."""

    def __init__(self):
        self._alerts: List[RiskAlert] = []

    def check_portfolio(
        self,
        total_equity: float,
        initial_equity: float,
        cash_balance: float,
        daily_pnl: float,
        positions: List[dict],
        max_position_symbol: Optional[str] = None,
    ) -> List[RiskAlert]:
        self._alerts.clear()

        # ── Max drawdown ──────────────────────────────────────────────────
        if initial_equity > 0:
            drawdown = (initial_equity - total_equity) / initial_equity
            if drawdown > settings.MAX_DRAWDOWN_PCT:
                self._fire(
                    "CRITICAL", "MAX_DRAWDOWN_BREACHED",
                    f"Portfolio drawdown {drawdown*100:.1f}% exceeds limit {settings.MAX_DRAWDOWN_PCT*100:.0f}%",
                    drawdown, settings.MAX_DRAWDOWN_PCT,
                )
            elif drawdown > settings.MAX_DRAWDOWN_PCT * 0.8:
                self._fire(
                    "WARN", "DRAWDOWN_WARNING",
                    f"Drawdown {drawdown*100:.1f}% approaching limit",
                    drawdown, settings.MAX_DRAWDOWN_PCT,
                )

        # ── Daily loss ────────────────────────────────────────────────────
        if total_equity > 0:
            daily_pnl_pct = daily_pnl / total_equity
            if daily_pnl_pct < -settings.MAX_DAILY_LOSS_PCT:
                self._fire(
                    "CRITICAL", "DAILY_LOSS_LIMIT",
                    f"Daily loss {daily_pnl_pct*100:.1f}% exceeds {settings.MAX_DAILY_LOSS_PCT*100:.0f}% limit",
                    abs(daily_pnl_pct), settings.MAX_DAILY_LOSS_PCT,
                )

        # ── Cash level ────────────────────────────────────────────────────
        if total_equity > 0:
            cash_pct = cash_balance / total_equity
            if cash_pct < settings.MIN_CASH_PCT:
                self._fire(
                    "WARN", "LOW_CASH",
                    f"Cash {cash_pct*100:.1f}% below minimum {settings.MIN_CASH_PCT*100:.0f}%",
                    cash_pct, settings.MIN_CASH_PCT,
                )

        # ── Concentration ─────────────────────────────────────────────────
        for pos in positions:
            pct = pos.get("market_value", 0) / max(total_equity, 1)
            if pct > settings.MAX_POSITION_SIZE_PCT * 1.5:
                self._fire(
                    "WARN", "POSITION_CONCENTRATION",
                    f"{pos.get('symbol')} position {pct*100:.1f}% exceeds limit",
                    pct, settings.MAX_POSITION_SIZE_PCT,
                )

        # ── Kill switch ───────────────────────────────────────────────────
        if settings.KILL_SWITCH_ENABLED:
            self._fire(
                "CRITICAL", "KILL_SWITCH_ACTIVE",
                "Kill switch is enabled — all trading halted",
                1.0, 0.0,
            )

        return self._alerts

    def _fire(self, level: str, code: str, message: str, value: float, threshold: float) -> None:
        alert = RiskAlert(level=level, code=code, message=message, value=value, threshold=threshold)
        self._alerts.append(alert)
        if level == "CRITICAL":
            log.warning("RISK ALERT", level=level, code=code, message=message)

    @property
    def active_alerts(self) -> List[RiskAlert]:
        return self._alerts

    @property
    def has_critical(self) -> bool:
        return any(a.level == "CRITICAL" for a in self._alerts)


_risk_manager: Optional[RiskManager] = None


def get_risk_manager() -> RiskManager:
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager
