"""Portfolio endpoints — account, positions, equity curve."""
from __future__ import annotations

from fastapi import APIRouter
from libs.common.config import settings

router = APIRouter()

# In-memory demo state (real impl would query DB)
_demo_account = {
    "account_id": "demo-001",
    "name": "Demo Account",
    "account_type": settings.ACCOUNT_TYPE,
    "initial_balance": settings.INITIAL_BALANCE,
    "cash_balance": settings.INITIAL_BALANCE * 0.85,
    "positions_value": settings.INITIAL_BALANCE * 0.15,
    "total_equity": settings.INITIAL_BALANCE * 1.023,
    "daily_pnl": 230.5,
    "daily_pnl_pct": 0.23,
    "cumulative_pnl": 2300.0,
    "cumulative_pnl_pct": 2.3,
    "drawdown_pct": 1.2,
    "is_paper": True,
}

_demo_positions = [
    {"symbol": "AAPL", "asset_class": "stock", "quantity": 25.0, "average_cost": 183.40,
     "current_price": 185.20, "market_value": 4630.0, "unrealized_pnl": 45.0, "pnl_pct": 0.98},
    {"symbol": "MSFT", "asset_class": "stock", "quantity": 10.0, "average_cost": 415.0,
     "current_price": 422.10, "market_value": 4221.0, "unrealized_pnl": 71.0, "pnl_pct": 1.71},
    {"symbol": "BTC/USDT", "asset_class": "crypto", "quantity": 0.05, "average_cost": 67500.0,
     "current_price": 68200.0, "market_value": 3410.0, "unrealized_pnl": 35.0, "pnl_pct": 1.04},
]


@router.get("/account")
async def get_account():
    return _demo_account


@router.get("/positions")
async def get_positions():
    return {"positions": _demo_positions, "count": len(_demo_positions)}


@router.get("/equity-curve")
async def get_equity_curve(days: int = 30):
    """Generate a synthetic equity curve for demo."""
    import numpy as np
    from datetime import datetime, timedelta, timezone

    rng = np.random.default_rng(42)
    start = settings.INITIAL_BALANCE
    curve = [start]
    dates = []
    now = datetime.now(timezone.utc)

    for i in range(days):
        ret = rng.normal(0.001, 0.012)
        curve.append(curve[-1] * (1 + ret))
        dates.append((now - timedelta(days=days - i)).date().isoformat())

    return {
        "dates": dates,
        "equity": [round(v, 2) for v in curve[1:]],
        "initial": start,
        "current": round(curve[-1], 2),
        "total_return_pct": round((curve[-1] - start) / start * 100, 2),
    }


@router.get("/metrics")
async def get_portfolio_metrics():
    return {
        "sharpe_ratio": 1.42,
        "sortino_ratio": 1.85,
        "max_drawdown_pct": 3.8,
        "win_rate_pct": 58.3,
        "profit_factor": 1.65,
        "avg_trade_pct": 0.82,
        "total_trades": 24,
        "open_positions": len(_demo_positions),
        "portfolio_beta": 0.87,
        "portfolio_alpha": 0.12,
    }
