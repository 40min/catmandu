# Multi-stage build for echo cattackle - optimized for caching and size
FROM python:3.13-slim AS base

# Set environment variables for optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies in optimized layers
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv in separate layer for better caching
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Create non-root user for security
RUN groupadd --gid 1000 cattackle && \
    useradd --uid 1000 --gid cattackle --shell /bin/bash --create-home cattackle

# Set working directory
WORKDIR /app

# Dependencies stage with aggressive caching
FROM base AS deps

# Copy only requirements file first for maximum cache reuse
COPY requirements.txt .

# Install dependencies with cache mount and optimized settings
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv pip install --system -r requirements.txt --link-mode=copy

# Development stage with dev tools
FROM deps AS development

# Copy application code (will be overridden by volume mounts)
COPY --chown=cattackle:cattackle src/ ./src/

# Switch to non-root user
USER cattackle

# Configure environment variables for development
ENV LOG_LEVEL=DEBUG \
    MCP_SERVER_PORT=8001 \
    GEMINI_API_KEY="" \
    GEMINI_MODEL=""

# Expose the MCP server port
EXPOSE 8001

# Development command with debug logging
CMD ["python", "src/echo/server.py", "--port", "8001", "--log-level", "DEBUG"]

# Production stage - minimal and optimized
FROM base AS production

# Copy only the installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code with proper ownership
COPY --chown=cattackle:cattackle src/ ./src/

# Switch to non-root user
USER cattackle

# Configure environment variables with production defaults
ENV LOG_LEVEL=INFO \
    MCP_SERVER_PORT=8001 \
    GEMINI_API_KEY="" \
    GEMINI_MODEL="" \
    PYTHONPATH=/app

# Expose the MCP server port
EXPOSE 8001

# Optimized health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Production command with optimized settings
CMD ["python", "src/echo/server.py", "--port", "8001", "--log-level", "INFO"]
