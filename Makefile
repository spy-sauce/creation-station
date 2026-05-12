# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Talent Agent — Makefile                                                   ║
# ║  VibeSpace LLC · Digital Dash integrated                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

.PHONY: up down build logs shell test migrate install dev \
        deploy-local deploy-staging deploy-prod rollback \
        lint pipeline frontend-dev setup-aws

# ─── Local Development ───────────────────────────────────────────────────────

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

install:
	pip install -r requirements.txt
	playwright install chromium

dev:
	uvicorn backend.main:app --reload --port 8000

frontend-dev:
	cd frontend && npm run dev

# ─── Database ────────────────────────────────────────────────────────────────

migrate:
	docker-compose exec db psql -U talent_agent -d talent_agent -f /docker-entrypoint-initdb.d/000_init.sql
	docker-compose exec db psql -U talent_agent -d talent_agent -f /docker-entrypoint-initdb.d/001_discovery.sql
	docker-compose exec db psql -U talent_agent -d talent_agent -f /docker-entrypoint-initdb.d/002_application.sql
	docker-compose exec db psql -U talent_agent -d talent_agent -f /docker-entrypoint-initdb.d/003_auth.sql

# ─── Testing ─────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

lint:
	ruff check backend/ --output-format=github
	ruff format backend/ --check
	cd frontend && npm run lint

# ─── Digital Dash Pipeline (local simulation) ────────────────────────────────

pipeline:
	@echo ""
	@echo "╔══════════════════════════════════════════════════╗"
	@echo "║  Digital Dash — Local Pipeline Run               ║"
	@echo "╚══════════════════════════════════════════════════╝"
	@echo ""
	@echo "Stage 1: Lint..."
	@$(MAKE) lint || (echo "🔴 Lint failed — pipeline blocked" && exit 1)
	@echo "✅ Lint passed"
	@echo ""
	@echo "Stage 2: Test..."
	@$(MAKE) test || (echo "🔴 Tests failed — pipeline blocked" && exit 1)
	@echo "✅ Tests passed"
	@echo ""
	@echo "Stage 3: Build..."
	@docker build -t talent-agent-backend:local -f Dockerfile . || (echo "🔴 Backend build failed" && exit 1)
	@cd frontend && docker build -t talent-agent-frontend:local -f Dockerfile . || (echo "🔴 Frontend build failed" && exit 1)
	@echo "✅ Images built"
	@echo ""
	@echo "╔══════════════════════════════════════════════════╗"
	@echo "║  ✅ Pipeline GREEN — ready for deployment        ║"
	@echo "╚══════════════════════════════════════════════════╝"

# ─── Deployment ──────────────────────────────────────────────────────────────

deploy-local:
	./deploy/deploy.sh local

deploy-staging:
	./deploy/deploy.sh staging all

deploy-prod:
	./deploy/deploy.sh prod all

rollback:
	@echo "Usage: make rollback-staging or make rollback-prod"

rollback-staging:
	./deploy/deploy.sh staging backend --rollback
	./deploy/deploy.sh staging frontend --rollback

rollback-prod:
	./deploy/deploy.sh prod backend --rollback
	./deploy/deploy.sh prod frontend --rollback

# ─── AWS Setup (one-time) ───────────────────────────────────────────────────

setup-aws:
	./deploy/setup-aws.sh
