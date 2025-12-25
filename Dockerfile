# =============================================================================
# TNSE - Telegram News Search Engine
# Dockerfile for Development and Production
# =============================================================================

FROM python:3.10-slim as base

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

# Copy source code
COPY src/ ./src/
COPY pyproject.toml ./

# Install the package
RUN pip install --no-cache-dir .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Production command with multiple workers
CMD ["uvicorn", "src.tnse.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
