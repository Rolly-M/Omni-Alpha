#!/usr/bin/env bash
set -e
echo "============================================================"
echo "  OmniAlpha — Local Startup Script"
echo "  Paper Trading Only - For Research and Education"
echo "============================================================"

# Copy .env
[ ! -f .env ] && cp .env.example .env && echo "Created .env from example"

# Install deps
pip install -r requirements.txt -q

# Set PYTHONPATH
export PYTHONPATH=$(pwd)

# Seed demo data
python scripts/seed_demo.py

# Start API
uvicorn apps.api.main:app --reload --port 8000 --host 0.0.0.0 &
API_PID=$!

# Wait
sleep 2

# Start dashboard
streamlit run apps/dashboard/main.py --server.port 8501 --server.address 0.0.0.0 &
DASH_PID=$!

echo ""
echo "============================================================"
echo "  OmniAlpha running!"
echo "  API:       http://localhost:8000"
echo "  Dashboard: http://localhost:8501"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Press Ctrl+C to stop"
echo "============================================================"

wait $API_PID $DASH_PID
