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
        cache_key = f"{parent_id}:{title}"
        self.logger.info(
            "🔑 GENERATED CACHE KEY",
            parent_id=parent_id,
            title=title,
            cache_key=cache_key,
            parent_id_type=type(parent_id).__name__,
            title_type=type(title).__name__,
            parent_id_len=len(parent_id),
            title_len=len(title),
        )
        return cache_key

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

            self.logger.info(
                "✅ SUCCESSFULLY CREATED PAGE AND CACHED",
                page_id=page_id,
                title=title,
                cache_key=cache_key,
                cache_size=len(self._page_cache),
                parent_id=parent_id,
                all_cache_keys=list(self._page_cache.keys()),
            )

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

        self.logger.info(
            "🔍 CACHE LOOKUP ATTEMPT",
            parent_id=parent_id,
            title=title,
            cache_key=cache_key,
            cache_size=len(self._page_cache),
            cache_keys=list(self._page_cache.keys()),
            found_in_cache=cached_page_id is not None,
            cached_page_id=cached_page_id,
        )

        if not cached_page_id:
            self.logger.info("❌ PAGE NOT IN CACHE", parent_id=parent_id, title=title, cache_key=cache_key)
            return None

        self.logger.info("🔍 FOUND IN CACHE - VERIFYING EXISTENCE", page_id=cached_page_id, title=title)

        # Verify the cached page still exists and is not archived
        try:
            page_response = await self.client.pages.retrieve(page_id=cached_page_id)

            # Check if the page is archived (deleted in Notion UI)
            is_archived = page_response.get("archived", False)

            if is_archived:
                # Page is archived, remove from cache
                self.logger.info(
                    "🗑️ CACHED PAGE IS ARCHIVED - REMOVING FROM CACHE",
                    page_id=cached_page_id,
                    title=title,
                    cache_key=cache_key,
                    cache_size_before=len(self._page_cache),
                )
                del self._page_cache[cache_key]
                self.logger.info("🗑️ REMOVED ARCHIVED PAGE FROM CACHE", cache_size_after=len(self._page_cache))
                return None

            self.logger.info(
                "✅ CACHE HIT - PAGE VERIFIED TO EXIST AND NOT ARCHIVED", page_id=cached_page_id, title=title
            )
            return cached_page_id

        except APIResponseError as e:
            if e.status == 404:
                # Page no longer exists, remove from cache
                self.logger.info(
                    "🗑️ CACHED PAGE NO LONGER EXISTS - REMOVING FROM CACHE",
                    page_id=cached_page_id,
                    title=title,
                    cache_key=cache_key,
                    cache_size_before=len(self._page_cache),
                )
                del self._page_cache[cache_key]
                self.logger.info("🗑️ REMOVED FROM CACHE", cache_size_after=len(self._page_cache))
                return None
            else:
                # Other API error, log but don't remove from cache
                self.logger.info(
                    "⚠️ ERROR VERIFYING CACHED PAGE - KEEPING IN CACHE",
                    error=str(e),
                    status_code=e.status,
                    page_id=cached_page_id,
                    title=title,
                )
                return None
        except Exception as e:
            self.logger.info(
                "💥 UNEXPECTED ERROR VERIFYING CACHED PAGE - KEEPING IN CACHE",
                error=str(e),
                page_id=cached_page_id,
                title=title,
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
            self.logger.info("Searching for page via search API", parent_id=parent_id, title=title)

            response = await self.client.search(query=title, filter={"value": "page", "property": "object"})
            results = response.get("results", [])

            self.logger.info(
                "🔍 SEARCH API RETURNED RESULTS", parent_id=parent_id, title=title, result_count=len(results)
            )

            # Look for exact title match in the results
            for i, result in enumerate(results):
                self.logger.info(
                    "🔍 EXAMINING SEARCH RESULT",
                    result_index=i,
                    result_object_type=result.get("object"),
                    result_id=result.get("id"),
                    full_result_keys=list(result.keys()),
                )

                if result.get("object") == "page":
                    # Check if this page has the parent we're looking for
                    parent = result.get("parent", {})
                    result_parent_id = parent.get("page_id") or parent.get("database_id")

                    # Normalize both IDs to handle format differences (with/without dashes)
                    normalized_result_parent = self._normalize_notion_id(result_parent_id) if result_parent_id else None
                    normalized_expected_parent = self._normalize_notion_id(parent_id)

                    self.logger.info(
                        "🔍 CHECKING PARENT MATCH",
                        result_parent_id=result_parent_id,
                        expected_parent_id=parent_id,
                        normalized_result_parent=normalized_result_parent,
                        normalized_expected_parent=normalized_expected_parent,
                        parent_matches=normalized_result_parent == normalized_expected_parent,
                        parent_structure=parent,
                    )

                    if normalized_result_parent == normalized_expected_parent:
                        # Check if the title matches exactly
                        properties = result.get("properties", {})
                        title_prop = properties.get("title", {})
                        title_content = title_prop.get("title", [])

                        actual_title = None
                        if title_content and len(title_content) > 0:
                            actual_title = title_content[0].get("text", {}).get("content")

                        self.logger.info(
                            "🔍 CHECKING TITLE MATCH",
                            actual_title=actual_title,
                            expected_title=title,
                            title_matches=actual_title == title,
                            title_content_structure=title_content,
                            properties_structure=properties,
                        )

                        if title_content and title_content[0].get("text", {}).get("content") == title:
                            page_id = result["id"]
                            self.logger.info("✅ FOUND EXACT MATCH VIA SEARCH API", page_id=page_id, title=title)

                            # Cache the result
                            cache_key = self._get_cache_key(parent_id, title)
                            self._page_cache[cache_key] = page_id

                            self.logger.info(
                                "💾 CACHED PAGE FROM SEARCH API",
                                page_id=page_id,
                                cache_key=cache_key,
                                cache_size=len(self._page_cache),
                            )

                            return page_id
                        else:
                            self.logger.info(
                                "❌ TITLE MISMATCH - SKIPPING RESULT",
                                actual_title=actual_title,
                                expected_title=title,
                                result_id=result.get("id"),
                            )
                    else:
                        self.logger.info(
                            "❌ PARENT MISMATCH - SKIPPING RESULT",
                            result_parent_id=result_parent_id,
                            expected_parent_id=parent_id,
                            result_id=result.get("id"),
                        )
                else:
                    self.logger.info(
                        "❌ NON-PAGE RESULT - SKIPPING", object_type=result.get("object"), result_id=result.get("id")
                    )

            self.logger.info("❌ PAGE NOT FOUND VIA SEARCH API", parent_id=parent_id, title=title)
            return None

        except APIResponseError as e:
            self.logger.info("Search API failed", error=str(e), status_code=e.status, parent_id=parent_id, title=title)
            raise
        except RequestTimeoutError as e:
            self.logger.info("Search API timeout", error=str(e), parent_id=parent_id, title=title)
            raise
        except Exception as e:
            self.logger.info("Unexpected error in search API", error=str(e), parent_id=parent_id, title=title)
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
            self.logger.info("Listing child pages to find page", parent_id=parent_id, title=title)

            children_response = await self.client.blocks.children.list(block_id=parent_id)
            results = children_response.get("results", [])

            self.logger.info(
                "Child listing returned results", parent_id=parent_id, title=title, result_count=len(results)
            )

            for child in results:
                if child.get("type") == "child_page":
                    child_title = child.get("child_page", {}).get("title", "")
                    if child_title == title:
                        page_id = child["id"]
                        self.logger.info("Found page via child listing", page_id=page_id, title=title)

                        # Cache the result
                        cache_key = self._get_cache_key(parent_id, title)
                        self._page_cache[cache_key] = page_id

                        self.logger.info(
                            "Cached page from child listing",
                            page_id=page_id,
                            cache_key=cache_key,
                            cache_size=len(self._page_cache),
                        )

                        return page_id

            self.logger.info("Page not found via child listing", parent_id=parent_id, title=title)
            return None

        except APIResponseError as e:
            self.logger.info(
                "Child listing failed", error=str(e), status_code=e.status, parent_id=parent_id, title=title
            )
            # If direct listing fails (e.g., parent is a database), this is expected
            if e.status == 400:
                self.logger.info("Child listing not supported for this parent type", parent_id=parent_id, title=title)
                return None
            raise
        except RequestTimeoutError as e:
            self.logger.info("Child listing timeout", error=str(e), parent_id=parent_id, title=title)
            raise
        except Exception as e:
            self.logger.info("Unexpected error in child listing", error=str(e), parent_id=parent_id, title=title)
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
            self.logger.info(
                "🔍 STARTING PAGE SEARCH",
                parent_id=parent_id,
                title=title,
                cache_size_before=len(self._page_cache),
                all_cache_keys=list(self._page_cache.keys()),
            )

            # Stage 1: Check cache
            page_id = await self._find_page_in_cache(parent_id, title)
            if page_id:
                self.logger.info("✅ FOUND VIA CACHE", page_id=page_id, title=title)
                return page_id

            # Stage 2: Search API
            page_id = await self._find_page_via_search(parent_id, title)
            if page_id:
                self.logger.info(
                    "✅ FOUND VIA SEARCH API", page_id=page_id, title=title, cache_size_after=len(self._page_cache)
                )
                return page_id

            # Stage 3: List all child pages
            page_id = await self._find_page_via_listing(parent_id, title)
            if page_id:
                self.logger.info(
                    "✅ FOUND VIA CHILD LISTING", page_id=page_id, title=title, cache_size_after=len(self._page_cache)
                )
                return page_id

            self.logger.info(
                "❌ PAGE NOT FOUND VIA ANY METHOD",
                parent_id=parent_id,
                title=title,
                final_cache_size=len(self._page_cache),
            )
            return None

        except APIResponseError as e:
            self.logger.error(
                "🚨 API ERROR during page search", error=str(e), status_code=e.status, parent_id=parent_id, title=title
            )
            raise
        except RequestTimeoutError as e:
            self.logger.error("⏰ TIMEOUT ERROR during page search", error=str(e), parent_id=parent_id, title=title)
            raise
        except Exception as e:
            self.logger.error("💥 UNEXPECTED ERROR during page search", error=str(e), parent_id=parent_id, title=title)
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
