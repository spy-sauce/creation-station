#!/usr/bin/env bash
# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0
#
# auto-commit.sh — VibeSpace intelligent auto-commit script
# Usage:
#   ./auto-commit.sh                     # auto-generates commit message
#   ./auto-commit.sh "custom message"    # custom message passed directly

set -euo pipefail

# ─── helpers ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

log()  { echo -e "${CYAN}[auto-commit]${RESET} $*"; }
ok()   { echo -e "${GREEN}[auto-commit]${RESET} $*"; }
warn() { echo -e "${YELLOW}[auto-commit]${RESET} $*"; }
die()  { echo -e "${RED}[auto-commit]${RESET} $*" >&2; exit 1; }

# ─── guards ───────────────────────────────────────────────────────────────────

git rev-parse --git-dir > /dev/null 2>&1 || die "Not a git repository."

# ─── stage all changes ────────────────────────────────────────────────────────

git add -A

# Check if there is anything to commit
if git diff --cached --quiet; then
  warn "Nothing to commit — working tree clean."
  exit 0
fi

# ─── build commit message ─────────────────────────────────────────────────────

if [[ $# -ge 1 && -n "$1" ]]; then
  COMMIT_MSG="$1"
  log "Using custom message: ${COMMIT_MSG}"
else
  # Detect scope from staged file paths
  STAGED_FILES=$(git diff --cached --name-only)

  detect_scope() {
    local files="$1"
    # Priority order: most specific wins
    if echo "$files" | grep -qE '^backend/api/|^backend/routes/'; then
      echo "api"
    elif echo "$files" | grep -qE '^frontend/|\.tsx?$|\.css$|\.html$'; then
      echo "ui"
    elif echo "$files" | grep -qE '^backend/migrations/|\.sql$'; then
      echo "db"
    elif echo "$files" | grep -qE 'auth|login|token|session'; then
      echo "auth"
    elif echo "$files" | grep -qE '^docs/|\.md$|README'; then
      echo "docs"
    elif echo "$files" | grep -qE '^backend/config|docker|Makefile|requirements|Dockerfile|\.env'; then
      echo "config"
    elif echo "$files" | grep -qE '^tests/|_test\.py$|test_'; then
      echo "test"
    elif echo "$files" | grep -qE '^backend/agents/'; then
      echo "agents"
    else
      echo "core"
    fi
  }

  detect_action() {
    local files="$1"
    local added deleted modified
    added=$(git diff --cached --diff-filter=A --name-only | wc -l | tr -d ' ')
    deleted=$(git diff --cached --diff-filter=D --name-only | wc -l | tr -d ' ')
    modified=$(git diff --cached --diff-filter=M --name-only | wc -l | tr -d ' ')

    if [[ "$deleted" -gt 0 && "$added" -eq 0 ]]; then
      echo "remove"
    elif [[ "$added" -gt 0 && "$modified" -eq 0 && "$deleted" -eq 0 ]]; then
      echo "add"
    elif [[ "$modified" -gt 0 && "$added" -eq 0 ]]; then
      echo "update"
    else
      echo "refactor"
    fi
  }

  SCOPE=$(detect_scope "$STAGED_FILES")
  ACTION=$(detect_action "$STAGED_FILES")
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
  FILE_COUNT=$(echo "$STAGED_FILES" | wc -l | tr -d ' ')

  # Build a short file summary for the message body
  TOP_FILES=$(echo "$STAGED_FILES" | head -3 | paste -sd ', ')
  [[ "$FILE_COUNT" -gt 3 ]] && TOP_FILES="${TOP_FILES} (+$((FILE_COUNT - 3)) more)"

  COMMIT_MSG="feat(${SCOPE}): ${ACTION} changes [${TIMESTAMP}]

Files: ${TOP_FILES}"

  log "Auto-generated message: feat(${SCOPE}): ${ACTION} changes [${TIMESTAMP}]"
fi

# ─── commit ───────────────────────────────────────────────────────────────────

git commit -m "$COMMIT_MSG"
ok "Committed: ${COMMIT_MSG%%$'\n'*}"

# ─── push ─────────────────────────────────────────────────────────────────────

BRANCH=$(git rev-parse --abbrev-ref HEAD)
log "Pushing to origin/${BRANCH}..."

if git remote get-url origin > /dev/null 2>&1; then
  git push origin "$BRANCH"
  ok "Pushed to origin/${BRANCH}"
else
  warn "No remote 'origin' configured — skipping push."
fi
