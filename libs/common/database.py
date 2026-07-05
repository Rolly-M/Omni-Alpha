"""Database engine, session factory, and Base model for SQLAlchemy 2.0."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from libs.common.config import settings

# ── Engine ───────────────────────────────────────────────────────────────────
def _make_engine() -> AsyncEngine:
    url = settings.DATABASE_URL
    kwargs: dict = {"echo": settings.DEBUG}
    if "sqlite" in url:
        kwargs["connect_args"] = {"check_same_thread": False}
    elif "postgresql" in url or "asyncpg" in url:
        # Supabase/PgBouncer transaction-mode pooler requires prepared statements disabled.
        # Safe to set for direct connections too.
        kwargs["connect_args"] = {"statement_cache_size": 0}
    return create_async_engine(url, **kwargs)


engine: AsyncEngine = _make_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Base ─────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Session dependency ────────────────────────────────────────────────────────
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
