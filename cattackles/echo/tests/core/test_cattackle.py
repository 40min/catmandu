"""
Tests for the core EchoCattackle functionality.
These tests focus on the business logic without external dependencies.
"""

import json

import pytest


class TestEchoCattackle:
    """Test class for core EchoCattackle functionality."""

    # Echo command tests
    @pytest.mark.asyncio
    async def test_echo_with_immediate_text(self, cattackle_without_gemini, sample_text):
        """Test echo command with immediate text parameter."""
        result = await cattackle_without_gemini.echo(sample_text)
        parsed = json.loads(result)

        assert parsed["data"] == sample_text
        assert parsed["error"] is None

    @pytest.mark.asyncio
    async def test_echo_with_accumulated_params(self, cattackle_without_gemini, sample_accumulated_params):
        """Test echo command with accumulated parameters."""
        result = await cattackle_without_gemini.echo("", sample_accumulated_params)
        parsed = json.loads(result)

        assert parsed["data"] == "param1; param2; param3"
        assert parsed["error"] is None

    @pytest.mark.asyncio
    async def test_echo_prefers_accumulated_over_immediate(self, cattackle_without_gemini):
        """Test that echo prefers accumulated parameters over immediate text."""
        result = await cattackle_without_gemini.echo("immediate", ["accumulated"])
        parsed = json.loads(result)

        assert parsed["data"] == "accumulated"
        assert parsed["error"] is None

    @pytest.mark.asyncio
    async def test_echo_empty_input(self, cattackle_without_gemini):
        """Test echo command with no input."""
        result = await cattackle_without_gemini.echo("")
        parsed = json.loads(result)

        assert "Please provide some text to echo" in parsed["data"]
        assert parsed["error"] is None

    @pytest.mark.asyncio
    async def test_echo_whitespace_input(self, cattackle_without_gemini):
        """Test echo command with whitespace-only input."""
        result = await cattackle_without_gemini.echo("   ")
        parsed = json.loads(result)

        assert "Please provide some text to echo" in parsed["data"]
        assert parsed["error"] is None

    # Ping command tests
    @pytest.mark.asyncio
    async def test_ping_no_params(self, cattackle_without_gemini):
        """Test ping command with no parameters."""
        result = await cattackle_without_gemini.ping("")
        parsed = json.loads(result)

        assert parsed["data"] == "pong"
        assert parsed["error"] is None

    @pytest.mark.asyncio
    async def test_ping_with_immediate_param(self, cattackle_without_gemini):
        """Test ping command with immediate parameter."""
        result = await cattackle_without_gemini.ping("test")
        parsed = json.loads(result)

        assert parsed["data"] == "pong (received immediate param: 'test')"
        assert parsed["error"] is None

    @pytest.mark.asyncio
    async def test_ping_with_accumulated_params(self, cattackle_without_gemini):
        """Test ping command with accumulated parameters."""
        result = await cattackle_without_gemini.ping("", ["param1", "param2"])
        parsed = json.loads(result)

        assert parsed["data"] == "pong (received 2 accumulated params)"
        assert parsed["error"] is None

    # Joke command tests
    @pytest.mark.asyncio
    async def test_joke_without_gemini_client(self, cattackle_without_gemini, sample_joke_topic):
        """Test joke command without Gemini client configured."""
        result = await cattackle_without_gemini.joke(sample_joke_topic)
        parsed = json.loads(result)

        assert parsed["data"] == ""
        assert "Gemini model not configured" in parsed["error"]

    @pytest.mark.asyncio
    async def test_joke_with_immediate_text(self, cattackle_with_gemini, sample_joke_topic):
        """Test joke command with immediate text."""
        result = await cattackle_with_gemini.joke(sample_joke_topic)
        parsed = json.loads(result)

        assert parsed["error"] is None
        assert len(parsed["data"]) > 0

    @pytest.mark.asyncio
    async def test_joke_with_accumulated_params(self, cattackle_with_gemini):
        """Test joke command with accumulated parameters."""
        result = await cattackle_with_gemini.joke("", ["cats", "dogs"])
        parsed = json.loads(result)

        assert parsed["error"] is None
        assert len(parsed["data"]) > 0

    @pytest.mark.asyncio
    async def test_joke_prefers_accumulated_over_immediate(self, cattackle_with_gemini):
        """Test that joke prefers accumulated parameters over immediate text."""
        result = await cattackle_with_gemini.joke("immediate", ["accumulated"])
        parsed = json.loads(result)

        assert parsed["error"] is None
        assert len(parsed["data"]) > 0

    @pytest.mark.asyncio
    async def test_joke_empty_input(self, cattackle_with_gemini):
        """Test joke command with no input."""
        result = await cattackle_with_gemini.joke("")
        parsed = json.loads(result)

        assert parsed["data"] == ""
        assert "Please provide some text to create a joke about" in parsed["error"]

    @pytest.mark.asyncio
    async def test_joke_whitespace_input(self, cattackle_with_gemini):
        """Test joke command with whitespace-only input."""
        result = await cattackle_with_gemini.joke("   ")
        parsed = json.loads(result)

        assert parsed["data"] == ""
        assert "Please provide some text to create a joke about" in parsed["error"]

    @pytest.mark.asyncio
    async def test_joke_generation_error(self, cattackle_with_gemini):
        """Test joke command when Gemini client raises an error."""
        from unittest.mock import AsyncMock

        # Make the mock client raise an exception
        cattackle_with_gemini.gemini_client.generate_content = AsyncMock(side_effect=Exception("API Error"))

        result = await cattackle_with_gemini.joke("cats")
        parsed = json.loads(result)

        assert parsed["data"] == ""
        assert "Failed to generate joke" in parsed["error"]
