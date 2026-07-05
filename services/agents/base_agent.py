"""Base agent class and AgentOutput dataclass shared by all agents."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AgentOutput:
    """Structured output every agent must return."""
    agent_name: str
    symbol: str
    timeframe: str
    signal_type: str               # BUY / SELL / HOLD / NEUTRAL
    confidence: float              # 0–100
    risk_score: float              # 0–100 (higher = riskier)
    thesis: str
    supporting_signals: List[str] = field(default_factory=list)
    contradicting_signals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    cycle_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "signal_type": self.signal_type,
            "confidence": round(self.confidence, 1),
            "risk_score": round(self.risk_score, 1),
            "thesis": self.thesis,
            "supporting_signals": self.supporting_signals,
            "contradicting_signals": self.contradicting_signals,
            "metadata": self.metadata,
            "cycle_id": self.cycle_id,
            "created_at": self.created_at.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class BaseAgent:
    """All agents inherit this. Provides logging, error wrapping, and output schema."""

    name: str = "BaseAgent"

    def run(self, symbol: str, **kwargs) -> AgentOutput:
        """Entry point — wraps _analyze with error handling."""
        from libs.common.logger import get_logger
        log = get_logger(self.name)
        try:
            out = self._analyze(symbol, **kwargs)
            log.debug("Agent output", symbol=symbol, signal=out.signal_type, conf=out.confidence)
            return out
        except Exception as exc:
            log.warning("Agent failed, returning NEUTRAL", symbol=symbol, error=str(exc))
            return AgentOutput(
                agent_name=self.name,
                symbol=symbol,
                timeframe=kwargs.get("timeframe", "1d"),
                signal_type="NEUTRAL",
                confidence=0.0,
                risk_score=50.0,
                thesis=f"Agent error: {exc}",
            )

    def _analyze(self, symbol: str, **kwargs) -> AgentOutput:
        raise NotImplementedError
