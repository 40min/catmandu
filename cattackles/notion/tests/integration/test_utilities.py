"""Test utilities for integration testing.

This module provides utilities for mocking Notion API responses,
user configurations, and other common test setup needs.
"""

from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from notion.clients.notion_client import NotionClientWrapper
from notion_client.errors import APIResponseError, RequestTimeoutError


class NotionAPIResponseBuilder:
    """Builder for creating mock Notion API responses."""

    @staticmethod
    def create_page_response(page_id: str, title: str, parent_id: str) -> Dict:
        """Create a mock response for page creation."""
        return {
            "id": page_id,
            "object": "page",
            "created_time": "2025-01-15T10:00:00.000Z",
            "last_edited_time": "2025-01-15T10:00:00.000Z",
            "parent": {"page_id": parent_id},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
        }

    @staticmethod
    def search_response_with_pages(pages: List[Dict]) -> Dict:
        """Create a mock search response with multiple pages."""
        return {"object": "list", "results": pages, "next_cursor": None, "has_more": False}

    @staticmethod
    def empty_search_response() -> Dict:
        """Create a mock empty search response."""
        return {"object": "list", "results": [], "next_cursor": None, "has_more": False}

    @staticmethod
    def create_api_error(message: str, status: int, code: Optional[str] = None) -> APIResponseError:
        """Create a mock APIResponseError."""
        from unittest.mock import MagicMock

        # Create a mock response object
        mock_response = MagicMock()
        mock_response.status_code = status

        # Create the error with proper constructor
        error_code = code or "api_error"
        error = APIResponseError(mock_response, message, error_code)
        error.status = status  # Set the status attribute that the code expects
        return error

    @staticmethod
    def create_timeout_error(message: str = "Request timed out") -> RequestTimeoutError:
        """Create a mock RequestTimeoutError."""
        return RequestTimeoutError(message)


class MockNotionClientBuilder:
    """Builder for creating configured mock Notion clients."""

    def __init__(self):
        self.client = MagicMock(spec=NotionClientWrapper)
        self.client.find_page_by_title = AsyncMock()
        self.client.create_page = AsyncMock()
        self.client.append_content_to_page = AsyncMock()

    def with_existing_page(self, parent_id: str, title: str, page_id: str) -> "MockNotionClientBuilder":
        """Configure the client to return an existing page for the given title."""
        self.client.find_page_by_title.return_value = page_id
        return self

    def with_no_existing_page(self, parent_id: str, title: str) -> "MockNotionClientBuilder":
        """Configure the client to return None for page search (page doesn't exist)."""
        self.client.find_page_by_title.return_value = None
        return self

    def with_successful_page_creation(self, page_id: str) -> "MockNotionClientBuilder":
        """Configure the client to successfully create a page."""
        self.client.create_page.return_value = page_id
        return self

    def with_page_creation_error(self, error: Exception) -> "MockNotionClientBuilder":
        """Configure the client to fail page creation."""
        self.client.create_page.side_effect = error
        return self

    def with_successful_content_append(self) -> "MockNotionClientBuilder":
        """Configure the client to successfully append content."""
        self.client.append_content_to_page.return_value = None
        return self

    def with_content_append_error(self, error: Exception) -> "MockNotionClientBuilder":
        """Configure the client to fail content appending."""
        self.client.append_content_to_page.side_effect = error
        return self

    def with_find_page_error(self, error: Exception) -> "MockNotionClientBuilder":
        """Configure the client to fail page searching."""
        self.client.find_page_by_title.side_effect = error
        return self

    def build(self) -> MagicMock:
        """Build and return the configured mock client."""
        return self.client


class UserConfigBuilder:
    """Builder for creating test user configurations."""

    def __init__(self):
        self.configs = {}

    def add_user(self, username: str, token: str, parent_page_id: str) -> "UserConfigBuilder":
        """Add a user configuration."""
        self.configs[username] = {"token": token, "parent_page_id": parent_page_id}
        return self

    def add_test_user(self, username: str = "testuser") -> "UserConfigBuilder":
        """Add a standard test user configuration."""
        return self.add_user(
            username=username, token=f"secret_test_token_{username}", parent_page_id=f"test_parent_page_id_{username}"
        )

    def add_invalid_user(self, username: str, missing_field: str = "token") -> "UserConfigBuilder":
        """Add a user with invalid configuration (missing required field)."""
        config = {"token": f"secret_test_token_{username}", "parent_page_id": f"test_parent_page_id_{username}"}
        # Remove the specified field to make config invalid
        if missing_field in config:
            del config[missing_field]
        self.configs[username] = config
        return self

    def build(self) -> Dict[str, Dict[str, str]]:
        """Build and return the user configuration dictionary."""
        return self.configs


class IntegrationTestScenario:
    """Helper class for setting up common integration test scenarios."""

    @staticmethod
    def new_page_creation_scenario():
        """Set up scenario where a new daily page needs to be created."""
        user_config = UserConfigBuilder().add_test_user("testuser").build()

        notion_client = (
            MockNotionClientBuilder()
            .with_no_existing_page("test_parent_page_id_testuser", "2025-01-15")
            .with_successful_page_creation("new_page_id_123")
            .with_successful_content_append()
            .build()
        )

        return user_config, notion_client

    @staticmethod
    def existing_page_scenario():
        """Set up scenario where daily page already exists."""
        user_config = UserConfigBuilder().add_test_user("testuser").build()

        notion_client = (
            MockNotionClientBuilder()
            .with_existing_page("test_parent_page_id_testuser", "2025-01-15", "existing_page_id_456")
            .with_successful_content_append()
            .build()
        )

        return user_config, notion_client

    @staticmethod
    def unauthorized_user_scenario():
        """Set up scenario with unauthorized user (no configuration)."""
        user_config = {}  # Empty configuration
        notion_client = MockNotionClientBuilder().build()  # Won't be used

        return user_config, notion_client

    @staticmethod
    def api_error_scenario(error_type: str = "auth", status: int = 401):
        """Set up scenario with Notion API errors."""
        user_config = UserConfigBuilder().add_test_user("testuser").build()

        if error_type == "auth":
            error = NotionAPIResponseBuilder.create_api_error("Authentication failed", status)
        elif error_type == "timeout":
            error = NotionAPIResponseBuilder.create_timeout_error()
        elif error_type == "not_found":
            error = NotionAPIResponseBuilder.create_api_error("Object not found", 404, "object_not_found")
        elif error_type == "rate_limit":
            error = NotionAPIResponseBuilder.create_api_error("Rate limit exceeded", 429)
        else:
            error = NotionAPIResponseBuilder.create_api_error("Generic API error", 500)

        notion_client = MockNotionClientBuilder().with_find_page_error(error).build()

        return user_config, notion_client

    @staticmethod
    def multiple_users_scenario():
        """Set up scenario with multiple users having different configurations."""
        user_config = (
            UserConfigBuilder()
            .add_test_user("user1")
            .add_test_user("user2")
            .add_invalid_user("invalid_user", "token")
            .build()
        )

        notion_client = (
            MockNotionClientBuilder()
            .with_existing_page("test_parent_page_id_user1", "2025-01-15", "user1_page_id")
            .with_no_existing_page("test_parent_page_id_user2", "2025-01-15")
            .with_successful_page_creation("user2_new_page_id")
            .with_successful_content_append()
            .build()
        )

        return user_config, notion_client


class MCPTestHelper:
    """Helper for testing MCP-related functionality."""

    @staticmethod
    def create_mcp_arguments(text: str, username: str, accumulated_params: Optional[List[str]] = None) -> Dict:
        """Create MCP tool call arguments."""
        args = {"text": text, "username": username}
        if accumulated_params is not None:
            args["accumulated_params"] = accumulated_params
        return args

    @staticmethod
    def extract_response_data(mcp_result):
        """Extract data from MCP tool call result."""
        import json

        if not mcp_result or len(mcp_result) == 0:
            return None, None

        response_data = json.loads(mcp_result[0].text)
        return response_data.get("data", ""), response_data.get("error", "")

    @staticmethod
    def assert_success_response(mcp_result, expected_message_part: str = "✅"):
        """Assert that MCP result indicates success."""
        data, error = MCPTestHelper.extract_response_data(mcp_result)
        assert expected_message_part in data
        assert error == ""

    @staticmethod
    def assert_error_response(mcp_result, expected_error_part: str = "❌"):
        """Assert that MCP result indicates an error."""
        data, error = MCPTestHelper.extract_response_data(mcp_result)
        # Error messages can be in either data or error field depending on the error type
        has_error = (expected_error_part in data) or (expected_error_part in error)
        assert has_error, f"Expected '{expected_error_part}' in response. Got data='{data}', error='{error}'"

    @staticmethod
    def assert_silent_skip_response(mcp_result):
        """Assert that MCP result indicates a silent skip (empty response)."""
        data, error = MCPTestHelper.extract_response_data(mcp_result)
        assert data == ""
        assert error == ""


class DateTestHelper:
    """Helper for date-related testing."""

    @staticmethod
    def get_today_string() -> str:
        """Get today's date in the format used by the cattackle."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def get_test_date_string() -> str:
        """Get a fixed test date string."""
        return "2025-01-15"

    @staticmethod
    def mock_datetime_now(test_date_str: str = "2025-01-15"):
        """Create a mock for datetime.now() that returns a fixed date."""
        return patch("notion.core.cattackle.datetime")


class ContentTestHelper:
    """Helper for testing content formatting and handling."""

    @staticmethod
    def create_test_content(base_message: str = "Test message") -> str:
        """Create test content with various characteristics."""
        return base_message

    @staticmethod
    def create_unicode_content() -> str:
        """Create test content with Unicode characters."""
        return "Test message with emojis 🎉📝 and unicode: café, naïve, résumé"

    @staticmethod
    def create_long_content(length: int = 1000) -> str:
        """Create test content of specified length."""
        base = "This is a test message. "
        repeat_count = (length // len(base)) + 1
        return (base * repeat_count)[:length]

    @staticmethod
    def create_accumulated_params(count: int = 3) -> List[str]:
        """Create a list of accumulated parameters for testing."""
        return [f"Accumulated message {i+1}" for i in range(count)]

    @staticmethod
    def assert_content_contains_timestamp(content: str):
        """Assert that content contains a timestamp in the expected format."""
        import re

        # Look for timestamp pattern like [HH:MM:SS]
        timestamp_pattern = r"\[\d{2}:\d{2}:\d{2}\]"
        assert re.search(timestamp_pattern, content), f"Content should contain timestamp: {content}"

    @staticmethod
    def assert_content_contains_all_parts(content: str, expected_parts: List[str]):
        """Assert that content contains all expected parts."""
        for part in expected_parts:
            assert part in content, f"Content should contain '{part}': {content}"
