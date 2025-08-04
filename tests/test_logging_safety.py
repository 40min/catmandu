"""
Tests to verify that logging failures don't interrupt business logic.

These tests demonstrate that the critical logging issues have been resolved.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from catmandu.core.config import Settings
from catmandu.core.cost_tracker import CostTracker
from catmandu.core.services.logging_service import LoggingService


@pytest.fixture
def mock_logging_service():
    """Create mock logging service."""
    mock = Mock()
    mock.log_chat_interaction_safely = Mock()
    return mock


class TestLoggingSafety:
    """Test that logging failures don't interrupt business logic."""

    @pytest.fixture
    def settings(self):
        """Create test settings with minimal configuration."""
        settings = Mock(spec=Settings)
        settings.cost_logs_dir = "test_logs/costs"
        settings.chat_logs_dir = "test_logs/chats"
        settings.whisper_cost_per_minute = 0.006
        settings.gpt4o_mini_input_cost_per_1m_tokens = 0.15
        settings.gpt4o_mini_output_cost_per_1m_tokens = 0.60
        return settings

    @pytest.fixture
    def logging_service(self, settings):
        """Create logging service for testing."""
        with patch("pathlib.Path.mkdir"):  # Prevent actual directory creation
            return LoggingService(settings)

    @pytest.fixture
    def cost_tracker(self, settings):
        """Create cost tracker for testing."""
        with patch("pathlib.Path.mkdir"):  # Prevent actual directory creation
            return CostTracker(settings)

    def test_cost_logging_failure_does_not_raise(self, logging_service):
        """Test that cost logging failures don't raise exceptions."""
        # Invalid cost data that would normally cause logging to fail
        invalid_cost_data = {
            "incomplete": "data",
            # Missing required fields like timestamp, chat_id, etc.
        }

        # This should NOT raise an exception
        try:
            logging_service.log_cost_data_safely(invalid_cost_data)
            # If we reach here, the test passes
            assert True
        except Exception as e:
            pytest.fail(f"Cost logging failure raised exception: {e}")

    def test_chat_logging_failure_does_not_raise(self, logging_service):
        """Test that chat logging failures don't raise exceptions."""
        # Mock file operations to simulate failure
        with patch("builtins.open", side_effect=PermissionError("Cannot write to file")):
            # This should NOT raise an exception
            try:
                logging_service.log_chat_interaction_safely(
                    chat_id=12345, message_type="test", text="Test message", user_info={"user_id": 123}
                )
                # If we reach here, the test passes
                assert True
            except Exception as e:
                pytest.fail(f"Chat logging failure raised exception: {e}")

    def test_safe_log_with_logger_failure(self, logging_service):
        """Test that even logger failures are handled safely."""
        # Mock the logger to raise an exception
        with patch.object(logging_service.logger, "info", side_effect=Exception("Logger failed")):
            # This should NOT raise an exception
            try:
                logging_service._safe_log(logging_service.logger.info, "Test message", test_param="test_value")
                # If we reach here, the test passes
                assert True
            except Exception as e:
                pytest.fail(f"Safe logging raised exception: {e}")

    def test_valid_cost_data_logging_works(self, logging_service):
        """Test that valid cost data is logged successfully."""
        valid_cost_data = {
            "timestamp": datetime.now(),
            "chat_id": 12345,
            "user_info": {"user_id": 123, "username": "testuser"},
            "audio_duration": 1.5,
            "whisper_cost": 0.006,
            "gpt_tokens_input": 100,
            "gpt_tokens_output": 50,
            "gpt_cost": 0.001,
            "total_cost": 0.007,
            "file_size": 1024000,
            "processing_time": 5.2,
            "message_type": "voice",
            "mime_type": "audio/ogg",
            "transcription_language": "en",
        }

        # Mock file operations to avoid actual file I/O in tests
        with patch("builtins.open", create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            # This should work without raising exceptions
            logging_service.log_cost_data_safely(valid_cost_data)

            # Verify that file write was attempted
            mock_file.write.assert_called_once()

    def test_cost_tracker_calculation_methods(self, cost_tracker):
        """Test that CostTracker calculation methods work correctly."""
        # Test Whisper cost calculation
        whisper_cost = cost_tracker.calculate_whisper_cost(2.5)  # 2.5 minutes
        expected_whisper_cost = 2.5 * 0.006  # 0.015
        assert whisper_cost == expected_whisper_cost

        # Test GPT cost calculation
        gpt_cost = cost_tracker.calculate_gpt_cost(1000, 500)  # 1000 input, 500 output tokens
        expected_input_cost = (1000 / 1_000_000) * 0.15  # 0.00015
        expected_output_cost = (500 / 1_000_000) * 0.60  # 0.0003
        expected_total = expected_input_cost + expected_output_cost  # 0.00045
        assert gpt_cost == expected_total

    def test_audio_processing_logging_methods(self, logging_service):
        """Test that all audio processing logging methods are safe."""
        from catmandu.core.models import AudioFileInfo, TranscriptionResult

        # Test all logging methods don't raise exceptions
        try:
            logging_service.log_audio_processing_start(12345, 67890, {"user_id": 123})

            file_info = AudioFileInfo(
                file_id="test_file_id",
                file_unique_id="unique_id",
                duration=60,
                mime_type="audio/ogg",
                file_size=1024000,
            )
            logging_service.log_audio_file_info(file_info, "voice")

            logging_service.log_audio_download_start("test_file_id")
            logging_service.log_audio_download_complete("test_file_id", 2.5, 1024000)

            logging_service.log_transcription_start("test.ogg", 1024000)

            transcription_result = TranscriptionResult(
                text="Test transcription", language="en", confidence=None, processing_time=3.2
            )
            logging_service.log_transcription_complete(transcription_result, 3.2)

            logging_service.log_text_improvement_complete(100, 120, 1.8)
            logging_service.log_audio_processing_complete(12345, 8.5, 1024000, 60, 0.007)

            # If we reach here, all methods are safe
            assert True

        except Exception as e:
            pytest.fail(f"Audio processing logging method raised exception: {e}")


class TestBusinessLogicContinuity:
    """Test that business logic continues even when logging fails."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock()
        settings.cost_logs_dir = "test_logs/costs"
        settings.chat_logs_dir = "test_logs/chats"
        settings.whisper_cost_per_minute = 0.006
        settings.gpt4o_mini_input_cost_per_1m_tokens = 0.15
        settings.gpt4o_mini_output_cost_per_1m_tokens = 0.60
        settings.audio_processing_enabled = True
        settings.max_audio_file_size_mb = 25
        settings.max_audio_duration_minutes = 10
        settings.openai_api_key = "test_key"
        return settings

    def test_audio_processor_uses_safe_logging(self, mock_settings):
        """Test that AudioProcessor uses safe logging methods."""
        from catmandu.core.audio_processor import AudioProcessor
        from catmandu.core.clients.telegram import TelegramClient

        # Mock dependencies
        with patch("pathlib.Path.mkdir"):
            logging_service = LoggingService(mock_settings)
            cost_tracker = CostTracker(mock_settings)
            telegram_client = Mock(spec=TelegramClient)

            # Create AudioProcessor
            audio_processor = AudioProcessor(
                settings=mock_settings,
                telegram_client=telegram_client,
                cost_tracker=cost_tracker,
                logging_service=logging_service,
            )

            # Verify that the audio processor has the logging service
            assert hasattr(audio_processor, "logging_service")
            assert audio_processor.logging_service is logging_service

    def test_message_router_uses_safe_logging(self, mock_settings, mock_logging_service):
        """Test that MessageRouter uses safe logging methods."""
        from catmandu.core.infrastructure.router import MessageRouter

        # Mock dependencies
        with patch("pathlib.Path.mkdir"):
            logging_service = LoggingService(mock_settings)

            # Create MessageRouter with mocked dependencies
            router = MessageRouter(
                mcp_service=Mock(),
                cattackle_registry=Mock(),
                accumulator_manager=Mock(),
                chat_logger=Mock(),
                logging_service=logging_service,
                audio_processor=None,
            )

            # Verify that the router has the logging service
            assert hasattr(router, "_logging_service")
            assert router._logging_service is logging_service

    def test_logging_service_directory_creation_failure_is_safe(self):
        """Test that LoggingService handles directory creation failures safely."""
        settings = Mock()
        settings.cost_logs_dir = "/invalid/path/costs"
        settings.chat_logs_dir = "/invalid/path/chats"

        # This should not raise an exception even if directory creation fails
        try:
            LoggingService(settings)
            # If we reach here, the test passes
            assert True
        except Exception as e:
            pytest.fail(f"LoggingService initialization raised exception: {e}")

    def test_cost_tracker_directory_creation_failure_is_safe(self):
        """Test that CostTracker handles directory creation failures safely."""
        settings = Mock()
        settings.cost_logs_dir = "/invalid/path/costs"
        settings.whisper_cost_per_minute = 0.006
        settings.gpt4o_mini_input_cost_per_1m_tokens = 0.15
        settings.gpt4o_mini_output_cost_per_1m_tokens = 0.60

        # This should not raise an exception even if directory creation fails
        try:
            CostTracker(settings)
            # If we reach here, the test passes
            assert True
        except Exception as e:
            pytest.fail(f"CostTracker initialization raised exception: {e}")


class TestDeprecatedMethodsRemoval:
    """Test that deprecated methods have been properly removed."""

    @pytest.fixture
    def cost_tracker(self):
        """Create cost tracker for testing."""
        settings = Mock()
        settings.cost_logs_dir = "test_logs/costs"
        settings.whisper_cost_per_minute = 0.006
        settings.gpt4o_mini_input_cost_per_1m_tokens = 0.15
        settings.gpt4o_mini_output_cost_per_1m_tokens = 0.60

        with patch("pathlib.Path.mkdir"):
            return CostTracker(settings)

    def test_deprecated_logging_method_removed(self, cost_tracker):
        """Test that the deprecated log_audio_processing_cost method has been removed."""
        # The deprecated method should no longer exist
        assert not hasattr(cost_tracker, "log_audio_processing_cost")
        assert not hasattr(cost_tracker, "_log_cost_data_internal")

    def test_cost_tracker_only_has_calculation_methods(self, cost_tracker):
        """Test that CostTracker now only has calculation and reporting methods."""
        # Check that calculation methods exist
        assert hasattr(cost_tracker, "calculate_whisper_cost")
        assert hasattr(cost_tracker, "calculate_gpt_cost")

        # Check that reporting methods exist
        assert hasattr(cost_tracker, "get_daily_costs")
        assert hasattr(cost_tracker, "get_date_range_costs")
        assert hasattr(cost_tracker, "get_user_breakdown")

        # Check that logging methods don't exist
        assert not hasattr(cost_tracker, "log_audio_processing_cost")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
