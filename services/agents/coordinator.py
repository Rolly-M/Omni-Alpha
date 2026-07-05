"""Coordinator — orchestrates the full analysis pipeline for all instruments.

Pipeline per instrument:
  1. Fetch features (market data + indicators)
  2. Run analyst agents in parallel
  3. Run strategy + bull/bear debate
  4. Risk check (with veto power)
  5. Portfolio sizing
  6. Paper order submission
  7. Audit log
"""
from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from libs.common.config import settings
from libs.common.constants import ASSET_CRYPTO, SECTOR_MAP
from libs.common.logger import get_logger
from services.agents.base_agent import AgentOutput
from services.agents.bear_agent import BearAgent
from services.agents.bull_agent import BullAgent
from services.agents.crypto_agent import CryptoMicrostructureAgent
from services.agents.execution_agent import ExecutionAgent
from services.agents.fundamentals_agent import FundamentalsAgent
from services.agents.macro_agent import MacroAgent
from services.agents.market_data_agent import MarketDataAgent
from services.agents.news_agent import NewsAgent
from services.agents.portfolio_agent import PortfolioManagerAgent
from services.agents.reflection_agent import ReflectionAgent
from services.agents.risk_agent import RiskAgent, RiskVerdict
from services.agents.sentiment_agent import SentimentAgent
from services.agents.strategy_agent import StrategyAgent
from services.ingestion.ingestion_service import get_features, get_news

log = get_logger("coordinator")


class Decision:
    """Full pipeline output for one instrument."""
    def __init__(self):
        self.decision_id: str = str(uuid.uuid4())
        self.cycle_id: str = ""
        self.symbol: str = ""
        self.asset_class: str = ""
        self.timeframe: str = "1d"
        self.action: str = "HOLD"
        self.entry_price: float = 0.0
        self.stop_loss: Optional[float] = None
        self.take_profit: Optional[float] = None
        self.position_size_pct: float = 0.0
        self.confidence: float = 0.0
        self.risk_score: float = 50.0
        self.expected_holding_period: str = "1-5 days"
        self.entry_logic: str = ""
        self.exit_logic: str = ""
        self.thesis: str = ""
        self.supporting_signals: List[str] = []
        self.contradicting_signals: List[str] = []
        self.explanation: str = ""
        self.source_references: List[str] = []
        self.agent_outputs: Dict[str, dict] = {}
        self.risk_verdict: str = "PENDING"
        self.risk_notes: List[str] = []
        self.created_at: datetime = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "cycle_id": self.cycle_id,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "timeframe": self.timeframe,
            "action": self.action,
            "entry_price": round(self.entry_price, 4),
            "stop_loss": round(self.stop_loss, 4) if self.stop_loss else None,
            "take_profit": round(self.take_profit, 4) if self.take_profit else None,
            "position_size_pct": round(self.position_size_pct * 100, 2),
            "confidence": round(self.confidence, 1),
            "risk_score": round(self.risk_score, 1),
            "expected_holding_period": self.expected_holding_period,
            "entry_logic": self.entry_logic,
            "exit_logic": self.exit_logic,
            "thesis": self.thesis,
            "supporting_signals": self.supporting_signals,
            "contradicting_signals": self.contradicting_signals,
            "explanation": self.explanation,
            "source_references": self.source_references,
            "agent_outputs": {k: v for k, v in self.agent_outputs.items()},
            "risk_verdict": self.risk_verdict,
            "risk_notes": self.risk_notes,
            "created_at": self.created_at.isoformat(),
        }


class Coordinator:
    """Main pipeline orchestrator."""

    def __init__(self):
        self.market_data_agent = MarketDataAgent()
        self.news_agent = NewsAgent()
        self.sentiment_agent = SentimentAgent()
        self.fundamentals_agent = FundamentalsAgent()
        self.macro_agent = MacroAgent()
        self.crypto_agent = CryptoMicrostructureAgent()
        self.strategy_agent = StrategyAgent()
        self.bull_agent = BullAgent()
        self.bear_agent = BearAgent()
        self.risk_agent = RiskAgent()
        self.portfolio_agent = PortfolioManagerAgent()
        self.execution_agent = ExecutionAgent()
        self.reflection_agent = ReflectionAgent()

    def run_cycle(
        self,
        symbols: Optional[List[str]] = None,
        timeframe: str = "1d",
        portfolio_state: Optional[dict] = None,
        account_state: Optional[dict] = None,
    ) -> List[Decision]:
        cycle_id = str(uuid.uuid4())[:8]
        if symbols is None:
            symbols = settings.all_symbols
        if portfolio_state is None:
            portfolio_state = self._default_portfolio_state()
        if account_state is None:
            account_state = {"total_equity": settings.INITIAL_BALANCE, "current_price": {}}

        log.info("Cycle started", cycle_id=cycle_id, symbols=len(symbols))
        decisions: List[Decision] = []

        for symbol in symbols:
            try:
                d = self._analyze_instrument(
                    symbol, cycle_id, timeframe, portfolio_state, account_state
                )
                decisions.append(d)
                log.info(
                    "Decision created",
                    cycle_id=cycle_id,
                    symbol=symbol,
                    action=d.action,
                    confidence=round(d.confidence, 1),
                    risk=d.risk_verdict,
                )
            except Exception as exc:
                log.warning("Instrument analysis failed", symbol=symbol, error=str(exc))

        log.info("Cycle complete", cycle_id=cycle_id, decisions=len(decisions))
        return decisions

    def _analyze_instrument(
        self,
        symbol: str,
        cycle_id: str,
        timeframe: str,
        portfolio_state: dict,
        account_state: dict,
    ) -> Decision:
        d = Decision()
        d.cycle_id = cycle_id
        d.symbol = symbol
        d.timeframe = timeframe

        # Classify asset
        if "USDT" in symbol or "BTC" in symbol or "ETH" in symbol:
            d.asset_class = ASSET_CRYPTO
        elif "=X" in symbol:
            d.asset_class = "forex"
        elif symbol in ("SPY", "QQQ", "GLD", "TLT", "IWM"):
            d.asset_class = "etf"
        else:
            d.asset_class = "stock"

        # ── Step 1: Features ─────────────────────────────────────────────
        features = get_features(symbol, timeframe)
        d.entry_price = features.current_price

        # ── Step 2: News ─────────────────────────────────────────────────
        news = get_news(symbol)

        # ── Step 3: Analyst agents (parallel) ────────────────────────────
        analyst_outputs: Dict[str, AgentOutput] = {}

        def run_agent(name_agent_pair):
            name, agent = name_agent_pair
            return name, agent.run(
                symbol,
                features=features,
                news=news,
                asset_class=d.asset_class,
                timeframe=timeframe,
            )

        agent_map = {
            "MarketDataAgent": self.market_data_agent,
            "NewsAgent": self.news_agent,
            "SentimentAgent": self.sentiment_agent,
            "FundamentalsAgent": self.fundamentals_agent,
            "MacroAgent": self.macro_agent,
        }
        if d.asset_class == ASSET_CRYPTO:
            agent_map["CryptoMicrostructureAgent"] = self.crypto_agent

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(run_agent, pair): pair[0] for pair in agent_map.items()}
            for future in as_completed(futures):
                name, output = future.result()
                analyst_outputs[name] = output
                d.agent_outputs[name] = output.to_dict()

        # ── Step 4: Strategy ──────────────────────────────────────────────
        strategy_out = self.strategy_agent.run(
            symbol,
            agent_outputs=analyst_outputs,
            features=features,
            timeframe=timeframe,
        )
        analyst_outputs["StrategyAgent"] = strategy_out
        d.agent_outputs["StrategyAgent"] = strategy_out.to_dict()

        # ── Step 5: Bull / Bear debate ────────────────────────────────────
        bull_out = self.bull_agent.run(
            symbol,
            agent_outputs=analyst_outputs,
            features=features,
            entry_price=d.entry_price,
            timeframe=timeframe,
        )
        bear_out = self.bear_agent.run(
            symbol,
            agent_outputs=analyst_outputs,
            features=features,
            entry_price=d.entry_price,
            timeframe=timeframe,
        )
        analyst_outputs["BullAgent"] = bull_out
        analyst_outputs["BearAgent"] = bear_out
        d.agent_outputs["BullAgent"] = bull_out.to_dict()
        d.agent_outputs["BearAgent"] = bear_out.to_dict()

        # ── Step 6: Risk check ────────────────────────────────────────────
        proposed_size = min(0.02, settings.MAX_POSITION_SIZE_PCT)
        risk_verdict: RiskVerdict = self.risk_agent.evaluate(
            symbol=symbol,
            proposed_size_pct=proposed_size,
            agent_outputs=analyst_outputs,
            portfolio_state=portfolio_state,
            features=features,
        )
        d.risk_verdict = risk_verdict.verdict
        d.risk_notes = risk_verdict.reasons
        d.agent_outputs["RiskAgent"] = {
            "verdict": risk_verdict.verdict,
            "reasons": risk_verdict.reasons,
            "adjusted_size_pct": risk_verdict.adjusted_size_pct,
        }

        if risk_verdict.verdict == "REJECTED":
            d.action = "HOLD"
            d.confidence = strategy_out.confidence
            d.thesis = f"BLOCKED by RiskAgent: {'; '.join(risk_verdict.reasons[:2])}"
            return d

        # ── Step 7: Portfolio sizing ───────────────────────────────────────
        portfolio_out = self.portfolio_agent.run(
            symbol,
            agent_outputs=analyst_outputs,
            portfolio_state=portfolio_state,
            risk_verdict=risk_verdict,
            features=features,
            timeframe=timeframe,
        )
        d.agent_outputs["PortfolioManagerAgent"] = portfolio_out.to_dict()

        # ── Step 8: Build decision ─────────────────────────────────────────
        d.action = strategy_out.signal_type
        d.confidence = strategy_out.confidence
        d.risk_score = bear_out.risk_score

        pm_meta = portfolio_out.metadata
        d.position_size_pct = pm_meta.get("position_size_pct", 0.0)
        d.stop_loss = pm_meta.get("stop_loss")
        d.take_profit = pm_meta.get("take_profit")
        d.expected_holding_period = pm_meta.get("holding_period", "1-5 days")

        # Combine signals from all agents
        all_supporting: list[str] = []
        all_contradicting: list[str] = []
        for out in analyst_outputs.values():
            if hasattr(out, "supporting_signals"):
                all_supporting.extend(out.supporting_signals[:2])
                all_contradicting.extend(out.contradicting_signals[:2])
        d.supporting_signals = list(dict.fromkeys(all_supporting))[:6]
        d.contradicting_signals = list(dict.fromkeys(all_contradicting))[:4]

        d.thesis = strategy_out.thesis
        d.entry_logic = f"Enter {d.action} at market (~{d.entry_price:.2f})"
        d.exit_logic = (
            f"Stop: {d.stop_loss:.2f} | Target: {d.take_profit:.2f} | "
            f"Holding: {d.expected_holding_period}"
        )

        d.explanation = self._build_explanation(d, bull_out, bear_out)
        d.source_references = [
            f"yfinance/mock OHLCV ({timeframe})",
            "NewsAgent (RSS/mock)",
            "SentimentAgent (synthetic)",
            "FundamentalsAgent (static profile)",
            "MacroAgent (mock macro state)",
        ]

        # ── Step 9: Execution (paper) ──────────────────────────────────────
        if d.action in ("BUY", "SELL") and risk_verdict.verdict in ("APPROVED", "REDUCE_SIZE"):
            exec_state = dict(account_state)
            exec_state["current_price"] = {symbol: d.entry_price}
            exec_out = self.execution_agent.run(
                symbol,
                portfolio_out=portfolio_out,
                account_state=exec_state,
            )
            d.agent_outputs["ExecutionAgent"] = exec_out.to_dict()

        return d

    def _build_explanation(
        self, d: Decision, bull_out: AgentOutput, bear_out: AgentOutput
    ) -> str:
        return (
            f"=== OmniAlpha Decision Explanation ===\n"
            f"Symbol: {d.symbol} | Action: {d.action} | Confidence: {d.confidence:.1f}/100\n"
            f"Risk verdict: {d.risk_verdict} | Size: {d.position_size_pct*100:.2f}%\n\n"
            f"BULL CASE:\n{bull_out.thesis}\n\n"
            f"BEAR CASE:\n{bear_out.thesis}\n\n"
            f"CONCLUSION: {d.thesis}\n"
            f"Risk notes: {'; '.join(d.risk_notes)}\n"
        )

    @staticmethod
    def _default_portfolio_state() -> dict:
        return {
            "cash_pct": 0.85,
            "daily_pnl_pct": 0.0,
            "drawdown_pct": 0.0,
            "sector_exposure": {},
        }


# Global singleton
_coordinator: Optional[Coordinator] = None


def get_coordinator() -> Coordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = Coordinator()
    return _coordinator
