# ──────────────────────────────────────────────────────────────────────────────
# Hotel Management System — Docker Image
#
# Multi-stage build:
#   Stage 1 (builder): Install Python dependencies
#   Stage 2 (runtime): Lean production image with app code
#
# Usage:
#   docker build -t hms:latest .
#   docker run -p 8000:8000 -p 8080:8080 hms:latest
#
# Data persistence:
#   docker run -v hms-data:/app/data -p 8000:8000 -p 8080:8080 hms:latest
# ──────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Labels
LABEL maintainer="HMS Development Team"
LABEL description="Hotel Management System — Offline-first POS"
LABEL version="1.0.0"

# Create non-root user for security
RUN groupadd --gid 1000 hms && \
    useradd --uid 1000 --gid hms --create-home hms

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY .env.example ./.env.example

# Create data and log directories
RUN mkdir -p /app/data /app/logs && \
    chown -R hms:hms /app

# Environment defaults (can be overridden at runtime)
ENV DATABASE_URL=sqlite:///./data/hms.db \
    LOG_LEVEL=INFO \
    LOG_DIR=/app/logs \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    PRINTER_ENABLED=false \
    OFFLINE_MODE=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose ports
#   8000 — FastAPI backend
#   8080 — Flet UI (web browser mode)
EXPOSE 8000 8080

# Switch to non-root user
USER hms

# Health check — verify API is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Copy and use entrypoint script
COPY --chown=hms:hms scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
