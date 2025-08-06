# Notion Cattackle

A Catmandu cattackle that enables users to save Telegram messages directly to Notion pages organized by date.

## Features

- Save messages to daily Notion pages using `/to_notion` command
- Automatic page creation with date-based organization
- User-specific configuration for authentication and workspace paths
- Silent skip for unconfigured users

## Configuration

User configurations are managed through a Python configuration module that maps usernames to Notion tokens and workspace paths.

## Commands

- `/to_notion [message content]` - Save message content to today's Notion page

## Requirements

- Python 3.12+
- Notion integration token
- Configured workspace path for each user

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
