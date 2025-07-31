"""
Tests for the GeminiClient.
These tests focus on the Gemini API client functionality.
"""

from unittest.mock import MagicMock, patch

import pytest

from cattackles.echo.src.clients.gemini_client import GeminiClient


class TestGeminiClient:
    """Test class for GeminiClient functionality."""

    def test_initialization_success(self, test_api_key, test_model_name):
        """Test successful client initialization."""
        with (
            patch("google.generativeai.configure") as mock_configure,
            patch("google.generativeai.GenerativeModel") as mock_model_class,
        ):

            mock_model = MagicMock()
            mock_model_class.return_value = mock_model

            client = GeminiClient(api_key=test_api_key, model_name=test_model_name)

            assert client.api_key == test_api_key
            assert client.model_name == test_model_name
            assert client.model == mock_model
            mock_configure.assert_called_once_with(api_key=test_api_key)
            mock_model_class.assert_called_once_with(test_model_name)

    def test_initialization_failure(self, test_api_key, test_model_name):
        """Test client initialization failure."""
        with patch("google.generativeai.configure", side_effect=Exception("API Error")):
            with pytest.raises(RuntimeError, match="Failed to configure Gemini API"):
                GeminiClient(api_key=test_api_key, model_name=test_model_name)

    @pytest.mark.asyncio
    async def test_generate_content_success(self, test_api_key, test_model_name):
        """Test successful content generation."""
        with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel") as mock_model_class:

            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Generated joke content"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            client = GeminiClient(api_key=test_api_key, model_name=test_model_name)
            result = await client.generate_content("Tell me a joke about cats")

            assert result == "Generated joke content"
            mock_model.generate_content.assert_called_once_with("Tell me a joke about cats")

    @pytest.mark.asyncio
    async def test_generate_content_strips_whitespace(self, test_api_key, test_model_name):
        """Test that generated content is stripped of whitespace."""
        with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel") as mock_model_class:

            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "  Generated joke content  \n"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            client = GeminiClient(api_key=test_api_key, model_name=test_model_name)
            result = await client.generate_content("Tell me a joke")

            assert result == "Generated joke content"

    @pytest.mark.asyncio
    async def test_generate_content_no_model(self, test_api_key, test_model_name):
        """Test content generation when model is not configured."""
        with (
            patch("google.generativeai.configure"),
            patch("google.generativeai.GenerativeModel", side_effect=Exception("Config error")),
        ):

            with pytest.raises(RuntimeError):
                GeminiClient(api_key=test_api_key, model_name=test_model_name)

    @pytest.mark.asyncio
    async def test_generate_content_api_error(self, test_api_key, test_model_name):
        """Test content generation when API call fails."""
        with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel") as mock_model_class:

            mock_model = MagicMock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_model_class.return_value = mock_model

            client = GeminiClient(api_key=test_api_key, model_name=test_model_name)

            with pytest.raises(RuntimeError, match="Failed to generate content"):
                await client.generate_content("Tell me a joke")

    def test_default_model_name(self, test_api_key):
        """Test that default model name is used when not specified."""
        with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel") as mock_model_class:

            mock_model_class.return_value = MagicMock()

            client = GeminiClient(api_key=test_api_key)

            assert client.model_name == "gemini-pro"
            mock_model_class.assert_called_once_with("gemini-pro")
