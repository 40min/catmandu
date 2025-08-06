# Notion Cattackle

A Catmandu cattackle that enables users to save Telegram messages directly to Notion pages organized by date. This cattackle automatically creates daily pages with ISO date format (YYYY-MM-DD) and appends messages to the appropriate page based on user-specific configuration.

## Features

- **Daily Page Organization**: Automatically creates and manages daily Notion pages
- **User-Specific Configuration**: Each user has their own Notion workspace and authentication
- **Message Accumulation Support**: Works with both immediate parameters and accumulated messages
- **Silent Skip**: Gracefully handles unconfigured users without errors
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Container Ready**: Optimized Docker container with health checks and security features

## Commands

- `/to_notion [message content]` - Save message content to today's Notion page
  - Supports immediate text: `/to_notion This is my note`
  - Supports accumulated messages: Send messages first, then `/to_notion`
  - Creates daily pages automatically if they don't exist
  - Appends content to existing daily pages

## Configuration

### User Configuration

User configurations are managed through the `src/notion/config/user_config.py` module. Each user must be configured with:

1. **Telegram Username**: The user's Telegram username (without @)
2. **Notion Token**: Integration token from Notion workspace
3. **Parent Page ID**: Notion page or database ID where daily pages will be created

Example configuration:

```python
USER_CONFIGS = {
    "your_telegram_username": {
        "token": "secret_notion_integration_token",
        "parent_page_id": "your_notion_page_or_database_id"
    },
    "another_user": {
        "token": "another_notion_token",
        "parent_page_id": "another_parent_page_id"
    }
}
```

### Environment Configuration

Copy `.env.example` to `.env` and configure as needed:

```bash
# Server configuration
MCP_SERVER_PORT=8002
HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO

# Notion API
NOTION_API_BASE_URL=https://api.notion.com/v1
```

### Notion Integration Setup

1. **Create Notion Integration**:

   - Go to https://www.notion.so/my-integrations
   - Create a new integration
   - Copy the integration token

2. **Configure Page Access**:

   - Share your target parent page with the integration
   - Copy the page ID from the URL

3. **Add User Configuration**:
   - Edit `src/notion/config/user_config.py`
   - Add your username, token, and parent page ID

## Requirements

- Python 3.12+
- Notion integration token with page access
- Configured workspace path for each user
- Dependencies: `notion-client==2.2.1`, `mcp`, `fastapi`, `uvicorn`

## Container Deployment

### Building the Container

The notion cattackle supports multi-stage Docker builds optimized for both development and production environments.

#### Development Build

```bash
# Build development image with debug tools
docker build --target development -t notion-cattackle:dev .

# Run development container with volume mounts for live code changes
docker run -d \
  --name notion-cattackle-dev \
  -p 8002:8002 \
  -v $(pwd)/src:/app/src \
  -e LOG_LEVEL=DEBUG \
  notion-cattackle:dev
```

#### Production Build

```bash
# Build optimized production image
docker build --target production -t notion-cattackle:latest .

# Run production container
docker run -d \
  --name notion-cattackle \
  -p 8002:8002 \
  -e LOG_LEVEL=INFO \
  -e MCP_SERVER_PORT=8002 \
  --restart unless-stopped \
  notion-cattackle:latest
```

### Docker Compose Integration

The cattackle can be integrated into the main Catmandu docker-compose setup:

```yaml
services:
  notion-cattackle:
    build:
      context: ./cattackles/notion
      target: production
    ports:
      - "8002:8002"
    environment:
      - LOG_LEVEL=INFO
      - MCP_SERVER_PORT=8002
      - NOTION_API_BASE_URL=https://api.notion.com/v1
    networks:
      - catmandu-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      start_period: 20s
      retries: 3
```

### Container Configuration

The container configuration is defined in `cattackle.toml` under the `[cattackle.container]` section:

- **Port**: 8002 (MCP server port)
- **Health Check**: HTTP endpoint at `/health`
- **Restart Policy**: `unless-stopped`
- **Network**: `catmandu-network`
- **User**: Non-root user `cattackle` (UID 1000)

### Environment Variables

- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `MCP_SERVER_PORT`: Port for the MCP server (default: 8002)
- `NOTION_API_BASE_URL`: Notion API base URL (default: https://api.notion.com/v1)

### Security Features

- Multi-stage build for minimal production image size
- Non-root user execution for enhanced security
- Optimized layer caching for faster builds
- Health checks for container monitoring
- Proper file permissions and ownership

## Deployment Validation

The cattackle includes a comprehensive deployment validation script that tests all aspects of the configuration and deployment:

```bash
# Run deployment validation tests
cd cattackles/notion
python test_deployment.py
```

The validation script tests:

1. **TOML Configuration**: Validates cattackle.toml structure and required fields
2. **Container Build**: Ensures Docker container builds successfully
3. **Health Checks**: Verifies container starts and health endpoint responds
4. **Registry Integration**: Confirms cattackle can be discovered by core system

### Deployment Checklist

Before deploying the Notion cattackle:

- [ ] Configure user tokens and parent page IDs in `src/notion/config/user_config.py`
- [ ] Set environment variables in `.env` file (copy from `.env.example`)
- [ ] Run deployment validation: `python test_deployment.py`
- [ ] Verify all tests pass
- [ ] Deploy using Docker Compose or container orchestration

### Production Deployment

#### Using Docker Compose

The cattackle is automatically included in the main Catmandu docker-compose configuration:

```bash
# Start all services including notion cattackle
docker-compose up -d

# Check cattackle health
curl http://localhost:8002/health
```

#### Manual Container Deployment

```bash
# Build production image
docker build --target production -t notion-cattackle:latest cattackles/notion/

# Run container
docker run -d \
  --name notion-cattackle \
  -p 8002:8002 \
  -e LOG_LEVEL=INFO \
  -e MCP_SERVER_PORT=8002 \
  --network catmandu-network \
  --restart unless-stopped \
  notion-cattackle:latest
```

### Monitoring and Troubleshooting

#### Health Monitoring

The cattackle provides a health endpoint for monitoring:

```bash
# Check health status
curl http://localhost:8002/health

# Expected response
{"status":"healthy","service":"notion-cattackle","version":"1.0.0"}
```

#### Log Monitoring

```bash
# View container logs
docker logs notion-cattackle

# Follow logs in real-time
docker logs -f notion-cattackle
```

#### Common Issues

1. **Import Errors**: Ensure PYTHONPATH is set to `/app/src` in container
2. **Health Check Failures**: Verify port 8002 is accessible and server is running
3. **Registry Discovery Issues**: Confirm cattackle.toml is valid and in correct location
4. **User Configuration**: Check that users are properly configured in user_config.py

### Version Information

- **Cattackle Version**: 1.0.0
- **MCP Transport**: HTTP
- **Container Port**: 8002
- **Health Endpoint**: `/health`
- **MCP Endpoint**: `/mcp`

For additional support and troubleshooting, refer to the main Catmandu documentation and architecture specifications.
