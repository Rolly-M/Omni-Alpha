"""Feature store — computes technical indicators from OHLCV DataFrames.

All indicators use vectorised pandas/numpy — no TA-Lib dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class FeatureSet:
    """All computed features for one symbol / timeframe."""
    symbol: str
    timeframe: str
    current_price: float
    # ── Trend ──────────────────────────────────────────────────────────────
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0
    trend_label: str = "NEUTRAL"   # UPTREND / DOWNTREND / NEUTRAL
    # ── Momentum ───────────────────────────────────────────────────────────
    rsi_14: float = 50.0
    rsi_label: str = "NEUTRAL"     # OVERSOLD / OVERBOUGHT / NEUTRAL
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    macd_cross: str = "NONE"       # BULLISH_CROSS / BEARISH_CROSS / NONE
    roc_10: float = 0.0            # rate of change 10 bar
    # ── Volatility ─────────────────────────────────────────────────────────
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_position: float = 0.5       # 0 = at lower, 1 = at upper band
    bb_squeeze: bool = False
    atr_14: float = 0.0
    atr_pct: float = 0.0           # ATR as % of price
    volatility_regime: str = "NORMAL"   # LOW / NORMAL / HIGH
    # ── Volume ─────────────────────────────────────────────────────────────
    volume_ratio: float = 1.0      # current / 20-bar avg
    volume_trend: str = "NORMAL"   # SPIKE / DRYING_UP / NORMAL
    # ── Price levels ───────────────────────────────────────────────────────
    high_52w: float = 0.0
    low_52w: float = 0.0
    pct_from_52w_high: float = 0.0
    # ── Returns ────────────────────────────────────────────────────────────
    return_1d: float = 0.0
    return_5d: float = 0.0
    return_20d: float = 0.0
    return_60d: float = 0.0
    # ── Composite ──────────────────────────────────────────────────────────
    bull_score: float = 0.0        # 0–100 sum of bullish evidence
    bear_score: float = 0.0        # 0–100 sum of bearish evidence
    signal_list: list[str] = field(default_factory=list)


class FeatureStore:
    """Stateless feature calculator — pass in a DataFrame, get a FeatureSet."""

    def compute(self, symbol: str, timeframe: str, df: pd.DataFrame) -> FeatureSet:
        if df.empty or len(df) < 20:
            return FeatureSet(symbol=symbol, timeframe=timeframe, current_price=0.0)

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        volume = df["volume"].astype(float)
        price = float(close.iloc[-1])

        fs = FeatureSet(symbol=symbol, timeframe=timeframe, current_price=price)
        signals: list[str] = []

        # ── Moving averages ───────────────────────────────────────────────
        fs.sma_20 = float(close.rolling(20).mean().iloc[-1])
        fs.sma_50 = float(close.rolling(min(50, len(df))).mean().iloc[-1])
        fs.sma_200 = float(close.rolling(min(200, len(df))).mean().iloc[-1])
        fs.ema_12 = float(close.ewm(span=12, adjust=False).mean().iloc[-1])
        fs.ema_26 = float(close.ewm(span=26, adjust=False).mean().iloc[-1])

        if price > fs.sma_20 > fs.sma_50:
            fs.trend_label = "UPTREND"
            fs.bull_score += 20
            signals.append(f"Uptrend: price {price:.2f} > SMA20 {fs.sma_20:.2f} > SMA50 {fs.sma_50:.2f}")
        elif price < fs.sma_20 < fs.sma_50:
            fs.trend_label = "DOWNTREND"
            fs.bear_score += 20
            signals.append(f"Downtrend: price {price:.2f} < SMA20 {fs.sma_20:.2f} < SMA50 {fs.sma_50:.2f}")

        # ── RSI ───────────────────────────────────────────────────────────
        fs.rsi_14 = float(self._rsi(close, 14).iloc[-1])
        if fs.rsi_14 < 30:
            fs.rsi_label = "OVERSOLD"
            fs.bull_score += 25
            signals.append(f"RSI oversold: {fs.rsi_14:.1f}")
        elif fs.rsi_14 > 70:
            fs.rsi_label = "OVERBOUGHT"
            fs.bear_score += 25
            signals.append(f"RSI overbought: {fs.rsi_14:.1f}")

        # ── MACD ──────────────────────────────────────────────────────────
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        fs.macd = float(macd_line.iloc[-1])
        fs.macd_signal = float(signal_line.iloc[-1])
        fs.macd_histogram = float(histogram.iloc[-1])

        if len(histogram) >= 2:
            if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0:
                fs.macd_cross = "BULLISH_CROSS"
                fs.bull_score += 20
                signals.append("MACD bullish crossover")
            elif histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0:
                fs.macd_cross = "BEARISH_CROSS"
                fs.bear_score += 20
                signals.append("MACD bearish crossover")

        # ── Bollinger Bands ───────────────────────────────────────────────
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        fs.bb_upper = float((bb_mid + 2 * bb_std).iloc[-1])
        fs.bb_middle = float(bb_mid.iloc[-1])
        fs.bb_lower = float((bb_mid - 2 * bb_std).iloc[-1])

        band_range = fs.bb_upper - fs.bb_lower
        if band_range > 0:
            fs.bb_position = (price - fs.bb_lower) / band_range

        # Squeeze: band width < 20-bar average
        bw = (bb_mid + 2 * bb_std) - (bb_mid - 2 * bb_std)
        fs.bb_squeeze = float(bw.iloc[-1]) < float(bw.rolling(20).mean().iloc[-1])

        if price < fs.bb_lower:
            fs.bull_score += 15
            signals.append(f"Price below lower BB ({fs.bb_lower:.2f})")
        elif price > fs.bb_upper:
            fs.bear_score += 15
            signals.append(f"Price above upper BB ({fs.bb_upper:.2f})")

        # ── ATR ───────────────────────────────────────────────────────────
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        fs.atr_14 = float(tr.rolling(14).mean().iloc[-1])
        fs.atr_pct = fs.atr_14 / price * 100 if price > 0 else 0

        if fs.atr_pct > 3.0:
            fs.volatility_regime = "HIGH"
            fs.bull_score *= 0.85
            fs.bear_score *= 0.85
            signals.append(f"High volatility: ATR={fs.atr_pct:.1f}%")
        elif fs.atr_pct < 0.5:
            fs.volatility_regime = "LOW"

        # ── Volume ────────────────────────────────────────────────────────
        avg_vol = float(volume.rolling(20).mean().iloc[-1])
        fs.volume_ratio = float(volume.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0
        if fs.volume_ratio > 2.0:
            fs.volume_trend = "SPIKE"
            signals.append(f"Volume spike: {fs.volume_ratio:.1f}x average")
        elif fs.volume_ratio < 0.5:
            fs.volume_trend = "DRYING_UP"

        # ── 52-week ───────────────────────────────────────────────────────
        bars_year = min(252, len(df))
        fs.high_52w = float(high.tail(bars_year).max())
        fs.low_52w = float(low.tail(bars_year).min())
        if fs.high_52w > 0:
            fs.pct_from_52w_high = (price - fs.high_52w) / fs.high_52w * 100

        # ── Returns ───────────────────────────────────────────────────────
        def _ret(n: int) -> float:
            if len(close) > n:
                return (float(close.iloc[-1]) - float(close.iloc[-n])) / float(close.iloc[-n]) * 100
            return 0.0

        fs.return_1d = _ret(1)
        fs.return_5d = _ret(5)
        fs.return_20d = _ret(20)
        fs.return_60d = _ret(60)

        # ── Rate of change ────────────────────────────────────────────────
        fs.roc_10 = _ret(10)
        if fs.roc_10 > 5:
            fs.bull_score += 10
        elif fs.roc_10 < -5:
            fs.bear_score += 10

        # Cap scores at 100
        fs.bull_score = min(100.0, fs.bull_score)
        fs.bear_score = min(100.0, fs.bear_score)
        fs.signal_list = signals
        return fs

    @staticmethod
    def _rsi(close: pd.Series, period: int) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))


_feature_store = FeatureStore()


def compute_features(symbol: str, timeframe: str, df: pd.DataFrame) -> FeatureSet:
    return _feature_store.compute(symbol, timeframe, df)
