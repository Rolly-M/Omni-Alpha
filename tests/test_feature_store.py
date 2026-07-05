"""Tests for feature store — technical indicator computation."""
import numpy as np
import pandas as pd
import pytest
from services.ingestion.feature_store import FeatureStore, FeatureSet, compute_features


def test_compute_features_returns_feature_set(sample_ohlcv):
    fs = compute_features("AAPL", "1d", sample_ohlcv)
    assert isinstance(fs, FeatureSet)
    assert fs.symbol == "AAPL"
    assert fs.timeframe == "1d"


def test_current_price_matches_last_close(sample_ohlcv):
    fs = compute_features("AAPL", "1d", sample_ohlcv)
    assert abs(fs.current_price - float(sample_ohlcv["close"].iloc[-1])) < 0.001


def test_rsi_bounds(sample_ohlcv):
    fs = compute_features("AAPL", "1d", sample_ohlcv)
    assert 0 <= fs.rsi_14 <= 100


def test_bb_position_bounds(sample_ohlcv):
    fs = compute_features("AAPL", "1d", sample_ohlcv)
    # BB position is not strictly bounded but should be reasonable
    assert -2 < fs.bb_position < 3


def test_bull_bear_scores_non_negative(sample_ohlcv):
    fs = compute_features("AAPL", "1d", sample_ohlcv)
    assert fs.bull_score >= 0
    assert fs.bear_score >= 0


def test_bull_bear_scores_max_100(sample_ohlcv):
    fs = compute_features("AAPL", "1d", sample_ohlcv)
    assert fs.bull_score <= 100
    assert fs.bear_score <= 100


def test_volume_ratio_positive(sample_ohlcv):
    fs = compute_features("AAPL", "1d", sample_ohlcv)
    assert fs.volume_ratio > 0


def test_empty_dataframe_returns_zero_price():
    fs = compute_features("AAPL", "1d", pd.DataFrame())
    assert fs.current_price == 0.0


def test_small_dataframe_handled(sample_ohlcv):
    """15 bars is below lookback — should not raise."""
    small_df = sample_ohlcv.tail(15)
    fs = compute_features("AAPL", "1d", small_df)
    assert fs.current_price > 0  # price extracted even with small window


def test_trend_labels_are_valid(sample_ohlcv):
    fs = compute_features("AAPL", "1d", sample_ohlcv)
    assert fs.trend_label in ("UPTREND", "DOWNTREND", "NEUTRAL")


def test_volatility_regime_valid(sample_ohlcv):
    fs = compute_features("AAPL", "1d", sample_ohlcv)
    assert fs.volatility_regime in ("LOW", "NORMAL", "HIGH")


def test_returns_computed(sample_ohlcv):
    fs = compute_features("AAPL", "1d", sample_ohlcv)
    # Should have 200 bars, so all return windows are available
    assert isinstance(fs.return_20d, float)
    assert isinstance(fs.return_60d, float)
