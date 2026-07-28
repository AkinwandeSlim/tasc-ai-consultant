# =============================================================================
# TASC Backend — Dockerfile
# Build: docker build -f docker/backend/Dockerfile -t tasc-backend .
# =============================================================================

FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY apps/backend/pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY apps/backend/app /app/app
COPY apps/backend/app/resources /app/app/resources
COPY apps/backend/data /app/data

# Create non-root user
RUN useradd -m -u 1000 tasc && \
    chown -R tasc:tasc /app
USER tasc

# Health check
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
