"""News Agent — headline clustering, sentiment scoring, event impact tagging."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import List

from services.agents.base_agent import AgentOutput, BaseAgent

_POSITIVE_KEYWORDS = {
    "beats", "exceeds", "upgrade", "buy", "strong", "record", "growth",
    "deal", "partnership", "buyback", "dividend", "surge", "rally", "gain",
    "outperform", "positive", "breakthrough", "launch", "approval"
}
_NEGATIVE_KEYWORDS = {
    "misses", "below", "downgrade", "sell", "weak", "loss", "decline",
    "warning", "risk", "investigation", "fine", "penalty", "cut", "drop",
    "underperform", "negative", "concern", "lawsuit", "recall", "fraud"
}
_HIGH_IMPACT = {
    "earnings", "beat", "miss", "fda", "acquisition", "merger", "buyout",
    "ceo", "fraud", "sec", "crash", "bankruptcy", "revenue"
}


def _score_headline(headline: str, hint: str) -> tuple[float, float, str]:
    """Returns (sentiment_score, impact_score, tag)."""
    lower = headline.lower()
    words = set(re.findall(r"\w+", lower))

    pos = len(words & _POSITIVE_KEYWORDS)
    neg = len(words & _NEGATIVE_KEYWORDS)
    impact = len(words & _HIGH_IMPACT)

    if hint == "positive":
        pos = max(pos, 1)
    elif hint == "negative":
        neg = max(neg, 1)

    sentiment = (pos - neg) / max(pos + neg, 1)   # –1 to +1
    impact_score = min(100.0, impact * 25 + 25)

    if sentiment > 0.3:
        tag = "BULLISH"
    elif sentiment < -0.3:
        tag = "BEARISH"
    else:
        tag = "NEUTRAL"

    return sentiment, impact_score, tag


class NewsAgent(BaseAgent):
    name = "NewsAgent"

    def _analyze(self, symbol: str, news: List[dict] = None, **kwargs) -> AgentOutput:  # type: ignore[override]
        if news is None:
            from services.ingestion.ingestion_service import get_news
            news = get_news(symbol, limit=10)

        if not news:
            return AgentOutput(
                agent_name=self.name, symbol=symbol, timeframe="event",
                signal_type="NEUTRAL", confidence=40.0, risk_score=30.0,
                thesis="No recent news found.", metadata={"article_count": 0},
            )

        now = datetime.now(timezone.utc)
        weighted_sentiment = 0.0
        total_weight = 0.0
        bullish_count = 0
        bearish_count = 0
        top_headlines: list[str] = []
        risk_flags: list[str] = []
        max_impact = 0.0

        for item in news:
            headline = item.get("headline", "")
            hint = item.get("sentiment_hint", "neutral")

            # Recency weight: newer = higher weight
            try:
                pub = datetime.fromisoformat(item.get("published_at", now.isoformat()).replace("Z", "+00:00"))
                age_hours = max(0, (now - pub).total_seconds() / 3600)
            except Exception:
                age_hours = 24
            recency_weight = max(0.1, 1.0 - age_hours / 72)

            sentiment, impact, tag = _score_headline(headline, hint)
            weight = recency_weight * (impact / 50)
            weighted_sentiment += sentiment * weight
            total_weight += weight
            max_impact = max(max_impact, impact)

            if tag == "BULLISH":
                bullish_count += 1
                top_headlines.append(f"[+] {headline}")
            elif tag == "BEARISH":
                bearish_count += 1
                top_headlines.append(f"[-] {headline}")
                if impact > 60:
                    risk_flags.append(f"High-impact negative news: {headline[:60]}")

        avg_sentiment = weighted_sentiment / total_weight if total_weight > 0 else 0

        if avg_sentiment > 0.3:
            signal_type = "BUY"
            confidence = min(80.0, 50 + avg_sentiment * 60)
        elif avg_sentiment < -0.3:
            signal_type = "SELL"
            confidence = min(80.0, 50 + abs(avg_sentiment) * 60)
        else:
            signal_type = "HOLD"
            confidence = 45.0

        risk_score = min(100.0, 20 + len(risk_flags) * 25 + (max_impact * 0.3 if avg_sentiment < 0 else 0))

        thesis = (
            f"News analysis for {symbol}: "
            f"{len(news)} articles, {bullish_count} bullish, {bearish_count} bearish. "
            f"Avg weighted sentiment: {avg_sentiment:.2f}. Max impact: {max_impact:.0f}."
        )

        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            timeframe="event",
            signal_type=signal_type,
            confidence=confidence,
            risk_score=risk_score,
            thesis=thesis,
            supporting_signals=[h for h in top_headlines if h.startswith("[+]")][:3],
            contradicting_signals=risk_flags[:3] or [h for h in top_headlines if h.startswith("[-]")][:3],
            metadata={
                "article_count": len(news),
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
                "avg_sentiment": round(avg_sentiment, 3),
                "max_impact": round(max_impact, 1),
                "top_headlines": top_headlines[:5],
            },
        )
