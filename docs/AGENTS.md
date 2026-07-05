# OmniAlpha — Agent Reference

> ⚠️ For research and education only. No guarantee of returns.

## Agent Architecture Overview

All agents inherit from `BaseAgent` (`services/agents/base_agent.py`). Every agent:
- Implements `_analyze(symbol, **kwargs) → AgentOutput`
- Returns an `AgentOutput` with `signal_type`, `confidence` (0-100), `risk_score` (0-100), `thesis`, `supporting_signals`, `contradicting_signals`
- Never raises — errors return `NEUTRAL` output gracefully
- Is stateless — all state lives in the database

---

## 1. MarketDataAgent
**File:** `services/agents/market_data_agent.py`

**Purpose:** Technical analysis, trend detection, volatility regime, volume anomalies.

**Indicators:** RSI(14), MACD(12/26/9), Bollinger Bands(20,2σ), ATR(14), SMA20/50/200, EMA12/26, Volume ratio, Rate of change

**Scoring:**
| Condition | Bull Points | Bear Points |
|---|---|---|
| RSI < 30 | +25 | |
| RSI > 70 | | +25 |
| MACD bullish cross | +20 | |
| MACD bearish cross | | +20 |
| Price < Lower BB | +15 | |
| Price > Upper BB | | +15 |
| Price > SMA20 > SMA50 | +20 | |
| High ATR (>3%) | ×0.85 penalty | ×0.85 penalty |

---

## 2. NewsAgent
**File:** `services/agents/news_agent.py`

**Purpose:** Headline clustering, entity extraction, market impact tagging, recency weighting.

**Logic:** Positive/negative keyword matching + recency decay (72-hour half-life) + impact scoring for high-magnitude events.

---

## 3. SentimentAgent
**File:** `services/agents/sentiment_agent.py`

**Purpose:** Social/news/forum sentiment aggregation with source-quality weighting.

**Sources (live mode):** NewsAPI, Reddit (public RSS), synthetic
**Weights:** News=45%, Social=30%, Forum=25%
**Special flags:** Hype detection (high forum / low news), Contrarian alerts at extremes

---

## 4. FundamentalsAgent
**File:** `services/agents/fundamentals_agent.py`

**Purpose:** P/E vs sector median, ROE, revenue growth, balance-sheet leverage.

**Asset classes:** Stocks and ETFs only. Returns NEUTRAL for crypto/forex.

---

## 5. MacroAgent
**File:** `services/agents/macro_agent.py`

**Purpose:** Rates, inflation, PMI, VIX, yield curve. Outputs RISK_ON/RISK_OFF/NEUTRAL regime.

**Inputs:** Fed funds rate, CPI, VIX, 10Y yield, yield curve spread (10Y−2Y), PMI, DXY, oil

---

## 6. CryptoMicrostructureAgent
**File:** `services/agents/crypto_agent.py`

**Purpose:** Funding rate, open interest changes, exchange netflow, Fear & Greed index.

**Asset class:** Crypto only. Automatically skipped for other asset classes.

---

## 7. StrategyAgent
**File:** `services/agents/strategy_agent.py`

**Purpose:** Selects active strategies based on regime. Aggregates votes from all analyst agents.

**Strategies:** trend_following, mean_reversion, momentum, breakout, news_event, crypto_momentum

---

## 8. BullAgent
**File:** `services/agents/bull_agent.py`

**Purpose:** Constructs the strongest possible case FOR a trade. Uses all analyst outputs. Computes upside target.

**Note:** Confidence capped at 85 — never expresses certainty.

---

## 9. BearAgent
**File:** `services/agents/bear_agent.py`

**Purpose:** Constructs the strongest possible case AGAINST a trade. Estimates downside, suggests stop-loss level.

---

## 10. RiskAgent ⛔ (Veto Authority)
**File:** `services/agents/risk_agent.py`

**Purpose:** Enforces all risk limits. Can REJECT or REDUCE_SIZE any trade.

**Checks:**
1. Kill switch active → immediate REJECTED
2. Daily loss limit breached
3. Max drawdown breached
4. Cash minimum not preserved
5. High volatility → halve position size
6. Aggregate risk score > 75
7. Fat-finger limit (> 20%)

---

## 11. PortfolioManagerAgent
**File:** `services/agents/portfolio_agent.py`

**Purpose:** Kelly criterion-based position sizing, account type multiplier, sector exposure cap.

**Formula:** `size = half_Kelly × account_multiplier × risk_adjustment`
- Conservative: ×0.5, Balanced: ×1.0, Aggressive: ×1.5
- Caps at `MAX_POSITION_SIZE_PCT`

---

## 12. ExecutionAgent
**File:** `services/agents/execution_agent.py`

**Purpose:** Translates portfolio decisions into paper orders with simulated fills.

**Simulates:** Slippage (0.05% default), commission (0.1% default), partial fills (5% probability)

---

## 13. ReflectionAgent
**File:** `services/agents/reflection_agent.py`

**Purpose:** Reviews completed trades, scores agent attribution, writes lessons. Never auto-deploys parameter changes without human approval.

---

## Coordinator
**File:** `services/agents/coordinator.py`

Orchestrates the full pipeline. Runs analyst agents in parallel (ThreadPoolExecutor), then sequentially: Strategy → Bull/Bear → Risk → Portfolio → Execution.

Each `Decision` object is fully serializable and contains every agent's output for drill-down.
