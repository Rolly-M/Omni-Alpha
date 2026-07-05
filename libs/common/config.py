"""Central configuration — all settings loaded from .env or environment variables."""
from __future__ import annotations

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "OmniAlpha"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./omni_alpha.db",
        description="Async DB URL. SQLite for dev, asyncpg for production.",
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Modes ─────────────────────────────────────────────────────────────────
    MOCK_MODE: bool = Field(
        default=True,
        description="Use synthetic data — no external API keys required.",
    )
    LIVE_TRADING_ENABLED: bool = Field(
        default=False,
        description="DANGER: enables real broker connections. Paper-trading only when False.",
    )
    MANUAL_APPROVAL_REQUIRED: bool = Field(
        default=True,
        description="Require human approval before any order is submitted.",
    )

    # ── Portfolio ─────────────────────────────────────────────────────────────
    INITIAL_BALANCE: float = 100_000.0
    ACCOUNT_TYPE: str = "balanced"  # conservative | balanced | aggressive

    # ── Risk limits (fractions of portfolio unless noted) ────────────────────
    MAX_POSITION_SIZE_PCT: float = 0.05   # 5 % per position
    MAX_DAILY_LOSS_PCT: float = 0.02      # 2 % max daily loss
    MAX_DRAWDOWN_PCT: float = 0.15        # 15 % max drawdown before circuit-break
    MAX_LEVERAGE: float = 1.0             # no leverage by default
    MIN_CASH_PCT: float = 0.10            # keep ≥ 10 % cash
    MAX_SECTOR_EXPOSURE_PCT: float = 0.30 # 30 % max in one sector
    MAX_CORRELATION_THRESHOLD: float = 0.85

    # ── Execution simulation ──────────────────────────────────────────────────
    COMMISSION_RATE: float = 0.001   # 0.1 % per side
    SLIPPAGE_RATE: float = 0.0005    # 0.05 % market impact

    # ── Scheduling ────────────────────────────────────────────────────────────
    ANALYSIS_INTERVAL_SECONDS: int = 300  # run full pipeline every 5 min

    # ── Kill switch ───────────────────────────────────────────────────────────
    KILL_SWITCH_ENABLED: bool = False

    # ── Optional API keys ────────────────────────────────────────────────────
    ALPHA_VANTAGE_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    FINNHUB_KEY: Optional[str] = None
    POLYGON_KEY: Optional[str] = None
    FRED_API_KEY: Optional[str] = None
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None

    # ── Watchlists ───────────────────────────────────────────────────────────
    STOCK_WATCHLIST: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]
    ETF_WATCHLIST: List[str] = ["SPY", "QQQ", "GLD", "TLT", "IWM"]
    CRYPTO_WATCHLIST: List[str] = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    FOREX_WATCHLIST: List[str] = ["EURUSD=X", "GBPUSD=X"]

    @field_validator("ACCOUNT_TYPE")
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        valid = {"conservative", "balanced", "aggressive"}
        if v not in valid:
            raise ValueError(f"ACCOUNT_TYPE must be one of {valid}")
        return v

    @property
    def all_symbols(self) -> List[str]:
        return (
            self.STOCK_WATCHLIST
            + self.ETF_WATCHLIST
            + self.CRYPTO_WATCHLIST
            + self.FOREX_WATCHLIST
        )

    @property
    def is_postgres(self) -> bool:
        return "postgresql" in self.DATABASE_URL or "asyncpg" in self.DATABASE_URL


settings = Settings()
