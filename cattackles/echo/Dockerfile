# Multi-stage build for echo cattackle
FROM python:3.13-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 cattackle && \
    useradd --uid 1000 --gid cattackle --shell /bin/bash --create-home cattackle

# Set working directory
WORKDIR /app

# Dependencies stage
FROM base as deps

# Install uv for fast dependency management
RUN pip install uv

# Copy requirements and install dependencies
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Production stage
FROM deps as production

# Copy application code
COPY src/ ./src/

# Change ownership to non-root user
RUN chown -R cattackle:cattackle /app

# Switch to non-root user
USER cattackle

# Configure environment variables with defaults
ENV LOG_LEVEL=INFO \
    MCP_SERVER_PORT=8001 \
    GEMINI_API_KEY="" \
    GEMINI_MODEL=""

# Expose the MCP server port
EXPOSE ${MCP_SERVER_PORT}

# Health check using dedicated health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${MCP_SERVER_PORT}/health || exit 1

# Use exec form for proper signal handling and environment variable substitution
CMD python src/server.py --port ${MCP_SERVER_PORT} --log-level ${LOG_LEVEL}
