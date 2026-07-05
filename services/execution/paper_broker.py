"""Paper broker — simulates order fills with configurable slippage, fees, latency.

All orders are paper orders (is_paper=True). Live broker integration is disabled
unless LIVE_TRADING_ENABLED is explicitly set and additional safety conditions are met.
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from libs.common.config import settings
from libs.common.constants import (
    ORDER_FILLED, ORDER_MARKET, ORDER_PARTIAL, ORDER_REJECTED,
    ORDER_SUBMITTED, SIDE_BUY, SIDE_SELL,
)
from libs.common.logger import get_logger

log = get_logger("paper_broker")


class PaperOrder:
    """In-memory order object (persisted to DB separately)."""
    def __init__(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = ORDER_MARKET,
        limit_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.order_type = order_type
        self.limit_price = limit_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.status = ORDER_SUBMITTED
        self.filled_quantity = 0.0
        self.average_fill_price: Optional[float] = None
        self.commission = 0.0
        self.slippage = 0.0
        self.rejection_reason: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.filled_at: Optional[datetime] = None
        self.is_paper = True

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "limit_price": self.limit_price,
            "status": self.status,
            "filled_quantity": self.filled_quantity,
            "average_fill_price": self.average_fill_price,
            "commission": self.commission,
            "slippage": self.slippage,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "rejection_reason": self.rejection_reason,
            "is_paper": self.is_paper,
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
        }


class PaperBroker:
    """Simulates a brokerage for paper trading.

    Configurable:
    - commission_rate: fraction of order value
    - slippage_rate: additional execution cost above market
    - partial_fill_probability: fraction of orders that partially fill
    - latency_ms_range: (min, max) simulated fill latency
    """

    def __init__(
        self,
        commission_rate: float = None,
        slippage_rate: float = None,
        partial_fill_probability: float = 0.05,
        latency_ms_range: tuple = (50, 500),
    ):
        self.commission_rate = commission_rate or settings.COMMISSION_RATE
        self.slippage_rate = slippage_rate or settings.SLIPPAGE_RATE
        self.partial_fill_probability = partial_fill_probability
        self.latency_ms_range = latency_ms_range
        self._orders: Dict[str, PaperOrder] = {}

    def submit(
        self,
        symbol: str,
        side: str,
        quantity: float,
        market_price: float,
        order_type: str = ORDER_MARKET,
        limit_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> PaperOrder:
        if settings.KILL_SWITCH_ENABLED:
            o = PaperOrder(str(uuid.uuid4()), symbol, side, quantity)
            o.status = ORDER_REJECTED
            o.rejection_reason = "KILL SWITCH active — no orders accepted"
            log.warning("Order rejected by kill switch", symbol=symbol)
            return o

        if settings.LIVE_TRADING_ENABLED:
            log.warning("LIVE TRADING ENABLED — this system uses paper mode only")

        order = PaperOrder(
            order_id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        # Duplicate prevention
        recent = [
            o for o in self._orders.values()
            if o.symbol == symbol and o.side == side
            and (datetime.now(timezone.utc) - o.created_at).seconds < 60
            and o.status in (ORDER_SUBMITTED, ORDER_FILLED)
        ]
        if recent:
            order.status = ORDER_REJECTED
            order.rejection_reason = f"Duplicate order prevention: {len(recent)} recent {side} order(s) for {symbol}"
            log.warning("Duplicate order blocked", symbol=symbol, side=side)
            self._orders[order.order_id] = order
            return order

        # Simulate fill
        order = self._simulate_fill(order, market_price)
        self._orders[order.order_id] = order
        return order

    def _simulate_fill(self, order: PaperOrder, market_price: float) -> PaperOrder:
        rng = random.Random()

        # Slippage direction
        if order.side == SIDE_BUY:
            slippage_multiplier = 1 + self.slippage_rate
        else:
            slippage_multiplier = 1 - self.slippage_rate

        fill_price = market_price * slippage_multiplier

        # Partial fill simulation
        if rng.random() < self.partial_fill_probability:
            fill_ratio = rng.uniform(0.5, 0.95)
            order.filled_quantity = order.quantity * fill_ratio
            order.status = ORDER_PARTIAL
        else:
            order.filled_quantity = order.quantity
            order.status = ORDER_FILLED

        order.average_fill_price = fill_price
        order.slippage = abs(fill_price - market_price) * order.filled_quantity
        order.commission = fill_price * order.filled_quantity * self.commission_rate
        order.filled_at = datetime.now(timezone.utc)

        # Simulated latency
        latency_ms = rng.randint(*self.latency_ms_range)

        log.info(
            "Paper order filled",
            symbol=order.symbol,
            side=order.side,
            qty=order.filled_quantity,
            price=round(fill_price, 4),
            commission=round(order.commission, 2),
            latency_ms=latency_ms,
        )
        return order

    def get_order(self, order_id: str) -> Optional[PaperOrder]:
        return self._orders.get(order_id)

    def get_all_orders(self) -> List[PaperOrder]:
        return list(self._orders.values())


_paper_broker: Optional[PaperBroker] = None


def get_paper_broker() -> PaperBroker:
    global _paper_broker
    if _paper_broker is None:
        _paper_broker = PaperBroker()
    return _paper_broker
