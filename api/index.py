"""Vercel serverless entry point for the OmniAlpha FastAPI app."""
import sys
import os

# Make the project root importable from this file's location (api/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Vercel's filesystem is read-only except /tmp; default SQLite there if not overridden.
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/omni_alpha.db"

from apps.api.main import app  # noqa: F401  (Vercel looks for `app`)
