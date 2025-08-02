# Multi-stage Dockerfile for Catmandu Core application
# Optimized for maximum layer caching and minimal image size

# Stage 1: Base environment with Python 3.13 and uv
FROM python:3.13-slim AS base

# Set environment variables for optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies in a single layer for better caching
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv in a separate layer for better caching
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Create non-root user for security in a separate layer
RUN groupadd --gid 1000 catmandu \
    && useradd --uid 1000 --gid catmandu --shell /bin/bash --create-home catmandu

# Stage 2: Dependencies installation with aggressive caching
FROM base AS deps

# Copy only dependency files first for maximum cache reuse
COPY pyproject.toml ./
COPY uv.lock ./

# Create virtual environment and install dependencies
# Use --link-mode=copy for better performance in containers
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --frozen --no-dev --link-mode=copy

# Stage 3: Development stage with dev dependencies and volume support
FROM deps AS development

# Install development dependencies with cache mount
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --frozen --link-mode=copy

# Copy source code (will be overridden by volume mounts in development)
COPY --chown=catmandu:catmandu src/ ./src/
COPY --chown=catmandu:catmandu cattackles/ ./cattackles/

# Create necessary directories with proper permissions
RUN mkdir -p logs/chats logs/costs .data && chown -R catmandu:catmandu logs .data

# Switch to non-root user
USER catmandu

# Expose port for FastAPI application
EXPOSE 8000

# Set environment variables for development
ENV PYTHONPATH=/app/src \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_LOG_LEVEL=debug

# Development command with auto-reload
CMD ["uv", "run", "uvicorn", "catmandu.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# Stage 4: Production stage - minimal and optimized
FROM base AS production

# Copy only the virtual environment from deps stage
COPY --from=deps /app/.venv /app/.venv

# Copy only necessary source code files
COPY --chown=catmandu:catmandu src/ ./src/
COPY --chown=catmandu:catmandu cattackles/ ./cattackles/

# Create necessary directories with proper permissions
RUN mkdir -p logs/chats logs/costs .data && chown -R catmandu:catmandu logs .data

# Switch to non-root user
USER catmandu

# Expose port for FastAPI application
EXPOSE 8000

# Set environment variables for production
ENV PYTHONPATH=/app/src \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_LOG_LEVEL=info \
    PATH="/app/.venv/bin:$PATH"

# Add optimized health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command with optimized settings
CMD ["python", "-m", "uvicorn", "catmandu.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
