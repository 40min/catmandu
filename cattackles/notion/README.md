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

## Quick Start

### 1. User Management

```bash
# List configured users
make list-notion-users

# Add a new user
make add-notion-user USER="John Doe" TOKEN="secret_token_123" PAGE_ID="page_id_456"

# Update user token
make update-notion-user-token USER="John Doe" TOKEN="new_token"

# Remove user
make remove-notion-user USER="John Doe"
```

### 2. Testing & Deployment

```bash
# Test configuration
make test-notion-config

# Start services
make docker-up

# Check health
make docker-health
```

## Requirements

- Python 3.12+
- Notion integration token with page access
- Dependencies: `notion-client==2.2.1`, `mcp`, `fastapi`, `uvicorn`

## Version Information

- **Cattackle Version**: 1.0.0
- **MCP Transport**: HTTP
- **Container Port**: 8002
- **Health Endpoint**: `/health`
- **MCP Endpoint**: `/mcp`

For detailed configuration and deployment information, see:

- [Configuration Guide](CONFIGURATION.md) - Setting up Notion integrations and user access
- [Docker Deployment Guide](../../docs/NOTION_DOCKER_DEPLOYMENT.md) - Production deployment with Docker
