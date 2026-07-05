"""Risk monitoring endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from libs.common.config import settings

router = APIRouter()


@router.get("/status")
async def get_risk_status():
    return {
        "kill_switch_enabled": settings.KILL_SWITCH_ENABLED,
        "live_trading_enabled": settings.LIVE_TRADING_ENABLED,
        "manual_approval_required": settings.MANUAL_APPROVAL_REQUIRED,
        "max_position_size_pct": settings.MAX_POSITION_SIZE_PCT * 100,
        "max_daily_loss_pct": settings.MAX_DAILY_LOSS_PCT * 100,
        "max_drawdown_pct": settings.MAX_DRAWDOWN_PCT * 100,
        "max_leverage": settings.MAX_LEVERAGE,
        "min_cash_pct": settings.MIN_CASH_PCT * 100,
    }


@router.get("/alerts")
async def get_risk_alerts():
    from services.risk.risk_manager import get_risk_manager
    rm = get_risk_manager()
    alerts = rm.check_portfolio(
        total_equity=102300.0,
        initial_equity=settings.INITIAL_BALANCE,
        cash_balance=85000.0,
        daily_pnl=230.5,
        positions=[
            {"symbol": "AAPL", "market_value": 4630.0},
            {"symbol": "MSFT", "market_value": 4221.0},
        ],
    )
    return {
        "alerts": [
            {"level": a.level, "code": a.code, "message": a.message}
            for a in alerts
        ],
        "has_critical": rm.has_critical,
    }


@router.get("/limits")
async def get_risk_limits():
    return {
        "position_limits": {
            "max_position_pct": settings.MAX_POSITION_SIZE_PCT * 100,
            "max_sector_exposure_pct": settings.MAX_SECTOR_EXPOSURE_PCT * 100,
            "max_leverage": settings.MAX_LEVERAGE,
        },
        "portfolio_limits": {
            "max_daily_loss_pct": settings.MAX_DAILY_LOSS_PCT * 100,
            "max_drawdown_pct": settings.MAX_DRAWDOWN_PCT * 100,
            "min_cash_pct": settings.MIN_CASH_PCT * 100,
        },
        "execution_limits": {
            "commission_rate_pct": settings.COMMISSION_RATE * 100,
            "slippage_rate_pct": settings.SLIPPAGE_RATE * 100,
        },
    }
