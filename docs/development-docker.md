# Development with Docker

This guide covers the development workflow using Docker containers for live code reloading, debugging, and testing.

## Quick Start

1. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your development values
   ```

2. **Start development environment:**

   ```bash
   make docker-up
   # This automatically uses the development override
   ```

3. **Monitor logs in real-time:**
   ```bash
   make docker-logs
   ```

## Development Features

### Live Code Reloading

The development setup includes volume mounts that enable live code reloading:

- **Core Application**: Changes to `src/` are automatically detected and trigger service restart
- **Echo Cattackle**: Changes to `cattackles/echo/src/` are automatically detected
- **Configuration**: Changes to cattackle configurations are picked up on restart
- **File Watching**: Uvicorn's `--reload` flag monitors file changes in real-time

### Enhanced Logging

Development containers run with enhanced logging:

- **Log Level**: DEBUG by default for detailed information
- **Uvicorn Logging**: Debug level for detailed request/response info
- **HTTP Debugging**: Detailed HTTP client logs for Telegram API calls
- **MCP Communication**: Debug logs for inter-service communication
- **Structured Logs**: Consistent formatting for better parsing

### Development Build Targets

Both Dockerfiles include optimized development targets:

- **Development Dependencies**: Additional tools and libraries for debugging
- **Debug Configuration**: Enhanced error reporting and stack traces
- **Volume Support**: Optimized for file watching and live reloading
- **Permission Handling**: Proper directory permissions for logs and data

## Development Workflow

### Standard Development Cycle

1. **Start the development environment:**

   ```bash
   make docker-dev-build  # Build optimized development images
   make docker-dev        # Start services with live reloading (foreground)
   # OR
   make docker-up         # Start services in background
   ```

2. **Make code changes:**

   - Edit files in `src/` or `cattackles/echo/src/`
   - Changes are automatically detected and services restart
   - Watch the logs to see reload notifications

3. **Monitor and debug:**

   ```bash
   make docker-logs       # View real-time logs from all services
   make docker-logs-core  # View only core application logs
   make docker-logs-echo  # View only echo cattackle logs
   make docker-health     # Check service health endpoints
   ```

4. **Test your changes:**

   ```bash
   # Test health endpoints
   make docker-health

   # Test via direct API calls
   curl http://localhost:8000/health

   # Test MCP communication
   docker-compose exec catmandu-core curl http://echo-cattackle:8001/health
   ```

5. **Reset or stop when done:**
   ```bash
   make docker-reset      # Reset development environment
   make docker-down       # Stop services
   ```

### Debugging Workflow

#### Access Container Shells

```bash
# Access core application container
make docker-exec-core

# Access echo cattackle container
make docker-exec-echo
```

#### View Specific Service Logs

```bash
# View only core application logs
docker-compose logs -f catmandu-core

# View only echo cattackle logs
docker-compose logs -f echo-cattackle
```

#### Debug MCP Communication

```bash
# Check MCP endpoint health
curl http://localhost:8000/health
docker-compose exec catmandu-core curl http://echo-cattackle:8001/health

# View MCP communication logs
docker-compose logs -f echo-cattackle | grep -i mcp
```

## Configuration

### Environment Variables for Development

Create a `.env` file with development-specific values:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_development_bot_token

# Optional - Development optimized
LOG_LEVEL=DEBUG
MAX_MESSAGES_PER_CHAT=10
MAX_MESSAGE_LENGTH=500
GEMINI_API_KEY=your_development_key
GEMINI_MODEL=gemini-1.5-flash
```

### Development Override File

The `docker-compose.override.yml` file provides development-specific configurations:

- **Build Target**: Uses `development` target from Dockerfiles
- **Volume Mounts**: Live code reloading for both services
- **Debug Logging**: Enhanced logging levels
- **Cache Optimization**: UV cache volumes for faster rebuilds

## Advanced Development

### Custom Development Configuration

Create additional override files for specific scenarios:

```bash
# For testing with different configurations
docker-compose -f docker-compose.yml -f docker-compose.test.yml up

# For debugging with additional tools
docker-compose -f docker-compose.yml -f docker-compose.debug.yml up
```

### Performance Optimization

#### Build Cache Optimization

The development setup includes aggressive caching:

```bash
# Clear build cache if needed
docker-compose build --no-cache

# Use BuildKit for advanced caching
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

#### Volume Performance

For better volume performance on macOS:

```bash
# Use delegated consistency for better performance
# (Already configured in docker-compose.override.yml)
```

### Testing in Development

#### Run Tests in Containers

```bash
# Run core tests in container
docker-compose exec catmandu-core uv run pytest

# Run echo cattackle tests in container
docker-compose exec echo-cattackle uv run pytest
```

#### Integration Testing

```bash
# Test the full stack
make docker-test

# Or manually test MCP communication
docker-compose exec catmandu-core curl -X POST http://echo-cattackle:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

## Troubleshooting

### Common Issues

#### Services Won't Start

1. **Check environment variables:**

   ```bash
   docker-compose config
   ```

2. **Verify build process:**

   ```bash
   make docker-build
   docker-compose logs
   ```

3. **Check port conflicts:**
   ```bash
   lsof -i :8000
   lsof -i :8001
   ```

#### Live Reloading Not Working

1. **Verify volume mounts:**

   ```bash
   docker-compose exec catmandu-core ls -la /app/src
   ```

2. **Check file permissions:**

   ```bash
   ls -la src/
   ```

3. **Restart services:**
   ```bash
   make docker-restart
   ```

#### MCP Communication Issues

1. **Check network connectivity:**

   ```bash
   docker-compose exec catmandu-core ping echo-cattackle
   ```

2. **Verify MCP server is running:**

   ```bash
   docker-compose exec echo-cattackle curl http://localhost:8001/health
   ```

3. **Check service dependencies:**
   ```bash
   make docker-ps
   ```

### Reset Development Environment

```bash
# Complete reset (removes volumes and rebuilds)
make docker-clean

# Soft reset (keeps volumes)
docker-compose down
docker-compose up -d
```

### Performance Issues

#### Slow Build Times

```bash
# Use BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Prune unused build cache
docker builder prune
```

#### High Resource Usage

```bash
# Check resource usage
docker stats

# Limit resources in docker-compose.yml if needed
```

## IDE Integration

### VS Code Development

1. **Install Docker extension**
2. **Use Dev Containers extension for container-based development**
3. **Configure debugger to attach to running containers**

### PyCharm Integration

1. **Configure Docker Compose as interpreter**
2. **Set up remote debugging**
3. **Use Docker integration for running and debugging**

## Best Practices

### Development Workflow

1. **Always use the development override** - Don't modify the main docker-compose.yml
2. **Keep environment variables in .env** - Don't commit sensitive values
3. **Use volume mounts for active development** - Avoid rebuilding for code changes
4. **Monitor logs regularly** - Use `make docker-logs` to catch issues early
5. **Test MCP communication** - Verify cattackle connectivity after changes

### Code Changes

1. **Test locally first** - Use `make run` for quick iteration
2. **Verify in containers** - Ensure changes work in containerized environment
3. **Check both services** - Changes to core may affect cattackles
4. **Monitor resource usage** - Watch for memory leaks or performance issues

### Debugging

1. **Use structured logging** - JSON format helps with log analysis
2. **Enable debug mode** - Set LOG_LEVEL=DEBUG for detailed information
3. **Access container shells** - Use exec commands for direct debugging
4. **Test MCP endpoints** - Verify communication between services

This development setup provides a robust, efficient workflow for building and testing Catmandu with Docker containers.
