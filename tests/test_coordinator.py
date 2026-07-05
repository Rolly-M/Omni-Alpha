"""Tests for the Coordinator pipeline."""
import pytest
from services.agents.coordinator import Coordinator, Decision


def test_coordinator_runs_single_symbol():
    coord = Coordinator()
    decisions = coord.run_cycle(symbols=["AAPL"])
    assert len(decisions) == 1
    assert isinstance(decisions[0], Decision)


def test_decision_has_required_fields():
    coord = Coordinator()
    d = coord.run_cycle(symbols=["MSFT"])[0]
    assert d.symbol == "MSFT"
    assert d.action in ("BUY", "SELL", "HOLD", "REDUCE", "EXIT", "NEUTRAL")
    assert 0 <= d.confidence <= 100
    assert d.risk_verdict in ("APPROVED", "REJECTED", "REDUCE_SIZE", "PENDING")
    assert d.agent_outputs  # at least some agent outputs


def test_multiple_symbols():
    coord = Coordinator()
    symbols = ["AAPL", "BTC/USDT", "EURUSD=X"]
    decisions = coord.run_cycle(symbols=symbols)
    assert len(decisions) == 3
    returned_symbols = {d.symbol for d in decisions}
    assert returned_symbols == set(symbols)


def test_decision_has_explanation():
    coord = Coordinator()
    d = coord.run_cycle(symbols=["SPY"])[0]
    assert len(d.explanation) > 20


def test_crypto_asset_class():
    coord = Coordinator()
    d = coord.run_cycle(symbols=["BTC/USDT"])[0]
    assert d.asset_class == "crypto"


def test_forex_asset_class():
    coord = Coordinator()
    d = coord.run_cycle(symbols=["EURUSD=X"])[0]
    assert d.asset_class == "forex"


def test_to_dict_is_json_serializable():
    import json
    coord = Coordinator()
    d = coord.run_cycle(symbols=["AAPL"])[0]
    json_str = json.dumps(d.to_dict(), default=str)
    assert "AAPL" in json_str
