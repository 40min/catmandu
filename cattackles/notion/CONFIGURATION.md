# Notion Cattackle Configuration

This document explains how to configure user access for the Notion cattackle.

## Environment Variable Configuration

The Notion cattackle uses environment variables to configure user access. This approach keeps sensitive tokens out of the codebase and allows for easy deployment configuration.

### Configuration Format

User configurations follow a flattened environment variable naming convention:

```bash
NOTION__USER__{USERNAME}__TOKEN=your_notion_integration_token
NOTION__USER__{USERNAME}__PARENT_PAGE_ID=your_target_page_or_database_id
```

Where:

- `{USERNAME}` should be replaced with the actual username in UPPERCASE with underscores
- The username lookup is case-insensitive (john_doe, JOHN_DOE, John_Doe all work)

### Example Configuration

Add these variables to your `.env` file:

```bash
# User: john_doe
NOTION__USER__JOHN_DOE__TOKEN=secret_notion_integration_token_1
NOTION__USER__JOHN_DOE__PARENT_PAGE_ID=page_id_or_database_id_1

# User: jane_smith
NOTION__USER__JANE_SMITH__TOKEN=secret_notion_integration_token_2
NOTION__USER__JANE_SMITH__PARENT_PAGE_ID=page_id_or_database_id_2
```

## Getting Notion Integration Tokens

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give it a name and select the workspace
4. Copy the "Internal Integration Token" (starts with `secret_`)
5. Share the target page/database with your integration

## Finding Page/Database IDs

### For Pages:

1. Open the page in Notion
2. Copy the URL - the page ID is the long string after the last `/`
3. Example: `https://notion.so/My-Page-123abc456def` → Page ID is `123abc456def`

### For Databases:

1. Open the database in Notion
2. Copy the URL - the database ID is the long string before the `?`
3. Example: `https://notion.so/123abc456def?v=...` → Database ID is `123abc456def`

## User Management Commands

### Adding Users

```bash
make add-notion-user USER="John Doe" TOKEN="secret_token_123" PAGE_ID="page_id_456"
```

### Listing Users

```bash
make list-notion-users
```

### Updating Users

```bash
# Update token
make update-notion-user-token USER="John Doe" TOKEN="new_token"

# Update page ID
make update-notion-user-page USER="John Doe" PAGE_ID="new_page_id"
```

### Removing Users

```bash
make remove-notion-user USER="John Doe"
```

## Testing Configuration

### Test All Users

```bash
make test-notion-config
```

### Test Specific User

```bash
make test-notion-config-user USER=john_doe
```

## Validation

Both `TOKEN` and `PARENT_PAGE_ID` must be provided for a user to be considered authorized. The system will:

- Log discovered users at startup (without sensitive data)
- Warn about incomplete configurations
- Reject unauthorized users with helpful error messages

## Security Notes

- Never commit `.env` files with real tokens to version control
- Use `.env.example` for documentation and templates
- Tokens should be kept secure and rotated regularly
- Each user should have their own Notion integration for proper access control
