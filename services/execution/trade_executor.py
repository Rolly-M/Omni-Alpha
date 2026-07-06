"""Trade executor — persists coordinator decisions and executes approved ones.

Execution routing:
  - Alpaca (if API keys configured; paper endpoint by default)
  - Internal simulated fill against the DB portfolio otherwise

Auto-execution fires only when ALL of these hold:
  - AUTO_TRADE_ENABLED=true
  - MANUAL_APPROVAL_REQUIRED=false
  - decision is BUY/SELL, risk verdict APPROVED/REDUCE_SIZE
  - confidence >= MIN_CONFIDENCE_TO_TRADE
  - kill switch is OFF

Otherwise actionable decisions are stored as PENDING and can be executed
manually via POST /api/orders/decisions/{decision_id}/execute.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select

from libs.common.config import settings
from libs.common.constants import (
    ASSET_FOREX, ORDER_FILLED, ORDER_MARKET, ORDER_PARTIAL,
    ORDER_REJECTED, RISK_APPROVED, RISK_REDUCE, SIDE_BUY, SIDE_SELL,
)
from libs.common.database import get_db_session
from libs.common.logger import get_logger
from libs.common.models.orders import Order, Position
from libs.common.models.portfolio import Account
from libs.common.models.signals import Decision as DecisionRow

from services.execution import alpaca_broker

log = get_logger("trade_executor")

DEFAULT_ACCOUNT_NAME = "personal"
DEDUP_WINDOW_HOURS = 20  # one trade per symbol+side per daily cycle


def _now() -> datetime:
    return datetime.now(timezone.utc)


def auto_trade_active() -> bool:
    return settings.AUTO_TRADE_ENABLED and not settings.MANUAL_APPROVAL_REQUIRED


# ── Persistence of coordinator output ─────────────────────────────────────────
def _to_row(d) -> DecisionRow:
    """Map a coordinator Decision (plain object) to the ORM row."""
    return DecisionRow(
        id=d.decision_id,
        cycle_id=d.cycle_id,
        symbol=d.symbol,
        asset_class=d.asset_class,
        timeframe=d.timeframe,
        action=d.action,
        entry_price=d.entry_price,
        stop_loss=d.stop_loss,
        take_profit=d.take_profit,
        position_size_pct=d.position_size_pct,
        confidence=d.confidence,
        risk_score=d.risk_score,
        expected_holding_period=d.expected_holding_period,
        entry_logic=d.entry_logic,
        exit_logic=d.exit_logic,
        thesis=d.thesis,
        supporting_signals=json.dumps(d.supporting_signals),
        contradicting_signals=json.dumps(d.contradicting_signals),
        explanation=d.explanation,
        source_references=json.dumps(d.source_references),
        agent_outputs_json=json.dumps(d.agent_outputs),
        risk_verdict=d.risk_verdict,
        risk_notes=json.dumps(d.risk_notes),
        status="PENDING",
    )


def _is_actionable(row: DecisionRow) -> tuple[bool, str]:
    if row.action not in (SIDE_BUY, SIDE_SELL):
        return False, f"action={row.action}"
    if row.risk_verdict not in (RISK_APPROVED, RISK_REDUCE):
        return False, f"risk_verdict={row.risk_verdict}"
    if row.confidence < settings.MIN_CONFIDENCE_TO_TRADE:
        return False, f"confidence {row.confidence:.0f} < {settings.MIN_CONFIDENCE_TO_TRADE:.0f}"
    if row.position_size_pct <= 0 and row.action == SIDE_BUY:
        return False, "position size 0"
    return True, ""


async def process_decisions(decisions: List) -> dict:
    """Persist all decisions; auto-execute actionable ones if enabled."""
    executed, pending, skipped = [], [], []

    async with get_db_session() as db:
        result = await db.execute(select(Account).where(Account.name == DEFAULT_ACCOUNT_NAME))
        account = result.scalar_one_or_none()

        for d in decisions:
            row = _to_row(d)
            db.add(row)

            actionable, why = _is_actionable(row)
            if not actionable:
                row.status = "NO_TRADE"
                skipped.append({"symbol": row.symbol, "reason": why})
                continue

            if not auto_trade_active():
                pending.append({"decision_id": row.id, "symbol": row.symbol,
                                "action": row.action, "confidence": round(row.confidence, 1)})
                continue

            if account is None:
                row.status = "SKIPPED"
                skipped.append({"symbol": row.symbol,
                                "reason": "no account — POST /api/portfolio/account first"})
                continue

            outcome = await _execute(db, account, row)
            executed.append(outcome)

    return {
        "auto_trade": auto_trade_active(),
        "broker": "alpaca" if alpaca_broker.is_configured() else "internal_paper",
        "executed": executed,
        "pending_approval": pending,
        "skipped": skipped,
    }


async def execute_decision_by_id(decision_id: str) -> dict:
    """Manually approve and execute a stored PENDING decision."""
    async with get_db_session() as db:
        row = await db.get(DecisionRow, decision_id)
        if row is None:
            return {"error": f"Decision '{decision_id}' not found"}
        if row.status != "PENDING":
            return {"error": f"Decision status is '{row.status}', expected PENDING"}

        actionable, why = _is_actionable(row)
        if not actionable:
            return {"error": f"Decision not actionable: {why}"}

        result = await db.execute(select(Account).where(Account.name == DEFAULT_ACCOUNT_NAME))
        account = result.scalar_one_or_none()
        if account is None:
            return {"error": "No account — POST /api/portfolio/account first"}

        return await _execute(db, account, row)


# ── Execution ─────────────────────────────────────────────────────────────────
async def _execute(db, account: Account, row: DecisionRow) -> dict:
    symbol, side, price = row.symbol, row.action, row.entry_price

    def reject(reason: str) -> dict:
        row.status = "REJECTED"
        order = _make_order(row, account, 0.0, ORDER_REJECTED, rejection_reason=reason)
        db.add(order)
        log.warning("Trade rejected", symbol=symbol, side=side, reason=reason)
        return {"symbol": symbol, "side": side, "status": ORDER_REJECTED, "reason": reason}

    if settings.KILL_SWITCH_ENABLED:
        return reject("Kill switch active")
    if price is None or price <= 0:
        return reject("No valid entry price")

    # Duplicate prevention (DB-level; survives serverless cold starts)
    cutoff = _now() - timedelta(hours=DEDUP_WINDOW_HOURS)
    result = await db.execute(
        select(Order).where(
            Order.portfolio_id == account.id,
            Order.symbol == symbol,
            Order.side == side,
            Order.created_at > cutoff,
            Order.status.in_((ORDER_FILLED, ORDER_PARTIAL, "SUBMITTED")),
        ).limit(1)
    )
    if result.scalar_one_or_none():
        return reject(f"Duplicate prevention: {side} {symbol} already traded "
                      f"in the last {DEDUP_WINDOW_HOURS}h")

    # Current open position (needed for sells and equity calc)
    result = await db.execute(
        select(Position).where(
            Position.portfolio_id == account.id,
            Position.is_open == True,  # noqa: E712
        )
    )
    open_positions = list(result.scalars())
    held = next((p for p in open_positions if p.symbol == symbol), None)
    equity = account.cash_balance + sum(p.quantity * p.current_price for p in open_positions)

    # ── Sizing ────────────────────────────────────────────────────────────────
    if side == SIDE_SELL:
        if held is None or held.quantity <= 0:
            return reject("No open position to sell (shorting disabled)")
        qty = held.quantity  # exit the whole position on a SELL signal
    else:
        size_pct = min(row.position_size_pct, settings.MAX_POSITION_SIZE_PCT)
        qty = equity * size_pct / price
        # Respect the cash floor
        max_spend = account.cash_balance - equity * settings.MIN_CASH_PCT
        cost = qty * price * (1 + settings.COMMISSION_RATE)
        if cost > max_spend:
            qty = max(0.0, max_spend) / (price * (1 + settings.COMMISSION_RATE))
        if qty * price < 1.0:
            return reject(f"Insufficient cash (floor {settings.MIN_CASH_PCT*100:.0f}% "
                          f"of equity must stay in cash)")
        qty = round(qty, 6)

    # ── Broker dispatch ───────────────────────────────────────────────────────
    use_alpaca = alpaca_broker.is_configured() and row.asset_class != ASSET_FOREX
    if use_alpaca:
        fill = await alpaca_broker.submit_market_order(
            symbol, side, qty, row.asset_class,
            stop_loss=row.stop_loss, take_profit=row.take_profit,
        )
        if fill["status"] == ORDER_REJECTED:
            return reject(fill["rejection_reason"])
        filled_qty = fill["filled_qty"] or qty
        fill_price = fill["filled_avg_price"] or price
        commission = 0.0  # Alpaca is commission-free for stocks/ETFs
        status = fill["status"]
        is_paper = not alpaca_broker.is_live()
    else:
        # Internal simulated fill (deterministic)
        slip = 1 + settings.SLIPPAGE_RATE if side == SIDE_BUY else 1 - settings.SLIPPAGE_RATE
        fill_price = price * slip
        filled_qty = qty
        commission = fill_price * filled_qty * settings.COMMISSION_RATE
        status = ORDER_FILLED
        is_paper = True

    order = _make_order(row, account, qty, status,
                        filled_qty=filled_qty, fill_price=fill_price,
                        commission=commission, is_paper=is_paper)
    db.add(order)

    # ── Portfolio bookkeeping ─────────────────────────────────────────────────
    if status in (ORDER_FILLED, ORDER_PARTIAL):
        if side == SIDE_BUY:
            account.cash_balance -= filled_qty * fill_price + commission
            if held:
                total_cost = held.average_cost * held.quantity + fill_price * filled_qty
                held.quantity += filled_qty
                held.average_cost = total_cost / held.quantity
                held.current_price = fill_price
            else:
                db.add(Position(
                    portfolio_id=account.id,
                    symbol=symbol,
                    asset_class=row.asset_class,
                    quantity=filled_qty,
                    average_cost=fill_price,
                    current_price=fill_price,
                    stop_loss=row.stop_loss,
                    take_profit=row.take_profit,
                ))
        else:
            account.cash_balance += filled_qty * fill_price - commission
            held.realized_pnl += (fill_price - held.average_cost) * filled_qty
            held.quantity -= filled_qty
            held.current_price = fill_price
            if held.quantity <= 1e-9:
                held.quantity = 0.0
                held.is_open = False
                held.closed_at = _now()

    row.status = "EXECUTED" if status in (ORDER_FILLED, ORDER_PARTIAL) else status
    row.executed_at = _now()

    log.info("Trade executed", symbol=symbol, side=side,
             qty=round(filled_qty, 6), price=round(fill_price, 4),
             broker="alpaca" if use_alpaca else "internal", status=status)

    return {
        "symbol": symbol,
        "side": side,
        "status": status,
        "quantity": round(filled_qty, 6),
        "fill_price": round(fill_price, 4),
        "commission": round(commission, 2),
        "broker": "alpaca" if use_alpaca else "internal_paper",
        "is_paper": is_paper,
        "decision_id": row.id,
    }


def _make_order(
    row: DecisionRow,
    account: Account,
    qty: float,
    status: str,
    filled_qty: float = 0.0,
    fill_price: Optional[float] = None,
    commission: float = 0.0,
    is_paper: bool = True,
    rejection_reason: Optional[str] = None,
) -> Order:
    return Order(
        decision_id=row.id,
        portfolio_id=account.id,
        symbol=row.symbol,
        asset_class=row.asset_class,
        order_type=ORDER_MARKET,
        side=row.action,
        quantity=qty,
        status=status,
        filled_quantity=filled_qty,
        average_fill_price=fill_price,
        commission=commission,
        rejection_reason=rejection_reason,
        is_paper=is_paper,
        submitted_at=_now(),
        filled_at=_now() if status in (ORDER_FILLED, ORDER_PARTIAL) else None,
    )
