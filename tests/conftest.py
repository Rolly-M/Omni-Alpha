"""Shared test fixtures."""
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force mock mode for all tests
os.environ["MOCK_MODE"] = "true"
os.environ["LIVE_TRADING_ENABLED"] = "false"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["KILL_SWITCH_ENABLED"] = "false"
os.environ["INITIAL_BALANCE"] = "100000.0"

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone


@pytest.fixture
def sample_ohlcv():
    """200-bar daily OHLCV DataFrame for AAPL."""
    n = 200
    rng = np.random.default_rng(42)
    close = 150.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, n)))
    high = close * (1 + rng.uniform(0.001, 0.02, n))
    low = close * (1 - rng.uniform(0.001, 0.02, n))
    opens = close * (1 + rng.uniform(-0.01, 0.01, n))
    volume = rng.uniform(50_000, 200_000, n) * 1000
    timestamps = [
        datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)
        for i in range(n)
    ]
    return pd.DataFrame(
        {"open": opens, "high": high, "low": low, "close": close, "volume": volume},
        index=pd.DatetimeIndex(timestamps, tz="UTC"),
    )


@pytest.fixture
def sample_features(sample_ohlcv):
    from services.ingestion.feature_store import compute_features
    return compute_features("AAPL", "1d", sample_ohlcv)


@pytest.fixture
def sample_news():
    return [
        {"headline": "AAPL beats earnings by 12%", "source": "Reuters",
         "published_at": datetime.now(timezone.utc).isoformat(),
         "sentiment_hint": "positive", "symbol": "AAPL"},
        {"headline": "Macro headwinds weigh on AAPL outlook", "source": "Bloomberg",
         "published_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
         "sentiment_hint": "negative", "symbol": "AAPL"},
    ]


@pytest.fixture
def demo_portfolio_state():
    return {
        "cash_pct": 0.85,
        "daily_pnl_pct": 0.001,
        "drawdown_pct": 0.01,
        "sector_exposure": {"Technology": 0.10},
    }


@pytest.fixture
def demo_account_state():
    return {
        "total_equity": 100_000.0,
        "current_price": {"AAPL": 185.0},
    }
