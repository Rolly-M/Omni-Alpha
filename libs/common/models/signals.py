"""Agent signal and decision ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from libs.common.database import Base


def _now() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc)


class AgentSignal(Base):
    __tablename__ = "agent_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(16), nullable=False)   # BUY/SELL/HOLD/NEUTRAL
    confidence: Mapped[float] = mapped_column(Float, nullable=False)        # 0–100
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)        # 0–100
    thesis: Mapped[Optional[str]] = mapped_column(Text)
    supporting_signals: Mapped[Optional[str]] = mapped_column(Text)         # JSON array
    contradicting_signals: Mapped[Optional[str]] = mapped_column(Text)      # JSON array
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)              # JSON object
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    cycle_id: Mapped[Optional[str]] = mapped_column(String(36), index=True) # groups one pipeline run

    def __repr__(self) -> str:
        return f"<AgentSignal {self.agent_name} {self.symbol} {self.signal_type} conf={self.confidence:.0f}>"


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cycle_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(16), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)           # BUY/SELL/HOLD/REDUCE/EXIT
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float)
    take_profit: Mapped[Optional[float]] = mapped_column(Float)
    position_size_pct: Mapped[float] = mapped_column(Float)                   # fraction of portfolio
    confidence: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    expected_holding_period: Mapped[Optional[str]] = mapped_column(String(32))
    entry_logic: Mapped[Optional[str]] = mapped_column(Text)
    exit_logic: Mapped[Optional[str]] = mapped_column(Text)
    thesis: Mapped[Optional[str]] = mapped_column(Text)
    supporting_signals: Mapped[Optional[str]] = mapped_column(Text)           # JSON
    contradicting_signals: Mapped[Optional[str]] = mapped_column(Text)        # JSON
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    source_references: Mapped[Optional[str]] = mapped_column(Text)            # JSON
    agent_outputs_json: Mapped[Optional[str]] = mapped_column(Text)           # JSON
    risk_verdict: Mapped[str] = mapped_column(String(16), default="PENDING")  # APPROVED/REJECTED
    risk_notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")        # PENDING/SUBMITTED/COMPLETED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Decision {self.action} {self.symbol} conf={self.confidence:.0f} risk={self.risk_verdict}>"
