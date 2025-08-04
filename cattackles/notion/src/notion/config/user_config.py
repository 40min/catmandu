"""User configuration management for Notion cattackle.

This module provides user authentication and configuration management
through a simple dictionary mapping usernames to their Notion tokens and paths.
"""

from typing import Dict, Optional

# User configuration mapping: username -> {token, path}
# Each user needs a Notion integration token and a target page/database ID
USER_CONFIGS: Dict[str, Dict[str, str]] = {
    # Example configuration (replace with actual user configurations):
    # "username1": {
    #     "token": "secret_notion_integration_token_1",
    #     "path": "page_id_or_database_id_1"
    # },
    # "username2": {
    #     "token": "secret_notion_integration_token_2",
    #     "path": "page_id_or_database_id_2"
    # }
}


def get_user_config(username: str) -> Optional[Dict[str, str]]:
    """Get user configuration by username.

    Args:
        username: The username to look up

    Returns:
        Dictionary containing 'token' and 'path' keys if user exists,
        None if user is not configured
    """
    if not username:
        return None

    return USER_CONFIGS.get(username)


def is_user_authorized(username: str) -> bool:
    """Check if a user is authorized (has valid configuration).

    Args:
        username: The username to check

    Returns:
        True if user has valid configuration, False otherwise
    """
    if not username:
        return False

    config = get_user_config(username)
    if not config:
        return False

    # Validate that both token and path are present and non-empty
    token = config.get("token", "").strip()
    path = config.get("path", "").strip()

    return bool(token and path)
