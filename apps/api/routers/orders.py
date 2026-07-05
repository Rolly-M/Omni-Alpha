"""Order management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter()

# Demo order history
_DEMO_ORDERS = [
    {"order_id": "ord-001", "symbol": "AAPL", "side": "BUY", "quantity": 25.0,
     "order_type": "MARKET", "status": "FILLED", "average_fill_price": 183.40,
     "commission": 4.59, "slippage": 0.92, "is_paper": True, "filled_at": "2024-12-01T14:32:00Z"},
    {"order_id": "ord-002", "symbol": "MSFT", "side": "BUY", "quantity": 10.0,
     "order_type": "MARKET", "status": "FILLED", "average_fill_price": 415.10,
     "commission": 4.15, "slippage": 0.83, "is_paper": True, "filled_at": "2024-12-02T09:45:00Z"},
    {"order_id": "ord-003", "symbol": "BTC/USDT", "side": "BUY", "quantity": 0.05,
     "order_type": "MARKET", "status": "FILLED", "average_fill_price": 67500.0,
     "commission": 3.38, "slippage": 16.88, "is_paper": True, "filled_at": "2024-12-03T16:20:00Z"},
    {"order_id": "ord-004", "symbol": "NVDA", "side": "BUY", "quantity": 5.0,
     "order_type": "MARKET", "status": "PARTIAL_FILL", "average_fill_price": 895.0,
     "commission": 2.24, "slippage": 1.12, "is_paper": True, "filled_at": "2024-12-04T10:05:00Z"},
    {"order_id": "ord-005", "symbol": "TSLA", "side": "SELL", "quantity": 15.0,
     "order_type": "MARKET", "status": "REJECTED", "average_fill_price": None,
     "commission": 0, "slippage": 0, "is_paper": True,
     "rejection_reason": "Risk agent veto: elevated volatility (ATR=4.2%)",
     "filled_at": None},
]


@router.get("/history")
async def get_order_history(
    limit: int = Query(50, ge=1, le=200),
    status: str = Query(None),
):
    orders = _DEMO_ORDERS
    if status:
        orders = [o for o in orders if o["status"] == status.upper()]
    return {"orders": orders[:limit], "count": len(orders)}


@router.get("/{order_id}")
async def get_order(order_id: str):
    for o in _DEMO_ORDERS:
        if o["order_id"] == order_id:
            return o
    return {"error": "Order not found"}
