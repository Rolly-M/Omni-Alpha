"""Order management endpoints — database-backed order history and the
manual-approval workflow for agent decisions."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from libs.common.database import get_db_session
from libs.common.models.orders import Order
from libs.common.models.signals import Decision as DecisionRow

router = APIRouter()


def _order_to_dict(o: Order) -> dict:
    return {
        "order_id": o.id,
        "decision_id": o.decision_id,
        "symbol": o.symbol,
        "asset_class": o.asset_class,
        "side": o.side,
        "quantity": o.quantity,
        "order_type": o.order_type,
        "status": o.status,
        "filled_quantity": o.filled_quantity,
        "average_fill_price": o.average_fill_price,
        "commission": o.commission,
        "slippage": o.slippage,
        "rejection_reason": o.rejection_reason,
        "is_paper": o.is_paper,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "filled_at": o.filled_at.isoformat() if o.filled_at else None,
    }


@router.get("/history")
async def get_order_history(
    limit: int = Query(50, ge=1, le=200),
    status: str = Query(None),
    symbol: str = Query(None),
):
    async with get_db_session() as db:
        query = select(Order).order_by(Order.created_at.desc()).limit(limit)
        if status:
            query = query.where(Order.status == status.upper())
        if symbol:
            query = query.where(Order.symbol == symbol)
        result = await db.execute(query)
        orders = [_order_to_dict(o) for o in result.scalars()]
        return {"orders": orders, "count": len(orders)}


# ── Decision approval workflow ────────────────────────────────────────────────
@router.get("/decisions/pending")
async def get_pending_decisions(limit: int = Query(50, ge=1, le=200)):
    """Actionable agent decisions awaiting manual approval."""
    async with get_db_session() as db:
        result = await db.execute(
            select(DecisionRow)
            .where(DecisionRow.status == "PENDING")
            .order_by(DecisionRow.created_at.desc())
            .limit(limit)
        )
        rows = [
            {
                "decision_id": r.id,
                "symbol": r.symbol,
                "action": r.action,
                "asset_class": r.asset_class,
                "entry_price": r.entry_price,
                "stop_loss": r.stop_loss,
                "take_profit": r.take_profit,
                "position_size_pct": round(r.position_size_pct * 100, 2),
                "confidence": round(r.confidence, 1),
                "risk_verdict": r.risk_verdict,
                "thesis": r.thesis,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars()
        ]
        return {"pending": rows, "count": len(rows),
                "hint": "POST /api/orders/decisions/{decision_id}/execute to approve"}


@router.post("/decisions/{decision_id}/execute")
async def execute_decision(decision_id: str):
    """Approve and execute a pending agent decision."""
    from services.execution.trade_executor import execute_decision_by_id
    result = await execute_decision_by_id(decision_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/decisions/{decision_id}/dismiss")
async def dismiss_decision(decision_id: str):
    """Dismiss a pending decision without executing it."""
    async with get_db_session() as db:
        row = await db.get(DecisionRow, decision_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Decision not found")
        if row.status != "PENDING":
            raise HTTPException(status_code=400, detail=f"Status is '{row.status}', expected PENDING")
        row.status = "DISMISSED"
        return {"decision_id": decision_id, "status": "DISMISSED"}


@router.get("/{order_id}")
async def get_order(order_id: str):
    async with get_db_session() as db:
        order = await db.get(Order, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return _order_to_dict(order)
