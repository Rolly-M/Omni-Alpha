"""Signal feed endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query
from services.agents.coordinator import get_coordinator

router = APIRouter()


@router.get("/latest")
async def get_latest_signals(
    limit: int = Query(20, ge=1, le=100),
    symbol: str = Query(None),
    asset_class: str = Query(None),
):
    """Run one cycle and return top signals."""
    coordinator = get_coordinator()
    symbols = None
    if symbol:
        symbols = [symbol]
    elif asset_class:
        from libs.common.config import settings
        ac_map = {
            "stock": settings.STOCK_WATCHLIST,
            "etf": settings.ETF_WATCHLIST,
            "crypto": settings.CRYPTO_WATCHLIST,
            "forex": settings.FOREX_WATCHLIST,
        }
        symbols = ac_map.get(asset_class, settings.all_symbols)

    decisions = coordinator.run_cycle(symbols=symbols)
    results = []
    for d in decisions[:limit]:
        results.append({
            "symbol": d.symbol,
            "asset_class": d.asset_class,
            "action": d.action,
            "confidence": round(d.confidence, 1),
            "risk_score": round(d.risk_score, 1),
            "risk_verdict": d.risk_verdict,
            "entry_price": round(d.entry_price, 4),
            "stop_loss": round(d.stop_loss, 4) if d.stop_loss else None,
            "take_profit": round(d.take_profit, 4) if d.take_profit else None,
            "position_size_pct": round(d.position_size_pct * 100, 2),
            "thesis": d.thesis[:120] + "..." if len(d.thesis) > 120 else d.thesis,
            "created_at": d.created_at.isoformat(),
        })

    return {"signals": results, "count": len(results)}


@router.get("/decision/{symbol}")
async def get_full_decision(symbol: str):
    """Full decision drill-down for one symbol."""
    coordinator = get_coordinator()
    decisions = coordinator.run_cycle(symbols=[symbol])
    if not decisions:
        return {"error": "No decision generated"}
    d = decisions[0]
    return d.to_dict()
