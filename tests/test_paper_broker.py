"""Tests for PaperBroker."""
import pytest
from services.execution.paper_broker import PaperBroker
from libs.common.constants import ORDER_FILLED, ORDER_PARTIAL, ORDER_REJECTED


def test_basic_buy_fills():
    broker = PaperBroker(commission_rate=0.001, slippage_rate=0.0005, partial_fill_probability=0)
    order = broker.submit("AAPL", "BUY", 10.0, market_price=185.0)
    assert order.status == ORDER_FILLED
    assert order.filled_quantity == 10.0
    assert order.average_fill_price > 185.0  # slippage adds cost
    assert order.commission > 0
    assert order.is_paper is True


def test_basic_sell_fills():
    broker = PaperBroker(partial_fill_probability=0)
    order = broker.submit("AAPL", "SELL", 10.0, market_price=185.0)
    assert order.status == ORDER_FILLED
    assert order.average_fill_price < 185.0  # slippage reduces proceeds


def test_duplicate_prevention():
    broker = PaperBroker(partial_fill_probability=0)
    order1 = broker.submit("AAPL", "BUY", 10.0, market_price=185.0)
    order2 = broker.submit("AAPL", "BUY", 5.0, market_price=186.0)
    assert order2.status == ORDER_REJECTED
    assert order2.rejection_reason is not None


def test_kill_switch_blocks_orders():
    from libs.common.config import settings
    settings.KILL_SWITCH_ENABLED = True
    broker = PaperBroker()
    order = broker.submit("AAPL", "BUY", 10.0, market_price=185.0)
    assert order.status == ORDER_REJECTED
    assert "KILL" in order.rejection_reason.upper()
    settings.KILL_SWITCH_ENABLED = False


def test_partial_fill_simulation():
    broker = PaperBroker(partial_fill_probability=1.0)  # always partial
    order = broker.submit("MSFT", "BUY", 20.0, market_price=420.0)
    assert order.status == ORDER_PARTIAL
    assert 0 < order.filled_quantity < 20.0


def test_order_is_stored():
    broker = PaperBroker(partial_fill_probability=0)
    order = broker.submit("TSLA", "BUY", 5.0, market_price=250.0)
    retrieved = broker.get_order(order.order_id)
    assert retrieved is not None
    assert retrieved.symbol == "TSLA"
