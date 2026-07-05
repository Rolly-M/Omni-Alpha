"""Mock connector — generates realistic synthetic data with no external calls.

Uses Geometric Brownian Motion for prices and templated news headlines.
This is the default data source when MOCK_MODE=true or when live APIs are unavailable.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from services.ingestion.base_connector import BaseConnector

# Realistic drift / volatility assumptions per asset class
_PARAMS: dict[str, dict] = {
    "stock": {"mu": 0.0003, "sigma": 0.015, "base": 150.0},
    "etf": {"mu": 0.0002, "sigma": 0.010, "base": 420.0},
    "crypto": {"mu": 0.0005, "sigma": 0.040, "base": 50_000.0},
    "forex": {"mu": 0.00005, "sigma": 0.004, "base": 1.10},
}

_BASE_PRICES: dict[str, float] = {
    "AAPL": 185.0, "MSFT": 420.0, "GOOGL": 175.0, "AMZN": 190.0,
    "TSLA": 250.0, "NVDA": 900.0, "META": 530.0,
    "SPY": 520.0, "QQQ": 440.0, "GLD": 220.0, "TLT": 95.0, "IWM": 200.0,
    "BTC/USDT": 68_000.0, "ETH/USDT": 3_500.0, "SOL/USDT": 175.0,
    "EURUSD=X": 1.085, "GBPUSD=X": 1.265,
}

_NEWS_TEMPLATES: list[dict] = [
    {"headline": "{sym} beats earnings estimates by 12%", "sentiment_hint": "positive"},
    {"headline": "{sym} misses revenue expectations for Q2", "sentiment_hint": "negative"},
    {"headline": "Analyst upgrades {sym} to Buy, raises PT to ${pt}", "sentiment_hint": "positive"},
    {"headline": "Analyst downgrades {sym} citing valuation concerns", "sentiment_hint": "negative"},
    {"headline": "{sym} announces $5B share buyback program", "sentiment_hint": "positive"},
    {"headline": "{sym} faces regulatory scrutiny from SEC", "sentiment_hint": "negative"},
    {"headline": "{sym} launches new product line, shares rise", "sentiment_hint": "positive"},
    {"headline": "Macro headwinds weigh on {sym} outlook", "sentiment_hint": "negative"},
    {"headline": "{sym} CEO buys $10M in stock on open market", "sentiment_hint": "positive"},
    {"headline": "Hedge fund exits large {sym} position", "sentiment_hint": "negative"},
    {"headline": "{sym} trading range remains tight; analysts mixed", "sentiment_hint": "neutral"},
    {"headline": "Market volatility creates opportunity in {sym}", "sentiment_hint": "neutral"},
]


def _asset_class_for(symbol: str) -> str:
    if symbol in ("BTC/USDT", "ETH/USDT", "SOL/USDT"):
        return "crypto"
    if symbol in ("EURUSD=X", "GBPUSD=X"):
        return "forex"
    if symbol in ("SPY", "QQQ", "GLD", "TLT", "IWM"):
        return "etf"
    return "stock"


def _seeded_rng(symbol: str) -> np.random.Generator:
    """Deterministic RNG per symbol so data is reproducible across restarts."""
    seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
    return np.random.default_rng(seed)


class MockConnector(BaseConnector):
    name = "mock"
    reliability_score = 0.95

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        ac = _asset_class_for(symbol)
        p = _PARAMS[ac]
        base_price = _BASE_PRICES.get(symbol, p["base"])

        rng = _seeded_rng(symbol)

        tf_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
        mins = tf_minutes.get(timeframe, 1440)

        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        if end is None:
            end = now
        if start is None:
            start = end - timedelta(minutes=mins * limit)

        n_bars = int((end - start).total_seconds() / 60 / mins) + 1
        n_bars = max(1, min(n_bars, limit))

        # GBM path
        dt = mins / (252 * 390)   # fraction of trading year
        log_returns = rng.normal(
            (p["mu"] - 0.5 * p["sigma"] ** 2) * dt,
            p["sigma"] * np.sqrt(dt),
            n_bars,
        )
        closes = base_price * np.exp(np.cumsum(log_returns))

        # Build OHLCV
        wicks = rng.uniform(0.001, p["sigma"] * 2, n_bars)
        opens = closes * (1 + rng.uniform(-wicks / 2, wicks / 2))
        highs = np.maximum(opens, closes) * (1 + rng.uniform(0, wicks))
        lows = np.minimum(opens, closes) * (1 - rng.uniform(0, wicks))
        base_vol = base_price * 1e6 / closes if ac != "crypto" else base_price * 100
        volumes = rng.uniform(0.5, 2.0, n_bars) * base_vol

        timestamps = [start + timedelta(minutes=i * mins) for i in range(n_bars)]

        df = pd.DataFrame(
            {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
            index=pd.DatetimeIndex(timestamps, tz="UTC"),
        )
        return df

    def fetch_news(self, symbol: str, limit: int = 10) -> List[dict]:
        rng = random.Random(symbol + str(datetime.now(timezone.utc).date()))
        base_price = _BASE_PRICES.get(symbol, 100.0)
        items = []
        for i in range(min(limit, len(_NEWS_TEMPLATES))):
            tmpl = rng.choice(_NEWS_TEMPLATES)
            pt = round(base_price * rng.uniform(1.05, 1.25), 0)
            headline = tmpl["headline"].format(sym=symbol.split("/")[0], pt=int(pt))
            items.append({
                "headline": headline,
                "source": rng.choice(["Reuters", "Bloomberg", "WSJ", "CNBC", "MarketWatch"]),
                "url": f"https://mock-news.example/{symbol.lower()}/{i}",
                "published_at": (
                    datetime.now(timezone.utc) - timedelta(hours=rng.randint(0, 48))
                ).isoformat(),
                "sentiment_hint": tmpl["sentiment_hint"],
                "symbol": symbol,
            })
        return items
