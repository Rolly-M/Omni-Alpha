"""Tests for the mock data connector."""
import pytest
import pandas as pd
from services.ingestion.mock_connector import MockConnector


def test_fetch_ohlcv_returns_dataframe():
    conn = MockConnector()
    df = conn.fetch_ohlcv("AAPL", "1d", limit=100)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 100


def test_ohlcv_has_required_columns():
    conn = MockConnector()
    df = conn.fetch_ohlcv("AAPL", "1d", limit=50)
    for col in ["open", "high", "low", "close", "volume"]:
        assert col in df.columns


def test_ohlcv_prices_are_positive():
    conn = MockConnector()
    df = conn.fetch_ohlcv("BTC/USDT", "1d", limit=50)
    assert (df["close"] > 0).all()
    assert (df["volume"] > 0).all()


def test_high_gte_low():
    conn = MockConnector()
    df = conn.fetch_ohlcv("MSFT", "1d", limit=100)
    assert (df["high"] >= df["low"]).all()


def test_timestamps_are_utc():
    conn = MockConnector()
    df = conn.fetch_ohlcv("AAPL", "1d", limit=10)
    assert str(df.index.tz) == "UTC"


def test_reproducibility():
    conn = MockConnector()
    df1 = conn.fetch_ohlcv("AAPL", "1d", limit=50)
    df2 = conn.fetch_ohlcv("AAPL", "1d", limit=50)
    # Same symbol → same seed → same data
    assert abs(df1["close"].iloc[-1] - df2["close"].iloc[-1]) < 0.01


def test_different_symbols_different_prices():
    conn = MockConnector()
    df_aapl = conn.fetch_ohlcv("AAPL", "1d", limit=50)
    df_msft = conn.fetch_ohlcv("MSFT", "1d", limit=50)
    assert not (df_aapl["close"].values == df_msft["close"].values).all()


def test_fetch_news_returns_list():
    conn = MockConnector()
    news = conn.fetch_news("AAPL", limit=5)
    assert isinstance(news, list)
    assert len(news) <= 5


def test_news_has_required_keys():
    conn = MockConnector()
    news = conn.fetch_news("MSFT", limit=3)
    for item in news:
        assert "headline" in item
        assert "published_at" in item
        assert "sentiment_hint" in item
