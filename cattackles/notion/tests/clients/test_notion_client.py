from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from notion.clients.notion_client import NotionClientWrapper
from notion_client.errors import APIResponseError, RequestTimeoutError


class TestNotionClientWrapper:
    """Test suite for NotionClientWrapper."""

    @pytest.fixture
    def notion_wrapper(self):
        """Create a NotionClientWrapper instance for testing."""
        return NotionClientWrapper(token="test_token")

    @pytest.fixture
    def mock_notion_client(self, notion_wrapper):
        """Mock the underlying Notion client."""
        with patch.object(notion_wrapper, "client") as mock_client:
            yield mock_client

    class TestCreatePage:
        """Test cases for create_page method."""

        @pytest.mark.asyncio
        async def test_create_page_success_without_content(self, notion_wrapper, mock_notion_client):
            """Test successful page creation without initial content."""
            # Arrange
            mock_response = {"id": "test_page_id_123"}
            mock_notion_client.pages.create = AsyncMock(return_value=mock_response)

            # Act
            result = await notion_wrapper.create_page(parent_id="parent_123", title="Test Page")

            # Assert
            assert result == "test_page_id_123"
            mock_notion_client.pages.create.assert_called_once()

            # Verify the call arguments
            call_args = mock_notion_client.pages.create.call_args
            assert call_args.kwargs["parent"] == {"page_id": "parent_123"}
            assert call_args.kwargs["properties"]["title"]["title"][0]["text"]["content"] == "Test Page"
            assert "children" not in call_args.kwargs

        @pytest.mark.asyncio
        async def test_create_page_success_with_content(self, notion_wrapper, mock_notion_client):
            """Test successful page creation with initial content."""
            # Arrange
            mock_response = {"id": "test_page_id_456"}
            mock_notion_client.pages.create = AsyncMock(return_value=mock_response)

            # Act
            result = await notion_wrapper.create_page(
                parent_id="parent_456", title="Test Page with Content", content="Initial content here"
            )

            # Assert
            assert result == "test_page_id_456"
            mock_notion_client.pages.create.assert_called_once()

            # Verify the call arguments include content
            call_args = mock_notion_client.pages.create.call_args
            assert "children" in call_args.kwargs
            children = call_args.kwargs["children"]
            assert len(children) == 1
            assert children[0]["type"] == "paragraph"
            assert children[0]["paragraph"]["rich_text"][0]["text"]["content"] == "Initial content here"

        @pytest.mark.asyncio
        async def test_create_page_api_error(self, notion_wrapper, mock_notion_client):
            """Test handling of Notion API errors during page creation."""
            # Arrange
            api_error = APIResponseError(
                response=MagicMock(status_code=400), message="Invalid parent ID", code="validation_error"
            )
            mock_notion_client.pages.create = AsyncMock(side_effect=api_error)

            # Act & Assert
            with pytest.raises(APIResponseError):
                await notion_wrapper.create_page(parent_id="invalid_parent", title="Test Page")

        @pytest.mark.asyncio
        async def test_create_page_timeout_error(self, notion_wrapper, mock_notion_client):
            """Test handling of timeout errors during page creation."""
            # Arrange
            timeout_error = RequestTimeoutError("Request timed out")
            mock_notion_client.pages.create = AsyncMock(side_effect=timeout_error)

            # Act & Assert
            with pytest.raises(RequestTimeoutError):
                await notion_wrapper.create_page(parent_id="parent_123", title="Test Page")

        @pytest.mark.asyncio
        async def test_create_page_unexpected_error(self, notion_wrapper, mock_notion_client):
            """Test handling of unexpected errors during page creation."""
            # Arrange
            unexpected_error = Exception("Unexpected error occurred")
            mock_notion_client.pages.create = AsyncMock(side_effect=unexpected_error)

            # Act & Assert
            with pytest.raises(Exception):
                await notion_wrapper.create_page(parent_id="parent_123", title="Test Page")

    class TestFindPageByTitle:
        """Test cases for find_page_by_title method."""

        @pytest.mark.asyncio
        async def test_find_page_by_title_found(self, notion_wrapper, mock_notion_client):
            """Test successful page finding by title."""
            # Arrange
            mock_response = {
                "results": [
                    {
                        "object": "page",
                        "id": "found_page_id",
                        "parent": {"page_id": "parent_123"},
                        "properties": {"title": {"title": [{"text": {"content": "Daily Notes 2025-01-15"}}]}},
                    }
                ]
            }
            mock_notion_client.search = AsyncMock(return_value=mock_response)

            # Act
            result = await notion_wrapper.find_page_by_title(parent_id="parent_123", title="Daily Notes 2025-01-15")

            # Assert
            assert result == "found_page_id"
            mock_notion_client.search.assert_called_once_with(
                query="Daily Notes 2025-01-15", filter={"value": "page", "property": "object"}
            )

        @pytest.mark.asyncio
        async def test_find_page_by_title_not_found(self, notion_wrapper, mock_notion_client):
            """Test page not found scenario."""
            # Arrange
            mock_response = {"results": []}
            mock_notion_client.search = AsyncMock(return_value=mock_response)

            # Act
            result = await notion_wrapper.find_page_by_title(parent_id="parent_123", title="Non-existent Page")

            # Assert
            assert result is None

        @pytest.mark.asyncio
        async def test_find_page_by_title_wrong_parent(self, notion_wrapper, mock_notion_client):
            """Test page found but with wrong parent."""
            # Arrange
            mock_response = {
                "results": [
                    {
                        "object": "page",
                        "id": "wrong_parent_page_id",
                        "parent": {"page_id": "different_parent"},
                        "properties": {"title": {"title": [{"text": {"content": "Daily Notes 2025-01-15"}}]}},
                    }
                ]
            }
            mock_notion_client.search = AsyncMock(return_value=mock_response)

            # Act
            result = await notion_wrapper.find_page_by_title(parent_id="parent_123", title="Daily Notes 2025-01-15")

            # Assert
            assert result is None

        @pytest.mark.asyncio
        async def test_find_page_by_title_database_parent(self, notion_wrapper, mock_notion_client):
            """Test finding page with database as parent."""
            # Arrange
            mock_response = {
                "results": [
                    {
                        "object": "page",
                        "id": "database_page_id",
                        "parent": {"database_id": "database_123"},
                        "properties": {"title": {"title": [{"text": {"content": "Database Page"}}]}},
                    }
                ]
            }
            mock_notion_client.search = AsyncMock(return_value=mock_response)

            # Act
            result = await notion_wrapper.find_page_by_title(parent_id="database_123", title="Database Page")

            # Assert
            assert result == "database_page_id"

        @pytest.mark.asyncio
        async def test_find_page_by_title_api_error(self, notion_wrapper, mock_notion_client):
            """Test handling of API errors during page search."""
            # Arrange
            api_error = APIResponseError(
                response=MagicMock(status_code=401), message="Unauthorized", code="unauthorized"
            )
            mock_notion_client.search = AsyncMock(side_effect=api_error)

            # Act & Assert
            with pytest.raises(APIResponseError):
                await notion_wrapper.find_page_by_title(parent_id="parent_123", title="Test Page")

        @pytest.mark.asyncio
        async def test_find_page_by_title_timeout_error(self, notion_wrapper, mock_notion_client):
            """Test handling of timeout errors during page search."""
            # Arrange
            timeout_error = RequestTimeoutError("Search timed out")
            mock_notion_client.search = AsyncMock(side_effect=timeout_error)

            # Act & Assert
            with pytest.raises(RequestTimeoutError):
                await notion_wrapper.find_page_by_title(parent_id="parent_123", title="Test Page")

    class TestAppendContentToPage:
        """Test cases for append_content_to_page method."""

        @pytest.mark.asyncio
        async def test_append_content_success(self, notion_wrapper, mock_notion_client):
            """Test successful content appending."""
            # Arrange
            mock_notion_client.blocks.children.append = AsyncMock()

            # Act
            await notion_wrapper.append_content_to_page(page_id="page_123", content="New content to append")

            # Assert
            mock_notion_client.blocks.children.append.assert_called_once()

            # Verify the call arguments
            call_args = mock_notion_client.blocks.children.append.call_args
            assert call_args.kwargs["block_id"] == "page_123"

            children = call_args.kwargs["children"]
            assert len(children) == 1
            assert children[0]["type"] == "paragraph"
            assert children[0]["paragraph"]["rich_text"][0]["text"]["content"] == "New content to append"

        @pytest.mark.asyncio
        async def test_append_content_api_error(self, notion_wrapper, mock_notion_client):
            """Test handling of API errors during content appending."""
            # Arrange
            api_error = APIResponseError(
                response=MagicMock(status_code=404), message="Page not found", code="object_not_found"
            )
            mock_notion_client.blocks.children.append = AsyncMock(side_effect=api_error)

            # Act & Assert
            with pytest.raises(APIResponseError):
                await notion_wrapper.append_content_to_page(page_id="nonexistent_page", content="Content to append")

        @pytest.mark.asyncio
        async def test_append_content_timeout_error(self, notion_wrapper, mock_notion_client):
            """Test handling of timeout errors during content appending."""
            # Arrange
            timeout_error = RequestTimeoutError("Append operation timed out")
            mock_notion_client.blocks.children.append = AsyncMock(side_effect=timeout_error)

            # Act & Assert
            with pytest.raises(RequestTimeoutError):
                await notion_wrapper.append_content_to_page(page_id="page_123", content="Content to append")

        @pytest.mark.asyncio
        async def test_append_content_unexpected_error(self, notion_wrapper, mock_notion_client):
            """Test handling of unexpected errors during content appending."""
            # Arrange
            unexpected_error = Exception("Network connection failed")
            mock_notion_client.blocks.children.append = AsyncMock(side_effect=unexpected_error)

            # Act & Assert
            with pytest.raises(Exception):
                await notion_wrapper.append_content_to_page(page_id="page_123", content="Content to append")

    class TestInitialization:
        """Test cases for client initialization."""

        def test_initialization_with_token(self):
            """Test proper initialization with token."""
            wrapper = NotionClientWrapper(token="test_token_123")

            assert wrapper.client is not None
            assert wrapper.logger is not None

        @patch("notion.clients.notion_client.AsyncClient")
        def test_client_created_with_correct_auth(self, mock_async_client):
            """Test that AsyncClient is created with correct authentication."""
            NotionClientWrapper(token="secret_token")

            mock_async_client.assert_called_once_with(auth="secret_token")
