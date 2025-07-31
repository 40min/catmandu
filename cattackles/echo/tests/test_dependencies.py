"""
Tests for the dependency injection system.
These tests focus on the factory functions for creating dependencies.
"""

from unittest.mock import patch

from cattackles.echo.src.clients.gemini_client import GeminiClient
from cattackles.echo.src.core.cattackle import EchoCattackle
from cattackles.echo.src.dependencies import create_echo_cattackle, create_gemini_client


class TestDependencies:
    """Test class for dependency injection functionality."""

    def test_create_gemini_client_with_api_key(self, settings_with_gemini):
        """Test creating Gemini client when API key is available."""
        with patch("cattackles.echo.src.dependencies.GeminiClient") as mock_client_class:
            mock_client = mock_client_class.return_value

            result = create_gemini_client(settings_with_gemini)

            assert result == mock_client
            mock_client_class.assert_called_once_with(api_key="test-api-key", model_name="gemini-pro")

    def test_create_gemini_client_without_api_key(self, settings_without_gemini):
        """Test creating Gemini client when API key is not available."""
        result = create_gemini_client(settings_without_gemini)

        assert result is None

    def test_create_echo_cattackle_with_gemini(self, settings_with_gemini):
        """Test creating EchoCattackle with Gemini client."""
        with (
            patch("cattackles.echo.src.dependencies.GeminiClient") as mock_client_class,
            patch("cattackles.echo.src.dependencies.EchoCattackle") as mock_cattackle_class,
        ):

            mock_client = mock_client_class.return_value
            mock_cattackle = mock_cattackle_class.return_value

            result = create_echo_cattackle(settings_with_gemini)

            assert result == mock_cattackle
            mock_client_class.assert_called_once_with(api_key="test-api-key", model_name="gemini-pro")
            mock_cattackle_class.assert_called_once_with(gemini_client=mock_client)

    def test_create_echo_cattackle_without_gemini(self, settings_without_gemini):
        """Test creating EchoCattackle without Gemini client."""
        with patch("cattackles.echo.src.dependencies.EchoCattackle") as mock_cattackle_class:
            mock_cattackle = mock_cattackle_class.return_value

            result = create_echo_cattackle(settings_without_gemini)

            assert result == mock_cattackle
            mock_cattackle_class.assert_called_once_with(gemini_client=None)

    def test_integration_create_echo_cattackle_real_objects(self, settings_with_gemini):
        """Test creating EchoCattackle with real objects (integration test)."""
        with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel"):

            result = create_echo_cattackle(settings_with_gemini)

            assert isinstance(result, EchoCattackle)
            assert isinstance(result.gemini_client, GeminiClient)
            assert result.gemini_client.api_key == "test-api-key"
            assert result.gemini_client.model_name == "gemini-pro"

    def test_integration_create_echo_cattackle_no_gemini(self, settings_without_gemini):
        """Test creating EchoCattackle without Gemini (integration test)."""
        result = create_echo_cattackle(settings_without_gemini)

        assert isinstance(result, EchoCattackle)
        assert result.gemini_client is None
