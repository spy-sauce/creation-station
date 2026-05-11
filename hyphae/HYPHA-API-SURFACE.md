# HYPHA-API-SURFACE

> HYPHA tag: `TA/API`

## Goal

Own the FastAPI application: app lifespan, middleware, health endpoint, CORS, and the `/api/v1` router that mounts every domain router (auth, onboarding, discovery, application, review). The seam between the dashboard and the agents.

## Scope

### In Scope
- `backend/main.py` — FastAPI app, lifespan, CORS, `/health`
- `backend/api/router.py` — `APIRouter(prefix="/api/v1")` mounting per-domain routers under prefixes
- `backend/api/discovery.py` — discovery trigger + digest read endpoints
- `backend/api/application.py` — application start, submit, list, get-pipeline endpoints
- `backend/api/review.py` — review queue + approve/reject endpoints
- `backend/config.py` — Pydantic Settings (env-driven config)
- `backend/database.py` — async SQLAlchemy engine, session factory, `get_db` dependency, Redis client factory
- `backend/seed.py` — dev-mode seeding helper

### Out of Scope
- The auth, onboarding routers (own their own HYPHAs but mount here)
- Per-endpoint business logic (delegated to agent biomes)
- API documentation generation beyond FastAPI's built-in OpenAPI
- Versioned API surfaces beyond `/api/v1`

## Inputs

- auth: `auth.router` + `get_current_user`
- onboarding: `onboarding.router`
- discovery-engine: `DiscoveryOrchestrator`
- application-engine: `ApplicationOrchestrator`
- agent-manager: `AgentManager` (optional dispatch path)
- schema-core: every ORM model and Pydantic schema this surface returns

## Outputs (Deliverables)

Existing files locked at HEAD:
- `backend/main.py`
- `backend/config.py`
- `backend/database.py`
- `backend/seed.py`
- `backend/api/__init__.py`
- `backend/api/router.py`
- `backend/api/discovery.py`
- `backend/api/application.py`
- `backend/api/review.py`

Mounted contracts:
- All routes under `/api/v1/{auth,onboarding,discovery,application,review}/…`
- `GET /health` → `{ status: "ok", version: "<semver>" }`
- OpenAPI schema served at `/docs` and `/openapi.json` in non-prod

## Acceptance Criteria

- [ ] `uvicorn backend.main:app` starts cleanly against a live Postgres + Redis
- [ ] `GET /health` returns `200 { "status": "ok", "version": <string> }`
- [ ] CORS allows the configured frontend origins (dev: `http://localhost:5173`)
- [ ] `app.include_router(router)` mounts the `/api/v1` router at the app root
- [ ] All five sub-routers (`auth`, `onboarding`, `discovery`, `application`, `review`) are mounted with their declared prefixes + tags
- [ ] Database engine uses `postgresql+asyncpg://` URL from `DATABASE_URL`
- [ ] Redis client uses `redis://` URL from `REDIS_URL`
- [ ] `get_db()` yields an `AsyncSession` and rolls back on exception
- [ ] Settings load from environment via Pydantic Settings; missing required env returns a clean startup error
- [ ] `backend/seed.py` can seed a dev candidate + sample scored job + sample pipeline without crashing
- [ ] `ruff check backend/main.py backend/api/ backend/config.py backend/database.py` clean
- [ ] `pytest tests/` runs the smoke suite green with the test database + test Redis

## Notes

- `backend/api/router.py` is the canonical aggregator. New domain routers must be added here, not at `main.py` level.
- `backend/config.py` is the only legal place to read env vars. Importing `os.environ.get` elsewhere is a violation.
- `app.state` is the convention for sharing the Anthropic client and Redis pool across requests (don't instantiate per-request).
- `/health` is consumed by the Digital Dash pipeline `health-check` stage — its response shape is contractually frozen.
- API versioning: a `/api/v2` breaking change requires a brief amendment.
- All endpoints that mutate state require `Depends(get_current_user)`. The exceptions are `/auth/request-link` and `/auth/verify` (bootstrap), and `/health` (infra).
- The `discovery` / `application` / `review` router contents are referenced in the brief but exact endpoint lists live in their per-domain router files. Adding routes within an existing domain is a leaf-level change, not a brief amendment.
- CORS allowlist + JWT secret are the two staging/prod-sensitive settings — confirm both before any non-local deploy.
