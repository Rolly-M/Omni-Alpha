"""Sentiment Agent — aggregates social, news, and forum sentiment signals."""
from __future__ import annotations

import random
from datetime import datetime, timezone

from services.agents.base_agent import AgentOutput, BaseAgent


class SentimentAgent(BaseAgent):
    """Simulates sentiment aggregation from social / forum / news sources.

    In mock mode: generates plausible synthetic sentiment scores.
    In live mode: would call NewsAPI, Reddit, Twitter/X via legal public endpoints.
    """
    name = "SentimentAgent"

    def _analyze(self, symbol: str, features=None, **kwargs) -> AgentOutput:  # type: ignore[override]
        from libs.common.config import settings

        if settings.MOCK_MODE:
            return self._mock_sentiment(symbol)
        return self._mock_sentiment(symbol)   # fallback until live API is wired

    def _mock_sentiment(self, symbol: str) -> AgentOutput:
        rng = random.Random(symbol + str(datetime.now(timezone.utc).date()))

        # Synthetic scores: -1 to +1 with realistic distributions
        social_score = rng.gauss(0.05, 0.35)
        news_score = rng.gauss(0.02, 0.30)
        forum_score = rng.gauss(0.0, 0.40)

        # Source quality weights
        w_social, w_news, w_forum = 0.3, 0.45, 0.25
        composite = w_social * social_score + w_news * news_score + w_forum * forum_score
        composite = max(-1.0, min(1.0, composite))

        # Hype vs durable: high forum score with low news = potential hype
        hype_flag = abs(forum_score) > 0.5 and abs(news_score) < 0.2
        contrarian_signal = None
        if abs(composite) > 0.7:
            contrarian_signal = f"Extreme {'bullish' if composite > 0 else 'bearish'} sentiment — contrarian risk"

        if composite > 0.25:
            signal_type = "BUY"
            confidence = min(70.0, 45 + composite * 50)
        elif composite < -0.25:
            signal_type = "SELL"
            confidence = min(70.0, 45 + abs(composite) * 50)
        else:
            signal_type = "HOLD"
            confidence = 40.0

        risk_score = 30.0 + (20 if hype_flag else 0) + (15 if abs(composite) > 0.6 else 0)

        supporting = [f"Composite sentiment: {composite:.2f}"]
        if composite > 0:
            supporting.append(f"News sentiment: {news_score:.2f}")
        contradicting = []
        if hype_flag:
            contradicting.append("Hype pattern detected (high forum / low news)")
        if contrarian_signal:
            contradicting.append(contrarian_signal)

        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            timeframe="event",
            signal_type=signal_type,
            confidence=confidence,
            risk_score=risk_score,
            thesis=(
                f"Sentiment analysis for {symbol}: composite={composite:.2f}, "
                f"social={social_score:.2f}, news={news_score:.2f}, forum={forum_score:.2f}. "
                f"{'Hype pattern detected. ' if hype_flag else ''}"
                f"{'Contrarian alert: extreme reading. ' if contrarian_signal else ''}"
            ),
            supporting_signals=supporting,
            contradicting_signals=contradicting,
            metadata={
                "composite": round(composite, 3),
                "social_score": round(social_score, 3),
                "news_score": round(news_score, 3),
                "forum_score": round(forum_score, 3),
                "hype_flag": hype_flag,
                "contrarian_flag": bool(contrarian_signal),
            },
        )
