# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: str = "local"
    app_name: str = "talent-agent"
    app_version: str = "0.1.0"
    debug: bool = True

    database_url: str
    redis_url: str

    anthropic_api_key: str

    min_score: int = 60
    max_jobs_per_run: int = 500
    crawl_concurrency: int = 5
    discovery_cron: str = "0 7 * * *"

    max_parallel_applications: int = 3
    auto_apply_enabled: bool = False
    outreach_enabled: bool = False

    hunter_api_key: str = ""

    test_candidate_email: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
