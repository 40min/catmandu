from typing import Dict, Optional

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
        # Cache for date -> page_id mapping to optimize repeated lookups
        self._page_cache: Dict[str, str] = {}

    def _get_cache_key(self, parent_id: str, title: str) -> str:
        """Generate a cache key for the page lookup."""
        return f"{parent_id}:{title}"

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

            # Cache the newly created page
            cache_key = self._get_cache_key(parent_id, title)
            self._page_cache[cache_key] = page_id

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

    def _normalize_notion_id(self, notion_id: str) -> str:
        """
        Normalize Notion IDs to handle format differences.

        Notion IDs can be returned in different formats:
        - With dashes: 24713202-e62c-8028-94aa-c2d396532b14
        - Without dashes: 24713202e62c802894aac2d396532b14

        This method normalizes them to the format without dashes for consistent comparison.

        Args:
            notion_id: The Notion ID to normalize

        Returns:
            str: Normalized ID without dashes
        """
        if not notion_id:
            return notion_id
        return notion_id.replace("-", "")

    async def _find_page_in_cache(self, parent_id: str, title: str) -> Optional[str]:
        """
        Stage 1: Check if page exists in memory cache.

        Args:
            parent_id: ID of the parent page or database
            title: Title of the page to find

        Returns:
            Optional[str]: Cached page ID if found and verified to exist, None otherwise
        """
        cache_key = self._get_cache_key(parent_id, title)
        cached_page_id = self._page_cache.get(cache_key)

        if not cached_page_id:
            return None

        # Verify the cached page still exists and is not archived
        try:
            page_response = await self.client.pages.retrieve(page_id=cached_page_id)

            # Check if the page is archived (deleted in Notion UI)
            is_archived = page_response.get("archived", False)

            if is_archived:
                # Page is archived, remove from cache
                del self._page_cache[cache_key]
                return None
            return cached_page_id

        except APIResponseError as e:
            if e.status == 404:
                # Page no longer exists, remove from cache
                del self._page_cache[cache_key]
                return None
            else:
                # Other API error, don't remove from cache
                return None
        except Exception:
            return None

    async def _find_page_via_search(self, parent_id: str, title: str) -> Optional[str]:
        """
        Stage 2: Search for page using Notion's search API.

        Args:
            parent_id: ID of the parent page or database
            title: Title of the page to find

        Returns:
            Optional[str]: Page ID if found via search, None otherwise
        """
        try:

            response = await self.client.search(query=title, filter={"value": "page", "property": "object"})
            results = response.get("results", [])

            # Look for exact title match in the results
            for result in results:

                if result.get("object") == "page":
                    # Check if this page has the parent we're looking for
                    parent = result.get("parent", {})
                    result_parent_id = parent.get("page_id") or parent.get("database_id")

                    # Normalize both IDs to handle format differences (with/without dashes)
                    normalized_result_parent = self._normalize_notion_id(result_parent_id) if result_parent_id else None
                    normalized_expected_parent = self._normalize_notion_id(parent_id)

                    if normalized_result_parent == normalized_expected_parent:
                        # Check if the title matches exactly
                        properties = result.get("properties", {})
                        title_prop = properties.get("title", {})
                        title_content = title_prop.get("title", [])

                        if title_content and title_content[0].get("text", {}).get("content") == title:
                            page_id = result["id"]

                            # Cache the result
                            cache_key = self._get_cache_key(parent_id, title)
                            self._page_cache[cache_key] = page_id

                            return page_id

            return None

        except APIResponseError as e:
            self.logger.error("Search API failed", error=str(e), status_code=e.status, parent_id=parent_id, title=title)
            raise
        except RequestTimeoutError as e:
            self.logger.error("Search API timeout", error=str(e), parent_id=parent_id, title=title)
            raise
        except Exception as e:
            self.logger.error("Unexpected error in search API", error=str(e), parent_id=parent_id, title=title)
            raise

    async def _find_page_via_listing(self, parent_id: str, title: str) -> Optional[str]:
        """
        Stage 3: List all child pages and search through them.

        Args:
            parent_id: ID of the parent page or database
            title: Title of the page to find

        Returns:
            Optional[str]: Page ID if found via listing, None otherwise
        """
        try:

            children_response = await self.client.blocks.children.list(block_id=parent_id)
            results = children_response.get("results", [])

            for child in results:
                if child.get("type") == "child_page":
                    child_title = child.get("child_page", {}).get("title", "")
                    if child_title == title:
                        page_id = child["id"]

                        # Cache the result
                        cache_key = self._get_cache_key(parent_id, title)
                        self._page_cache[cache_key] = page_id

                        return page_id
            return None

        except APIResponseError as e:
            # If direct listing fails (e.g., parent is a database), this is expected
            if e.status == 400:
                return None
            self.logger.error(
                "Child listing failed", error=str(e), status_code=e.status, parent_id=parent_id, title=title
            )
            raise
        except RequestTimeoutError as e:
            self.logger.error("Child listing timeout", error=str(e), parent_id=parent_id, title=title)
            raise
        except Exception as e:
            self.logger.error("Unexpected error in child listing", error=str(e), parent_id=parent_id, title=title)
            raise

    async def find_page_by_title(self, parent_id: str, title: str) -> Optional[str]:
        """
        Find a page by title within a parent page or database.

        Uses a three-stage approach:
        1. Check memory cache (with existence verification)
        2. Search API (faster, but may miss recent pages)
        3. List all child pages (comprehensive, but slower for large numbers of pages)

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
            # Stage 1: Check cache
            page_id = await self._find_page_in_cache(parent_id, title)
            if page_id:
                return page_id

            # Stage 2: Search API
            page_id = await self._find_page_via_search(parent_id, title)
            if page_id:
                return page_id

            # Stage 3: List all child pages
            page_id = await self._find_page_via_listing(parent_id, title)
            if page_id:
                return page_id

            return None

        except APIResponseError as e:
            self.logger.error(
                "API error during page search", error=str(e), status_code=e.status, parent_id=parent_id, title=title
            )
            raise
        except RequestTimeoutError as e:
            self.logger.error("Timeout error during page search", error=str(e), parent_id=parent_id, title=title)
            raise
        except Exception as e:
            self.logger.error("Unexpected error during page search", error=str(e), parent_id=parent_id, title=title)
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
