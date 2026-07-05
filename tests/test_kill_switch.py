"""Tests for the kill switch."""
import pytest
from services.risk.kill_switch import KillSwitch


def test_kill_switch_starts_inactive():
    ks = KillSwitch()
    # By default (env var KILL_SWITCH_ENABLED=false in conftest)
    ks._enabled = False
    assert not ks.is_active


def test_activate_and_check():
    ks = KillSwitch()
    ks._enabled = False
    ks.activate(reason="Test activation", triggered_by="pytest")
    assert ks.is_active
    assert ks._reason == "Test activation"
    ks.deactivate()


def test_deactivate():
    ks = KillSwitch()
    ks.activate(reason="Test")
    ks.deactivate(authorized_by="test_user")
    assert not ks._enabled


def test_assert_inactive_raises_when_active():
    ks = KillSwitch()
    ks.activate(reason="Test")
    with pytest.raises(RuntimeError, match="Kill switch is active"):
        ks.assert_inactive()
    ks.deactivate()


def test_status_dict():
    ks = KillSwitch()
    ks.activate(reason="Test")
    status = ks.status()
    assert status["active"] is True
    assert status["reason"] == "Test"
    assert status["triggered_at"] is not None
    ks.deactivate()
