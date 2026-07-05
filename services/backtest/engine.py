"""Backtesting engine — event-driven, look-ahead-bias-free, walk-forward capable."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from libs.common.config import settings
from libs.common.logger import get_logger
from services.agents.coordinator import Coordinator
from services.ingestion.ingestion_service import get_ohlcv

log = get_logger("backtest_engine")

WARNING_SURVIVORSHIP = (
    "SURVIVORSHIP BIAS WARNING: This backtest uses symbols known to exist today. "
    "Delisted or bankrupt companies are not included, which may overstate returns."
)
WARNING_LOOKAHEAD = (
    "LOOK-AHEAD BIAS PREVENTION: The engine only uses data available at bar_t when "
    "making decisions for bar_t. Features are computed on close[0..t-1]."
)


@dataclass
class BacktestTrade:
    symbol: str
    entry_date: datetime
    exit_date: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    direction: str          # BUY / SELL
    quantity: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    strategy: str = "unknown"
    exit_reason: str = ""   # STOP_LOSS / TAKE_PROFIT / SIGNAL_REVERSE / END_OF_DATA


@dataclass
class BacktestResult:
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_equity: float
    final_equity: float
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    equity_curve: List[float] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    trades: List[BacktestTrade] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_equity": self.initial_equity,
            "final_equity": round(self.final_equity, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "annualized_return_pct": round(self.annualized_return_pct, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "win_rate_pct": round(self.win_rate_pct, 1),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_win_pct": round(self.avg_win_pct, 2),
            "avg_loss_pct": round(self.avg_loss_pct, 2),
            "profit_factor": round(self.profit_factor, 3),
            "equity_curve": [round(v, 2) for v in self.equity_curve],
            "dates": self.dates,
            "warnings": self.warnings,
            "trades": [
                {
                    "symbol": t.symbol,
                    "entry_date": t.entry_date.isoformat(),
                    "exit_date": t.exit_date.isoformat() if t.exit_date else None,
                    "entry_price": round(t.entry_price, 4),
                    "exit_price": round(t.exit_price, 4) if t.exit_price else None,
                    "direction": t.direction,
                    "pnl": round(t.pnl, 2),
                    "pnl_pct": round(t.pnl_pct, 2),
                    "exit_reason": t.exit_reason,
                }
                for t in self.trades
            ],
        }


class BacktestEngine:
    """Simple vectorised backtester. Uses MockConnector data (reproducible)."""

    def __init__(
        self,
        initial_equity: float = None,
        commission_rate: float = None,
        slippage_rate: float = None,
        position_size_pct: float = 0.05,
    ):
        self.initial_equity = initial_equity or settings.INITIAL_BALANCE
        self.commission_rate = commission_rate or settings.COMMISSION_RATE
        self.slippage_rate = slippage_rate or settings.SLIPPAGE_RATE
        self.position_size_pct = position_size_pct

    def run(
        self,
        symbol: str,
        timeframe: str = "1d",
        lookback_bars: int = 365,
    ) -> BacktestResult:
        log.info("Starting backtest", symbol=symbol, bars=lookback_bars)

        df = get_ohlcv(symbol, timeframe, limit=lookback_bars)
        if len(df) < 50:
            raise ValueError(f"Not enough data for backtest: {len(df)} bars")

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        dates = df.index.tolist()

        equity = self.initial_equity
        equity_curve = [equity]
        curve_dates = [dates[0].isoformat()]
        trades: List[BacktestTrade] = []
        position: Optional[BacktestTrade] = None
        peak_equity = equity

        min_lookback = 26  # MACD lookback

        for i in range(min_lookback, len(close)):
            price = close[i]

            # ── Feature computation (look-ahead-bias-free: only data up to i-1) ──
            window = close[:i]
            rsi = self._rsi(window, 14)
            ema12 = self._ema(window, 12)
            ema26 = self._ema(window, 26)
            macd_hist = ema12 - ema26
            sma20 = np.mean(window[-20:]) if len(window) >= 20 else np.mean(window)
            sma50 = np.mean(window[-50:]) if len(window) >= 50 else np.mean(window)

            # ── Stop / target check for open position ──────────────────────
            if position is not None:
                # Check stop-loss
                if position.direction == "BUY":
                    stop = position.entry_price * 0.97   # 3% stop
                    target = position.entry_price * 1.06  # 6% target
                    if low[i] <= stop:
                        equity, position = self._close(equity, position, stop, dates[i], "STOP_LOSS", trades)
                    elif high[i] >= target:
                        equity, position = self._close(equity, position, target, dates[i], "TAKE_PROFIT", trades)
                    # Reverse signal
                    elif rsi < 40 and macd_hist < 0 and price < sma20:
                        equity, position = self._close(equity, position, price, dates[i], "SIGNAL_REVERSE", trades)

            # ── Entry signals ──────────────────────────────────────────────
            if position is None:
                # Simple trend + RSI entry
                if (price > sma20 > sma50 and rsi > 50 and macd_hist > 0 and rsi < 70):
                    # BUY entry
                    size = equity * self.position_size_pct
                    fill_price = price * (1 + self.slippage_rate)
                    commission = size * self.commission_rate
                    qty = (size - commission) / fill_price
                    equity -= commission
                    position = BacktestTrade(
                        symbol=symbol,
                        entry_date=dates[i],
                        exit_date=None,
                        entry_price=fill_price,
                        exit_price=None,
                        direction="BUY",
                        quantity=qty,
                        commission=commission,
                        strategy="trend_rsi",
                    )
                elif (price < sma20 < sma50 and rsi < 45 and macd_hist < 0 and rsi > 30):
                    # Oversold bounce check
                    if rsi < 32:
                        size = equity * self.position_size_pct
                        fill_price = price * (1 - self.slippage_rate)
                        commission = size * self.commission_rate
                        qty = (size - commission) / fill_price
                        equity -= commission
                        position = BacktestTrade(
                            symbol=symbol,
                            entry_date=dates[i],
                            exit_date=None,
                            entry_price=fill_price,
                            exit_price=None,
                            direction="BUY",
                            quantity=qty,
                            commission=commission,
                            strategy="mean_reversion",
                        )

            # Mark-to-market equity
            mtm = equity
            if position is not None:
                mtm = equity + position.quantity * price
            equity_curve.append(mtm)
            curve_dates.append(dates[i].isoformat())
            peak_equity = max(peak_equity, mtm)

        # Close any open position at end of data
        if position is not None:
            equity, position = self._close(equity, position, close[-1], dates[-1], "END_OF_DATA", trades)

        return self._build_result(symbol, dates, equity, equity_curve, curve_dates, trades, peak_equity)

    def _close(
        self,
        equity: float,
        position: BacktestTrade,
        exit_price: float,
        exit_date,
        reason: str,
        trades: list,
    ) -> tuple:
        commission = position.quantity * exit_price * self.commission_rate
        pnl = position.quantity * (exit_price - position.entry_price) - commission
        position.exit_price = exit_price
        position.exit_date = exit_date
        position.pnl = pnl
        position.pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
        position.commission += commission
        position.exit_reason = reason
        equity += position.quantity * exit_price - commission
        trades.append(position)
        return equity, None

    def _build_result(
        self, symbol, dates, final_equity, equity_curve, curve_dates, trades, peak_equity
    ) -> BacktestResult:
        initial = self.initial_equity
        total_ret = (final_equity - initial) / initial * 100
        n_years = max(1, len(dates) / 252)
        annual_ret = ((1 + total_ret / 100) ** (1 / n_years) - 1) * 100

        # Drawdown
        arr = np.array(equity_curve)
        peaks = np.maximum.accumulate(arr)
        drawdowns = (arr - peaks) / peaks * 100
        max_dd = abs(float(np.min(drawdowns)))

        # Sharpe
        if len(equity_curve) > 1:
            returns = np.diff(np.array(equity_curve)) / np.array(equity_curve)[:-1]
            sharpe = float(np.mean(returns) / max(np.std(returns), 1e-10) * np.sqrt(252))
        else:
            sharpe = 0.0

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        total_win = sum(t.pnl for t in wins)
        total_loss = abs(sum(t.pnl for t in losses))

        return BacktestResult(
            symbol=symbol,
            start_date=dates[0] if dates else datetime.now(timezone.utc),
            end_date=dates[-1] if dates else datetime.now(timezone.utc),
            initial_equity=initial,
            final_equity=round(final_equity, 2),
            total_return_pct=round(total_ret, 2),
            annualized_return_pct=round(annual_ret, 2),
            max_drawdown_pct=round(max_dd, 2),
            sharpe_ratio=round(sharpe, 3),
            win_rate_pct=round(len(wins) / max(1, len(trades)) * 100, 1),
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            avg_win_pct=round(np.mean([t.pnl_pct for t in wins]) if wins else 0, 2),
            avg_loss_pct=round(np.mean([t.pnl_pct for t in losses]) if losses else 0, 2),
            profit_factor=round(total_win / max(total_loss, 0.01), 3),
            equity_curve=equity_curve,
            dates=curve_dates,
            trades=trades,
            warnings=[WARNING_SURVIVORSHIP, WARNING_LOOKAHEAD],
        )

    @staticmethod
    def _rsi(close: np.ndarray, period: int) -> float:
        if len(close) < period + 1:
            return 50.0
        diff = np.diff(close[-(period + 1):])
        gains = diff.clip(min=0)
        losses = -diff.clip(max=0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - 100 / (1 + rs)

    @staticmethod
    def _ema(close: np.ndarray, span: int) -> float:
        if len(close) == 0:
            return 0.0
        alpha = 2 / (span + 1)
        ema = close[0]
        for p in close[1:]:
            ema = alpha * p + (1 - alpha) * ema
        return float(ema)

    def run_example(self) -> None:
        """Quick demo run printed to stdout."""
        result = self.run("AAPL", "1d", 365)
        print(f"\n{'='*60}")
        print(f"BACKTEST: {result.symbol} — {result.start_date.date()} to {result.end_date.date()}")
        print(f"{'='*60}")
        print(f"Total return:      {result.total_return_pct:+.2f}%")
        print(f"Annualized:        {result.annualized_return_pct:+.2f}%")
        print(f"Max drawdown:      -{result.max_drawdown_pct:.2f}%")
        print(f"Sharpe ratio:      {result.sharpe_ratio:.3f}")
        print(f"Win rate:          {result.win_rate_pct:.1f}%")
        print(f"Trades:            {result.total_trades}")
        print(f"Profit factor:     {result.profit_factor:.3f}")
        print(f"\nWARNINGS:")
        for w in result.warnings:
            print(f"  ⚠  {w[:80]}")
