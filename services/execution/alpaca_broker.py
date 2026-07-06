"""Alpaca brokerage connector — REST API via httpx, no SDK dependency.

Defaults to Alpaca's PAPER endpoint (fake money, real market data).
The LIVE endpoint is used only when BOTH conditions hold:
  - ALPACA_PAPER=false
  - LIVE_TRADING_ENABLED=true
Otherwise the connector falls back to paper and logs a warning.

Forex is not supported by Alpaca; callers should route forex orders
to the internal paper broker instead.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from libs.common.config import settings
from libs.common.constants import ASSET_CRYPTO, ASSET_FOREX, SIDE_BUY
from libs.common.logger import get_logger

log = get_logger("alpaca_broker")

PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"

FILL_POLL_ATTEMPTS = 5
FILL_POLL_DELAY_S = 1.0


def is_configured() -> bool:
    return bool(settings.ALPACA_API_KEY and settings.ALPACA_SECRET_KEY)


def is_live() -> bool:
    return not settings.ALPACA_PAPER and settings.LIVE_TRADING_ENABLED


def base_url() -> str:
    if not settings.ALPACA_PAPER:
        if settings.LIVE_TRADING_ENABLED:
            return LIVE_URL
        log.warning(
            "ALPACA_PAPER=false but LIVE_TRADING_ENABLED=false — "
            "refusing live endpoint, using paper"
        )
    return PAPER_URL


def _headers() -> dict:
    return {
        "APCA-API-KEY-ID": settings.ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": settings.ALPACA_SECRET_KEY,
    }


def to_alpaca_symbol(symbol: str, asset_class: str) -> Optional[str]:
    """Map internal symbols to Alpaca's format. Returns None if unsupported."""
    if asset_class == ASSET_FOREX:
        return None
    if asset_class == ASSET_CRYPTO:
        if "/" in symbol:
            base, quote = symbol.split("/", 1)
            if quote.upper() in ("USDT", "USDC", "BUSD"):
                quote = "USD"
            return f"{base}/{quote}"
        return symbol
    return symbol


async def submit_market_order(
    symbol: str,
    side: str,
    quantity: float,
    asset_class: str,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
) -> dict:
    """Submit a market order and poll briefly for the fill.

    Returns a normalized dict:
      {status, broker_order_id, filled_qty, filled_avg_price, rejection_reason}
    """
    alpaca_symbol = to_alpaca_symbol(symbol, asset_class)
    if alpaca_symbol is None:
        return {
            "status": "REJECTED",
            "broker_order_id": None,
            "filled_qty": 0.0,
            "filled_avg_price": None,
            "rejection_reason": f"Asset class '{asset_class}' not supported by Alpaca",
        }

    is_crypto = asset_class == ASSET_CRYPTO
    payload: dict = {
        "symbol": alpaca_symbol,
        "qty": str(round(quantity, 9 if is_crypto else 4)),
        "side": side.lower(),
        "type": "market",
        "time_in_force": "gtc" if is_crypto else "day",
    }
    # Bracket orders (auto stop-loss/take-profit) — stocks/ETFs, buy side only
    if not is_crypto and side == SIDE_BUY and stop_loss and take_profit:
        payload["order_class"] = "bracket"
        payload["stop_loss"] = {"stop_price": str(round(stop_loss, 2))}
        payload["take_profit"] = {"limit_price": str(round(take_profit, 2))}

    url = base_url()
    log.info(
        "Submitting Alpaca order",
        symbol=alpaca_symbol, side=side, qty=quantity,
        endpoint="LIVE" if url == LIVE_URL else "PAPER",
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(f"{url}/v2/orders", json=payload, headers=_headers())
        if resp.status_code >= 400:
            reason = resp.json().get("message", resp.text) if resp.text else str(resp.status_code)
            log.warning("Alpaca order rejected", symbol=alpaca_symbol, reason=reason)
            return {
                "status": "REJECTED",
                "broker_order_id": None,
                "filled_qty": 0.0,
                "filled_avg_price": None,
                "rejection_reason": f"Alpaca: {reason}",
            }

        order = resp.json()
        order_id = order["id"]

        # Poll briefly for the fill (market orders usually fill fast in market hours)
        for _ in range(FILL_POLL_ATTEMPTS):
            if order.get("status") in ("filled", "partially_filled", "rejected", "canceled"):
                break
            await asyncio.sleep(FILL_POLL_DELAY_S)
            poll = await client.get(f"{url}/v2/orders/{order_id}", headers=_headers())
            if poll.status_code == 200:
                order = poll.json()

    status_map = {
        "filled": "FILLED",
        "partially_filled": "PARTIAL_FILL",
        "rejected": "REJECTED",
        "canceled": "CANCELLED",
    }
    return {
        "status": status_map.get(order.get("status"), "SUBMITTED"),
        "broker_order_id": order_id,
        "filled_qty": float(order.get("filled_qty") or 0.0),
        "filled_avg_price": (
            float(order["filled_avg_price"]) if order.get("filled_avg_price") else None
        ),
        "rejection_reason": None,
    }
