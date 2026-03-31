# TALENT AGENT — PHASE 1 INFRASTRUCTURE SETUP
## Claude Code Prompt · Execute Before Everything Else

---

## CONTEXT

You are setting up the foundational infrastructure for **VibeSpace Talent Agent** — an autonomous AI talent system built by **Sean Young (Space Cowboy #9)** at **VibeSpace LLC ("The Dot Connector")**, Miami, FL.

This is the **infrastructure-first prompt**. Before any agent code is written, the project skeleton, dependencies, database, Docker environment, and config layer must exist and be verified working. Everything built in Phase 1 (Discovery Engine) and Phase 2 (Application Engine) depends on this foundation being solid.

Read `CLAUDE.md` before starting. Follow every standard defined there.

---

## YOUR MISSION

Scaffold the complete project structure, install all dependencies, configure the environment, and verify the stack is running end-to-end locally. When you are done, the developer should be able to run one command and have the full local environment up with a green health check.

---

## STEP 1 — PROJECT STRUCTURE

Create the following directory and file structure exactly:

```
talent-agent/
├── CLAUDE.md                        ← already exists
├── README.md                        ← already exists
├── prompts/                         ← already exists
│   ├── 01-discovery-engine.md
│   ├── 02-application-engine.md
│   └── 03-vibespace-framework.md
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── logging_config.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── discovery/
│   │   │   └── __init__.py
│   │   └── application/
│   │       └── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── discovery.py
│   │   └── application.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── discovery.py
│   │   ├── application.py
│   │   └── review.py
│   └── migrations/
│       ├── 000_init.sql
│       ├── 001_discovery.sql
│       └── 002_application.sql
├── frontend/
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── discovery/
│   │   └── __init__.py
│   └── application/
│       └── __init__.py
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .env                             ← gitignored, created from .env.example
├── .gitignore
├── requirements.txt
└── Makefile
```

---

## STEP 2 — DEPENDENCIES

### `requirements.txt`

```txt
# Web framework
fastapi==0.115.0
uvicorn[standard]==0.30.6

# Data validation
pydantic==2.9.2
pydantic-settings==2.5.2

# Database
sqlalchemy==2.0.35
asyncpg==0.29.0
alembic==1.13.3

# Task queue
celery==5.4.0
redis==5.1.1

# HTTP client
httpx==0.27.2

# Web scraping
playwright==1.47.0
beautifulsoup4==4.12.3
lxml==5.3.0

# AI
anthropic==0.34.2

# Logging
structlog==24.4.0

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-httpx==0.32.0
httpx==0.27.2

# Utilities
python-dotenv==1.0.1
tenacity==9.0.0
python-multipart==0.0.12
```

---

## STEP 3 — DOCKER SETUP

### `docker-compose.yml`

```yaml
version: '3.9'

services:
  app:
    build: .
    container_name: talent-agent-app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app/backend
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15-alpine
    container_name: talent-agent-db
    environment:
      POSTGRES_DB: talent_agent
      POSTGRES_USER: talent_agent
      POSTGRES_PASSWORD: talent_agent_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/migrations:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U talent_agent"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: talent-agent-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  celery:
    build: .
    container_name: talent-agent-celery
    env_file:
      - .env
    depends_on:
      - redis
      - db
    command: celery -A backend.celery_app worker --loglevel=info

volumes:
  postgres_data:
```

### `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium --with-deps

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## STEP 4 — ENVIRONMENT CONFIG

### `.env.example`

```env
# App
APP_ENV=local
APP_NAME=talent-agent
APP_VERSION=0.1.0
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://talent_agent:talent_agent_dev@localhost:5432/talent_agent

# Redis
REDIS_URL=redis://localhost:6379/0

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Discovery Engine
MIN_SCORE=60
MAX_JOBS_PER_RUN=500
CRAWL_CONCURRENCY=5
DISCOVERY_CRON=0 7 * * *

# Application Engine
MAX_PARALLEL_APPLICATIONS=3
AUTO_APPLY_ENABLED=false
OUTREACH_ENABLED=false

# External APIs
HUNTER_API_KEY=your_hunter_api_key_here

# Candidates
TEST_CANDIDATE_EMAIL=spy@seanyoung.biz
```

Copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY`.

---

## STEP 5 — CORE BACKEND FILES

### `backend/config.py`

```python
# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
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
```

### `backend/database.py`

```python
# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

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
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### `backend/logging_config.py`

```python
# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

import structlog
import logging
from backend.config import settings


def configure_logging():
    log_level = logging.DEBUG if settings.debug else logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


logger = structlog.get_logger()
```

### `backend/main.py`

```python
# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.logging_config import configure_logging, logger
from backend.database import engine, Base
from backend.api.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("talent-agent starting", env=settings.app_env, version=settings.app_version)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }
```

### `backend/api/router.py`

```python
# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

from fastapi import APIRouter
from backend.api import discovery, application, review

router = APIRouter(prefix="/api/v1")

router.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
router.include_router(application.router, prefix="/application", tags=["application"])
router.include_router(review.router, prefix="/review", tags=["review"])
```

### `backend/api/discovery.py`, `backend/api/application.py`, `backend/api/review.py`

Create each as a stub router with a single placeholder endpoint:

```python
# discovery.py example
from fastapi import APIRouter
router = APIRouter()

@router.get("/status")
async def status():
    return {"engine": "discovery", "status": "ready"}
```

Repeat for application and review.

### `backend/models/base.py`

```python
# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

import uuid
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from backend.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class BaseModel(Base, TimestampMixin):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
```

---

## STEP 6 — DATABASE MIGRATIONS

### `backend/migrations/000_init.sql`

```sql
-- VibeSpace Talent Agent — Init Migration
-- Extensions

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Pipeline status enum
CREATE TYPE pipeline_status AS ENUM (
    'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING', 'DEAD'
);

-- Job status enum
CREATE TYPE job_status AS ENUM (
    'DISCOVERED', 'SCORED', 'APPROVED', 'SKIPPED', 'APPLIED', 'INTERVIEWING', 'OFFERED', 'REJECTED'
);
```

### `backend/migrations/001_discovery.sql`

```sql
-- VibeSpace Talent Agent — Discovery Engine Schema

CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    resume_text TEXT,
    linkedin_url VARCHAR(500),
    github_url VARCHAR(500),
    personal_context TEXT,
    target_locations TEXT[],
    remote_preference VARCHAR(50) DEFAULT 'flexible',
    min_compensation INTEGER,
    excluded_companies TEXT[],
    excluded_industries TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS discovered_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES candidates(id),
    title VARCHAR(500) NOT NULL,
    company VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    url VARCHAR(1000) UNIQUE NOT NULL,
    url_hash VARCHAR(64) UNIQUE NOT NULL,
    description TEXT,
    source VARCHAR(100),
    posted_date TIMESTAMPTZ,
    status job_status DEFAULT 'DISCOVERED',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scored_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES discovered_jobs(id),
    candidate_id UUID REFERENCES candidates(id),
    composite_score INTEGER NOT NULL,
    technical_match INTEGER,
    level_match INTEGER,
    culture_match INTEGER,
    industry_match INTEGER,
    growth_potential INTEGER,
    compensation_match INTEGER,
    reasoning TEXT,
    is_hot BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_digests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES candidates(id),
    run_date DATE NOT NULL,
    total_discovered INTEGER DEFAULT 0,
    total_scored INTEGER DEFAULT 0,
    digest_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crawl_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES candidates(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    jobs_discovered INTEGER DEFAULT 0,
    jobs_scored INTEGER DEFAULT 0,
    status pipeline_status DEFAULT 'RUNNING',
    error_log TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discovered_jobs_candidate ON discovered_jobs(candidate_id);
CREATE INDEX IF NOT EXISTS idx_discovered_jobs_url_hash ON discovered_jobs(url_hash);
CREATE INDEX IF NOT EXISTS idx_scored_jobs_candidate ON scored_jobs(candidate_id);
CREATE INDEX IF NOT EXISTS idx_scored_jobs_score ON scored_jobs(composite_score DESC);
```

### `backend/migrations/002_application.sql`

```sql
-- VibeSpace Talent Agent — Application Engine Schema

CREATE TABLE IF NOT EXISTS parsed_jds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES discovered_jobs(id) UNIQUE,
    required_skills TEXT[],
    preferred_skills TEXT[],
    seniority_level VARCHAR(100),
    tech_stack TEXT[],
    culture_signals TEXT[],
    tone VARCHAR(50),
    key_responsibilities TEXT[],
    pain_points TEXT,
    comp_mentioned VARCHAR(255),
    red_flags TEXT[],
    application_instructions TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tailored_resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES discovered_jobs(id),
    candidate_id UUID REFERENCES candidates(id),
    summary TEXT,
    full_text TEXT NOT NULL,
    change_log TEXT,
    pdf_path VARCHAR(500),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS company_intel (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    about TEXT,
    recent_news TEXT,
    tech_stack TEXT[],
    engineering_culture TEXT,
    growth_stage VARCHAR(100),
    team_size VARCHAR(100),
    notable_facts TEXT,
    cache_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_intel_id UUID REFERENCES company_intel(id),
    name VARCHAR(255),
    title VARCHAR(255),
    email VARCHAR(255),
    linkedin_url VARCHAR(500),
    confidence VARCHAR(20) DEFAULT 'LOW',
    source VARCHAR(100),
    fallback_email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outreach_emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES discovered_jobs(id),
    candidate_id UUID REFERENCES candidates(id),
    contact_id UUID REFERENCES contacts(id),
    subject VARCHAR(500),
    body TEXT NOT NULL,
    tone_used VARCHAR(100),
    hook_used TEXT,
    status VARCHAR(50) DEFAULT 'DRAFT',
    sent_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS application_pipelines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES discovered_jobs(id),
    candidate_id UUID REFERENCES candidates(id),
    status VARCHAR(100) DEFAULT 'QUEUED',
    current_step VARCHAR(100),
    resume_id UUID REFERENCES tailored_resumes(id),
    email_id UUID REFERENCES outreach_emails(id),
    submitted_at TIMESTAMPTZ,
    confirmation_number VARCHAR(255),
    screenshot_dir VARCHAR(500),
    error_log TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_intel_name ON company_intel(company_name);
CREATE INDEX IF NOT EXISTS idx_application_pipelines_status ON application_pipelines(status);
CREATE INDEX IF NOT EXISTS idx_outreach_emails_job ON outreach_emails(job_id);
```

---

## STEP 7 — TEST SCAFFOLD

### `tests/conftest.py`

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

### `tests/test_health.py`

```python
import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "talent-agent"
```

---

## STEP 8 — MAKEFILE

```makefile
.PHONY: up down build logs shell test migrate install

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f app

shell:
	docker-compose exec app bash

test:
	pytest tests/ -v

migrate:
	docker-compose exec db psql -U talent_agent -d talent_agent -f /docker-entrypoint-initdb.d/000_init.sql
	docker-compose exec db psql -U talent_agent -d talent_agent -f /docker-entrypoint-initdb.d/001_discovery.sql
	docker-compose exec db psql -U talent_agent -d talent_agent -f /docker-entrypoint-initdb.d/002_application.sql

install:
	pip install -r requirements.txt
	playwright install chromium

dev:
	uvicorn backend.main:app --reload --port 8000
```

---

## STEP 9 — .gitignore

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.venv/
venv/
*.egg-info/
dist/
build/
.DS_Store
screenshots/
*.pdf
postgres_data/
```

---

## STEP 10 — VERIFY

Run these checks in order. All must pass before you declare infrastructure complete:

```bash
# 1. Start the stack
make up

# 2. Check all containers are healthy
docker-compose ps
# Expected: app, db, redis, celery all Up/healthy

# 3. Hit the health endpoint
curl http://localhost:8000/health
# Expected: {"status":"ok","app":"talent-agent",...}

# 4. Check API stubs
curl http://localhost:8000/api/v1/discovery/status
curl http://localhost:8000/api/v1/application/status
curl http://localhost:8000/api/v1/review/status
# Expected: each returns {"engine":"...","status":"ready"}

# 5. Verify DB migrations ran
docker-compose exec db psql -U talent_agent -d talent_agent -c "\dt"
# Expected: candidates, discovered_jobs, scored_jobs, daily_digests,
#           crawl_runs, parsed_jds, tailored_resumes, company_intel,
#           contacts, outreach_emails, application_pipelines

# 6. Run tests
make test
# Expected: test_health PASSED

# 7. Verify Redis
docker-compose exec redis redis-cli ping
# Expected: PONG
```

---

## DONE WHEN

- [ ] Full directory structure created
- [ ] `requirements.txt` installed
- [ ] Docker stack runs with `make up`
- [ ] All containers healthy
- [ ] `/health` returns 200
- [ ] All 3 API stub routes return 200
- [ ] All 11 DB tables exist
- [ ] `make test` is green
- [ ] Redis responds to PING
- [ ] `.env` created from `.env.example` with real `ANTHROPIC_API_KEY`

Infrastructure is live. Now run `01-discovery-engine.md`. 🚀
