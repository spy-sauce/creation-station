#!/usr/bin/env bash
# Stop everything — servers + Docker containers

echo "Stopping Talent Agent..."

# Kill any running uvicorn/vite
pkill -f "uvicorn backend.main" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# Stop Docker containers
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true

echo "✓ Everything stopped"
