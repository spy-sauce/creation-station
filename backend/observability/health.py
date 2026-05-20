# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Health endpoint response schema and dependency checks.

Contract from NUTRIENTS.md API_CONTRACTS:

    GET /health
    Response (200):
    {
      "status": "ok",
      "version": string,  // semver
      "git_sha": string,
      "redis": "ok" | "down",
      "db": "ok" | "down"
    }

This module provides:
  - HealthResponse Pydantic model matching the frozen contract
  - Dependency health check functions (Redis, PostgreSQL)
  - git_sha retrieval from environment or git command
"""

import os
import subprocess
from typing import Literal

from pydantic import BaseModel, Field

import structlog

from backend.config import settings

logger = structlog.get_logger(__name__)


# ─── Health Response Schema ──────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """
    Health check response — frozen contract from NUTRIENTS.md.

    This is the exact shape returned by GET /health.
    """

    status: Literal["ok", "degraded", "down"] = Field(
        ..., description="Overall service status"
    )
    version: str = Field(..., description="Semantic version (e.g., 0.1.0)")
    git_sha: str = Field(..., description="Git commit SHA (short or full)")
    redis: Literal["ok", "down"] = Field(..., description="Redis connectivity status")
    db: Literal["ok", "down"] = Field(..., description="PostgreSQL connectivity status")


# ─── Git SHA Retrieval ───────────────────────────────────────────────────────


def get_git_sha() -> str:
    """
    Get the current git commit SHA.

    Checks in order:
      1. GIT_SHA environment variable (set by CI/CD)
      2. git rev-parse HEAD (if in a git repo)
      3. "unknown" fallback

    Returns:
        Short git SHA or "unknown"
    """
    # Check environment variable first (set by Digital Dash pipeline)
    env_sha = os.environ.get("GIT_SHA", "")
    if env_sha:
        return env_sha[:8]  # Short SHA

    # Try git command
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return "unknown"


# ─── Dependency Health Checks ────────────────────────────────────────────────


async def check_redis_health(redis_client) -> Literal["ok", "down"]:
    """
    Check Redis connectivity via PING.

    Args:
        redis_client: Async Redis client instance

    Returns:
        "ok" if Redis responds to PING, "down" otherwise
    """
    try:
        await redis_client.ping()
        return "ok"
    except Exception as e:
        logger.warning("health.redis_down", error=str(e))
        return "down"


async def check_db_health(db_session) -> Literal["ok", "down"]:
    """
    Check PostgreSQL connectivity via simple query.

    Args:
        db_session: Async SQLAlchemy session

    Returns:
        "ok" if database responds, "down" otherwise
    """
    try:
        from sqlalchemy import text
        await db_session.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:
        logger.warning("health.db_down", error=str(e))
        return "down"


# ─── Health Builder ──────────────────────────────────────────────────────────


async def build_health_response(
    redis_client=None,
    db_session=None,
) -> HealthResponse:
    """
    Build a complete health response with all dependency checks.

    Args:
        redis_client: Optional async Redis client (skipped if None)
        db_session: Optional async SQLAlchemy session (skipped if None)

    Returns:
        HealthResponse with all fields populated
    """
    # Check dependencies
    redis_status: Literal["ok", "down"] = "ok"
    db_status: Literal["ok", "down"] = "ok"

    if redis_client is not None:
        redis_status = await check_redis_health(redis_client)

    if db_session is not None:
        db_status = await check_db_health(db_session)

    # Determine overall status
    if redis_status == "down" or db_status == "down":
        overall_status: Literal["ok", "degraded", "down"] = "degraded"
    else:
        overall_status = "ok"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        git_sha=get_git_sha(),
        redis=redis_status,
        db=db_status,
    )
