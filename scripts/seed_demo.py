"""Seed script — initialises the database and inserts demo data.

Run: python scripts/seed_demo.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timedelta, timezone

from libs.common.database import create_all_tables, async_session_factory
from libs.common.models.market import Instrument, DataSource
from libs.common.models.orders import Order, Position
from libs.common.models.portfolio import Account, Portfolio
from libs.common.config import settings
from libs.common.logger import configure_logging, get_logger

configure_logging()
log = get_logger("seed")

INSTRUMENTS = [
    ("AAPL", "Apple Inc.", "stock", "NASDAQ", "Technology"),
    ("MSFT", "Microsoft Corp.", "stock", "NASDAQ", "Technology"),
    ("GOOGL", "Alphabet Inc.", "stock", "NASDAQ", "Communication Services"),
    ("AMZN", "Amazon.com Inc.", "stock", "NASDAQ", "Consumer Discretionary"),
    ("TSLA", "Tesla Inc.", "stock", "NASDAQ", "Consumer Discretionary"),
    ("NVDA", "NVIDIA Corp.", "stock", "NASDAQ", "Technology"),
    ("META", "Meta Platforms", "stock", "NASDAQ", "Communication Services"),
    ("SPY", "SPDR S&P 500 ETF", "etf", "NYSE", "ETF"),
    ("QQQ", "Invesco QQQ ETF", "etf", "NASDAQ", "ETF"),
    ("GLD", "SPDR Gold Shares ETF", "etf", "NYSE", "ETF"),
    ("TLT", "iShares 20+ Year Treasury ETF", "etf", "NASDAQ", "ETF"),
    ("IWM", "iShares Russell 2000 ETF", "etf", "NYSE", "ETF"),
    ("BTC/USDT", "Bitcoin / USDT", "crypto", "BINANCE", "Crypto"),
    ("ETH/USDT", "Ethereum / USDT", "crypto", "BINANCE", "Crypto"),
    ("SOL/USDT", "Solana / USDT", "crypto", "BINANCE", "Crypto"),
    ("EURUSD=X", "EUR/USD", "forex", "FOREX", "Forex"),
    ("GBPUSD=X", "GBP/USD", "forex", "FOREX", "Forex"),
]

DATA_SOURCES = [
    ("mock_connector", "prices", 0.95),
    ("yfinance", "prices", 0.85),
    ("rss_news", "news", 0.80),
    ("synthetic_sentiment", "sentiment", 0.70),
    ("static_fundamentals", "fundamentals", 0.90),
    ("mock_macro", "macro", 0.75),
]


async def seed():
    log.info("Creating tables...")
    await create_all_tables()

    async with async_session_factory() as session:
        # Instruments
        from sqlalchemy import select
        result = await session.execute(select(Instrument).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            log.info("Instruments already seeded, skipping.")
        else:
            for sym, name, ac, exchange, sector in INSTRUMENTS:
                inst = Instrument(
                    symbol=sym, name=name, asset_class=ac,
                    exchange=exchange, sector=sector,
                )
                session.add(inst)
            log.info(f"Added {len(INSTRUMENTS)} instruments")

        # Data sources
        for name, stype, reliability in DATA_SOURCES:
            ds = DataSource(name=name, source_type=stype, reliability_score=reliability)
            session.add(ds)

        # Demo account
        account = Account(
            id="demo-001",
            name="Demo Account",
            account_type=settings.ACCOUNT_TYPE,
            initial_balance=settings.INITIAL_BALANCE,
            cash_balance=settings.INITIAL_BALANCE * 0.85,
            total_equity=settings.INITIAL_BALANCE * 1.023,
            is_paper=True,
        )
        session.add(account)

        # Demo positions
        now = datetime.now(timezone.utc)
        demo_positions = [
            Position(portfolio_id="demo-001", symbol="AAPL", asset_class="stock",
                     quantity=25.0, average_cost=183.40, current_price=185.20,
                     unrealized_pnl=45.0, opened_at=now - timedelta(days=3)),
            Position(portfolio_id="demo-001", symbol="MSFT", asset_class="stock",
                     quantity=10.0, average_cost=415.0, current_price=422.10,
                     unrealized_pnl=71.0, opened_at=now - timedelta(days=2)),
        ]
        for pos in demo_positions:
            session.add(pos)

        await session.commit()

    log.info("✅ Seed complete — OmniAlpha demo data loaded.")
    print(f"\n{'='*50}")
    print("✅ OmniAlpha demo data seeded successfully!")
    print(f"  Account: Demo Account (paper)")
    print(f"  Balance: ${settings.INITIAL_BALANCE:,.0f}")
    print(f"  Instruments: {len(INSTRUMENTS)}")
    print(f"  Data sources: {len(DATA_SOURCES)}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    asyncio.run(seed())
