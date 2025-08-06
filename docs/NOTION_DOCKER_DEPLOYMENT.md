# Notion Cattackle Docker Deployment Guide

This guide explains how to deploy the Notion cattackle with Docker Compose, handling multiple user configurations.

## The Challenge

The Notion cattackle uses a dynamic environment variable pattern for user configurations:

```bash
NOTION__USER__{USERNAME}__TOKEN=token
NOTION__USER__{USERNAME}__PARENT_PAGE_ID=page_id
```

Since usernames can vary, we can't hardcode all possible combinations in `docker-compose.yml`. This document explains the solution.

## Solution: Using `env_file`

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

## Managing User Configurations

### Method 1: Makefile Commands

```bash
# List users
make list-notion-users

# Add user
make add-notion-user USER="John Doe" TOKEN="secret_token_123" PAGE_ID="page_id_456"

# Update token
make update-notion-user-token USER="John Doe" TOKEN="new_token"

# Remove user
make remove-notion-user USER="John Doe"
```

### Method 3: Manual .env Editing

Add directly to your `.env` file:

```bash
# User: John Doe
NOTION__USER__JOHN_DOE__TOKEN=secret_token_123
NOTION__USER__JOHN_DOE__PARENT_PAGE_ID=page_id_456

# User: Jane Smith
NOTION__USER__JANE_SMITH__TOKEN=secret_token_789
NOTION__USER__JANE_SMITH__PARENT_PAGE_ID=page_id_012
```

## Deployment Workflow

1. **Configure Users**: Add user configurations using any method above
2. **Test Configuration**:
   ```bash
   make test-notion-config
   ```
3. **Start Services**:
   ```bash
   make docker-up
   # or for QNAP
   make docker-qnap
   ```
4. **Verify Deployment**:
   ```bash
   make docker-health
   ```

## Environment Variable Format Rules

- **Username Format**: Must be UPPERCASE with underscores only
- **Pattern**: `NOTION__USER__{USERNAME}__{FIELD}`
- **Fields**: `TOKEN` and `PARENT_PAGE_ID`
- **Example**: `NOTION__USER__JOHN_DOE__TOKEN`

The system automatically:

- Converts usernames to lowercase for internal use
- Handles case-insensitive lookups
- Validates both token and parent_page_id are present

## Troubleshooting

### Container Not Picking Up New Users

1. **Restart the container**:

   ```bash
   make docker-restart
   ```

2. **Check environment variables are passed**:
   ```bash
   docker exec catmandu-core env | grep NOTION__USER__
   ```

### Configuration Issues

1. **Test configuration**:

   ```bash
   make test-notion-config
   ```

2. **Check specific user**:

   ```bash
   make test-notion-config-user USER=john_doe
   ```

3. **Validate in container**:
   ```bash
   docker exec catmandu-core python scripts/manage_notion_users.py test
   ```

### Common Issues

- **Username contains numbers**: Use letters and underscores only
- **Missing environment variables**: Check `.env` file syntax
- **Container not restarted**: Changes require container restart
- **Case sensitivity**: System handles this automatically

## Best Practices

1. **Use the management script** for user operations
2. **Test configurations** before deployment
3. **Restart containers** after configuration changes
4. **Use meaningful usernames** that match Telegram usernames
5. **Keep tokens secure** and rotate regularly
6. **Monitor logs** for configuration issues

## Security Considerations

- Never commit `.env` files with real tokens
- Use separate Notion integrations per user
- Regularly rotate tokens
- Monitor access logs
- Use least-privilege page permissions

This approach provides a clean, scalable solution for managing multiple Notion users in Docker deployments while maintaining security and ease of use.
