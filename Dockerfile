# Multi-stage Dockerfile for Catmandu Core application
# Stage 1: Base environment with Python 3.13 and uv
FROM python:3.13-slim AS base

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 catmandu \
    && useradd --uid 1000 --gid catmandu --shell /bin/bash --create-home catmandu

# Stage 2: Dependencies installation
FROM base AS deps

# Copy dependency files for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv for fast installation
RUN uv sync --frozen --no-dev

# Stage 3: Development stage (optional target)
FROM deps AS development

# Install development dependencies
RUN uv sync --frozen

# Copy source code
COPY --chown=catmandu:catmandu . .

# Switch to non-root user
USER catmandu

# Expose port for FastAPI application
EXPOSE 8000

# Set environment variables for development
ENV PYTHONPATH=/app/src
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

# Development command with auto-reload
CMD ["uv", "run", "uvicorn", "catmandu.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Stage 4: Production stage
FROM deps AS production

# Copy source code
COPY --chown=catmandu:catmandu src/ ./src/
COPY --chown=catmandu:catmandu cattackles/ ./cattackles/

# Switch to non-root user
USER catmandu

# Expose port for FastAPI application
EXPOSE 8000

# Set environment variables for production
ENV PYTHONPATH=/app/src
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["uv", "run", "uvicorn", "catmandu.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
