# =============================================================================
# TNSE - Telegram News Search Engine
# Dockerfile for Development and Production
#
# Work Stream: WS-4.1 - Render.com Configuration
#
# Usage:
#   Development: docker build --target development -t tnse:dev .
#   Production:  docker build --target production -t tnse:prod .
#   Render.com:  Uses production stage by default
# =============================================================================

FROM python:3.12-slim as base

# Default port - Render.com sets PORT environment variable
ENV PORT=8000

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Development Stage
# =============================================================================
FROM base as development

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install all dependencies including dev
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./

# Install the package in development mode
RUN pip install -e .

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "src.tnse.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production Stage
# =============================================================================
FROM base as production

# Copy only production requirements
COPY requirements.txt ./

# Install production dependencies only
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and migrations
COPY src/ ./src/
COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Install the package
RUN pip install --no-cache-dir .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Expose port
EXPOSE 8000

# Health check - use shell form to expand PORT variable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; import os; httpx.get(f'http://localhost:{os.environ.get(\"PORT\", \"8000\")}/health')" || exit 1

# Production command - use shell form to expand PORT variable
# Render.com sets PORT dynamically, so we use sh -c to expand it
CMD ["sh", "-c", "uvicorn src.tnse.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-2}"]
