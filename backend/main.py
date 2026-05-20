# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.observability import configure_logging, get_logger, HealthResponse
from backend.observability.health import build_health_response
from backend.database import engine, Base, get_db, AsyncSessionLocal
from backend.api.router import router
from backend.seed import seed_admin_user

logger = get_logger(__name__)

# Global Redis client — initialized at startup
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency that returns the global Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    global _redis_client

    # Configure structured logging with PII redaction
    configure_logging()
    logger.info("talent-agent starting", env=settings.app_env, version=settings.app_version)

    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize Redis connection
    _redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    # Auto-seed admin user (Space Cowboy #9) if no users exist
    await seed_admin_user()

    yield

    # Cleanup
    logger.info("talent-agent shutting down")
    if _redis_client:
        await _redis_client.close()
    await engine.dispose()


app = FastAPI(
    title="Talent Agent API",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://seanyoung.biz"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check endpoint.

    Returns service status, version, git SHA, and dependency health.
    Contract: NUTRIENTS.md API_CONTRACTS → GET /health
    """
    global _redis_client

    # Get a fresh DB session for health check
    async with AsyncSessionLocal() as db:
        return await build_health_response(
            redis_client=_redis_client,
            db_session=db,
        )
