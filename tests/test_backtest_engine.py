"""Tests for the backtest engine."""
import pytest
from services.backtest.engine import BacktestEngine, BacktestResult


def test_backtest_runs():
    engine = BacktestEngine(initial_equity=100_000)
    result = engine.run("AAPL", timeframe="1d", lookback_bars=100)
    assert isinstance(result, BacktestResult)


def test_backtest_equity_curve_length():
    engine = BacktestEngine()
    result = engine.run("MSFT", timeframe="1d", lookback_bars=100)
    assert len(result.equity_curve) > 50


def test_backtest_final_equity_positive():
    engine = BacktestEngine(initial_equity=100_000)
    result = engine.run("SPY", timeframe="1d", lookback_bars=100)
    assert result.final_equity > 0


def test_backtest_contains_warnings():
    engine = BacktestEngine()
    result = engine.run("AAPL", timeframe="1d", lookback_bars=100)
    assert len(result.warnings) > 0
    assert any("survivorship" in w.lower() for w in result.warnings)
    assert any("look-ahead" in w.lower() for w in result.warnings)


def test_win_rate_bounds():
    engine = BacktestEngine()
    result = engine.run("AAPL", timeframe="1d", lookback_bars=200)
    assert 0 <= result.win_rate_pct <= 100


def test_to_dict_serializable():
    import json
    engine = BacktestEngine()
    result = engine.run("AAPL", timeframe="1d", lookback_bars=100)
    json_str = json.dumps(result.to_dict(), default=str)
    assert "AAPL" in json_str


def test_backtest_too_few_bars_raises():
    engine = BacktestEngine()
    with pytest.raises(ValueError):
        engine.run("AAPL", timeframe="1d", lookback_bars=10)
