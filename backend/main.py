# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.logging_config import configure_logging, logger
from backend.database import engine, Base
from backend.api.router import router
from backend.seed import seed_admin_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    configure_logging()
    logger.info("talent-agent starting", env=settings.app_env, version=settings.app_version)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Auto-seed admin user (Space Cowboy #9) if no users exist
    await seed_admin_user()
    yield
    logger.info("talent-agent shutting down")
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


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }
