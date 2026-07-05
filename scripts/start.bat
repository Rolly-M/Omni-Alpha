@echo off
echo ============================================================
echo   OmniAlpha — Local Startup Script (Windows)
echo   Paper Trading Only - For Research and Education
echo ============================================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+
    pause
    exit /b 1
)

REM Copy .env if needed
if not exist .env (
    echo Copying .env.example to .env...
    copy .env.example .env
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt -q

REM Set PYTHONPATH
set PYTHONPATH=%CD%

REM Seed demo data
echo Seeding demo data...
python scripts\seed_demo.py

REM Start API in background
echo Starting API server on port 8000...
start "OmniAlpha API" cmd /k "python -m uvicorn apps.api.main:app --reload --port 8000 --host 0.0.0.0"

REM Wait for API to start
timeout /t 3 /nobreak > nul

REM Start dashboard
echo Starting dashboard on port 8501...
start "OmniAlpha Dashboard" cmd /k "python -m streamlit run apps\dashboard\main.py --server.port 8501 --server.address 0.0.0.0"

echo.
echo ============================================================
echo   OmniAlpha is starting!
echo   API:       http://localhost:8000
echo   Dashboard: http://localhost:8501
echo   API Docs:  http://localhost:8000/docs
echo ============================================================
echo.
pause
