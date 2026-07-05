"""Abstract base class for all market-data connectors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

import pandas as pd


class BaseConnector(ABC):
    """All connectors must implement this interface.

    Every connector MUST:
    - Normalise timestamps to UTC.
    - Return a DataFrame with columns [open, high, low, close, volume] indexed by a UTC datetime.
    - Handle rate limits internally (tenacity retry).
    - Return an empty DataFrame (never raise) when data is unavailable.
    """

    name: str = "base"
    reliability_score: float = 1.0

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        """Return OHLCV bars for *symbol*.

        Returns a DataFrame with a UTC DatetimeIndex and columns:
        open, high, low, close, volume (all float64).
        Empty DataFrame on failure — never raises.
        """

    @abstractmethod
    def fetch_news(self, symbol: str, limit: int = 20) -> List[dict]:
        """Return a list of news dicts with keys:
        headline, source, url, published_at (ISO-8601 UTC), sentiment_hint.
        """

    def is_available(self) -> bool:
        """Quick health check — override for connectors that need auth."""
        return True
