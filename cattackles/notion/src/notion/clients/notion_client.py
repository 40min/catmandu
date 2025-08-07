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

            # Cache the newly created page
            cache_key = self._get_cache_key(parent_id, title)
            self._page_cache[cache_key] = page_id

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

    def _get_cache_key(self, parent_id: str, title: str) -> str:
        """Generate a cache key for the page lookup."""
        return f"{parent_id}:{title}"

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
            self.logger.debug("Page not found in cache", parent_id=parent_id, title=title)
            return None

        self.logger.debug("Found page in cache, verifying existence", page_id=cached_page_id, title=title)

        # Verify the cached page still exists
        try:
            await self.client.pages.retrieve(page_id=cached_page_id)
            self.logger.debug("Cache hit: page verified to exist", page_id=cached_page_id, title=title)
            return cached_page_id
        except APIResponseError as e:
            if e.status == 404:
                # Page no longer exists, remove from cache
                self.logger.debug(
                    "Cached page no longer exists, removing from cache", page_id=cached_page_id, title=title
                )
                del self._page_cache[cache_key]
                return None
            else:
                # Other API error, log but don't remove from cache
                self.logger.debug(
                    "Error verifying cached page existence", error=str(e), page_id=cached_page_id, title=title
                )
                return None
        except Exception as e:
            self.logger.debug(
                "Unexpected error verifying cached page", error=str(e), page_id=cached_page_id, title=title
            )
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
            self.logger.debug("Searching for page via search API", parent_id=parent_id, title=title)

            response = await self.client.search(query=title, filter={"value": "page", "property": "object"})
            results = response.get("results", [])

            self.logger.debug(
                "Search API returned results", parent_id=parent_id, title=title, result_count=len(results)
            )

            # Look for exact title match in the results
            for result in results:
                if result.get("object") == "page":
                    # Check if this page has the parent we're looking for
                    parent = result.get("parent", {})
                    result_parent_id = parent.get("page_id") or parent.get("database_id")

                    if result_parent_id == parent_id:
                        # Check if the title matches exactly
                        properties = result.get("properties", {})
                        title_prop = properties.get("title", {})
                        title_content = title_prop.get("title", [])

                        if title_content and title_content[0].get("text", {}).get("content") == title:
                            page_id = result["id"]
                            self.logger.debug("Found page via search API", page_id=page_id, title=title)

                            # Cache the result
                            cache_key = self._get_cache_key(parent_id, title)
                            self._page_cache[cache_key] = page_id

                            return page_id

            self.logger.debug("Page not found via search API", parent_id=parent_id, title=title)
            return None

        except APIResponseError as e:
            self.logger.debug("Search API failed", error=str(e), status_code=e.status, parent_id=parent_id, title=title)
            raise
        except RequestTimeoutError as e:
            self.logger.debug("Search API timeout", error=str(e), parent_id=parent_id, title=title)
            raise
        except Exception as e:
            self.logger.debug("Unexpected error in search API", error=str(e), parent_id=parent_id, title=title)
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
            self.logger.debug("Listing child pages to find page", parent_id=parent_id, title=title)

            children_response = await self.client.blocks.children.list(block_id=parent_id)
            results = children_response.get("results", [])

            self.logger.debug(
                "Child listing returned results", parent_id=parent_id, title=title, result_count=len(results)
            )

            for child in results:
                if child.get("type") == "child_page":
                    child_title = child.get("child_page", {}).get("title", "")
                    if child_title == title:
                        page_id = child["id"]
                        self.logger.debug("Found page via child listing", page_id=page_id, title=title)

                        # Cache the result
                        cache_key = self._get_cache_key(parent_id, title)
                        self._page_cache[cache_key] = page_id

                        return page_id

            self.logger.debug("Page not found via child listing", parent_id=parent_id, title=title)
            return None

        except APIResponseError as e:
            self.logger.debug(
                "Child listing failed", error=str(e), status_code=e.status, parent_id=parent_id, title=title
            )
            # If direct listing fails (e.g., parent is a database), this is expected
            if e.status == 400:
                self.logger.debug("Child listing not supported for this parent type", parent_id=parent_id, title=title)
                return None
            raise
        except RequestTimeoutError as e:
            self.logger.debug("Child listing timeout", error=str(e), parent_id=parent_id, title=title)
            raise
        except Exception as e:
            self.logger.debug("Unexpected error in child listing", error=str(e), parent_id=parent_id, title=title)
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
            self.logger.debug("Starting page search", parent_id=parent_id, title=title)

            # Stage 1: Check cache
            page_id = await self._find_page_in_cache(parent_id, title)
            if page_id:
                self.logger.info("Found page via cache", page_id=page_id, title=title)
                return page_id

            # Stage 2: Search API
            page_id = await self._find_page_via_search(parent_id, title)
            if page_id:
                self.logger.info("Found page via search API", page_id=page_id, title=title)
                return page_id

            # Stage 3: List all child pages
            page_id = await self._find_page_via_listing(parent_id, title)
            if page_id:
                self.logger.info("Found page via child listing", page_id=page_id, title=title)
                return page_id

            self.logger.info("Page not found via any method", parent_id=parent_id, title=title)
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
