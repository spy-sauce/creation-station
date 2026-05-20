#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  setup-aws.sh — One-time AWS infrastructure setup for Talent Agent         ║
# ║  VibeSpace LLC                                                             ║
# ║                                                                            ║
# ║  Run this ONCE to create all the AWS resources needed for deployment.      ║
# ║  After this, deploy.sh handles everything.                                 ║
# ║                                                                            ║
# ║  Prerequisites:                                                            ║
# ║    - AWS CLI configured with appropriate IAM permissions                   ║
# ║    - AWS_ACCOUNT_ID exported                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:?'AWS_ACCOUNT_ID must be set'}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

log()  { echo -e "${CYAN}[setup]${RESET} $*"; }
ok()   { echo -e "${GREEN}[setup]${RESET} $*"; }
warn() { echo -e "${YELLOW}[setup]${RESET} $*"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}║${RESET}  ${BOLD}Talent Agent — AWS Infrastructure Setup${RESET}        ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}  VibeSpace LLC · One-time bootstrap              ${CYAN}║${RESET}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${RESET}"
echo ""

# ── 1. ECR Repositories ──────────────────────────────────────────────────────

log "Creating ECR repositories..."

for repo in talent-agent-backend talent-agent-frontend; do
  if aws ecr describe-repositories --repository-names "$repo" --region "$AWS_REGION" >/dev/null 2>&1; then
    warn "ECR repo '${repo}' already exists — skipping"
  else
    aws ecr create-repository \
      --repository-name "$repo" \
      --region "$AWS_REGION" \
      --image-scanning-configuration scanOnPush=true \
      --encryption-configuration encryptionType=AES256 \
      --query 'repository.repositoryUri' \
      --output text
    ok "Created ECR repo: ${repo}"
  fi
done

# Set lifecycle policy (keep last 10 images)
LIFECYCLE_POLICY='{"rules":[{"rulePriority":1,"description":"Keep last 10 images","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":10},"action":{"type":"expire"}}]}'

for repo in talent-agent-backend talent-agent-frontend; do
  aws ecr put-lifecycle-policy \
    --repository-name "$repo" \
    --region "$AWS_REGION" \
    --lifecycle-policy-text "$LIFECYCLE_POLICY" >/dev/null
done
ok "ECR lifecycle policies set (keep last 10 images)"

# ── 2. CloudWatch Log Groups ─────────────────────────────────────────────────

log "Creating CloudWatch log groups..."

for group in /ecs/talent-agent-backend /ecs/talent-agent-frontend; do
  if aws logs describe-log-groups --log-group-name-prefix "$group" --region "$AWS_REGION" \
    --query "logGroups[?logGroupName=='${group}']" --output text | grep -q "$group"; then
    warn "Log group '${group}' already exists — skipping"
  else
    aws logs create-log-group --log-group-name "$group" --region "$AWS_REGION"
    aws logs put-retention-policy --log-group-name "$group" --retention-in-days 30 --region "$AWS_REGION"
    ok "Created log group: ${group} (30 day retention)"
  fi
done

# ── 3. ECS Cluster ───────────────────────────────────────────────────────────

log "Creating ECS clusters..."

for cluster in vibespace-prod vibespace-prod-staging; do
  if aws ecs describe-clusters --clusters "$cluster" --region "$AWS_REGION" \
    --query "clusters[?status=='ACTIVE'].clusterName" --output text | grep -q "$cluster"; then
    warn "ECS cluster '${cluster}' already exists — skipping"
  else
    aws ecs create-cluster \
      --cluster-name "$cluster" \
      --region "$AWS_REGION" \
      --capacity-providers FARGATE FARGATE_SPOT \
      --default-capacity-provider-strategy \
        capacityProvider=FARGATE,weight=1,base=1 \
        capacityProvider=FARGATE_SPOT,weight=3 \
      --query 'cluster.clusterName' \
      --output text
    ok "Created ECS cluster: ${cluster}"
  fi
done

# ── 4. Secrets Manager Placeholders ──────────────────────────────────────────

log "Creating Secrets Manager entries..."
warn "You'll need to update these with real values after creation."

SECRETS=(
  "talent-agent/database-url:postgresql+asyncpg://user:pass@host:5432/talent_agent"
  "talent-agent/redis-url:redis://host:6379/0"
  "talent-agent/anthropic-api-key:sk-ant-placeholder"
  "talent-agent/jwt-secret:change-me-in-production"
  "talent-agent/hunter-api-key:placeholder"
  "talent-agent/resend-api-key:re_placeholder"
)

for entry in "${SECRETS[@]}"; do
  name="${entry%%:*}"
  value="${entry#*:}"

  if aws secretsmanager describe-secret --secret-id "$name" --region "$AWS_REGION" >/dev/null 2>&1; then
    warn "Secret '${name}' already exists — skipping"
  else
    aws secretsmanager create-secret \
      --name "$name" \
      --region "$AWS_REGION" \
      --secret-string "$value" \
      --description "Talent Agent - ${name}" \
      --query 'Name' --output text
    ok "Created secret: ${name}"
  fi
done

# ── 5. Summary ───────────────────────────────────────────────────────────────

echo ""
ok "═══════════════════════════════════════════════════"
ok "  AWS infrastructure setup complete!"
ok "═══════════════════════════════════════════════════"
echo ""
log "Next steps:"
echo "  1. Update secrets in AWS Secrets Manager with real values:"
echo "     - talent-agent/database-url    (your RDS connection string)"
echo "     - talent-agent/redis-url       (your ElastiCache endpoint)"
echo "     - talent-agent/anthropic-api-key"
echo "     - talent-agent/jwt-secret      (generate a strong random string)"
echo "     - talent-agent/hunter-api-key  (Hunter.io for contact lookup)"
echo "     - talent-agent/resend-api-key  (Resend for magic link emails)"
echo ""
echo "  2. Create an RDS PostgreSQL 15 instance + ElastiCache Redis 7 cluster"
echo "     (if you haven't already)"
echo ""
echo "  3. Create an ALB with target groups for backend (:8000) and frontend (:80)"
echo "     - Route /api/* → backend target group"
echo "     - Route /*     → frontend target group"
echo ""
echo "  4. Register the ECS task definitions:"
echo "     aws ecs register-task-definition --cli-input-json file://deploy/ecs-task-def-backend.json"
echo "     aws ecs register-task-definition --cli-input-json file://deploy/ecs-task-def-frontend.json"
echo ""
echo "  5. Create the ECS services (after ALB + target groups are ready):"
echo "     aws ecs create-service --cluster vibespace-prod --service-name talent-agent-backend ..."
echo "     aws ecs create-service --cluster vibespace-prod --service-name talent-agent-frontend ..."
echo ""
echo "  6. Deploy:"
echo "     ./deploy/deploy.sh staging all"
echo ""
