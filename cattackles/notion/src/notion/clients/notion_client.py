from typing import Optional

import structlog
from notion_client import AsyncClient
from notion_client.errors import APIResponseError, RequestTimeoutError

logger = structlog.get_logger(__name__)


class NotionClientWrapper:
    """
    Async wrapper around the Notion Python SDK with standardized error handling.

    Provides simplified methods for common operations like page creation,
    content appending, and page searching.
    """

    def __init__(self, token: str):
        """
        Initialize the Notion client wrapper.

        Args:
            token: Notion integration token for API authentication
        """
        self.client = AsyncClient(auth=token)
        self.logger = logger.bind(component="notion_client")

    async def create_page(self, parent_id: str, title: str, content: Optional[str] = None) -> str:
        """
        Create a new page in Notion.

        Args:
            parent_id: ID of the parent page or database
            title: Title for the new page
            content: Optional initial content for the page

        Returns:
            str: ID of the created page

        Raises:
            APIResponseError: If the Notion API request fails
            RequestTimeoutError: If the request times out
        """
        try:
            self.logger.info("Creating new page", parent_id=parent_id, title=title, has_content=content is not None)

            # Build the page properties
            properties = {"title": {"title": [{"text": {"content": title}}]}}

            # Build the page payload
            page_data = {"parent": {"page_id": parent_id}, "properties": properties}

            # Add initial content if provided
            if content:
                page_data["children"] = [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
                    }
                ]

            response = await self.client.pages.create(**page_data)
            page_id = response["id"]

            self.logger.info("Successfully created page", page_id=page_id, title=title)

            return page_id

        except APIResponseError as e:
            self.logger.error(
                "Failed to create page", error=str(e), status_code=e.status, parent_id=parent_id, title=title
            )
            raise
        except RequestTimeoutError as e:
            self.logger.error("Request timeout while creating page", error=str(e), parent_id=parent_id, title=title)
            raise
        except Exception as e:
            self.logger.error("Unexpected error while creating page", error=str(e), parent_id=parent_id, title=title)
            raise

    async def find_page_by_title(self, parent_id: str, title: str) -> Optional[str]:
        """
        Find a page by title within a parent page or database.

        Args:
            parent_id: ID of the parent page or database to search in
            title: Title of the page to find

        Returns:
            Optional[str]: ID of the found page, or None if not found

        Raises:
            APIResponseError: If the Notion API request fails
            RequestTimeoutError: If the request times out
        """
        try:
            # Search for pages with the specified title
            response = await self.client.search(query=title, filter={"value": "page", "property": "object"})

            # Look for exact title match in the results
            for result in response.get("results", []):
                if result.get("object") == "page":
                    # Check if this page has the parent we're looking for
                    parent = result.get("parent", {})
                    if parent.get("page_id") == parent_id or parent.get("database_id") == parent_id:

                        # Check if the title matches exactly
                        properties = result.get("properties", {})
                        title_prop = properties.get("title", {})
                        title_content = title_prop.get("title", [])

                        if title_content and title_content[0].get("text", {}).get("content") == title:
                            page_id = result["id"]
                            return page_id
            return None

        except APIResponseError as e:
            self.logger.error(
                "Failed to search for page", error=str(e), status_code=e.status, parent_id=parent_id, title=title
            )
            raise
        except RequestTimeoutError as e:
            self.logger.error(
                "Request timeout while searching for page", error=str(e), parent_id=parent_id, title=title
            )
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error while searching for page", error=str(e), parent_id=parent_id, title=title
            )
            raise

    async def append_content_to_page(self, page_id: str, content: str) -> None:
        """
        Append content to an existing page.

        Args:
            page_id: ID of the page to append content to
            content: Text content to append

        Raises:
            APIResponseError: If the Notion API request fails
            RequestTimeoutError: If the request times out
        """
        try:
            # Create a paragraph block with the content
            new_block = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
            }

            # Append the block to the page
            await self.client.blocks.children.append(block_id=page_id, children=[new_block])

        except APIResponseError as e:
            self.logger.error(
                "Failed to append content to page",
                error=str(e),
                status_code=e.status,
                page_id=page_id,
                content_length=len(content),
            )
            raise
        except RequestTimeoutError as e:
            self.logger.error(
                "Request timeout while appending content", error=str(e), page_id=page_id, content_length=len(content)
            )
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error while appending content", error=str(e), page_id=page_id, content_length=len(content)
            )
            raise
