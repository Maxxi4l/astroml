"""Async database session management for the FastAPI backend (issue #251).

Provides:
  - Async SQLAlchemy engine + session factory
  - ``get_db`` FastAPI dependency (async)
  - ``get_sync_db`` for sync endpoints / scripts
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Import all models so Base.metadata is fully populated before create_all.
from astroml.db.schema import Base  # noqa: F401
import api.models.orm  # noqa: F401  registers api models on Base.metadata


def _async_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://astroml:astroml@localhost/astroml",
    )


def _sync_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://astroml:astroml@localhost/astroml",
    )
    return url.replace("+asyncpg", "").replace("+aiosqlite", "")


@lru_cache(maxsize=1)
def _async_engine():
    try:
        from astroml.db.session import load_database_config
        config = load_database_config()
        return create_async_engine(
            _async_url(), 
            pool_pre_ping=True,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle
        )
    except Exception:
        return create_async_engine(
            _async_url(), 
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800
        )


@lru_cache(maxsize=1)
def _sync_engine():
    try:
        from astroml.db.session import load_database_config
        config = load_database_config()
        return create_engine(
            _sync_url(), 
            pool_pre_ping=True,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle
        )
    except Exception:
        return create_engine(
            _sync_url(), 
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800
        )


def reset_engines() -> None:
    """Clear cached engines (used in tests when DATABASE_URL changes)."""
    _async_engine.cache_clear()
    _sync_engine.cache_clear()


def _async_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=_async_engine(), expire_on_commit=False)


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory (used by scheduler and WS)."""
    return _async_session_factory()


def _sync_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=_sync_engine(), autocommit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    factory = _async_session_factory()
    async with factory() as session:
        yield session


def get_sync_db() -> Generator[Session, None, None]:
    """FastAPI dependency for sync endpoints — yields a sync DB session."""
    session = _sync_session_factory()()
    try:
        yield session
    finally:
        session.close()
