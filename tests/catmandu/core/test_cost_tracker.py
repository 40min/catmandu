import json
import tempfile
from pathlib import Path

import pytest

from catmandu.core.config import Settings
from catmandu.core.cost_tracker import CostTracker


@pytest.fixture
def temp_cost_logs_dir():
    """Create a temporary directory for cost logs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def settings(temp_cost_logs_dir):
    """Create test settings with temporary cost logs directory."""
    return Settings(
        telegram_bot_token="test_token",
        cost_logs_dir=temp_cost_logs_dir,
        whisper_cost_per_minute=0.006,
        openai_gpt_nano_input_cost_per_1m_tokens=0.15,
        openai_gpt_nano_output_cost_per_1m_tokens=0.60,
    )


@pytest.fixture
def cost_tracker(settings):
    """Create a CostTracker instance for testing."""
    return CostTracker(settings)


class TestCostTracker:
    """Test cases for the CostTracker class."""

    def test_init_creates_logs_directory(self, settings, temp_cost_logs_dir):
        """Test that CostTracker creates the logs directory on initialization."""
        # Remove the directory to test creation
        Path(temp_cost_logs_dir).rmdir()

        # Initialize cost tracker
        CostTracker(settings)

        # Verify directory was created
        assert Path(temp_cost_logs_dir).exists()
        assert Path(temp_cost_logs_dir).is_dir()

    def test_calculate_whisper_cost(self, cost_tracker):
        """Test Whisper cost calculation."""
        # Test with various durations
        assert cost_tracker.calculate_whisper_cost(1.0) == 0.006
        assert cost_tracker.calculate_whisper_cost(2.5) == 0.015
        assert cost_tracker.calculate_whisper_cost(0.0) == 0.0

        # Test with fractional minutes
        assert cost_tracker.calculate_whisper_cost(0.5) == 0.003

    def test_calculate_gpt_cost(self, cost_tracker):
        """Test OpenAI model cost calculation."""
        # Test with 1M input tokens and 1M output tokens
        cost = cost_tracker.calculate_gpt_cost(1_000_000, 1_000_000)
        expected = 0.15 + 0.60  # input + output cost
        assert cost == expected

        # Test with smaller token counts
        cost = cost_tracker.calculate_gpt_cost(100_000, 50_000)
        expected = (100_000 / 1_000_000) * 0.15 + (50_000 / 1_000_000) * 0.60
        assert cost == expected

        # Test with zero tokens
        assert cost_tracker.calculate_gpt_cost(0, 0) == 0.0

    def test_get_daily_costs_no_data(self, cost_tracker):
        """Test getting daily costs when no data exists."""
        result = cost_tracker.get_daily_costs("2024-01-15")

        expected = {
            "date": "2024-01-15",
            "total_cost": 0.0,
            "whisper_cost": 0.0,
            "gpt_cost": 0.0,
            "total_requests": 0,
            "total_audio_duration": 0.0,
            "total_tokens_input": 0,
            "total_tokens_output": 0,
            "average_processing_time": 0.0,
            "total_file_size": 0,
        }

        assert result == expected

    def test_get_daily_costs_with_data(self, cost_tracker, temp_cost_logs_dir):
        """Test getting daily costs with existing data."""
        # Create test log file with sample data
        log_file = Path(temp_cost_logs_dir) / "costs-2024-01-15.jsonl"

        test_entries = [
            {
                "timestamp": "2024-01-15T10:30:45",
                "chat_id": 12345,
                "user_info": {"username": "user1"},
                "audio_duration_minutes": 2.0,
                "whisper_cost_usd": 0.012,
                "gpt_tokens_input": 100,
                "gpt_tokens_output": 50,
                "gpt_cost_usd": 0.045,
                "total_cost_usd": 0.057,
                "file_size_bytes": 1000000,
                "processing_time_seconds": 3.0,
            },
            {
                "timestamp": "2024-01-15T14:20:30",
                "chat_id": 67890,
                "user_info": {"username": "user2"},
                "audio_duration_minutes": 1.5,
                "whisper_cost_usd": 0.009,
                "gpt_tokens_input": 75,
                "gpt_tokens_output": 25,
                "gpt_cost_usd": 0.026,
                "total_cost_usd": 0.035,
                "file_size_bytes": 750000,
                "processing_time_seconds": 2.5,
            },
        ]

        with open(log_file, "w") as f:
            for entry in test_entries:
                f.write(json.dumps(entry) + "\n")

        # Get daily costs
        result = cost_tracker.get_daily_costs("2024-01-15")

        # Verify aggregated results
        assert result["date"] == "2024-01-15"
        assert result["total_cost"] == 0.092  # 0.057 + 0.035
        assert result["whisper_cost"] == 0.021  # 0.012 + 0.009
        assert result["gpt_cost"] == 0.071  # 0.045 + 0.026
        assert result["total_requests"] == 2
        assert result["total_audio_duration"] == 3.5  # 2.0 + 1.5
        assert result["total_tokens_input"] == 175  # 100 + 75
        assert result["total_tokens_output"] == 75  # 50 + 25
        assert result["average_processing_time"] == 2.75  # (3.0 + 2.5) / 2
        assert result["total_file_size"] == 1750000  # 1000000 + 750000

    def test_get_date_range_costs_no_data(self, cost_tracker):
        """Test getting date range costs when no data exists."""
        result = cost_tracker.get_date_range_costs("2024-01-15", "2024-01-17")

        expected = {
            "start_date": "2024-01-15",
            "end_date": "2024-01-17",
            "days_with_data": 0,
            "total_cost": 0.0,
            "whisper_cost": 0.0,
            "gpt_cost": 0.0,
            "total_requests": 0,
            "total_audio_duration": 0.0,
            "total_tokens_input": 0,
            "total_tokens_output": 0,
            "average_processing_time": 0.0,
            "total_file_size": 0,
        }

        assert result == expected

    def test_get_date_range_costs_invalid_range(self, cost_tracker):
        """Test that invalid date ranges raise an error."""
        with pytest.raises(ValueError, match="Start date must be before or equal to end date"):
            cost_tracker.get_date_range_costs("2024-01-17", "2024-01-15")

    def test_get_date_range_costs_with_data(self, cost_tracker, temp_cost_logs_dir):
        """Test getting date range costs with data across multiple days."""
        # Create test log files for multiple days
        dates_and_data = [
            (
                "2024-01-15",
                {
                    "timestamp": "2024-01-15T10:30:45",
                    "chat_id": 12345,
                    "user_info": {"username": "user1"},
                    "audio_duration_minutes": 2.0,
                    "whisper_cost_usd": 0.012,
                    "gpt_tokens_input": 100,
                    "gpt_tokens_output": 50,
                    "gpt_cost_usd": 0.045,
                    "total_cost_usd": 0.057,
                    "file_size_bytes": 1000000,
                    "processing_time_seconds": 3.0,
                },
            ),
            (
                "2024-01-16",
                {
                    "timestamp": "2024-01-16T14:20:30",
                    "chat_id": 67890,
                    "user_info": {"username": "user2"},
                    "audio_duration_minutes": 1.5,
                    "whisper_cost_usd": 0.009,
                    "gpt_tokens_input": 75,
                    "gpt_tokens_output": 25,
                    "gpt_cost_usd": 0.026,
                    "total_cost_usd": 0.035,
                    "file_size_bytes": 750000,
                    "processing_time_seconds": 2.5,
                },
            ),
        ]

        for date_str, entry in dates_and_data:
            log_file = Path(temp_cost_logs_dir) / f"costs-{date_str}.jsonl"
            with open(log_file, "w") as f:
                f.write(json.dumps(entry) + "\n")

        # Get date range costs
        result = cost_tracker.get_date_range_costs("2024-01-15", "2024-01-17")

        # Verify aggregated results across date range
        assert result["start_date"] == "2024-01-15"
        assert result["end_date"] == "2024-01-17"
        assert result["days_with_data"] == 2
        assert result["total_cost"] == 0.092  # 0.057 + 0.035
        assert result["whisper_cost"] == 0.021  # 0.012 + 0.009
        assert result["gpt_cost"] == 0.071  # 0.045 + 0.026
        assert result["total_requests"] == 2
        assert result["total_audio_duration"] == 3.5  # 2.0 + 1.5
        assert result["total_tokens_input"] == 175  # 100 + 75
        assert result["total_tokens_output"] == 75  # 50 + 25
        assert result["average_processing_time"] == 2.75  # (3.0 + 2.5) / 2
        assert result["total_file_size"] == 1750000  # 1000000 + 750000
