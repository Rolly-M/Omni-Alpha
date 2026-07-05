"""Agent output endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/run/{symbol}")
async def run_all_agents(symbol: str, timeframe: str = Query("1d")):
    """Run all agents for one symbol and return their individual outputs."""
    from services.agents.coordinator import get_coordinator
    coordinator = get_coordinator()
    decisions = coordinator.run_cycle(symbols=[symbol], timeframe=timeframe)
    if not decisions:
        return {"error": "No output"}

    d = decisions[0]
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "cycle_id": d.cycle_id,
        "agent_outputs": d.agent_outputs,
        "final_action": d.action,
        "confidence": round(d.confidence, 1),
        "risk_verdict": d.risk_verdict,
        "explanation": d.explanation,
    }


@router.get("/heatmap")
async def get_confidence_heatmap():
    """Returns agent × symbol confidence matrix for dashboard heatmap."""
    from libs.common.config import settings
    from services.ingestion.ingestion_service import get_features
    from services.agents.market_data_agent import MarketDataAgent
    from services.agents.news_agent import NewsAgent
    from services.agents.macro_agent import MacroAgent

    symbols = settings.STOCK_WATCHLIST[:5] + settings.ETF_WATCHLIST[:2]
    agents = {
        "MarketData": MarketDataAgent(),
        "News": NewsAgent(),
        "Macro": MacroAgent(),
    }

    result = {}
    for sym in symbols:
        result[sym] = {}
        features = get_features(sym, "1d")
        for agent_name, agent in agents.items():
            try:
                out = agent.run(sym, features=features)
                result[sym][agent_name] = {
                    "signal": out.signal_type,
                    "confidence": round(out.confidence, 1),
                }
            except Exception:
                result[sym][agent_name] = {"signal": "NEUTRAL", "confidence": 0.0}

    return {"heatmap": result}
