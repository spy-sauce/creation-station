# HYPHA-INFRA-DEPLOY

> HYPHA tag: `TA/INFRA`
> Maps to Mycelium agent: `infra-agent`

## Goal

Own the containerization, local-dev orchestration, AWS deployment, and Digital Dash CI/CD pipeline for Talent Agent. From `make up` to `./deploy/deploy.sh prod backend <sha>` to the production health check.

**Iter-4 Focus:** Decompose into leaves for surgical changes. Add Celery worker and beat containers to docker-compose and ECS. Each leaf owns one artifact — no cross-artifact edits.

## Scope

### In Scope

- Backend `Dockerfile` (multi-stage; final image runs uvicorn)
- Frontend `Dockerfile` + `nginx.conf` (builds React + serves `dist/`)
- `docker-compose.yml` — local dev stack (postgres + redis + backend + frontend + **celery-worker + celery-beat**)
- `Makefile` — common targets (`up`, `down`, `logs`, `seed`, `lint`, `test`)
- `start.sh` / `stop.sh` — opinionated dev wrappers
- `deploy/setup-aws.sh` — one-time bootstrap (ECR repos, ECS cluster, IAM, Secrets Manager entries, **Celery IAM role**)
- `deploy/deploy.sh` — service deploy + rollback for backend/frontend across local/staging/prod
- `deploy/ecs-task-def-backend.json` + `deploy/ecs-task-def-frontend.json` — Fargate task definitions
- **`deploy/ecs-task-def-celery-worker.json`** — (NEW in iter-4) Fargate task for Celery workers
- **`deploy/ecs-task-def-celery-beat.json`** — (NEW in iter-4) Fargate task for Celery beat scheduler
- `digital-dash-pipeline.yml` — pipeline spec (lint → test → build → deploy-staging → health-check → **deploy-celery** → deploy-prod with manual gate)
- `.env.example` — env-var template
- `.dockerignore` (if present; create if missing)

### Out of Scope

- Multi-region deployment (us-east-1 only)
- Blue/green or canary (rolling update via ECS service update)
- Database backups (RDS managed)
- TLS cert provisioning (assume ACM cert exists, wired in ALB)
- Container runtime alternatives (no Kubernetes; ECS Fargate only)
- Pipeline alternatives (no GitHub Actions / CircleCI — Digital Dash is the pipeline)

## Inputs

- api-surface: backend exposes port 8000, `/health` returns `{status: "ok", version}`
- review-dashboard: frontend builds to `dist/`, nginx serves on 80
- scheduler-agent: Celery app at `backend.scheduler.celery_app`, tasks in `backend.scheduler.tasks`
- Brief §0 (Stack lock) and §12 (Digital Dash result codes)
- AWS Secrets Manager entries (out-of-band): `ANTHROPIC_API_KEY`, `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL`

## Outputs (Deliverables)

### Leaf: infra-agent.docker.backend
- `backend/Dockerfile`

### Leaf: infra-agent.docker.frontend
- `frontend/Dockerfile`
- `frontend/nginx.conf`

### Leaf: infra-agent.docker.compose
- `docker-compose.yml`

### Leaf: infra-agent.ecs.task-defs
- `deploy/ecs-task-def-backend.json`
- `deploy/ecs-task-def-frontend.json`
- `deploy/ecs-task-def-celery-worker.json`
- `deploy/ecs-task-def-celery-beat.json`

### Leaf: infra-agent.ecs.bootstrap
- `deploy/setup-aws.sh`

### Leaf: infra-agent.pipeline.digital-dash
- `digital-dash-pipeline.yml`

### Shared (not leaf-assigned)
- `Makefile`
- `start.sh`, `stop.sh`
- `.env.example`
- `deploy/deploy.sh`
- `auto-commit.sh`

## Acceptance Criteria

### Local

- [ ] `docker-compose up -d` brings up 6 services: postgres, redis, backend, frontend, celery-worker, celery-beat with healthy containers
- [ ] `make up` is equivalent to `docker-compose up -d`
- [ ] `make down` stops all services cleanly
- [ ] `make seed` runs `backend/seed.py` against the local DB
- [ ] `make logs` tails container logs
- [ ] Backend reaches `GET /health` returning `{status: "ok", …}` within 30s of `make up`
- [ ] Frontend reaches `http://localhost:5173` and renders Landing
- [ ] `docker-compose logs celery-beat` shows the daily task scheduled
- [ ] `docker-compose logs celery-worker` shows worker ready to accept tasks

### Docker images

- [ ] Backend `Dockerfile` is multi-stage; runtime image is sub-500MB and runs as non-root
- [ ] Backend image starts uvicorn on `0.0.0.0:8000` by default
- [ ] Frontend `Dockerfile` builds the React app with `npm ci && npm run build`, copies `dist/` into nginx, serves at port 80
- [ ] Frontend nginx config falls back to `index.html` for unmatched routes (SPA history routing)
- [ ] Celery containers reuse backend image with different entrypoint

### docker-compose.yml (Iter-4)

- [ ] `celery-worker` service defined with `depends_on: [redis, postgres]` and healthcheck
- [ ] `celery-beat` service defined with `depends_on: [redis, postgres]` and healthcheck
- [ ] Both services read same `.env` as backend
- [ ] Worker command: `celery -A backend.scheduler.celery_app worker --loglevel=info`
- [ ] Beat command: `celery -A backend.scheduler.celery_app beat --loglevel=info`

### AWS / ECS

- [ ] `deploy/setup-aws.sh` runs idempotently — re-running does not duplicate ECR repos or IAM roles
- [ ] ECR repos `talent-agent-backend` and `talent-agent-frontend` exist after bootstrap
- [ ] ECS cluster `vibespace-prod` exists with services `talent-agent-backend`, `talent-agent-frontend`, `talent-agent-celery-worker`, `talent-agent-celery-beat`
- [ ] Task definitions pull `ANTHROPIC_API_KEY`, `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL` from AWS Secrets Manager (no plaintext secrets in JSON)
- [ ] `deploy/ecs-task-def-celery-worker.json` has `desired_count: 2` with auto-scaling on CPU > 70%
- [ ] `deploy/ecs-task-def-celery-beat.json` has `desired_count: 1` (singleton)
- [ ] `./deploy/deploy.sh staging backend <git-sha>` builds, pushes to ECR, registers a new task def revision, updates the ECS service, waits for the deployment to stabilize
- [ ] `./deploy/deploy.sh prod backend --rollback` reverts the service to the previous task def revision
- [ ] `./deploy/deploy.sh local` is a `docker-compose up` shortcut
- [ ] `aws ecs describe-task-definition --task-definition talent-agent-celery-worker` returns a definition matching the JSON file

### Celery IAM Role (Iter-4)

- [ ] `setup-aws.sh` provisions IAM role `talent-agent-celery-task-role`
- [ ] Role has permissions: `ses:SendEmail`, `sqs:*` (for dead-letter), `cloudwatch:PutMetricData`
- [ ] Role is append-only — does not modify existing role declarations

### Digital Dash pipeline

- [ ] `digital-dash-pipeline.yml` validates as YAML
- [ ] Stages run in order: `lint` → `test` → `build` → `deploy-staging` → `health-check` → `deploy-celery` → `deploy-prod`
- [ ] `lint` runs `ruff check backend/`, `ruff format backend/ --check`, frontend `npm run lint`, and `bandit -ll` / `safety check` (warn-only)
- [ ] `test` provisions postgres + redis services and runs `pytest tests/`
- [ ] `build` is gated to `main` and `release/*` branches
- [ ] `deploy-celery` stage deploys celery-worker and celery-beat to staging, gated by manual approval
- [ ] `deploy-prod` requires manual approval from `spy@seanyoung.biz` with 24h timeout
- [ ] `verify-prod` triggers an auto-rollback (backend + frontend + celery) if `/health` is not `ok` post-deploy
- [ ] Green pipeline auto-merges; red flags for human review; warned passes notify

### Auto-commit

- [ ] `./auto-commit.sh "[TA] message"` stages tracked changes, creates a commit prefixed with the stream tag, and refuses to commit secrets (`.env`, `credentials.json`)
- [ ] `./auto-commit.sh` with no args auto-detects scope from changed files

## Notes

- The `vibespace-prod` ECS cluster is shared across VibeSpace products. Service names are product-scoped.
- Region is `us-east-1` everywhere. Changing region requires a brief amendment.
- Secrets must NEVER appear in task definition JSON in plaintext — always `valueFrom` ARNs to Secrets Manager.
- `health-check` stage uses `${STAGING_URL}` and a 5×10s retry pattern. Don't shorten the retry window.
- `deploy-prod` manual gate is non-negotiable for this cultivation.
- Rollback strategy: deploy.sh stores the previous task def revision; rollback re-registers it as the active service.
- Database migrations are NOT auto-rolled back — that's a manual revert with explicit confirmation.
- The pipeline spec version (`spec_version: "1.0.0"`) tracks the Digital Dash framework.
- `auto-commit.sh` is the canonical commit path. Skipping it for ad-hoc commits is a CLAUDE.md violation.
- Celery worker and beat share the backend image but with different entrypoints. No separate Dockerfile needed.
- The `deploy-celery` stage is gated by manual approval because schedulers should not auto-deploy on every push.
