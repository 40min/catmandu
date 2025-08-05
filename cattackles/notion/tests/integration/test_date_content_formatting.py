"""Integration tests for date handling and content formatting."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from notion.core.cattackle import NotionCattackle
from notion.utils.content_utils import format_message_content, sanitize_content
from notion.utils.date_utils import format_date_for_page_title, format_timestamp_for_content


class TestDateContentFormattingIntegration:
    """Integration tests for date and content formatting functionality."""

    @pytest.fixture
    def cattackle(self):
        """Create a NotionCattackle instance for testing."""
        return NotionCattackle()

    @pytest.fixture
    def mock_notion_client(self):
        """Create a mock Notion client."""
        mock_client = AsyncMock()
        mock_client.find_page_by_title.return_value = None  # Force page creation
        mock_client.create_page.return_value = "new_page_id"
        mock_client.append_content_to_page.return_value = None
        return mock_client

    @pytest.fixture
    def sample_user_config(self):
        """Sample user configuration for testing."""
        return {"token": "secret_test_token", "parent_page_id": "test_parent_page_id"}

    @pytest.mark.asyncio
    async def test_end_to_end_date_formatting(self, cattackle, mock_notion_client, sample_user_config):
        """Test that date formatting works end-to-end in the save workflow."""
        username = "testuser"
        message_content = "Test message with special chars: <>&"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):
            # Mock specific date for consistent testing
            test_date = datetime(2024, 3, 15, 10, 30, 45, tzinfo=timezone.utc)
            with patch("notion.utils.date_utils.datetime") as mock_datetime:
                mock_datetime.now.return_value = test_date

                result = await cattackle.save_to_notion(username, message_content)

                # Verify success message includes properly formatted date (user-friendly)
                assert "2024-03-15" in result
                assert result.startswith("✅")

                # Verify page creation was called with full datetime format
                mock_notion_client.create_page.assert_called_once_with(
                    sample_user_config["parent_page_id"], "2024-03-15 10:30:45"
                )

    @pytest.mark.asyncio
    async def test_end_to_end_content_formatting(self, cattackle, mock_notion_client, sample_user_config):
        """Test that content formatting and sanitization works end-to-end."""
        username = "testuser"
        message_content = "Message with HTML entities: &amp; &lt;script&gt;"
        accumulated_params = ["Accumulated", "  ", "params&gt;"]

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):
            mock_notion_client.find_page_by_title.return_value = "existing_page_id"

            await cattackle.save_to_notion(username, message_content, accumulated_params)

            # Verify content was properly formatted and sanitized
            mock_notion_client.append_content_to_page.assert_called_once()
            call_args = mock_notion_client.append_content_to_page.call_args[0]

            page_id = call_args[0]
            formatted_content = call_args[1]

            assert page_id == "existing_page_id"

            # Content should include timestamp, sanitized content, and accumulated params
            assert formatted_content.startswith("[")  # Timestamp format
            assert "] Accumulated params> Message with HTML entities: & <script>" in formatted_content

    @pytest.mark.asyncio
    async def test_content_truncation_integration(self, cattackle, mock_notion_client, sample_user_config):
        """Test that very long content gets truncated properly."""
        username = "testuser"
        # Create content longer than default limit (2000 chars)
        long_message = "This is a very long message. " * 100  # ~3000 chars

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):
            mock_notion_client.find_page_by_title.return_value = "existing_page_id"

            await cattackle.save_to_notion(username, long_message)

            # Verify content was truncated
            mock_notion_client.append_content_to_page.assert_called_once()
            call_args = mock_notion_client.append_content_to_page.call_args[0]
            formatted_content = call_args[1]

            # Should be truncated (including timestamp prefix)
            assert len(formatted_content) <= 2010  # 2000 + some buffer for timestamp
            assert "..." in formatted_content

    @pytest.mark.asyncio
    async def test_timezone_consistency(self, cattackle, mock_notion_client, sample_user_config):
        """Test that timezone handling is consistent across date and timestamp formatting."""
        username = "testuser"
        message_content = "Test message"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):
            # Mock specific UTC time
            test_datetime = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)

            with patch("notion.utils.date_utils.datetime") as mock_datetime:
                mock_datetime.now.return_value = test_datetime

                mock_notion_client.find_page_by_title.return_value = "existing_page_id"

                await cattackle.save_to_notion(username, message_content)

                # Verify both date and timestamp use UTC consistently
                # Page lookup should use full datetime
                mock_notion_client.find_page_by_title.assert_called_once_with(
                    sample_user_config["parent_page_id"], "2024-06-15 14:30:45"
                )

                # Content should include timestamp part
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args[0]
                formatted_content = call_args[1]

                assert "[14:30:45]" in formatted_content

    def test_date_utils_integration(self):
        """Test that date utility functions work together consistently."""
        # Test with specific datetime
        test_datetime = datetime(2024, 12, 25, 23, 59, 59, tzinfo=timezone.utc)

        date_result = format_date_for_page_title(test_datetime)
        timestamp_result = format_timestamp_for_content(test_datetime)

        assert date_result == "2024-12-25 23:59:59"
        assert timestamp_result == "[23:59:59]"

    def test_content_utils_integration(self):
        """Test that content utility functions work together consistently."""
        raw_content = "Message with &amp; HTML entities"
        accumulated_params = ["Param1", "  ", "Param2&lt;"]

        # Test the full formatting pipeline
        formatted_content = format_message_content(raw_content, accumulated_params)

        # Should combine params, sanitize HTML entities, and normalize whitespace
        expected = "Param1 Param2< Message with & HTML entities"
        assert formatted_content == expected

    def test_special_character_handling_integration(self):
        """Test that special characters are handled consistently throughout the pipeline."""
        test_cases = [
            ("Simple message", "Simple message"),
            ("Message with &amp; entities", "Message with & entities"),
            ("Message\twith\ttabs", "Message with tabs"),
            ("Message\n\nwith\nnewlines", "Message with newlines"),
            ("Message   with   spaces", "Message with spaces"),
        ]

        for input_content, expected_output in test_cases:
            result = sanitize_content(input_content)
            assert result == expected_output
