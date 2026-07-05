-- OmniAlpha PostgreSQL initialization
-- This script runs automatically when the TimescaleDB container starts.

-- Enable TimescaleDB extension (for time-series optimizations)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create application user (if running as superuser)
-- The user is created by POSTGRES_USER env var, so we just grant privileges here.

-- Comment: SQLAlchemy / Alembic will create all tables via create_all_tables().
-- This file handles only extension setup and any custom indexes.

COMMENT ON SCHEMA public IS 'OmniAlpha investment research platform';
