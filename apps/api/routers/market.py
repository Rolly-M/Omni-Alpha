"""Market data endpoints."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query

from services.ingestion.ingestion_service import get_ohlcv, get_features

router = APIRouter()


@router.get("/ohlcv/{symbol}")
async def get_ohlcv_data(
    symbol: str,
    timeframe: str = Query("1d", description="1m/5m/15m/1h/4h/1d/1w"),
    limit: int = Query(100, ge=1, le=1000),
):
    df = get_ohlcv(symbol, timeframe, limit)
    records = []
    for ts, row in df.iterrows():
        records.append({
            "timestamp": ts.isoformat(),
            "open": round(float(row["open"]), 4),
            "high": round(float(row["high"]), 4),
            "low": round(float(row["low"]), 4),
            "close": round(float(row["close"]), 4),
            "volume": round(float(row["volume"]), 0),
        })
    return {"symbol": symbol, "timeframe": timeframe, "bars": records}


@router.get("/features/{symbol}")
async def get_symbol_features(
    symbol: str,
    timeframe: str = Query("1d"),
):
    fs = get_features(symbol, timeframe)
    return {
        "symbol": fs.symbol,
        "timeframe": fs.timeframe,
        "current_price": round(fs.current_price, 4),
        "rsi_14": round(fs.rsi_14, 2),
        "rsi_label": fs.rsi_label,
        "macd_histogram": round(fs.macd_histogram, 6),
        "macd_cross": fs.macd_cross,
        "bb_position": round(fs.bb_position, 3),
        "trend_label": fs.trend_label,
        "atr_pct": round(fs.atr_pct, 2),
        "volatility_regime": fs.volatility_regime,
        "volume_ratio": round(fs.volume_ratio, 2),
        "return_1d": round(fs.return_1d, 2),
        "return_5d": round(fs.return_5d, 2),
        "return_20d": round(fs.return_20d, 2),
        "bull_score": round(fs.bull_score, 1),
        "bear_score": round(fs.bear_score, 1),
        "signal_list": fs.signal_list,
    }


@router.get("/watchlist")
async def get_watchlist():
    from libs.common.config import settings
    return {
        "stocks": settings.STOCK_WATCHLIST,
        "etfs": settings.ETF_WATCHLIST,
        "crypto": settings.CRYPTO_WATCHLIST,
        "forex": settings.FOREX_WATCHLIST,
    }
