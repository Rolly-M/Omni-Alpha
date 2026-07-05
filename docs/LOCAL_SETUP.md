# OmniAlpha — Local Setup Guide

## Prerequisites

- Python 3.11+
- pip
- (Optional) Docker + Docker Compose for full stack

## Zero-Docker Dev Setup

```bash
# 1. Navigate to project
cd omni-alpha

# 2. Virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS/Linux

# 3. Install
pip install -r requirements.txt -r requirements-dev.txt

# 4. Configure
copy .env.example .env
# Edit .env — defaults work as-is for demo

# 5. Set PYTHONPATH
set PYTHONPATH=%CD%          # Windows
export PYTHONPATH=$(pwd)     # macOS/Linux

# 6. Seed demo data
python scripts/seed_demo.py

# 7. Run sandbox simulation (no servers needed)
python scripts/run_sandbox_day.py --verbose

# 8. Start API server
uvicorn apps.api.main:app --reload --port 8000

# 9. Start dashboard (new terminal with PYTHONPATH set)
streamlit run apps/dashboard/main.py --server.port 8501
```

## Docker Setup

```bash
# Start all services
docker compose up -d

# Check logs
docker compose logs -f api

# Seed demo data
docker compose exec api python scripts/seed_demo.py

# Stop
docker compose down
```

## Running Tests

```bash
pytest tests/ -v
pytest tests/ -v --cov=. --cov-report=html   # with coverage
```

## Configuration Reference

All settings in `.env`. Key flags:

| Setting | Default | What it does |
|---|---|---|
| `MOCK_MODE=true` | true | Use synthetic data — zero external calls |
| `LIVE_TRADING_ENABLED=false` | false | **Never change without reading RISK_CONTROLS.md** |
| `DATABASE_URL` | sqlite | SQLite for dev, asyncpg for prod |
| `INITIAL_BALANCE` | 100000 | Starting fake balance |
| `ACCOUNT_TYPE` | balanced | conservative / balanced / aggressive |

## Troubleshooting

**ModuleNotFoundError:** Ensure `PYTHONPATH` is set to the project root.

**asyncio errors in tests:** The `pyproject.toml` sets `asyncio_mode = "auto"` — ensure pytest-asyncio is installed.

**Empty dashboard charts:** The dashboard uses cached `@st.cache_data` — click "Refresh Data" or wait 2 minutes.

**yfinance throttling:** The system automatically falls back to mock data. Set `MOCK_MODE=true` to always use synthetic data.
