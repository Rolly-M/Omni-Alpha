"""Immutable audit log model — append-only, never update rows."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from libs.common.database import Base


def _now() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Every agent action, decision, order, and risk event is written here.
    Rows are NEVER updated or deleted — immutable audit trail."""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cycle_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # e.g. "AGENT_SIGNAL" / "DECISION_CREATED" / "ORDER_SUBMITTED" / "KILL_SWITCH_TRIGGERED"
    actor: Mapped[str] = mapped_column(String(64), nullable=False)           # agent name or "system"
    symbol: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="INFO")        # INFO/WARN/ERROR/CRITICAL
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detail_json: Mapped[Optional[str]] = mapped_column(Text)                 # full payload as JSON
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    risk_score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<AuditLog [{self.event_type}] {self.actor} {self.symbol} {self.summary[:40]}>"
