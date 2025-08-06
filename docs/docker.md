# Docker Deployment Guide

This document describes how to run Catmandu using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Environment variables configured (see `.env.example`)

## Quick Start

1. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

2. **Start the services:**

   ```bash
   make docker-up
   # Or directly: docker-compose up -d
   ```

3. **View logs:**

   ```bash
   make docker-logs
   # Or directly: docker-compose logs -f
   ```

4. **Stop the services:**

   ```bash
   make docker-down
   # Or directly: docker-compose down
   ```

## Makefile Commands

For convenience, use the provided Makefile commands:

```bash
make help-docker          # Show all Docker commands
make docker-build         # Build Docker images
make docker-up            # Start services
make docker-down          # Stop services
make docker-logs          # View logs
make docker-ps            # Check service status
make docker-test          # Test configuration
make docker-clean         # Reset everything
```

## Services

### catmandu-core

- **Port**: 8000 (exposed externally)
- **Health Check**: `/health` endpoint
- **Dependencies**: echo-cattackle, notion-cattackle services

### echo-cattackle

- **Port**: 8001 (internal only)
- **Health Check**: MCP endpoint
- **Purpose**: Provides echo, ping, and joke commands

### notion-cattackle

- **Port**: 8002 (internal only)
- **Health Check**: MCP endpoint
- **Purpose**: Saves Telegram messages to Notion pages organized by date

## Environment Variables

### Required

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token

### Optional

- `GEMINI_API_KEY`: For AI joke generation
- `GEMINI_MODEL`: Gemini model to use (default: gemini-1.5-flash)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL - default: INFO)
- `MAX_MESSAGES_PER_CHAT`: Message accumulation limit (default: 100)
- `MAX_MESSAGE_LENGTH`: Maximum message length (default: 1000)
- `MCP_SERVER_PORT`: Port for echo cattackle MCP server (default: 8001)
- `NOTION_TOKEN`: Notion integration token (for notion cattackle)

## Development

For development with live code reloading:

1. **Use development override:**

   ```bash
   make docker-up
   # Or directly: docker-compose up
   ```

   The override file is loaded automatically for development.

2. **Development workflow:**

   ```bash
   make docker-build     # Build images
   make docker-up        # Start services
   make docker-logs      # Monitor logs
   make docker-ps        # Check status
   make docker-down      # Stop when done
   ```

3. **The development setup includes:**
   - Volume mounts for live code reloading
   - Debug logging enabled
   - Development build target with additional tools

## Networking

Services communicate via the `catmandu-network` bridge network:

- Core application connects to echo-cattackle via `http://echo-cattackle:8001/mcp`
- Core application connects to notion-cattackle via `http://notion-cattackle:8002/mcp`
- External access to core application via `localhost:8000`

## Volumes

- `catmandu-update-data`: Persists Telegram polling offset
- `catmandu-chat-logs`: Persists chat interaction logs

## Troubleshooting

### Service won't start

1. Check environment variables are set correctly
2. Verify Docker images build successfully:
   ```bash
   make docker-build
   # Or directly: docker-compose build
   ```

### Connection issues

1. Check service health:
   ```bash
   make docker-ps
   # Or directly: docker-compose ps
   ```
2. View service logs:
   ```bash
   make docker-logs
   # Or directly: docker-compose logs [service-name]
   ```

### Reset everything

```bash
make docker-clean
# Or directly:
# docker-compose down -v
# docker-compose build --no-cache
# docker-compose up
```
