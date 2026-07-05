"""Tests for RiskAgent."""
import pytest
from services.agents.risk_agent import RiskAgent, RiskVerdict
from libs.common.constants import RISK_APPROVED, RISK_REJECTED, RISK_REDUCE


def test_basic_approval(sample_features, demo_portfolio_state):
    agent = RiskAgent()
    verdict = agent.evaluate(
        symbol="AAPL",
        proposed_size_pct=0.02,
        portfolio_state=demo_portfolio_state,
        features=sample_features,
    )
    # Under normal conditions with healthy portfolio, should be approved
    assert verdict.verdict in (RISK_APPROVED, RISK_REDUCE)


def test_kill_switch_rejects_all():
    import os
    os.environ["KILL_SWITCH_ENABLED"] = "true"
    # Reload settings
    from importlib import reload
    import libs.common.config as cfg
    reload(cfg)
    from libs.common.config import settings
    settings.KILL_SWITCH_ENABLED = True

    agent = RiskAgent()
    verdict = agent.evaluate(symbol="AAPL", proposed_size_pct=0.02)
    assert verdict.verdict == RISK_REJECTED
    assert verdict.kill_switch_triggered

    # Reset
    settings.KILL_SWITCH_ENABLED = False
    os.environ["KILL_SWITCH_ENABLED"] = "false"


def test_daily_loss_limit():
    agent = RiskAgent()
    bad_state = {"cash_pct": 0.85, "daily_pnl_pct": -0.05, "drawdown_pct": 0.01}
    verdict = agent.evaluate(symbol="AAPL", proposed_size_pct=0.02, portfolio_state=bad_state)
    assert verdict.verdict == RISK_REJECTED
    assert any("daily" in r.lower() for r in verdict.reasons)


def test_max_drawdown_breached():
    agent = RiskAgent()
    bad_state = {"cash_pct": 0.60, "daily_pnl_pct": 0.0, "drawdown_pct": 0.20}
    verdict = agent.evaluate(symbol="AAPL", proposed_size_pct=0.02, portfolio_state=bad_state)
    assert verdict.verdict == RISK_REJECTED


def test_fat_finger_rejected():
    agent = RiskAgent()
    verdict = agent.evaluate(symbol="AAPL", proposed_size_pct=0.25)
    assert verdict.verdict == RISK_REJECTED
    assert any("fat" in r.lower() for r in verdict.reasons)


def test_size_reduction_on_high_volatility(sample_features):
    from services.ingestion.feature_store import FeatureSet
    sample_features.volatility_regime = "HIGH"
    sample_features.atr_pct = 4.0
    agent = RiskAgent()
    verdict = agent.evaluate(
        symbol="AAPL", proposed_size_pct=0.05, features=sample_features
    )
    # Should reduce size or reject
    assert verdict.verdict in (RISK_REDUCE, RISK_REJECTED)
