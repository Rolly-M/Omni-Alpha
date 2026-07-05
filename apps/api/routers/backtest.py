"""Backtest endpoints."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Query

from services.backtest.engine import BacktestEngine

router = APIRouter()


@router.post("/run")
async def run_backtest(
    symbol: str = Query("AAPL"),
    timeframe: str = Query("1d"),
    lookback_bars: int = Query(365, ge=50, le=2000),
    initial_equity: float = Query(None),
):
    """Run a backtest and return full results."""
    engine = BacktestEngine(initial_equity=initial_equity)
    result = engine.run(symbol=symbol, timeframe=timeframe, lookback_bars=lookback_bars)
    return result.to_dict()


@router.get("/strategies")
async def list_strategies():
    return {
        "strategies": [
            {"name": "trend_following", "description": "Buy in uptrend, SMA crossover confirmation"},
            {"name": "mean_reversion", "description": "RSI oversold bounce"},
            {"name": "momentum", "description": "Recent winner continuation"},
            {"name": "breakout", "description": "Volume-confirmed breakout from consolidation"},
            {"name": "news_event", "description": "Trade on high-impact news"},
        ]
    }
