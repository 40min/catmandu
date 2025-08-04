"""Core business logic for the Notion cattackle.

This module contains the main NotionCattackle class that orchestrates
the message saving workflow, including page management and content operations.
"""

from datetime import datetime
from typing import List, Optional

import structlog
from notion.clients.notion_client import NotionClientWrapper
from notion.config.user_config import get_user_config, is_user_authorized

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
        try:
            self.logger.info(
                "Processing save_to_notion request",
                username=username,
                content_length=len(message_content),
                has_accumulated_params=accumulated_params is not None,
            )

            # Check if user is authorized (silent skip if not configured)
            if not is_user_authorized(username):
                self.logger.debug("User not authorized, silently skipping", username=username)
                return ""  # Silent skip for unconfigured users

            # Get user configuration
            user_config = get_user_config(username)
            if not user_config:
                self.logger.error("User config not found after authorization check", username=username)
                return "❌ Configuration error. Please contact administrator."

            token = user_config["token"]
            parent_page_id = user_config["parent_page_id"]

            # Initialize Notion client for this user
            notion_client = NotionClientWrapper(token)

            # Get today's date for page title
            today = datetime.now().strftime("%Y-%m-%d")

            # Get or create today's daily page
            page_id = await self._get_or_create_daily_page(notion_client, parent_page_id, today)

            # Prepare content to append
            content_to_append = message_content
            if accumulated_params:
                # If there are accumulated parameters, include them in the content
                accumulated_text = " ".join(accumulated_params)
                content_to_append = f"{accumulated_text} {message_content}".strip()

            # Append message to the page
            await self._append_message_to_page(notion_client, page_id, content_to_append)

            self.logger.info(
                "Successfully saved message to Notion",
                username=username,
                page_id=page_id,
                content_length=len(content_to_append),
            )

            return f"✅ Message saved to Notion page for {today}"

        except Exception as e:
            self.logger.error(
                "Failed to save message to Notion", username=username, error=str(e), error_type=type(e).__name__
            )
            return f"❌ Failed to save message: {str(e)}"

    async def _get_or_create_daily_page(
        self, notion_client: NotionClientWrapper, parent_page_id: str, date: str
    ) -> str:
        """
        Get or create a daily page for the specified date.

        Args:
            notion_client: Initialized Notion client wrapper
            parent_page_id: Parent page or database ID where the daily page should be created
            date: Date string in YYYY-MM-DD format

        Returns:
            str: Page ID of the daily page

        Raises:
            Exception: If page creation or lookup fails

        Requirements: 2.1, 2.2
        """
        try:
            self.logger.debug("Getting or creating daily page", parent_page_id=parent_page_id, date=date)

            # First, try to find existing page with today's date
            existing_page_id = await notion_client.find_page_by_title(parent_page_id, date)

            if existing_page_id:
                self.logger.debug("Found existing daily page", page_id=existing_page_id, date=date)
                return existing_page_id

            # Page doesn't exist, create a new one
            self.logger.info("Creating new daily page", parent_page_id=parent_page_id, date=date)
            page_id = await notion_client.create_page(parent_page_id, date)

            self.logger.info("Successfully created daily page", page_id=page_id, date=date)
            return page_id

        except Exception as e:
            self.logger.error(
                "Failed to get or create daily page",
                parent_page_id=parent_page_id,
                date=date,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def _append_message_to_page(self, notion_client: NotionClientWrapper, page_id: str, content: str) -> None:
        """
        Append message content to the specified page.

        Args:
            notion_client: Initialized Notion client wrapper
            page_id: ID of the page to append content to
            content: Message content to append

        Raises:
            Exception: If content appending fails

        Requirements: 1.3, 2.2
        """
        try:
            self.logger.debug("Appending message to page", page_id=page_id, content_length=len(content))

            # Add timestamp to the message
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_content = f"[{timestamp}] {content}"

            await notion_client.append_content_to_page(page_id, formatted_content)

            self.logger.debug("Successfully appended message to page", page_id=page_id)

        except Exception as e:
            self.logger.error(
                "Failed to append message to page",
                page_id=page_id,
                content_length=len(content),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
