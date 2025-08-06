# Notion Cattackle Docker Deployment Guide

This guide explains how to deploy the Notion cattackle with Docker Compose, handling multiple user configurations.

## Docker Configuration

The `docker-compose.yml` uses the `env_file` directive to automatically pass all environment variables from `.env` to the container:

```yaml
notion-cattackle:
  env_file:
    - .env # This automatically passes all NOTION__USER__* variables
  environment:
    - LOG_LEVEL=${LOG_LEVEL:-INFO}
    - MCP_SERVER_PORT=8002
    - NOTION_API_BASE_URL=https://api.notion.com/v1
```

## Deployment Workflow

### 1. Configure Users

```bash
# Add users using make commands
make add-notion-user USER="John Doe" TOKEN="secret_token_123" PAGE_ID="page_id_456"
make list-notion-users
```

### 2. Test Configuration

```bash
make test-notion-config
```

### 3. Deploy Services

```bash
# Standard deployment
make docker-up

# QNAP deployment
make docker-qnap
```

### 4. Verify Deployment

```bash
make docker-health
```

## Environment Variable Format

- **Pattern**: `NOTION__USER__{USERNAME}__{FIELD}`
- **Username Format**: UPPERCASE with underscores only
- **Fields**: `TOKEN` and `PARENT_PAGE_ID`
- **Example**: `NOTION__USER__JOHN_DOE__TOKEN`

The system automatically:

- Converts usernames to lowercase for internal use
- Handles case-insensitive lookups
- Validates both token and parent_page_id are present

## Container Management

### Restart After Configuration Changes

```bash
make docker-restart
```

### Check Environment Variables

```bash
docker exec catmandu-core env | grep NOTION__USER__
```

### Monitor Logs

```bash
make docker-logs
```

## Troubleshooting

### Configuration Issues

```bash
# Test all users
make test-notion-config

# Test specific user
make test-notion-config-user USER=john_doe
```

### Container Health

```bash
# Check service health
make docker-health

# View logs
make docker-logs
```

### Common Issues

- **Missing environment variables**: Check `.env` file syntax
- **Container not restarted**: Changes require container restart
- **Username format**: Use letters and underscores only
- **Case sensitivity**: System handles this automatically

## Security Best Practices

- Never commit `.env` files with real tokens
- Use separate Notion integrations per user
- Regularly rotate tokens
- Monitor access logs
- Use least-privilege page permissions
- Test configurations before deployment

## Production Deployment

### QNAP Deployment

```bash
# Start QNAP services
make docker-qnap

# Monitor QNAP logs
make docker-qnap-logs

# Restart QNAP services
make docker-qnap-restart
```

### Health Monitoring

```bash
# Check all service health
make docker-health

# Analyze logs for issues
make docker-qnap-analyze-chats
```

This approach provides a clean, scalable solution for managing multiple Notion users in Docker deployments while maintaining security and ease of use.
