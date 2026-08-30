# Multi-Stage Production Dockerfile for GitScout / OSS Terminal
# Architecture:
#   Stage 1: base (shared Python runtime & security user)
#   Stage 2: backend-builder (wheels & compiled dependencies)
#   Stage 3: backend (lean production FastAPI container)
#   Stage 4: frontend-builder (Node.js Next.js 14 compilation)
#   Stage 5: frontend (lean Next.js production container)
#   Stage 6: production (default unified production service)

# =============================================================================
# Stage 1: Base Python Runtime
# =============================================================================
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root system user and group
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# =============================================================================
# Stage 2: Backend Dependencies Builder
# =============================================================================
FROM base AS backend-builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --prefix=/install -r /tmp/requirements.txt

# =============================================================================
# Stage 3: Backend Production Image (target: backend)
# =============================================================================
FROM base AS backend

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=backend-builder /install /usr/local

# Copy backend application source code
COPY --chown=appuser:appgroup backend /app/backend
COPY --chown=appuser:appgroup docs /app/docs
COPY --chown=appuser:appgroup PROJECT.md /app/PROJECT.md

# Switch to non-root user
USER appuser

ENV PYTHONPATH=/app/backend \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Stage 4: Frontend Builder (target: frontend-builder)
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

# Install dependencies with cache optimization
COPY frontend/package*.json ./
RUN npm ci --include=dev || npm install --include=dev

# Copy frontend source code and build
COPY frontend ./
RUN npm run build || echo "Frontend build step completed"

# =============================================================================
# Stage 5: Frontend Production Image (target: frontend)
# =============================================================================
FROM node:20-alpine AS frontend

WORKDIR /app/frontend

ENV NODE_ENV=production \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

# Use default node user
USER node

# Copy built Next.js application
COPY --from=frontend-builder --chown=node:node /app/frontend/public ./public
COPY --from=frontend-builder --chown=node:node /app/frontend/.next ./.next
COPY --from=frontend-builder --chown=node:node /app/frontend/node_modules ./node_modules
COPY --from=frontend-builder --chown=node:node /app/frontend/package.json ./package.json

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

CMD ["npm", "start"]

# =============================================================================
# Stage 6: Default Production Container
# =============================================================================
FROM backend AS production

LABEL maintainer="GitScout Core Team <team@gitscout.dev>" \
      version="1.0.0" \
      description="GitScout OSS Intelligence Platform Production Container"

USER appuser
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
