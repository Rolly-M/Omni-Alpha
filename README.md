# 🔭 OmniAlpha — Multi-Agent Investment Research & Paper-Trading Platform

> **⚠️ DISCLAIMER:** OmniAlpha is for **research, education, and simulation ONLY**.
> No guarantee of returns. Markets involve substantial risk.
> Users are responsible for legal, tax, and regulatory compliance.
> **This is not financial advice.**

---

## What is OmniAlpha?

OmniAlpha is a production-grade, fully automated **multi-agent decision-support** and **paper-trading** platform. Thirteen specialized AI agents analyse live and synthetic market data across stocks, ETFs, crypto, and forex, debate opportunities, size positions with risk controls, and execute **paper (simulated) trades** — with every decision fully explainable and auditable.

**Live trading is disabled by default.** The platform defaults to synthetic data (MOCK_MODE) so it works out of the box with zero API keys.

---

## Quick Start (No Docker, 5 minutes)

```bash
# 1. Clone / navigate to the project
cd omni-alpha

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy config
copy .env.example .env           # Windows
cp .env.example .env             # macOS/Linux

# 5. Seed demo data
python scripts/seed_demo.py

# 6. Run a full sandbox day simulation
python scripts/run_sandbox_day.py --verbose

# 7. Start the API
uvicorn apps.api.main:app --reload --port 8000

# 8. Start the dashboard (new terminal)
streamlit run apps/dashboard/main.py --server.port 8501
```

**Then open:**
- 🖥  Dashboard: http://localhost:8501
- 📚 API Docs:   http://localhost:8000/docs

---

## Quick Start (Docker, one command)

```bash
docker compose up -d
```

| Service    | URL                        |
|------------|---------------------------|
| Dashboard  | http://localhost:8501      |
| API        | http://localhost:8000      |
| API Docs   | http://localhost:8000/docs |
| Prometheus | http://localhost:9090      |

---

## One-click Windows startup

```
scripts\start.bat
```

---

## Repository Structure

```
omni-alpha/
├── apps/
│   ├── api/              FastAPI REST backend
│   └── dashboard/        Streamlit 8-page UI
├── services/
│   ├── agents/           13 specialized agents + coordinator
│   ├── ingestion/        Data connectors + feature store
│   ├── execution/        Paper broker + order manager
│   ├── risk/             Risk manager + kill switch
│   └── backtest/         Backtesting engine + reporter
├── libs/
│   └── common/           Config, DB, models, logger
├── infra/                Docker/DB/Prometheus config
├── mock_data/            Synthetic data generators
├── scripts/              Seed + sandbox scripts
├── tests/                45+ unit tests
└── docs/                 Full documentation
```

---

## 13-Agent Pipeline

```
Market Data ──┐
News          ├──► Strategy ──► Bull vs Bear ──► Risk (VETO) ──► Portfolio ──► Paper Broker
Sentiment     │                                      │
Fundamentals  ┤                               ┌──────┘
Macro         │                        REJECTED → audit log → HOLD
Crypto Micro ─┘
                                       Reflection (periodic review)
```

Each decision includes: asset · timeframe · thesis · supporting signals · contradicting signals · confidence 0-100 · risk score 0-100 · stop-loss · take-profit · position size · full explanation · source references.

---

## Key Safety Controls

| Control | Default |
|---|---|
| Live trading | **DISABLED** |
| Mock/paper mode | **ENABLED** |
| Kill switch | **OFF** (one API call to activate) |
| Manual approval | **REQUIRED** |
| Max position size | 5% |
| Max daily loss | 2% |
| Max drawdown | 15% |
| Fat-finger limit | 20% hard cap |
| Duplicate order prevention | ✅ |

---

## Optional API Keys (TODO)

The system works fully without API keys (`MOCK_MODE=true`). For live data, add to `.env`:

| Variable | Service | URL |
|---|---|---|
| `ALPHA_VANTAGE_KEY` | Stocks/Forex | alphavantage.co |
| `NEWS_API_KEY` | News | newsapi.org |
| `FINNHUB_KEY` | Financial data | finnhub.io |
| `POLYGON_KEY` | Market data | polygon.io |
| `FRED_API_KEY` | Macro/rates | fred.stlouisfed.org |
| `BINANCE_API_KEY` | Crypto (paper) | binance.com |

---

## Run Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

45+ tests covering agents, risk controls, paper broker, backtest engine, kill switch, and connectors.

---

## Documentation

| Doc | Contents |
|---|---|
| [SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | Full system design |
| [AGENTS.md](docs/AGENTS.md) | All 13 agents explained |
| [RISK_CONTROLS.md](docs/RISK_CONTROLS.md) | Every risk limit |
| [PAPER_TRADING_GUIDE.md](docs/PAPER_TRADING_GUIDE.md) | Paper trading how-to |
| [BACKTESTING_GUIDE.md](docs/BACKTESTING_GUIDE.md) | Backtest caveats |
| [DATA_SOURCES.md](docs/DATA_SOURCES.md) | Data connectors |
| [LOCAL_SETUP.md](docs/LOCAL_SETUP.md) | Detailed setup guide |

---

*OmniAlpha v1.0.0 — For research, education, and simulation only.*
