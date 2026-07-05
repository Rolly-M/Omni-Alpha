"""Kill switch — global emergency stop for all trading activity."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from libs.common.config import settings
from libs.common.logger import get_logger

log = get_logger("kill_switch")


class KillSwitch:
    _instance: Optional["KillSwitch"] = None

    def __init__(self):
        self._enabled: bool = settings.KILL_SWITCH_ENABLED
        self._reason: Optional[str] = None
        self._triggered_at: Optional[datetime] = None
        self._triggered_by: str = "system"

    @classmethod
    def get_instance(cls) -> "KillSwitch":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_active(self) -> bool:
        return self._enabled or settings.KILL_SWITCH_ENABLED

    def activate(self, reason: str, triggered_by: str = "system") -> None:
        self._enabled = True
        self._reason = reason
        self._triggered_at = datetime.now(timezone.utc)
        self._triggered_by = triggered_by
        # Persist to settings (runtime only — not written to .env)
        settings.KILL_SWITCH_ENABLED = True
        log.warning(
            "KILL SWITCH ACTIVATED",
            reason=reason,
            triggered_by=triggered_by,
            at=self._triggered_at.isoformat(),
        )

    def deactivate(self, authorized_by: str = "admin") -> None:
        self._enabled = False
        settings.KILL_SWITCH_ENABLED = False
        log.info("Kill switch deactivated", authorized_by=authorized_by)

    def status(self) -> dict:
        return {
            "active": self.is_active,
            "reason": self._reason,
            "triggered_at": self._triggered_at.isoformat() if self._triggered_at else None,
            "triggered_by": self._triggered_by,
        }

    def assert_inactive(self) -> None:
        """Raises RuntimeError if kill switch is active. Call before any order."""
        if self.is_active:
            raise RuntimeError(
                f"Kill switch is active: {self._reason or 'no reason given'}. "
                "Deactivate via the admin panel before submitting orders."
            )


kill_switch = KillSwitch.get_instance()
