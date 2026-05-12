#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  start.sh — One command to run Talent Agent locally                        ║
# ║  VibeSpace LLC · Space Cowboy #9                                           ║
# ║                                                                            ║
# ║  Just run:  ./start.sh                                                     ║
# ║                                                                            ║
# ║  This script:                                                              ║
# ║    1. Checks you have Docker + Node installed                              ║
# ║    2. Starts Postgres + Redis via Docker                                   ║
# ║    3. Installs Python + Node dependencies (if needed)                      ║
# ║    4. Runs database migrations                                             ║
# ║    5. Starts the FastAPI backend                                           ║
# ║    6. Starts the Vite frontend dev server                                  ║
# ║    7. Opens your browser to http://localhost:5173                          ║
# ║                                                                            ║
# ║  To stop everything:  Ctrl+C  (or ./stop.sh)                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

# ─── Colors ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

log()  { echo -e "${CYAN}▸${RESET} $*"; }
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
warn() { echo -e "${YELLOW}!${RESET} $*"; }
die()  { echo -e "${RED}✗${RESET} $*" >&2; exit 1; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# ─── Banner ──────────────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}  ╭──────────────────────────────────────╮${RESET}"
echo -e "${CYAN}  │${RESET}  ${BOLD}Talent Agent${RESET}  ${DIM}by VibeSpace LLC${RESET}       ${CYAN}│${RESET}"
echo -e "${CYAN}  │${RESET}  ${DIM}Starting local development server...${RESET}  ${CYAN}│${RESET}"
echo -e "${CYAN}  ╰──────────────────────────────────────╯${RESET}"
echo ""

# ─── Step 1: Check prerequisites ────────────────────────────────────────────

log "Checking prerequisites..."

HAS_DOCKER=true
HAS_NODE=true
HAS_PYTHON=true

command -v docker >/dev/null 2>&1 || HAS_DOCKER=false
command -v node >/dev/null 2>&1   || HAS_NODE=false
command -v python3 >/dev/null 2>&1 || HAS_PYTHON=false

if ! $HAS_DOCKER; then
  die "Docker not found. Install from https://docker.com/products/docker-desktop"
fi

if ! $HAS_NODE; then
  die "Node.js not found. Install from https://nodejs.org (v18+ recommended)"
fi

if ! $HAS_PYTHON; then
  die "Python 3 not found. Install from https://python.org (3.12 recommended)"
fi

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
  die "Docker is installed but not running. Start Docker Desktop first."
fi

ok "Docker, Node $(node -v), Python $(python3 --version | cut -d' ' -f2)"

# ─── Step 2: Environment file ───────────────────────────────────────────────

if [[ ! -f .env ]]; then
  log "Creating .env from .env.example..."
  cp .env.example .env
  warn "Created .env — update ANTHROPIC_API_KEY with your real key when ready"
else
  ok ".env exists"
fi

# ─── Step 3: Start Postgres + Redis ─────────────────────────────────────────

log "Starting database services..."

# Only start db and redis (not the app container — we run that natively for hot reload)
docker compose up -d db redis 2>/dev/null || docker-compose up -d db redis 2>/dev/null

# Wait for Postgres
log "Waiting for Postgres..."
for i in $(seq 1 20); do
  if docker exec talent-agent-db pg_isready -U talent_agent >/dev/null 2>&1; then
    ok "Postgres is ready"
    break
  fi
  if [[ $i -eq 20 ]]; then
    die "Postgres didn't start in time. Check: docker logs talent-agent-db"
  fi
  sleep 1
done

# Wait for Redis
for i in $(seq 1 10); do
  if docker exec talent-agent-redis redis-cli ping >/dev/null 2>&1; then
    ok "Redis is ready"
    break
  fi
  sleep 1
done

# ─── Step 4: Run migrations ─────────────────────────────────────────────────

log "Running database migrations..."

for migration in 000_init 001_discovery 002_application 003_auth; do
  docker exec -i talent-agent-db psql -U talent_agent -d talent_agent \
    < "backend/migrations/${migration}.sql" 2>/dev/null || true
done

ok "Migrations applied"

# ─── Step 5: Install dependencies (if needed) ───────────────────────────────

# Python deps (venv)
VENV_DIR="$PROJECT_ROOT/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  log "Creating Python virtual environment (python3.11)..."
  # Use python3.11 — asyncpg and other C extensions have pre-built wheels for 3.11
  # python3.12 is the project target but 3.11 is ABI-compatible and available on this machine
  PYTHON_BIN=$(command -v python3.11 || command -v python3.12 || command -v python3)
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  ok "venv created at .venv ($(\"$VENV_DIR/bin/python\" --version))"
fi
source "$VENV_DIR/bin/activate"
if ! python3 -c "import fastapi" 2>/dev/null; then
  log "Installing Python dependencies..."
  pip install -r requirements.txt -q
  ok "Python deps installed"
else
  ok "Python deps already installed"
fi

# Node deps
if [[ ! -d frontend/node_modules ]]; then
  log "Installing frontend dependencies..."
  cd frontend && npm install --silent && cd ..
  ok "Frontend deps installed"
else
  ok "Frontend deps already installed"
fi

# ─── Step 6: Start servers ──────────────────────────────────────────────────

echo ""
echo -e "${CYAN}  ╭──────────────────────────────────────╮${RESET}"
echo -e "${CYAN}  │${RESET}  ${GREEN}${BOLD}Starting servers...${RESET}                   ${CYAN}│${RESET}"
echo -e "${CYAN}  ╰──────────────────────────────────────╯${RESET}"
echo ""

# Cleanup function
cleanup() {
  echo ""
  log "Shutting down..."
  kill $BACKEND_PID 2>/dev/null || true
  kill $FRONTEND_PID 2>/dev/null || true
  # Leave Docker containers running (they're lightweight)
  ok "Servers stopped. Docker services still running (run ./stop.sh to stop everything)"
  echo ""
}
trap cleanup EXIT INT TERM

# Start backend
log "Starting FastAPI backend on ${BOLD}http://localhost:8000${RESET}"
cd "$PROJECT_ROOT"
"$VENV_DIR/bin/python" -m uvicorn backend.main:app --reload --port 8000 --log-level info &
BACKEND_PID=$!

# Give backend a moment
sleep 2

# Start frontend
log "Starting Vite frontend on ${BOLD}http://localhost:5173${RESET}"
cd "$PROJECT_ROOT/frontend"
npm run dev -- --host 2>/dev/null &
FRONTEND_PID=$!
cd "$PROJECT_ROOT"

# Wait for both to be ready
sleep 3

echo ""
echo -e "${GREEN}  ╭──────────────────────────────────────╮${RESET}"
echo -e "${GREEN}  │${RESET}                                        ${GREEN}│${RESET}"
echo -e "${GREEN}  │${RESET}  ${BOLD}Talent Agent is running!${RESET}              ${GREEN}│${RESET}"
echo -e "${GREEN}  │${RESET}                                        ${GREEN}│${RESET}"
echo -e "${GREEN}  │${RESET}  Frontend:  ${BOLD}http://localhost:5173${RESET}      ${GREEN}│${RESET}"
echo -e "${GREEN}  │${RESET}  Backend:   ${BOLD}http://localhost:8000${RESET}      ${GREEN}│${RESET}"
echo -e "${GREEN}  │${RESET}  API Docs:  ${BOLD}http://localhost:8000/docs${RESET}  ${GREEN}│${RESET}"
echo -e "${GREEN}  │${RESET}                                        ${GREEN}│${RESET}"
echo -e "${GREEN}  │${RESET}  ${DIM}Press Ctrl+C to stop${RESET}                  ${GREEN}│${RESET}"
echo -e "${GREEN}  │${RESET}                                        ${GREEN}│${RESET}"
echo -e "${GREEN}  ╰──────────────────────────────────────╯${RESET}"
echo ""

# Open browser (macOS)
if command -v open >/dev/null 2>&1; then
  sleep 1
  open "http://localhost:5173/login"
fi

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
