# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Talent Agent — Backend Dockerfile                                         ║
# ║  VibeSpace LLC · Multi-stage build for production                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ── Stage 1: Dependencies ────────────────────────────────────────────────────
FROM python:3.12-slim AS deps

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Playwright (heavy — cached separately) ─────────────────────────
FROM deps AS playwright

RUN playwright install chromium --with-deps

# ── Stage 3: Production image ───────────────────────────────────────────────
FROM playwright AS production

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Create non-root user for security (ECS Fargate best practice)
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

COPY --chown=appuser:appgroup backend/ ./backend/

# Switch to non-root user
USER appuser

# Health check for ECS
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Uvicorn with uvloop for production
CMD ["python", "-m", "uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--loop", "uvloop", \
     "--access-log"]
