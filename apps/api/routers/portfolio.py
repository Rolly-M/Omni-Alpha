"""Portfolio endpoints — database-backed account, positions, equity curve.

Track your real holdings: create an account, add positions at your actual
cost basis, and get live-priced valuations, P&L, and snapshot history.
"""
from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from libs.common.config import settings
from libs.common.database import get_db_session
from libs.common.logger import get_logger
from libs.common.models.portfolio import Account, Portfolio
from libs.common.models.orders import Position

router = APIRouter()
log = get_logger("portfolio_router")

DEFAULT_ACCOUNT_NAME = "personal"


# ── Schemas ───────────────────────────────────────────────────────────────────
class AccountCreate(BaseModel):
    name: str = DEFAULT_ACCOUNT_NAME
    account_type: str = Field(default="balanced", pattern="^(conservative|balanced|aggressive)$")
    initial_balance: float = Field(default=settings.INITIAL_BALANCE, gt=0)
    cash_balance: Optional[float] = Field(default=None, ge=0)


class AccountUpdate(BaseModel):
    cash_balance: Optional[float] = Field(default=None, ge=0)
    account_type: Optional[str] = Field(default=None, pattern="^(conservative|balanced|aggressive)$")


class PositionCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    quantity: float = Field(gt=0)
    average_cost: float = Field(gt=0)
    asset_class: Optional[str] = None  # inferred from symbol if omitted
    stop_loss: Optional[float] = Field(default=None, gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)


def _infer_asset_class(symbol: str) -> str:
    if "/" in symbol:
        return "crypto"
    if symbol.endswith("=X"):
        return "forex"
    if symbol.upper() in settings.ETF_WATCHLIST:
        return "etf"
    return "stock"


# ── Price helper ──────────────────────────────────────────────────────────────
async def _latest_price(symbol: str) -> Optional[float]:
    """Latest close via the ingestion service (yfinance when MOCK_MODE=false)."""
    def _fetch() -> Optional[float]:
        from services.ingestion.ingestion_service import get_ohlcv
        df = get_ohlcv(symbol, timeframe="1d", limit=2)
        if df is None or df.empty:
            return None
        return float(df["close"].iloc[-1])

    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _fetch)
    except Exception as exc:
        log.warning("Price fetch failed", symbol=symbol, error=str(exc))
        return None


async def _get_or_404(db, account_name: str) -> Account:
    result = await db.execute(select(Account).where(Account.name == account_name))
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=404,
            detail=f"Account '{account_name}' not found. Create one with POST /api/portfolio/account",
        )
    return account


async def _price_positions(db, account: Account) -> List[dict]:
    """Fetch open positions, refresh live prices, persist, and serialize."""
    result = await db.execute(
        select(Position).where(Position.portfolio_id == account.id, Position.is_open == True)  # noqa: E712
    )
    positions = list(result.scalars())

    rows = []
    for pos in positions:
        price = await _latest_price(pos.symbol)
        if price is not None:
            pos.current_price = price
            pos.unrealized_pnl = (price - pos.average_cost) * pos.quantity
        rows.append({
            "symbol": pos.symbol,
            "asset_class": pos.asset_class,
            "quantity": pos.quantity,
            "average_cost": pos.average_cost,
            "current_price": pos.current_price,
            "market_value": round(pos.market_value, 2),
            "unrealized_pnl": round(pos.unrealized_pnl, 2),
            "pnl_pct": round(pos.pnl_pct, 2),
            "stop_loss": pos.stop_loss,
            "take_profit": pos.take_profit,
            "opened_at": pos.opened_at.isoformat() if pos.opened_at else None,
        })
    return rows


# ── Account ───────────────────────────────────────────────────────────────────
@router.post("/account", status_code=201)
async def create_account(body: AccountCreate):
    """Create (or return existing) account. Idempotent on name."""
    async with get_db_session() as db:
        result = await db.execute(select(Account).where(Account.name == body.name))
        existing = result.scalar_one_or_none()
        if existing:
            return {"account_id": existing.id, "name": existing.name, "created": False}

        cash = body.cash_balance if body.cash_balance is not None else body.initial_balance
        account = Account(
            name=body.name,
            account_type=body.account_type,
            initial_balance=body.initial_balance,
            cash_balance=cash,
            total_equity=cash,
            is_paper=True,
        )
        db.add(account)
        await db.flush()
        return {"account_id": account.id, "name": account.name, "created": True}


@router.get("/account")
async def get_account(name: str = DEFAULT_ACCOUNT_NAME):
    async with get_db_session() as db:
        account = await _get_or_404(db, name)
        rows = await _price_positions(db, account)
        positions_value = sum(r["market_value"] for r in rows)
        total_equity = account.cash_balance + positions_value
        account.total_equity = total_equity

        return {
            "account_id": account.id,
            "name": account.name,
            "account_type": account.account_type,
            "initial_balance": account.initial_balance,
            "cash_balance": round(account.cash_balance, 2),
            "positions_value": round(positions_value, 2),
            "total_equity": round(total_equity, 2),
            "cumulative_pnl": round(total_equity - account.initial_balance, 2),
            "cumulative_pnl_pct": round(
                (total_equity - account.initial_balance) / account.initial_balance * 100, 2
            ),
            "open_positions": len(rows),
            "is_paper": account.is_paper,
        }


@router.patch("/account")
async def update_account(body: AccountUpdate, name: str = DEFAULT_ACCOUNT_NAME):
    async with get_db_session() as db:
        account = await _get_or_404(db, name)
        if body.cash_balance is not None:
            account.cash_balance = body.cash_balance
        if body.account_type is not None:
            account.account_type = body.account_type
        return {"account_id": account.id, "cash_balance": account.cash_balance,
                "account_type": account.account_type}


# ── Positions ─────────────────────────────────────────────────────────────────
@router.get("/positions")
async def get_positions(name: str = DEFAULT_ACCOUNT_NAME):
    async with get_db_session() as db:
        account = await _get_or_404(db, name)
        rows = await _price_positions(db, account)
        return {"positions": rows, "count": len(rows)}


@router.post("/positions", status_code=201)
async def add_position(body: PositionCreate, name: str = DEFAULT_ACCOUNT_NAME):
    """Record a real holding. If the symbol already has an open position,
    quantities are merged at the blended average cost."""
    async with get_db_session() as db:
        account = await _get_or_404(db, name)
        result = await db.execute(
            select(Position).where(
                Position.portfolio_id == account.id,
                Position.symbol == body.symbol,
                Position.is_open == True,  # noqa: E712
            )
        )
        pos = result.scalar_one_or_none()
        if pos:
            total_cost = pos.average_cost * pos.quantity + body.average_cost * body.quantity
            pos.quantity += body.quantity
            pos.average_cost = total_cost / pos.quantity
            merged = True
        else:
            pos = Position(
                portfolio_id=account.id,
                symbol=body.symbol,
                asset_class=body.asset_class or _infer_asset_class(body.symbol),
                quantity=body.quantity,
                average_cost=body.average_cost,
                current_price=body.average_cost,
                stop_loss=body.stop_loss,
                take_profit=body.take_profit,
            )
            db.add(pos)
            merged = False
        await db.flush()
        return {"position_id": pos.id, "symbol": pos.symbol, "quantity": pos.quantity,
                "average_cost": round(pos.average_cost, 4), "merged": merged}


@router.delete("/positions/{symbol:path}")
async def close_position(symbol: str, name: str = DEFAULT_ACCOUNT_NAME):
    """Mark a position closed (e.g. you sold it in your real brokerage)."""
    async with get_db_session() as db:
        account = await _get_or_404(db, name)
        result = await db.execute(
            select(Position).where(
                Position.portfolio_id == account.id,
                Position.symbol == symbol,
                Position.is_open == True,  # noqa: E712
            )
        )
        pos = result.scalar_one_or_none()
        if pos is None:
            raise HTTPException(status_code=404, detail=f"No open position for '{symbol}'")
        price = await _latest_price(symbol)
        if price is not None:
            pos.current_price = price
        pos.realized_pnl = (pos.current_price - pos.average_cost) * pos.quantity
        pos.is_open = False
        pos.closed_at = datetime.now(timezone.utc)
        return {"symbol": symbol, "closed": True, "realized_pnl": round(pos.realized_pnl, 2)}


# ── Snapshots / equity curve ──────────────────────────────────────────────────
async def take_snapshot(account_name: str = DEFAULT_ACCOUNT_NAME) -> dict:
    """Compute current equity and persist a portfolio snapshot."""
    async with get_db_session() as db:
        account = await _get_or_404(db, account_name)
        rows = await _price_positions(db, account)
        positions_value = sum(r["market_value"] for r in rows)
        total_equity = account.cash_balance + positions_value
        account.total_equity = total_equity

        result = await db.execute(
            select(Portfolio)
            .where(Portfolio.account_id == account.id)
            .order_by(Portfolio.snapshot_at.desc())
            .limit(1)
        )
        prev = result.scalar_one_or_none()
        daily_pnl = total_equity - prev.total_equity if prev else 0.0

        # Drawdown vs. historical peak equity
        result = await db.execute(select(Portfolio.total_equity).where(Portfolio.account_id == account.id))
        equities = [e for (e,) in result.all()] + [total_equity]
        peak = max(equities)
        drawdown_pct = (peak - total_equity) / peak * 100 if peak > 0 else 0.0

        snap = Portfolio(
            account_id=account.id,
            cash_balance=account.cash_balance,
            positions_value=positions_value,
            total_equity=total_equity,
            daily_pnl=daily_pnl,
            cumulative_pnl=total_equity - account.initial_balance,
            drawdown_pct=drawdown_pct,
            open_positions=len(rows),
        )
        db.add(snap)
        return {
            "snapshot": True,
            "total_equity": round(total_equity, 2),
            "daily_pnl": round(daily_pnl, 2),
            "drawdown_pct": round(drawdown_pct, 2),
            "open_positions": len(rows),
        }


@router.post("/snapshot")
async def create_snapshot(name: str = DEFAULT_ACCOUNT_NAME):
    return await take_snapshot(name)


@router.get("/equity-curve")
async def get_equity_curve(days: int = 90, name: str = DEFAULT_ACCOUNT_NAME):
    """Real equity curve from stored snapshots."""
    async with get_db_session() as db:
        account = await _get_or_404(db, name)
        result = await db.execute(
            select(Portfolio)
            .where(Portfolio.account_id == account.id)
            .order_by(Portfolio.snapshot_at.desc())
            .limit(days)
        )
        snaps = list(reversed(result.scalars().all()))
        return {
            "dates": [s.snapshot_at.date().isoformat() for s in snaps],
            "equity": [round(s.total_equity, 2) for s in snaps],
            "initial": account.initial_balance,
            "current": round(snaps[-1].total_equity, 2) if snaps else account.initial_balance,
            "total_return_pct": round(
                (snaps[-1].total_equity - account.initial_balance) / account.initial_balance * 100, 2
            ) if snaps else 0.0,
            "snapshots": len(snaps),
        }


@router.get("/metrics")
async def get_portfolio_metrics(name: str = DEFAULT_ACCOUNT_NAME):
    """Performance metrics computed from snapshot history."""
    async with get_db_session() as db:
        account = await _get_or_404(db, name)
        result = await db.execute(
            select(Portfolio)
            .where(Portfolio.account_id == account.id)
            .order_by(Portfolio.snapshot_at.asc())
        )
        snaps = result.scalars().all()

        if len(snaps) < 2:
            return {
                "message": "Need at least 2 snapshots for metrics. "
                           "POST /api/portfolio/snapshot daily (or let the cron do it).",
                "snapshots": len(snaps),
            }

        returns = []
        for prev, cur in zip(snaps, snaps[1:]):
            if prev.total_equity > 0:
                returns.append((cur.total_equity - prev.total_equity) / prev.total_equity)

        mean_r = sum(returns) / len(returns)
        var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        std_r = math.sqrt(var)
        downside = [r for r in returns if r < 0]
        downside_std = math.sqrt(sum(r ** 2 for r in downside) / len(returns)) if downside else 0.0

        wins = sum(1 for r in returns if r > 0)
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))

        return {
            "sharpe_ratio": round(mean_r / std_r * math.sqrt(252), 2) if std_r > 0 else None,
            "sortino_ratio": round(mean_r / downside_std * math.sqrt(252), 2) if downside_std > 0 else None,
            "max_drawdown_pct": round(max(s.drawdown_pct for s in snaps), 2),
            "win_rate_pct": round(wins / len(returns) * 100, 1),
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else None,
            "avg_daily_return_pct": round(mean_r * 100, 3),
            "total_return_pct": round(
                (snaps[-1].total_equity - account.initial_balance) / account.initial_balance * 100, 2
            ),
            "open_positions": snaps[-1].open_positions,
            "snapshots": len(snaps),
        }
