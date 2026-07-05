"""Market Data Agent — technical analysis, trend, volatility, volume anomalies."""
from __future__ import annotations

from services.agents.base_agent import AgentOutput, BaseAgent
from services.ingestion.feature_store import FeatureSet


class MarketDataAgent(BaseAgent):
    name = "MarketDataAgent"

    def _analyze(self, symbol: str, features: FeatureSet = None, **kwargs) -> AgentOutput:  # type: ignore[override]
        if features is None:
            from services.ingestion.ingestion_service import get_features
            features = get_features(symbol, kwargs.get("timeframe", "1d"))

        fs = features
        bull = fs.bull_score
        bear = fs.bear_score
        signals = list(fs.signal_list)

        net = bull - bear
        if net > 25:
            signal_type = "BUY"
            confidence = min(90.0, 50 + net * 0.8)
        elif net < -25:
            signal_type = "SELL"
            confidence = min(90.0, 50 + abs(net) * 0.8)
        else:
            signal_type = "HOLD"
            confidence = max(30.0, 60 - abs(net))

        risk_score = min(100.0, fs.atr_pct * 15 + (20 if fs.volatility_regime == "HIGH" else 0))

        bull_sigs = [s for s in signals if any(
            kw in s.lower() for kw in ["oversold", "below", "uptrend", "bullish", "spike"]
        )]
        bear_sigs = [s for s in signals if any(
            kw in s.lower() for kw in ["overbought", "above", "downtrend", "bearish", "high vol"]
        )]

        thesis = (
            f"{symbol} technical analysis ({fs.timeframe}): "
            f"RSI={fs.rsi_14:.1f} ({fs.rsi_label}), "
            f"MACD hist={fs.macd_histogram:.3f} ({fs.macd_cross}), "
            f"Trend={fs.trend_label}, "
            f"Volatility={fs.volatility_regime} (ATR={fs.atr_pct:.1f}%)"
        )

        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            timeframe=fs.timeframe,
            signal_type=signal_type,
            confidence=confidence,
            risk_score=risk_score,
            thesis=thesis,
            supporting_signals=bull_sigs or (signals[:2] if signal_type == "BUY" else []),
            contradicting_signals=bear_sigs or (signals[:2] if signal_type == "SELL" else []),
            metadata={
                "rsi": round(fs.rsi_14, 2),
                "macd_histogram": round(fs.macd_histogram, 4),
                "bb_position": round(fs.bb_position, 3),
                "volume_ratio": round(fs.volume_ratio, 2),
                "atr_pct": round(fs.atr_pct, 2),
                "trend_label": fs.trend_label,
                "return_5d": round(fs.return_5d, 2),
                "return_20d": round(fs.return_20d, 2),
                "bull_score": round(fs.bull_score, 1),
                "bear_score": round(fs.bear_score, 1),
            },
        )
