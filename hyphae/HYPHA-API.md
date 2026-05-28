# HYPHA-API

> HYPHA tag: `TA/API`
> Maps to Mycelium agent: `api-agent`

## Goal

Own the FastAPI application: app lifespan, middleware, health endpoint, CORS, and the `/api/v1` router that mounts every domain router (auth, onboarding, discovery, application, review). The seam between the frontend dashboard and the backend agents.

## Scope

### In Scope

- `backend/main.py` — FastAPI app, lifespan, CORS, `/health`
- `backend/api/router.py` — `APIRouter(prefix="/api/v1")` mounting per-domain routers
- `backend/api/discovery.py` — discovery trigger + digest read endpoints
- `backend/api/application.py` — application start, submit, list, get-pipeline endpoints
- `backend/api/review.py` — review queue + approve/reject endpoints
- `backend/api/onboarding.py` — resume upload, profile, status endpoints
- `backend/api/auth.py` — magic-link + JWT endpoints (mounted here, logic in auth-agent)
- `backend/config.py` — Pydantic Settings (env-driven config)
- `backend/database.py` — async SQLAlchemy engine, session factory, `get_db` dependency, Redis client
- `backend/seed.py` — dev-mode seeding helper
- OpenAPI schema served at `/docs` and `/openapi.json` in non-prod

### Out of Scope

- Per-endpoint business logic (delegated to agent biomes)
- API documentation beyond FastAPI's built-in OpenAPI
- Versioned API surfaces beyond `/api/v1`
- WebSocket / SSE endpoints (polling only for MVP)

## Inputs

- `TA/AUTH` (HYPHA-AUTH): `auth.router` + `get_current_user` dependency
- `TA/ONBOARD` (HYPHA-ONBOARDING): `onboarding.router`
- `TA/DISCOVER` (HYPHA-DISCOVERY-ENGINE): `DiscoveryOrchestrator`
- `TA/APPLY` (HYPHA-APPLICATION-ENGINE): `ApplicationOrchestrator`
- `TA/AGENTS` (HYPHA-AGENT-MANAGER): `AgentManager` (optional dispatch path)
- `TA/SCHEMA` (HYPHA-SCHEMA-CORE): Every ORM model and Pydantic schema
- `TA/DATA` (HYPHA-DATA): Database connection, migrations

## Outputs (Deliverables)

### Core App

- `backend/main.py`
- `backend/config.py`
- `backend/database.py`
- `backend/seed.py`

### Routers

- `backend/api/__init__.py`
- `backend/api/router.py`
- `backend/api/auth.py`
- `backend/api/onboarding.py`
- `backend/api/discovery.py`
- `backend/api/application.py`
- `backend/api/review.py`

### Mounted Contracts

All routes under `/api/v1/{auth,onboarding,discovery,application,review}/…`

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | `{ status: "ok", version, git_sha, redis, db }` |
| `/api/v1/auth/request-link` | POST | Request magic link |
| `/api/v1/auth/verify` | POST | Verify token, return JWT |
| `/api/v1/auth/me` | GET | Current user info |
| `/api/v1/onboarding/resume` | POST | Upload resume PDF |
| `/api/v1/onboarding/profile` | POST | Save profile |
| `/api/v1/onboarding/status` | GET | Onboarding completeness |
| `/api/v1/discovery/trigger` | POST | Trigger discovery run |
| `/api/v1/discovery/digest/{id}` | GET | Get daily digest |
| `/api/v1/application/start` | POST | Start application pipeline |
| `/api/v1/application/submit/{id}` | POST | Submit approved application |
| `/api/v1/application/list` | GET | List pipelines |
| `/api/v1/application/{id}` | GET | Get pipeline details |
| `/api/v1/review/queue` | GET | Pipelines awaiting review |
| `/api/v1/review/{id}/approve` | POST | Approve pipeline |
| `/api/v1/review/{id}/reject` | POST | Reject pipeline |

## Acceptance Criteria

- [ ] `uvicorn backend.main:app` starts cleanly against live Postgres + Redis
- [ ] `GET /health` returns `200 { "status": "ok", "version": <string>, "git_sha": <string>, "redis": "ok"|"down", "db": "ok"|"down" }`
- [ ] CORS allows configured frontend origins (dev: `http://localhost:5173`)
- [ ] `app.include_router(router)` mounts `/api/v1` router at app root
- [ ] All five sub-routers mounted with declared prefixes + tags
- [ ] Database engine uses `postgresql+asyncpg://` URL from `DATABASE_URL`
- [ ] Redis client uses `redis://` URL from `REDIS_URL`
- [ ] `get_db()` yields `AsyncSession` and rolls back on exception
- [ ] Settings load from environment via Pydantic Settings; missing required env returns clean startup error
- [ ] `backend/seed.py` seeds dev candidate + sample scored job + sample pipeline
- [ ] All endpoints that mutate state require `Depends(get_current_user)` except bootstrap routes
- [ ] `/docs` and `/openapi.json` served in non-prod environments
- [ ] `ruff check backend/main.py backend/api/ backend/config.py backend/database.py` clean
- [ ] `pytest tests/` runs smoke suite green

## Notes

- `backend/api/router.py` is the canonical aggregator. New domain routers added here, not at `main.py`.
- `backend/config.py` is the ONLY legal place to read env vars. No `os.environ.get` elsewhere.
- `app.state` convention for sharing Anthropic client and Redis pool across requests.
- `/health` consumed by Digital Dash `health-check` stage — response shape is contractually frozen.
- API versioning: `/api/v2` breaking change requires brief amendment.
- CORS allowlist + JWT secret are staging/prod-sensitive settings — verify before non-local deploy.
