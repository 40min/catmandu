"""
Tests for the dependency injection system.
These tests focus on the factory functions for creating dependencies.
"""

from unittest.mock import patch

from echo.clients.gemini_client import GeminiClient
from echo.clients.openai_client import OpenAIClient
from echo.core.cattackle import EchoCattackle
from echo.dependencies import create_echo_cattackle, create_gemini_client, create_openai_client


class TestDependencies:
    """Test class for dependency injection functionality."""

    def test_create_openai_client_with_api_key(self, settings_with_openai_only):
        """Test creating OpenAI client when API key is available."""
        with patch("echo.dependencies.OpenAIClient") as mock_client_class:
            mock_client = mock_client_class.return_value

            result = create_openai_client(settings_with_openai_only)

            assert result == mock_client
            mock_client_class.assert_called_once_with(api_key="test-openai-api-key", model_name="gpt-5-nano")

    def test_create_openai_client_without_api_key(self, settings_with_gemini_only):
        """Test creating OpenAI client when API key is not available."""
        result = create_openai_client(settings_with_gemini_only)

        assert result is None

    def test_create_gemini_client_with_api_key(self, settings_with_gemini_only):
        """Test creating Gemini client when API key is available."""
        with patch("echo.dependencies.GeminiClient") as mock_client_class:
            mock_client = mock_client_class.return_value

            result = create_gemini_client(settings_with_gemini_only)

            assert result == mock_client
            mock_client_class.assert_called_once_with(api_key="test-gemini-api-key", model_name="gemini-pro")

    def test_create_gemini_client_without_api_key(self, settings_with_openai_only):
        """Test creating Gemini client when API key is not available."""
        result = create_gemini_client(settings_with_openai_only)

        assert result is None

    def test_create_echo_cattackle_with_openai_only(self, settings_with_openai_only):
        """Test creating EchoCattackle with only OpenAI client."""
        with (
            patch("echo.dependencies.OpenAIClient") as mock_openai_class,
            patch("echo.dependencies.EchoCattackle") as mock_cattackle_class,
        ):

            mock_openai_client = mock_openai_class.return_value
            mock_cattackle = mock_cattackle_class.return_value

            result = create_echo_cattackle(settings_with_openai_only)

            assert result == mock_cattackle
            mock_openai_class.assert_called_once_with(api_key="test-openai-api-key", model_name="gpt-5-nano")
            mock_cattackle_class.assert_called_once_with(openai_client=mock_openai_client, gemini_client=None)

    def test_create_echo_cattackle_with_gemini_only(self, settings_with_gemini_only):
        """Test creating EchoCattackle with only Gemini client."""
        with (
            patch("echo.dependencies.GeminiClient") as mock_gemini_class,
            patch("echo.dependencies.EchoCattackle") as mock_cattackle_class,
        ):

            mock_gemini_client = mock_gemini_class.return_value
            mock_cattackle = mock_cattackle_class.return_value

            result = create_echo_cattackle(settings_with_gemini_only)

            assert result == mock_cattackle
            mock_gemini_class.assert_called_once_with(api_key="test-gemini-api-key", model_name="gemini-pro")
            mock_cattackle_class.assert_called_once_with(openai_client=None, gemini_client=mock_gemini_client)

    def test_create_echo_cattackle_with_both_clients(self, settings_with_both_apis):
        """Test creating EchoCattackle with both OpenAI and Gemini clients."""
        with (
            patch("echo.dependencies.OpenAIClient") as mock_openai_class,
            patch("echo.dependencies.GeminiClient") as mock_gemini_class,
            patch("echo.dependencies.EchoCattackle") as mock_cattackle_class,
        ):

            mock_openai_client = mock_openai_class.return_value
            mock_gemini_client = mock_gemini_class.return_value
            mock_cattackle = mock_cattackle_class.return_value

            result = create_echo_cattackle(settings_with_both_apis)

            assert result == mock_cattackle
            mock_openai_class.assert_called_once_with(api_key="test-openai-api-key", model_name="gpt-5-nano")
            mock_gemini_class.assert_called_once_with(api_key="test-gemini-api-key", model_name="gemini-pro")
            mock_cattackle_class.assert_called_once_with(
                openai_client=mock_openai_client, gemini_client=mock_gemini_client
            )

    def test_create_echo_cattackle_without_clients(self, settings_without_apis):
        """Test creating EchoCattackle without any AI clients."""
        with patch("echo.dependencies.EchoCattackle") as mock_cattackle_class:
            mock_cattackle = mock_cattackle_class.return_value

            result = create_echo_cattackle(settings_without_apis)

            assert result == mock_cattackle
            mock_cattackle_class.assert_called_once_with(openai_client=None, gemini_client=None)

    def test_integration_create_echo_cattackle_with_openai(self, settings_with_openai_only):
        """Test creating EchoCattackle with real OpenAI client (integration test)."""
        with patch("openai.AsyncOpenAI"):
            result = create_echo_cattackle(settings_with_openai_only)

            assert isinstance(result, EchoCattackle)
            assert isinstance(result.openai_client, OpenAIClient)
            assert result.openai_client.api_key == "test-openai-api-key"
            assert result.openai_client.model_name == "gpt-5-nano"
            assert result.gemini_client is None

    def test_integration_create_echo_cattackle_with_gemini(self, settings_with_gemini_only):
        """Test creating EchoCattackle with real Gemini client (integration test)."""
        with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel"):
            result = create_echo_cattackle(settings_with_gemini_only)

            assert isinstance(result, EchoCattackle)
            assert result.openai_client is None
            assert isinstance(result.gemini_client, GeminiClient)
            assert result.gemini_client.api_key == "test-gemini-api-key"
            assert result.gemini_client.model_name == "gemini-pro"

    def test_integration_create_echo_cattackle_no_clients(self, settings_without_apis):
        """Test creating EchoCattackle without any AI clients (integration test)."""
        result = create_echo_cattackle(settings_without_apis)

        assert isinstance(result, EchoCattackle)
        assert result.openai_client is None
        assert result.gemini_client is None
