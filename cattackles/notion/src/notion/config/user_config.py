"""User configuration management for Notion cattackle.

This module provides user authentication and configuration management
by parsing environment variables with flattened naming convention.

Environment variable format:
- NOTION__USER__{USERNAME}__TOKEN: Notion integration token for the user
- NOTION__USER__{USERNAME}__PARENT_PAGE_ID: Target parent page/database ID

Example:
- NOTION__USER__JOHN_DOE__TOKEN=secret_token_123
- NOTION__USER__JOHN_DOE__PARENT_PAGE_ID=page_id_456
"""

import os
import re
from typing import Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

# Cache for parsed user configurations
_user_configs_cache: Optional[Dict[str, Dict[str, str]]] = None


def _parse_user_configs() -> Dict[str, Dict[str, str]]:
    """Parse user configurations from environment variables.

    Looks for environment variables matching the pattern:
    NOTION__USER__{USERNAME}__TOKEN and NOTION__USER__{USERNAME}__PARENT_PAGE_ID

    Returns:
        Dictionary mapping usernames to their configuration dictionaries
    """
    user_configs: Dict[str, Dict[str, str]] = {}

    # Pattern to match NOTION__USER__{USERNAME}__{FIELD}
    pattern = re.compile(r"^NOTION__USER__([A-Z0-9_]+)__(TOKEN|PARENT_PAGE_ID)$")

    for env_var, value in os.environ.items():
        match = pattern.match(env_var)
        if not match:
            continue

        username_env = match.group(1)  # Username in environment format (UPPERCASE_WITH_UNDERSCORES)
        field = match.group(2).lower()  # token or parent_page_id

        # Convert environment username format to regular username
        # JOHN_DOE -> john_doe (or keep as is - depends on your preference)
        username = username_env.lower()

        # Initialize user config if not exists
        if username not in user_configs:
            user_configs[username] = {}

        # Map field names
        if field == "token":
            user_configs[username]["token"] = value.strip()
        elif field == "parent_page_id":
            user_configs[username]["parent_page_id"] = value.strip()

    # Log discovered users (without sensitive data)

    return user_configs


def _get_user_configs() -> Dict[str, Dict[str, str]]:
    """Get cached user configurations, parsing from environment if needed."""
    global _user_configs_cache

    if _user_configs_cache is None:
        _user_configs_cache = _parse_user_configs()

    return _user_configs_cache


def get_user_config(username: str) -> Optional[Dict[str, str]]:
    """Get user configuration by username.

    Args:
        username: The username to look up (case-insensitive)

    Returns:
        Dictionary containing 'token' and 'parent_page_id' keys if user exists,
        None if user is not configured
    """
    if not username:
        return None

    # Normalize username to lowercase for lookup
    normalized_username = username.lower()
    user_configs = _get_user_configs()

    return user_configs.get(normalized_username)


def is_user_authorized(username: str) -> bool:
    """Check if a user is authorized (has valid configuration).

    Args:
        username: The username to check (case-insensitive)

    Returns:
        True if user has valid configuration, False otherwise
    """
    if not username:
        return False

    config = get_user_config(username)
    if not config:
        return False

    # Validate that both token and parent_page_id are present and non-empty
    token = config.get("token", "").strip()
    parent_page_id = config.get("parent_page_id", "").strip()

    is_valid = bool(token and parent_page_id)

    # Only log when there's an actual configuration issue (not just missing user)
    if config and not is_valid:
        logger.warning(
            "User configuration is incomplete",
            username=username,
            has_token=bool(token),
            has_parent_page_id=bool(parent_page_id),
        )

    return is_valid


def get_all_user_configs() -> Dict[str, Dict[str, str]]:
    """Get all user configurations.

    Returns:
        Dictionary mapping usernames to their configuration dictionaries
    """
    return _get_user_configs()


def reload_user_configs() -> None:
    """Force reload of user configurations from environment variables.

    This can be useful during development or if environment variables change at runtime.
    """
    global _user_configs_cache
    _user_configs_cache = None
