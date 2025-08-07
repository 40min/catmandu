"""Date handling utilities for the Notion cattackle.

This module provides consistent date formatting and timezone handling
for page titles and content timestamps.
"""

import re
from datetime import datetime, timezone
from typing import Optional


def get_current_date_iso() -> str:
    """
    Get the current date in ISO format (YYYY-MM-DD).

    Uses UTC timezone for consistency across different server environments.

    Returns:
        str: Current date in YYYY-MM-DD format

    Requirements: 2.1, 2.2
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_current_timestamp() -> str:
    """
    Get the current timestamp in HH:MM:SS format.

    Uses UTC timezone for consistency across different server environments.

    Returns:
        str: Current time in HH:MM:SS format

    Requirements: 2.2
    """
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def validate_datetime_format(datetime_string: str) -> bool:
    """
    Validate that a datetime string follows the format (YYYY-MM-DD HH:MM:SS).

    Args:
        datetime_string: Datetime string to validate

    Returns:
        bool: True if the datetime string is valid format, False otherwise
    """
    if not isinstance(datetime_string, str):
        return False

    # Check format with regex
    datetime_pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
    if not re.match(datetime_pattern, datetime_string):
        return False

    # Try to parse the datetime to ensure it's a valid datetime
    try:
        datetime.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def validate_date_format(date_string: str) -> bool:
    """
    Validate that a date string follows the ISO format (YYYY-MM-DD).

    Args:
        date_string: Date string to validate

    Returns:
        bool: True if the date string is valid ISO format, False otherwise
    """
    if not isinstance(date_string, str):
        return False

    # Check format with regex
    iso_date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(iso_date_pattern, date_string):
        return False

    # Try to parse the date to ensure it's a valid date
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def format_date_for_page_title(date_input: Optional[datetime] = None) -> str:
    """
    Format a datetime for use as a Notion page title.

    Args:
        date_input: Optional datetime object. If None, uses current UTC time.

    Returns:
        str: Date formatted as YYYY-MM-DD for page title (without timestamp)

    Requirements: 2.1, 2.2
    """
    if date_input is None:
        date_input = datetime.now(timezone.utc)
    elif date_input.tzinfo is None:
        # If no timezone info, assume UTC
        date_input = date_input.replace(tzinfo=timezone.utc)

    return date_input.strftime("%Y-%m-%d")


def format_timestamp_for_content(timestamp_input: Optional[datetime] = None) -> str:
    """
    Format a timestamp for use in message content.

    Args:
        timestamp_input: Optional datetime object. If None, uses current UTC time.

    Returns:
        str: Timestamp formatted as [HH:MM:SS] for content

    Requirements: 2.2
    """
    if timestamp_input is None:
        timestamp_input = datetime.now(timezone.utc)
    elif timestamp_input.tzinfo is None:
        # If no timezone info, assume UTC
        timestamp_input = timestamp_input.replace(tzinfo=timezone.utc)

    return f"[{timestamp_input.strftime('%H:%M:%S')}]"
