"""Tests for content processing utilities."""

from notion.utils.content_utils import (
    escape_notion_special_characters,
    format_message_content,
    sanitize_content,
    truncate_content,
    validate_content_length,
)


class TestSanitizeContent:
    """Test sanitize_content function."""

    def test_handles_normal_text(self):
        """Test that normal text passes through unchanged."""
        content = "This is a normal message with some text."
        result = sanitize_content(content)

        assert result == content

    def test_decodes_html_entities(self):
        """Test that HTML entities are properly decoded."""
        test_cases = [
            ("&amp;", "&"),
            ("&lt;", "<"),
            ("&gt;", ">"),
            ("&quot;", '"'),
            ("&apos;", "'"),
            ("Hello&nbsp;world", "Hello world"),  # Non-breaking space gets normalized
            ("Hello &amp; goodbye", "Hello & goodbye"),
        ]

        for input_text, expected in test_cases:
            result = sanitize_content(input_text)
            assert result == expected

    def test_removes_control_characters(self):
        """Test that control characters are removed."""
        # Test various control characters
        content_with_controls = "Hello\x00\x01\x08\x0b\x0c\x0e\x1f\x7fWorld"
        result = sanitize_content(content_with_controls)

        assert result == "HelloWorld"

    def test_normalizes_whitespace(self):
        """Test that multiple whitespace characters are normalized."""
        test_cases = [
            ("Hello    world", "Hello world"),
            ("Hello\t\tworld", "Hello world"),
            ("Hello\n\nworld", "Hello world"),
            ("Hello   \t  \n  world", "Hello world"),
            ("  Hello  world  ", "Hello world"),
        ]

        for input_text, expected in test_cases:
            result = sanitize_content(input_text)
            assert result == expected

    def test_handles_empty_content(self):
        """Test handling of empty or whitespace-only content."""
        test_cases = [
            ("", ""),
            ("   ", ""),
            ("\t\n  ", ""),
        ]

        for input_text, expected in test_cases:
            result = sanitize_content(input_text)
            assert result == expected

    def test_handles_non_string_input(self):
        """Test that non-string input is converted to string."""
        test_cases = [
            (123, "123"),
            (None, "None"),
            ([], "[]"),
            ({}, "{}"),
        ]

        for input_value, expected in test_cases:
            result = sanitize_content(input_value)
            assert result == expected


class TestFormatMessageContent:
    """Test format_message_content function."""

    def test_formats_simple_content(self):
        """Test formatting of simple message content."""
        content = "Hello world"
        result = format_message_content(content)

        assert result == "Hello world"

    def test_combines_with_accumulated_params(self):
        """Test combining content with accumulated parameters."""
        content = "world"
        accumulated_params = ["Hello", "beautiful"]

        result = format_message_content(content, accumulated_params)

        assert result == "Hello beautiful world"

    def test_handles_empty_accumulated_params(self):
        """Test handling of empty accumulated parameters."""
        content = "Hello world"
        accumulated_params = []

        result = format_message_content(content, accumulated_params)

        assert result == "Hello world"

    def test_filters_empty_accumulated_params(self):
        """Test that empty/whitespace accumulated parameters are filtered out."""
        content = "world"
        accumulated_params = ["Hello", "", "   ", "beautiful", "\t"]

        result = format_message_content(content, accumulated_params)

        assert result == "Hello beautiful world"

    def test_sanitizes_all_content(self):
        """Test that both main content and accumulated params are sanitized."""
        content = "world&amp;"
        accumulated_params = ["Hello&lt;", "beautiful&gt;"]

        result = format_message_content(content, accumulated_params)

        assert result == "Hello< beautiful> world&"

    def test_handles_none_accumulated_params(self):
        """Test handling when accumulated_params is None."""
        content = "Hello world"

        result = format_message_content(content, None)

        assert result == "Hello world"


class TestEscapeNotionSpecialCharacters:
    """Test escape_notion_special_characters function."""

    def test_escapes_markdown_characters(self):
        """Test that markdown-style characters are escaped."""
        test_cases = [
            ("*bold*", "\\*bold\\*"),
            ("_italic_", "\\_italic\\_"),
            ("`code`", "\\`code\\`"),
            ("~~strikethrough~~", "\\~\\~strikethrough\\~\\~"),
            ("[link](url)", "\\[link\\]\\(url\\)"),
        ]

        for input_text, expected in test_cases:
            result = escape_notion_special_characters(input_text)
            assert result == expected

    def test_escapes_backslashes_first(self):
        """Test that backslashes are escaped first to avoid double escaping."""
        content = "This\\has\\backslashes"
        result = escape_notion_special_characters(content)

        assert result == "This\\\\has\\\\backslashes"

    def test_handles_mixed_special_characters(self):
        """Test handling of mixed special characters."""
        content = "This *has* _many_ `special` [characters]"
        result = escape_notion_special_characters(content)

        expected = "This \\*has\\* \\_many\\_ \\`special\\` \\[characters\\]"
        assert result == expected

    def test_handles_non_string_input(self):
        """Test that non-string input is converted to string."""
        result = escape_notion_special_characters(123)
        assert result == "123"

    def test_handles_normal_text(self):
        """Test that normal text without special characters passes through."""
        content = "This is normal text without special characters"
        result = escape_notion_special_characters(content)

        assert result == content


class TestTruncateContent:
    """Test truncate_content function."""

    def test_does_not_truncate_short_content(self):
        """Test that content shorter than max_length is not truncated."""
        content = "This is a short message"
        result = truncate_content(content, max_length=100)

        assert result == content

    def test_truncates_long_content(self):
        """Test that content longer than max_length is truncated."""
        content = "This is a very long message that should be truncated"
        result = truncate_content(content, max_length=20)

        assert len(result) <= 20
        assert result.endswith("...")

    def test_preserves_word_boundaries(self):
        """Test that truncation preserves word boundaries when possible."""
        content = "This is a message with multiple words"
        result = truncate_content(content, max_length=20)

        # Should not cut in the middle of a word
        assert not result[:-3].endswith(" ")  # Excluding the "..."
        assert result.endswith("...")

    def test_handles_no_spaces(self):
        """Test truncation when there are no spaces before max_length."""
        content = "Verylongwordwithoutspaces"
        result = truncate_content(content, max_length=10)

        assert len(result) == 10
        assert result.endswith("...")

    def test_uses_default_max_length(self):
        """Test that default max_length is used when not specified."""
        # Create content longer than default (2000 chars)
        content = "a" * 2500
        result = truncate_content(content)

        assert len(result) <= 2000
        assert result.endswith("...")

    def test_handles_non_string_input(self):
        """Test that non-string input is converted to string."""
        result = truncate_content(123, max_length=10)
        assert result == "123"

    def test_exact_length_boundary(self):
        """Test behavior when content is exactly at max_length."""
        content = "a" * 20
        result = truncate_content(content, max_length=20)

        assert result == content  # Should not be truncated


class TestValidateContentLength:
    """Test validate_content_length function."""

    def test_validates_short_content(self):
        """Test that content within limits is valid."""
        content = "This is a short message"
        result = validate_content_length(content, max_length=100)

        assert result is True

    def test_rejects_long_content(self):
        """Test that content exceeding limits is invalid."""
        content = "This is a very long message"
        result = validate_content_length(content, max_length=10)

        assert result is False

    def test_handles_exact_length(self):
        """Test that content exactly at max_length is valid."""
        content = "a" * 20
        result = validate_content_length(content, max_length=20)

        assert result is True

    def test_uses_default_max_length(self):
        """Test that default max_length is used when not specified."""
        content = "a" * 1500  # Less than default 2000
        result = validate_content_length(content)

        assert result is True

    def test_handles_non_string_input(self):
        """Test that non-string input is rejected."""
        non_strings = [None, 123, [], {}]

        for value in non_strings:
            result = validate_content_length(value)
            assert result is False
