"""Shared constants across the platform."""
from __future__ import annotations

# Asset classes
ASSET_STOCK = "stock"
ASSET_ETF = "etf"
ASSET_CRYPTO = "crypto"
ASSET_FOREX = "forex"

ALL_ASSET_CLASSES = [ASSET_STOCK, ASSET_ETF, ASSET_CRYPTO, ASSET_FOREX]

# Signal directions
SIGNAL_BUY = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_HOLD = "HOLD"
SIGNAL_REDUCE = "REDUCE"
SIGNAL_EXIT = "EXIT"
SIGNAL_NEUTRAL = "NEUTRAL"

# Order status
ORDER_PENDING = "PENDING"
ORDER_SUBMITTED = "SUBMITTED"
ORDER_FILLED = "FILLED"
ORDER_PARTIAL = "PARTIAL_FILL"
ORDER_REJECTED = "REJECTED"
ORDER_CANCELLED = "CANCELLED"

# Order types
ORDER_MARKET = "MARKET"
ORDER_LIMIT = "LIMIT"
ORDER_STOP = "STOP"

# Order sides
SIDE_BUY = "BUY"
SIDE_SELL = "SELL"

# Risk decisions
RISK_APPROVED = "APPROVED"
RISK_REJECTED = "REJECTED"
RISK_REDUCE = "REDUCE_SIZE"

# Regime labels
REGIME_BULL = "BULL"
REGIME_BEAR = "BEAR"
REGIME_NEUTRAL = "NEUTRAL"
REGIME_VOLATILE = "VOLATILE"
REGIME_RISK_ON = "RISK_ON"
REGIME_RISK_OFF = "RISK_OFF"

# Timeframes
TF_1M = "1m"
TF_5M = "5m"
TF_15M = "15m"
TF_1H = "1h"
TF_4H = "4h"
TF_1D = "1d"
TF_1W = "1w"

# Agent names
AGENT_MARKET_DATA = "MarketDataAgent"
AGENT_NEWS = "NewsAgent"
AGENT_SENTIMENT = "SentimentAgent"
AGENT_FUNDAMENTALS = "FundamentalsAgent"
AGENT_MACRO = "MacroAgent"
AGENT_CRYPTO = "CryptoMicrostructureAgent"
AGENT_STRATEGY = "StrategyAgent"
AGENT_BULL = "BullAgent"
AGENT_BEAR = "BearAgent"
AGENT_RISK = "RiskAgent"
AGENT_PORTFOLIO = "PortfolioManagerAgent"
AGENT_EXECUTION = "ExecutionAgent"
AGENT_REFLECTION = "ReflectionAgent"

ALL_ANALYST_AGENTS = [
    AGENT_MARKET_DATA,
    AGENT_NEWS,
    AGENT_SENTIMENT,
    AGENT_FUNDAMENTALS,
    AGENT_MACRO,
]

# Sector labels
SECTORS = [
    "Technology", "Healthcare", "Financials", "Consumer Discretionary",
    "Communication Services", "Industrials", "Consumer Staples",
    "Energy", "Utilities", "Real Estate", "Materials", "Crypto", "Forex",
]

SECTOR_MAP: dict[str, str] = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Communication Services",
    "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
    "NVDA": "Technology", "META": "Communication Services",
    "SPY": "ETF", "QQQ": "ETF", "GLD": "ETF", "TLT": "ETF", "IWM": "ETF",
    "BTC/USDT": "Crypto", "ETH/USDT": "Crypto", "SOL/USDT": "Crypto",
    "EURUSD=X": "Forex", "GBPUSD=X": "Forex",
}
