#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  deploy.sh — Talent Agent Deployment Script                                ║
# ║  VibeSpace LLC · Integrated with Digital Dash Pipeline                     ║
# ║                                                                            ║
# ║  Usage:                                                                    ║
# ║    ./deploy/deploy.sh <environment> <service> [image_tag]                  ║
# ║    ./deploy/deploy.sh <environment> <service> --rollback                   ║
# ║    ./deploy/deploy.sh <environment> all [image_tag]                        ║
# ║                                                                            ║
# ║  Examples:                                                                 ║
# ║    ./deploy/deploy.sh staging backend abc1234                              ║
# ║    ./deploy/deploy.sh prod all                     # uses :latest          ║
# ║    ./deploy/deploy.sh prod backend --rollback      # rolls back            ║
# ║    ./deploy/deploy.sh local                        # docker-compose up     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

# ─── Config ──────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECS_CLUSTER="${ECS_CLUSTER:-vibespace-prod}"

# Service → ECS mapping
declare -A ECS_SERVICES=(
  [backend]="talent-agent-backend"
  [frontend]="talent-agent-frontend"
)

declare -A ECR_REPOS=(
  [backend]="talent-agent-backend"
  [frontend]="talent-agent-frontend"
)

declare -A TASK_DEFS=(
  [backend]="talent-agent-backend"
  [frontend]="talent-agent-frontend"
)

# ─── Colors ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log()  { echo -e "${CYAN}[deploy]${RESET} $*"; }
ok()   { echo -e "${GREEN}[deploy]${RESET} $*"; }
warn() { echo -e "${YELLOW}[deploy]${RESET} $*"; }
die()  { echo -e "${RED}[deploy]${RESET} $*" >&2; exit 1; }

# ─── Helpers ─────────────────────────────────────────────────────────────────

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

get_git_sha() {
  git rev-parse --short HEAD 2>/dev/null || echo "unknown"
}

get_timestamp() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

ecr_login() {
  log "Authenticating with ECR..."
  aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${ECR_REGISTRY}" 2>/dev/null
  ok "ECR authentication successful"
}

# ─── Build ───────────────────────────────────────────────────────────────────

build_image() {
  local service="$1"
  local tag="$2"
  local image="${ECR_REGISTRY}/${ECR_REPOS[$service]}:${tag}"

  log "Building ${BOLD}${service}${RESET} image → ${image}"

  if [[ "$service" == "backend" ]]; then
    docker build \
      -t "${image}" \
      -t "${ECR_REGISTRY}/${ECR_REPOS[$service]}:latest" \
      -f "${PROJECT_ROOT}/Dockerfile" \
      "${PROJECT_ROOT}"
  elif [[ "$service" == "frontend" ]]; then
    local api_url=""
    if [[ "$ENV" == "staging" ]]; then
      api_url="https://staging.talent-agent.seanyoung.biz/api/v1"
    elif [[ "$ENV" == "prod" ]]; then
      api_url="https://talent-agent.seanyoung.biz/api/v1"
    fi

    docker build \
      --build-arg VITE_API_URL="${api_url}" \
      -t "${image}" \
      -t "${ECR_REGISTRY}/${ECR_REPOS[$service]}:latest" \
      -f "${PROJECT_ROOT}/frontend/Dockerfile" \
      "${PROJECT_ROOT}/frontend"
  fi

  ok "Built ${service} → ${image}"
}

push_image() {
  local service="$1"
  local tag="$2"
  local image="${ECR_REGISTRY}/${ECR_REPOS[$service]}"

  log "Pushing ${BOLD}${service}${RESET} images..."
  docker push "${image}:${tag}"
  docker push "${image}:latest"
  ok "Pushed ${service}:${tag} + :latest"
}

# ─── Deploy to ECS ───────────────────────────────────────────────────────────

deploy_ecs() {
  local service="$1"
  local tag="$2"
  local ecs_service="${ECS_SERVICES[$service]}"
  local task_def="${TASK_DEFS[$service]}"
  local image="${ECR_REGISTRY}/${ECR_REPOS[$service]}:${tag}"
  local cluster="${ECS_CLUSTER}"

  # Add environment suffix for staging
  if [[ "$ENV" == "staging" ]]; then
    cluster="${ECS_CLUSTER}-staging"
    ecs_service="${ecs_service}-staging"
    task_def="${task_def}-staging"
  fi

  log "Deploying ${BOLD}${service}${RESET} to ECS..."
  log "  Cluster:  ${cluster}"
  log "  Service:  ${ecs_service}"
  log "  Image:    ${image}"

  # Get current task definition
  local current_task_def
  current_task_def=$(aws ecs describe-task-definition \
    --task-definition "${task_def}" \
    --region "${AWS_REGION}" \
    --query 'taskDefinition' \
    --output json 2>/dev/null) || die "Failed to fetch task definition: ${task_def}"

  # Update the image in the container definition
  local new_task_def
  new_task_def=$(echo "$current_task_def" | \
    jq --arg IMAGE "$image" \
    '.containerDefinitions[0].image = $IMAGE |
     del(.taskDefinitionArn, .revision, .status, .requiresAttributes,
         .compatibilities, .registeredAt, .registeredBy)')

  # Register new task definition revision
  local new_revision
  new_revision=$(aws ecs register-task-definition \
    --region "${AWS_REGION}" \
    --cli-input-json "$new_task_def" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text) || die "Failed to register new task definition"

  log "  New task def: ${new_revision}"

  # Update the service to use the new task definition
  aws ecs update-service \
    --region "${AWS_REGION}" \
    --cluster "${cluster}" \
    --service "${ecs_service}" \
    --task-definition "${new_revision}" \
    --force-new-deployment \
    --query 'service.serviceName' \
    --output text >/dev/null || die "Failed to update ECS service"

  ok "Deployment initiated for ${service} on ${cluster}"

  # Wait for service stability
  log "Waiting for ${service} to stabilize (timeout: 5m)..."
  if aws ecs wait services-stable \
    --region "${AWS_REGION}" \
    --cluster "${cluster}" \
    --services "${ecs_service}" 2>/dev/null; then
    ok "${service} is stable and running ✓"
  else
    die "${service} failed to stabilize — check ECS console"
  fi
}

# ─── Rollback ────────────────────────────────────────────────────────────────

rollback_ecs() {
  local service="$1"
  local ecs_service="${ECS_SERVICES[$service]}"
  local task_def="${TASK_DEFS[$service]}"
  local cluster="${ECS_CLUSTER}"

  if [[ "$ENV" == "staging" ]]; then
    cluster="${ECS_CLUSTER}-staging"
    ecs_service="${ecs_service}-staging"
    task_def="${task_def}-staging"
  fi

  warn "Rolling back ${BOLD}${service}${RESET}..."

  # Get the previous task definition revision
  local revisions
  revisions=$(aws ecs list-task-definitions \
    --family-prefix "${task_def}" \
    --region "${AWS_REGION}" \
    --sort DESC \
    --query 'taskDefinitionArns[0:2]' \
    --output json)

  local previous_revision
  previous_revision=$(echo "$revisions" | jq -r '.[1] // empty')

  if [[ -z "$previous_revision" ]]; then
    die "No previous revision found for ${task_def} — cannot rollback"
  fi

  log "Rolling back to: ${previous_revision}"

  aws ecs update-service \
    --region "${AWS_REGION}" \
    --cluster "${cluster}" \
    --service "${ecs_service}" \
    --task-definition "${previous_revision}" \
    --force-new-deployment \
    --query 'service.serviceName' \
    --output text >/dev/null || die "Rollback failed"

  log "Waiting for rollback to stabilize..."
  aws ecs wait services-stable \
    --region "${AWS_REGION}" \
    --cluster "${cluster}" \
    --services "${ecs_service}" 2>/dev/null

  ok "Rollback complete for ${service} ✓"
}

# ─── Local Deploy (docker-compose) ──────────────────────────────────────────

deploy_local() {
  log "Running local deployment via docker-compose..."
  cd "${PROJECT_ROOT}"

  docker-compose down --remove-orphans 2>/dev/null || true
  docker-compose build
  docker-compose up -d

  log "Waiting for services..."
  sleep 5

  # Health check
  for i in 1 2 3 4 5; do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
      ok "Local deployment is healthy ✓"
      echo ""
      log "Services:"
      log "  Backend:   http://localhost:8000"
      log "  Frontend:  http://localhost:5173 (run 'cd frontend && npm run dev')"
      log "  Postgres:  localhost:5432"
      log "  Redis:     localhost:6379"
      echo ""
      docker-compose ps
      exit 0
    fi
    log "Attempt $i — waiting..."
    sleep 3
  done

  warn "Backend not responding yet — check logs with: docker-compose logs -f app"
}

# ─── Run Database Migrations ─────────────────────────────────────────────────

run_migrations() {
  local env="$1"
  log "Running database migrations for ${env}..."

  if [[ "$env" == "local" ]]; then
    docker-compose exec -T db psql -U talent_agent -d talent_agent \
      -f /docker-entrypoint-initdb.d/000_init.sql 2>/dev/null || true
    docker-compose exec -T db psql -U talent_agent -d talent_agent \
      -f /docker-entrypoint-initdb.d/001_discovery.sql
    docker-compose exec -T db psql -U talent_agent -d talent_agent \
      -f /docker-entrypoint-initdb.d/002_application.sql
    docker-compose exec -T db psql -U talent_agent -d talent_agent \
      -f /docker-entrypoint-initdb.d/003_auth.sql
  else
    # For staging/prod, migrations run via the app's SQLAlchemy create_all
    # or via a dedicated migration task
    log "Remote migrations handled by app startup (SQLAlchemy metadata.create_all)"
  fi

  ok "Migrations complete ✓"
}

# ─── Main ────────────────────────────────────────────────────────────────────

usage() {
  echo ""
  echo -e "${BOLD}Usage:${RESET}"
  echo "  ./deploy/deploy.sh <environment> [service] [image_tag|--rollback]"
  echo ""
  echo -e "${BOLD}Environments:${RESET}"
  echo "  local     Docker Compose (development)"
  echo "  staging   ECS Fargate staging cluster"
  echo "  prod      ECS Fargate production cluster"
  echo ""
  echo -e "${BOLD}Services:${RESET}"
  echo "  backend   FastAPI backend"
  echo "  frontend  React frontend (Nginx)"
  echo "  all       Both services"
  echo ""
  echo -e "${BOLD}Examples:${RESET}"
  echo "  ./deploy/deploy.sh local                        # spin up local env"
  echo "  ./deploy/deploy.sh local --migrate              # local + run migrations"
  echo "  ./deploy/deploy.sh staging backend abc1234      # deploy specific tag"
  echo "  ./deploy/deploy.sh staging all                  # deploy both, :latest"
  echo "  ./deploy/deploy.sh prod backend --rollback      # rollback backend"
  echo "  ./deploy/deploy.sh prod all abc1234             # deploy both to prod"
  echo ""
  exit 1
}

main() {
  ENV="${1:-}"
  SERVICE="${2:-all}"
  TAG="${3:-$(get_git_sha)}"

  [[ -z "$ENV" ]] && usage

  echo ""
  echo -e "${CYAN}╔══════════════════════════════════════════════════╗${RESET}"
  echo -e "${CYAN}║${RESET}  ${BOLD}Talent Agent — Deployment${RESET}                        ${CYAN}║${RESET}"
  echo -e "${CYAN}║${RESET}  VibeSpace LLC · Digital Dash Pipeline           ${CYAN}║${RESET}"
  echo -e "${CYAN}╚══════════════════════════════════════════════════╝${RESET}"
  echo ""
  log "Environment: ${BOLD}${ENV}${RESET}"
  log "Service:     ${BOLD}${SERVICE}${RESET}"
  log "Tag:         ${BOLD}${TAG}${RESET}"
  log "Timestamp:   $(get_timestamp)"
  log "Git SHA:     $(get_git_sha)"
  echo ""

  # ── Local deployment ───────────────────────────────────────────────────
  if [[ "$ENV" == "local" ]]; then
    require_cmd docker
    require_cmd docker-compose

    if [[ "$SERVICE" == "--migrate" || "$TAG" == "--migrate" ]]; then
      deploy_local
      run_migrations local
    else
      deploy_local
    fi
    exit 0
  fi

  # ── Cloud deployment (staging / prod) ──────────────────────────────────
  require_cmd aws
  require_cmd docker
  require_cmd jq

  [[ -z "$AWS_ACCOUNT_ID" ]] && die "AWS_ACCOUNT_ID is not set. Export it or add to .env"

  # Rollback mode
  if [[ "$TAG" == "--rollback" ]]; then
    if [[ "$SERVICE" == "all" ]]; then
      rollback_ecs backend
      rollback_ecs frontend
    else
      rollback_ecs "$SERVICE"
    fi
    exit 0
  fi

  # Build + Push + Deploy
  ecr_login

  deploy_service() {
    local svc="$1"
    build_image "$svc" "$TAG"
    push_image "$svc" "$TAG"
    deploy_ecs "$svc" "$TAG"
  }

  if [[ "$SERVICE" == "all" ]]; then
    deploy_service backend
    deploy_service frontend
  else
    [[ -z "${ECS_SERVICES[$SERVICE]+_}" ]] && die "Unknown service: ${SERVICE}. Use: backend, frontend, all"
    deploy_service "$SERVICE"
  fi

  echo ""
  ok "═══════════════════════════════════════════════════"
  ok "  Deployment complete! 🚀"
  ok "  ${ENV} / ${SERVICE} / ${TAG}"
  ok "═══════════════════════════════════════════════════"
  echo ""
}

main "$@"
