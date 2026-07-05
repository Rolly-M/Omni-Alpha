.PHONY: help install dev test lint format seed docker-up docker-down docker-logs clean

PYTHON := python
PIP    := pip
APP    := omni-alpha

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

install: ## Install all Python dependencies
	$(PIP) install -r requirements.txt

install-dev: ## Install dev + test dependencies
	$(PIP) install -r requirements.txt -r requirements-dev.txt

dev: ## Run API + dashboard locally (no Docker)
	@echo "Starting OmniAlpha in dev mode (SQLite + mock data)..."
	$(PYTHON) scripts/seed_demo.py
	start "OmniAlpha API" cmd /k "$(PYTHON) -m uvicorn apps.api.main:app --reload --port 8000"
	start "OmniAlpha Dashboard" cmd /k "$(PYTHON) -m streamlit run apps/dashboard/main.py --server.port 8501"

seed: ## Seed demo data and run one simulated trading day
	$(PYTHON) scripts/seed_demo.py
	$(PYTHON) scripts/run_sandbox_day.py

test: ## Run all tests
	$(PYTHON) -m pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	$(PYTHON) -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

lint: ## Lint with ruff
	$(PYTHON) -m ruff check .

format: ## Format with black + isort
	$(PYTHON) -m black . --line-length 100
	$(PYTHON) -m isort .

docker-up: ## Start all services with Docker Compose
	docker compose up -d
	@echo "API:       http://localhost:8000"
	@echo "Dashboard: http://localhost:8501"
	@echo "Prometheus:http://localhost:9090"

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Tail all service logs
	docker compose logs -f

docker-seed: ## Seed demo data inside Docker
	docker compose exec api python scripts/seed_demo.py

migrate: ## Run Alembic database migrations
	$(PYTHON) -m alembic upgrade head

migrate-new: ## Create a new Alembic migration (MSG=description)
	$(PYTHON) -m alembic revision --autogenerate -m "$(MSG)"

sandbox: ## Simulate one full trading day with live output
	$(PYTHON) scripts/run_sandbox_day.py --verbose

backtest: ## Run the built-in backtest example (SYMBOL=AAPL DAYS=365)
	$(PYTHON) -c "from services.backtest.engine import BacktestEngine; BacktestEngine().run_example()"

clean: ## Remove __pycache__, .pyc, temp files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
