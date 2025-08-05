"""Content processing utilities for the Notion cattackle.

This module provides text formatting and special character handling
for message content before saving to Notion.
"""

import html
import re
from typing import List, Optional


def sanitize_content(content: str) -> str:
    """
    Sanitize content for safe storage in Notion.

    Handles special characters, HTML entities, and ensures content
    is safe for Notion's rich text format.

    Args:
        content: Raw message content to sanitize

    Returns:
        str: Sanitized content safe for Notion storage

    Requirements: 6.3, 6.4
    """
    if not isinstance(content, str):
        return str(content)

    # Handle empty or whitespace-only content
    if not content.strip():
        return content.strip()

    # Decode HTML entities (e.g., &amp; -> &, &lt; -> <)
    sanitized = html.unescape(content)

    # Remove or replace problematic characters that might break Notion formatting
    # Replace null bytes and other control characters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

    # Normalize whitespace - replace multiple spaces/tabs with single space
    sanitized = re.sub(r"\s+", " ", sanitized)

    # Trim leading and trailing whitespace
    sanitized = sanitized.strip()

    return sanitized


def format_message_content(content: str, accumulated_params: Optional[List[str]] = None) -> str:
    """
    Format message content with accumulated parameters.

    Combines accumulated parameters with the main message content
    and applies proper formatting.

    Args:
        content: Main message content
        accumulated_params: Optional list of accumulated parameters from previous messages

    Returns:
        str: Formatted message content ready for Notion

    Requirements: 1.3, 6.3, 6.4
    """
    # Sanitize the main content
    sanitized_content = sanitize_content(content)

    # Handle accumulated parameters
    if accumulated_params:
        # Sanitize each accumulated parameter
        sanitized_params = [sanitize_content(param) for param in accumulated_params if param.strip()]

        if sanitized_params:
            # Join accumulated parameters and combine with main content
            accumulated_text = " ".join(sanitized_params)
            formatted_content = f"{accumulated_text} {sanitized_content}".strip()
        else:
            formatted_content = sanitized_content
    else:
        formatted_content = sanitized_content

    return formatted_content


def escape_notion_special_characters(content: str) -> str:
    """
    Escape special characters that have meaning in Notion's rich text format.

    This prevents user content from accidentally triggering Notion formatting
    when it should be displayed as plain text.

    Args:
        content: Content that may contain special characters

    Returns:
        str: Content with special characters escaped

    Requirements: 6.3, 6.4
    """
    if not isinstance(content, str):
        return str(content)

    # Notion uses markdown-like formatting, so we need to escape certain characters
    # that could be interpreted as formatting commands

    # Escape backslashes first (they're used for escaping)
    escaped = content.replace("\\", "\\\\")

    # Escape markdown-style formatting characters
    # Note: We're being conservative here - only escaping the most common ones
    # that could cause issues in Notion's rich text
    formatting_chars = ["*", "_", "`", "~", "[", "]", "(", ")"]

    for char in formatting_chars:
        escaped = escaped.replace(char, f"\\{char}")

    return escaped


def truncate_content(content: str, max_length: int = 2000) -> str:
    """
    Truncate content to a maximum length while preserving word boundaries.

    Notion has limits on block content length, so this ensures content
    fits within reasonable limits.

    Args:
        content: Content to potentially truncate
        max_length: Maximum allowed length (default: 2000 characters)

    Returns:
        str: Truncated content with ellipsis if truncation occurred

    Requirements: 6.3, 6.4
    """
    if not isinstance(content, str):
        content = str(content)

    if len(content) <= max_length:
        return content

    # Find the last space before the max_length to avoid cutting words
    truncate_at = content.rfind(" ", 0, max_length - 3)  # -3 for "..."

    if truncate_at == -1:
        # No space found, just truncate at max_length
        truncate_at = max_length - 3

    return content[:truncate_at] + "..."


def validate_content_length(content: str, max_length: int = 2000) -> bool:
    """
    Validate that content length is within acceptable limits.

    Args:
        content: Content to validate
        max_length: Maximum allowed length

    Returns:
        bool: True if content is within limits, False otherwise
    """
    if not isinstance(content, str):
        return False

    return len(content) <= max_length
