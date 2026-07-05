"""yfinance connector — free, no API key required.

Falls back to MockConnector on any error.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from libs.common.logger import get_logger
from services.ingestion.base_connector import BaseConnector
from services.ingestion.mock_connector import MockConnector

log = get_logger("yfinance_connector")

_TF_MAP = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "1d": "1d", "1w": "1wk"}

_fallback = MockConnector()


class YFinanceConnector(BaseConnector):
    name = "yfinance"
    reliability_score = 0.85

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        try:
            import yfinance as yf

            period_map = {
                "1m": "7d", "5m": "60d", "15m": "60d",
                "1h": "730d", "1d": "max", "1w": "max",
            }
            interval = _TF_MAP.get(timeframe, "1d")
            period = period_map.get(timeframe, "2y")

            # yfinance uses the raw Yahoo ticker (no "/" for crypto)
            ticker = symbol.replace("/", "-")
            df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)

            if df.empty:
                log.warning("yfinance returned empty df", symbol=symbol)
                return _fallback.fetch_ohlcv(symbol, timeframe, start, end, limit)

            df.columns = [c.lower() for c in df.columns]
            df.index = pd.to_datetime(df.index, utc=True)
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            if limit:
                df = df.tail(limit)
            return df
        except Exception as exc:
            log.warning("yfinance failed, using mock", symbol=symbol, error=str(exc))
            return _fallback.fetch_ohlcv(symbol, timeframe, start, end, limit)

    def fetch_news(self, symbol: str, limit: int = 10) -> List[dict]:
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol.replace("/", "-"))
            news = ticker.news or []
            results = []
            for item in news[:limit]:
                results.append({
                    "headline": item.get("title", ""),
                    "source": item.get("publisher", "Yahoo Finance"),
                    "url": item.get("link", ""),
                    "published_at": datetime.utcfromtimestamp(
                        item.get("providerPublishTime", 0)
                    ).isoformat() + "Z",
                    "sentiment_hint": "neutral",
                    "symbol": symbol,
                })
            return results or _fallback.fetch_news(symbol, limit)
        except Exception as exc:
            log.warning("yfinance news failed, using mock", symbol=symbol, error=str(exc))
            return _fallback.fetch_news(symbol, limit)
