"""Background scheduler — runs the coordinator pipeline at configured intervals."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from libs.common.config import settings
from libs.common.logger import get_logger

log = get_logger("scheduler")
_scheduler: BackgroundScheduler = None


def _run_analysis_cycle():
    try:
        from services.agents.coordinator import get_coordinator
        coordinator = get_coordinator()
        decisions = coordinator.run_cycle()
        log.info("Scheduled cycle complete", decisions=len(decisions))
    except Exception as exc:
        log.warning("Scheduled cycle failed", error=str(exc))


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_analysis_cycle,
        trigger=IntervalTrigger(seconds=settings.ANALYSIS_INTERVAL_SECONDS),
        id="analysis_cycle",
        name="OmniAlpha Analysis Cycle",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    log.info(
        "Scheduler started",
        interval_seconds=settings.ANALYSIS_INTERVAL_SECONDS,
    )


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
