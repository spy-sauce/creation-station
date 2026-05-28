# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from backend.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """
    FastAPI dependency that yields an async database session.

    Automatically rolls back on exception to prevent partial commits.
    Contract: HYPHA-API.md Acceptance Criteria
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ─── Redis Client ─────────────────────────────────────────────────────────────

# Global Redis client — initialized lazily or at startup via lifespan
_redis_client: Optional[aioredis.Redis] = None


def set_redis_client(client: aioredis.Redis) -> None:
    """Set the global Redis client (called from app lifespan)."""
    global _redis_client
    _redis_client = client


async def get_redis() -> aioredis.Redis:
    """
    FastAPI dependency that returns the global Redis client.

    The client is initialized at app startup via lifespan.
    Falls back to lazy initialization if not set.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client
