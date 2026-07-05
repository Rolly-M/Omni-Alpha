"""Ingestion service — selects the right connector and coordinates data fetching."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd

from libs.common.config import settings
from libs.common.logger import get_logger
from services.ingestion.mock_connector import MockConnector
from services.ingestion.yfinance_connector import YFinanceConnector
from services.ingestion.feature_store import FeatureSet, compute_features

log = get_logger("ingestion_service")

_mock = MockConnector()
_yf = YFinanceConnector()

# In-memory cache: {symbol: {timeframe: (df, fetched_at)}}
_cache: Dict[str, Dict[str, tuple]] = {}
CACHE_TTL_SECONDS = 120


def _get_connector():
    if settings.MOCK_MODE:
        return _mock
    return _yf


def get_ohlcv(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 500,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Fetch OHLCV data, using in-memory cache when fresh enough."""
    now = datetime.now(timezone.utc).timestamp()
    cached = _cache.get(symbol, {}).get(timeframe)
    if cached and not force_refresh:
        df, fetched_at = cached
        if now - fetched_at < CACHE_TTL_SECONDS:
            return df

    connector = _get_connector()
    df = connector.fetch_ohlcv(symbol, timeframe, limit=limit)

    if symbol not in _cache:
        _cache[symbol] = {}
    _cache[symbol][timeframe] = (df, now)

    log.debug("Fetched OHLCV", symbol=symbol, tf=timeframe, rows=len(df), source=connector.name)
    return df


def get_features(symbol: str, timeframe: str = "1d", limit: int = 500) -> FeatureSet:
    df = get_ohlcv(symbol, timeframe, limit)
    return compute_features(symbol, timeframe, df)


def get_news(symbol: str, limit: int = 10) -> List[dict]:
    connector = _get_connector()
    return connector.fetch_news(symbol, limit)


def get_bulk_features(symbols: List[str], timeframe: str = "1d") -> Dict[str, FeatureSet]:
    """Fetch features for all symbols. Returns dict keyed by symbol."""
    result = {}
    for sym in symbols:
        try:
            result[sym] = get_features(sym, timeframe)
        except Exception as exc:
            log.warning("Feature computation failed", symbol=sym, error=str(exc))
    return result
