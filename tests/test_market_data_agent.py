"""Tests for MarketDataAgent."""
import pytest
from services.agents.market_data_agent import MarketDataAgent
from services.agents.base_agent import AgentOutput


def test_agent_returns_output(sample_features):
    agent = MarketDataAgent()
    out = agent.run("AAPL", features=sample_features)
    assert isinstance(out, AgentOutput)


def test_signal_type_is_valid(sample_features):
    agent = MarketDataAgent()
    out = agent.run("AAPL", features=sample_features)
    assert out.signal_type in ("BUY", "SELL", "HOLD", "NEUTRAL")


def test_confidence_bounds(sample_features):
    agent = MarketDataAgent()
    out = agent.run("AAPL", features=sample_features)
    assert 0 <= out.confidence <= 100


def test_risk_score_bounds(sample_features):
    agent = MarketDataAgent()
    out = agent.run("AAPL", features=sample_features)
    assert 0 <= out.risk_score <= 100


def test_thesis_is_nonempty(sample_features):
    agent = MarketDataAgent()
    out = agent.run("AAPL", features=sample_features)
    assert len(out.thesis) > 10


def test_agent_recovers_from_error():
    """If features is None and mock mode fails, agent returns NEUTRAL gracefully."""
    agent = MarketDataAgent()
    out = agent.run("UNKNOWN_SYMBOL_XYZ")
    # Either a valid signal or graceful NEUTRAL
    assert out.signal_type in ("BUY", "SELL", "HOLD", "NEUTRAL")


def test_to_dict_serializable(sample_features):
    import json
    agent = MarketDataAgent()
    out = agent.run("AAPL", features=sample_features)
    d = out.to_dict()
    json_str = json.dumps(d)
    assert "AAPL" in json_str
