"""OmniAlpha FastAPI application entry point."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response

from libs.common.config import settings
from libs.common.database import create_all_tables
from libs.common.logger import configure_logging, get_logger
from apps.api.routers import (
    agents, audit, backtest, market, orders, portfolio, risk, signals
)

configure_logging(debug=settings.DEBUG)
log = get_logger("api")

REQUEST_COUNT = Counter("omni_http_requests_total", "Total HTTP requests", ["method", "path"])
REQUEST_LATENCY = Histogram("omni_http_request_duration_seconds", "HTTP latency", ["path"])

DISCLAIMER = (
    "⚠  OmniAlpha is for research, education, and simulation ONLY. "
    "No guarantee of returns. Markets involve substantial risk. "
    "Users are responsible for legal, tax, and regulatory compliance."
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    log.info("OmniAlpha starting", version=settings.APP_VERSION, mock_mode=settings.MOCK_MODE)
    await create_all_tables()
    log.info("Database tables ready")

    # Start background scheduler
    from apps.api.scheduler import start_scheduler
    start_scheduler()

    yield

    log.info("OmniAlpha shutting down")


app = FastAPI(
    title="OmniAlpha API",
    description=(
        "Multi-agent investment research and paper-trading platform.\n\n"
        f"**{DISCLAIMER}**"
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    REQUEST_COUNT.labels(method=request.method, path=path).inc()
    with REQUEST_LATENCY.labels(path=path).time():
        response = await call_next(request)
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(market.router, prefix="/api/market", tags=["Market Data"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtest"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "mock_mode": settings.MOCK_MODE,
        "live_trading": settings.LIVE_TRADING_ENABLED,
        "kill_switch": settings.KILL_SWITCH_ENABLED,
        "disclaimer": DISCLAIMER,
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/control/kill-switch/activate", tags=["Control"])
async def activate_kill_switch(reason: str = "Manual activation via API"):
    from services.risk.kill_switch import kill_switch
    kill_switch.activate(reason=reason, triggered_by="api")
    return {"status": "ACTIVATED", "reason": reason}


@app.post("/api/control/kill-switch/deactivate", tags=["Control"])
async def deactivate_kill_switch():
    from services.risk.kill_switch import kill_switch
    kill_switch.deactivate(authorized_by="api")
    return {"status": "DEACTIVATED"}


@app.get("/api/control/kill-switch/status", tags=["Control"])
async def kill_switch_status():
    from services.risk.kill_switch import kill_switch
    return kill_switch.status()


@app.post("/api/control/run-cycle", tags=["Control"])
async def trigger_cycle():
    """Manually trigger a full analysis cycle."""
    from services.agents.coordinator import get_coordinator
    coordinator = get_coordinator()
    loop = asyncio.get_event_loop()
    decisions = await loop.run_in_executor(None, coordinator.run_cycle)
    return {
        "cycle_ran": True,
        "decisions": len(decisions),
        "summary": [
            {"symbol": d.symbol, "action": d.action, "confidence": round(d.confidence, 1)}
            for d in decisions[:10]
        ],
    }


# ── Cron endpoints (Vercel crons send GET requests) ──────────────────────────
@app.get("/api/cron/daily-snapshot", tags=["Cron"], include_in_schema=False)
async def cron_daily_snapshot():
    """Record a daily portfolio snapshot — wired to a Vercel cron job."""
    from apps.api.routers.portfolio import take_snapshot
    try:
        return await take_snapshot()
    except Exception as exc:
        log.warning("Cron snapshot skipped", error=str(exc))
        return {"snapshot": False, "reason": str(exc)}


@app.get("/api/cron/run-cycle", tags=["Cron"], include_in_schema=False)
async def cron_run_cycle():
    """Run the agent analysis cycle — wired to a Vercel cron job."""
    return await trigger_cycle()
