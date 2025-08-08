"""Core business logic for the Notion cattackle.

This module contains the main NotionCattackle class that orchestrates
the message saving workflow, including page management and content operations.
"""

from typing import List, Optional

import structlog
from notion.clients.notion_client import NotionClientWrapper
from notion.config.user_config import get_user_config, is_user_authorized
from notion.utils.content_utils import format_message_content, truncate_content
from notion.utils.date_utils import format_date_for_page_title, format_timestamp_for_content
from notion_client.errors import APIResponseError, RequestTimeoutError

logger = structlog.get_logger(__name__)


class NotionCattackle:
    """
    Core business logic for saving messages to Notion.

    Handles the complete workflow of user validation, page management,
    and content appending for the Notion cattackle.
    """

    def __init__(self):
        """Initialize the NotionCattackle."""
        self.logger = logger.bind(component="notion_cattackle")
        # Will be populated by the server during lifespan initialization
        self._client_instances = {}

    async def save_to_notion(
        self, username: str, message_content: str, accumulated_params: Optional[List[str]] = None
    ) -> str:
        """
        Save a message to Notion for the specified user.

        This method orchestrates the complete workflow:
        1. Validate user configuration
        2. Get or create today's daily page
        3. Append the message content to the page

        Args:
            username: Telegram username of the user
            message_content: The message content to save
            accumulated_params: Optional accumulated parameters from previous messages

        Returns:
            str: Success message or error message for the user

        Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 6.1, 6.2
        """
        self.logger.info(
            "Processing save_to_notion request",
            username=username,
            content_length=len(message_content),
            has_accumulated_params=accumulated_params is not None,
        )

        # Check if user is authorized (silent skip if not configured)
        if not is_user_authorized(username):
            self.logger.debug("User not authorized, silently skipping", username=username)
            return "User not configured for Notion integration"  # Return message instead of empty string

        # Get user configuration
        user_config = get_user_config(username)
        if not user_config:
            self.logger.error("User config not found after authorization check", username=username)
            return "❌ Configuration error. Please contact administrator."

        token = user_config["token"]
        parent_page_id = user_config["parent_page_id"]

        # Get persistent Notion client for this user (with cache preservation)
        notion_client = self._get_notion_client(username, token)

        # Get today's date for page title (without timestamp so all messages for the day go to same page)
        today_date = format_date_for_page_title()

        try:
            # Get or create today's daily page
            page_id = await self._get_or_create_daily_page(notion_client, parent_page_id, today_date)

            # Prepare content to append with proper formatting and sanitization
            content_to_append = format_message_content(message_content, accumulated_params)

            # Truncate content if it's too long for Notion
            content_to_append = truncate_content(content_to_append)

            # Append message to the page
            await self._append_message_to_page(notion_client, page_id, content_to_append)

            self.logger.info(
                "Successfully saved message to Notion",
                username=username,
                page_id=page_id,
                content_length=len(content_to_append),
            )

            return f"✅ Message saved to Notion page for {today_date}"

        except Exception as e:
            # Handle any errors from the helper methods (they already log specific details)
            self.logger.error(
                "Failed to save message to Notion",
                username=username,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return the error message from the helper method if it's a string, otherwise generic message
            if (
                isinstance(e, Exception)
                and hasattr(e, "args")
                and e.args
                and isinstance(e.args[0], str)
                and e.args[0].startswith("❌")
            ):
                return e.args[0]
            return "❌ An unexpected error occurred. Please try again later."

    def _get_notion_client(self, username: str, token: str) -> NotionClientWrapper:
        """
        Get or create a persistent NotionClientWrapper for the user.

        This method ensures that each user gets a persistent client instance
        that maintains its own cache across requests, improving performance.

        Args:
            username: The username to get the client for
            token: The Notion API token for the user

        Returns:
            NotionClientWrapper: Persistent client instance for the user
        """
        # Try to get existing client instance first
        if username in self._client_instances:
            self.logger.debug("Using existing persistent client", username=username)
            return self._client_instances[username]

        # Create new client instance if not found (fallback for edge cases)
        self.logger.info("Creating new client instance", username=username)
        client = NotionClientWrapper(token)
        self._client_instances[username] = client
        return client

    async def _get_or_create_daily_page(
        self, notion_client: NotionClientWrapper, parent_page_id: str, date_str: str
    ) -> str:
        """
        Get or create a daily page for the specified date.

        Uses a retry mechanism to handle race conditions where multiple requests
        might try to create the same page simultaneously.

        Args:
            notion_client: Initialized Notion client wrapper
            parent_page_id: Parent page or database ID where the daily page should be created
            date_str: Date string in YYYY-MM-DD format

        Returns:
            str: Page ID of the daily page

        Raises:
            Exception: If page creation or lookup fails with user-friendly error message

        Requirements: 2.1, 2.2
        """
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                # First, try to find existing page with today's date
                existing_page_id = await notion_client.find_page_by_title(parent_page_id, date_str)

                if existing_page_id:
                    self.logger.info(
                        "Found existing daily page", page_id=existing_page_id, date=date_str, attempt=attempt + 1
                    )
                    return existing_page_id

                # Page doesn't exist, create a new one
                self.logger.info(
                    "Creating new daily page", parent_page_id=parent_page_id, date=date_str, attempt=attempt + 1
                )
                page_id = await notion_client.create_page(parent_page_id, date_str)

                self.logger.info("Successfully created daily page", page_id=page_id, date=date_str)
                return page_id

            except APIResponseError as e:
                # If we get a conflict error (page already exists), retry the search
                if getattr(e, "status", None) == 409 and attempt < max_retries:
                    self.logger.info("Page creation conflict, retrying search", date=date_str, attempt=attempt + 1)
                    continue

                # Handle other specific Notion API errors with user-friendly messages
                error_msg = self._handle_api_error(e)
                self.logger.error(
                    "Notion API error during page creation/lookup",
                    parent_page_id=parent_page_id,
                    date=date_str,
                    error=str(e),
                    status_code=getattr(e, "status", "unknown"),
                    error_code=getattr(e, "code", "unknown"),
                    attempt=attempt + 1,
                )
                raise Exception(error_msg)

            except RequestTimeoutError as e:
                self.logger.error(
                    "Request timeout during page creation/lookup",
                    parent_page_id=parent_page_id,
                    date=date_str,
                    error=str(e),
                    attempt=attempt + 1,
                )
                raise Exception("❌ Request timed out. Please try again later.")

            except Exception as e:
                # For unexpected errors, retry once in case it was a transient issue
                if attempt < max_retries:
                    self.logger.warning(
                        "Unexpected error during page creation/lookup, retrying",
                        parent_page_id=parent_page_id,
                        date=date_str,
                        error=str(e),
                        error_type=type(e).__name__,
                        attempt=attempt + 1,
                    )
                    continue

                self.logger.error(
                    "Unexpected error during page creation/lookup after retries",
                    parent_page_id=parent_page_id,
                    date=date_str,
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1,
                )
                raise Exception("❌ An unexpected error occurred. Please try again later.")

        # This should never be reached, but just in case
        raise Exception("❌ Failed to get or create daily page after all retries.")

    async def _append_message_to_page(self, notion_client: NotionClientWrapper, page_id: str, content: str) -> None:
        """
        Append message content to the specified page.

        Args:
            notion_client: Initialized Notion client wrapper
            page_id: ID of the page to append content to
            content: Message content to append

        Raises:
            Exception: If content appending fails with user-friendly error message

        Requirements: 1.3, 2.2
        """
        try:
            # Add timestamp to the message using proper timezone handling
            timestamp = format_timestamp_for_content()
            formatted_content = f"{timestamp} {content}"

            await notion_client.append_content_to_page(page_id, formatted_content)

        except APIResponseError as e:
            # Handle specific Notion API errors with user-friendly messages
            error_msg = self._handle_api_error(e)
            self.logger.error(
                "Notion API error during content appending",
                page_id=page_id,
                content_length=len(content),
                error=str(e),
                status_code=getattr(e, "status", "unknown"),
                error_code=getattr(e, "code", "unknown"),
            )
            raise Exception(error_msg)

        except RequestTimeoutError as e:
            self.logger.error(
                "Request timeout during content appending",
                page_id=page_id,
                content_length=len(content),
                error=str(e),
            )
            raise Exception("❌ Request timed out. Please try again later.")

        except Exception as e:
            self.logger.error(
                "Unexpected error during content appending",
                page_id=page_id,
                content_length=len(content),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise Exception("❌ An unexpected error occurred. Please try again later.")

    def _handle_api_error(self, error: APIResponseError) -> str:
        """
        Handle Notion API errors and return user-friendly error messages.

        Args:
            error: The APIResponseError from Notion client

        Returns:
            str: User-friendly error message

        Requirements: 5.1, 5.2
        """
        status_code = getattr(error, "status", None)
        error_code = getattr(error, "code", None)

        # Map common API errors to user-friendly messages
        if status_code == 401:
            return "❌ Authentication failed. Please check your Notion integration token."
        elif status_code == 403:
            return "❌ Access denied. Please check your Notion integration permissions."
        elif status_code == 404:
            if error_code == "object_not_found":
                return "❌ The configured parent page was not found. Please check your configuration."
            return "❌ The requested resource was not found."
        elif status_code == 429:
            return "❌ Rate limit exceeded. Please try again in a few minutes."
        elif status_code == 400:
            if error_code == "validation_error":
                return "❌ Invalid request. Please check your configuration."
            return "❌ Bad request. Please try again."
        elif status_code and 500 <= status_code < 600:
            return "❌ Notion service is temporarily unavailable. Please try again later."
        else:
            # Generic error message for unknown API errors
            return "❌ Notion API error occurred. Please try again later."
