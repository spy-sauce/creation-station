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
