"""
Unit tests for the audio processing core module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from catmandu.core.audio_processor import (
    AudioDownloadError,
    AudioProcessingError,
    AudioProcessor,
    AudioValidationError,
    TranscriptionError,
)
from catmandu.core.config import Settings
from catmandu.core.models import AudioFileInfo, TranscriptionResult


@pytest.fixture
def settings():
    """Create test settings with audio processing enabled."""
    return Settings(
        telegram_bot_token="test_token",
        openai_api_key="sk-test-key",
        audio_processing_enabled=True,
        max_audio_file_size_mb=25,
        max_audio_duration_minutes=10,
        whisper_cost_per_minute=0.006,
        gpt4o_mini_input_cost_per_1m_tokens=0.15,
        gpt4o_mini_output_cost_per_1m_tokens=0.60,
    )


@pytest.fixture
def disabled_settings():
    """Create test settings with audio processing disabled."""
    return Settings(
        telegram_bot_token="test_token",
        audio_processing_enabled=False,
    )


@pytest.fixture
def mock_telegram_client():
    """Create mock Telegram client."""
    client = AsyncMock()
    client.get_file.return_value = {"file_path": "voice/file_123.ogg"}
    client.download_file.return_value = b"fake_audio_data"
    return client


@pytest.fixture
def mock_cost_tracker():
    """Create mock cost tracker."""
    tracker = MagicMock()
    tracker.calculate_whisper_cost.return_value = 0.012
    tracker.calculate_gpt_cost.return_value = 0.003
    return tracker


@pytest.fixture
def audio_processor(settings, mock_telegram_client, mock_cost_tracker):
    """Create audio processor instance."""
    return AudioProcessor(settings, mock_telegram_client, mock_cost_tracker)


@pytest.fixture
def sample_voice_message():
    """Create sample voice message from Telegram."""
    return {
        "message": {
            "message_id": 123,
            "from": {
                "id": 12345,
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User",
            },
            "chat": {"id": 67890, "type": "private"},
            "date": 1234567890,
            "voice": {
                "file_id": "voice_file_123",
                "file_unique_id": "unique_123",
                "duration": 30,
                "mime_type": "audio/ogg",
                "file_size": 50000,
            },
        }
    }


@pytest.fixture
def sample_audio_message():
    """Create sample audio message from Telegram."""
    return {
        "message": {
            "message_id": 124,
            "from": {
                "id": 12345,
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User",
            },
            "chat": {"id": 67890, "type": "private"},
            "date": 1234567890,
            "audio": {
                "file_id": "audio_file_123",
                "file_unique_id": "unique_124",
                "duration": 120,
                "mime_type": "audio/mpeg",
                "file_size": 2000000,
                "title": "Test Audio",
                "performer": "Test Artist",
            },
        }
    }


class TestAudioProcessorInitialization:
    """Test audio processor initialization and configuration."""

    def test_init_with_valid_settings(self, settings, mock_telegram_client, mock_cost_tracker):
        """Test successful initialization with valid settings."""
        processor = AudioProcessor(settings, mock_telegram_client, mock_cost_tracker)
        assert processor.settings == settings
        assert processor.telegram_client == mock_telegram_client
        assert processor.cost_tracker == mock_cost_tracker

    def test_init_with_disabled_audio_processing(self, disabled_settings, mock_telegram_client, mock_cost_tracker):
        """Test initialization with audio processing disabled."""
        processor = AudioProcessor(disabled_settings, mock_telegram_client, mock_cost_tracker)
        assert processor.settings == disabled_settings

    def test_init_without_openai_key_when_enabled(self, mock_telegram_client, mock_cost_tracker):
        """Test initialization succeeds even without OpenAI key (validation happens at Settings level)."""
        settings = Settings(
            telegram_bot_token="test_token",
            audio_processing_enabled=True,
            openai_api_key=None,
        )
        # AudioProcessor should initialize successfully - validation is handled by Settings
        processor = AudioProcessor(settings, mock_telegram_client, mock_cost_tracker)
        assert processor.settings == settings


class TestAudioFileInfoExtraction:
    """Test audio file information extraction from messages."""

    def test_extract_voice_message_info(self, audio_processor, sample_voice_message):
        """Test extracting info from voice message."""
        message = sample_voice_message["message"]
        file_info, message_type = audio_processor._extract_audio_file_info(message)

        assert isinstance(file_info, AudioFileInfo)
        assert file_info.file_id == "voice_file_123"
        assert file_info.file_unique_id == "unique_123"
        assert file_info.duration == 30
        assert file_info.mime_type == "audio/ogg"
        assert file_info.file_size == 50000
        assert message_type == "voice"

    def test_extract_audio_message_info(self, audio_processor, sample_audio_message):
        """Test extracting info from audio message."""
        message = sample_audio_message["message"]
        file_info, message_type = audio_processor._extract_audio_file_info(message)

        assert isinstance(file_info, AudioFileInfo)
        assert file_info.file_id == "audio_file_123"
        assert file_info.duration == 120
        assert file_info.mime_type == "audio/mpeg"
        assert file_info.file_size == 2000000
        assert message_type == "audio"

    def test_extract_video_note_info(self, audio_processor):
        """Test extracting info from video note message."""
        message = {
            "video_note": {
                "file_id": "video_note_123",
                "file_unique_id": "unique_125",
                "duration": 15,
                "file_size": 100000,
            }
        }
        file_info, message_type = audio_processor._extract_audio_file_info(message)

        assert file_info.file_id == "video_note_123"
        assert file_info.duration == 15
        assert message_type == "video_note"

    def test_extract_no_audio_data(self, audio_processor):
        """Test extraction fails when no audio data present."""
        message = {"text": "Hello world"}
        with pytest.raises(AudioValidationError, match="No audio data found"):
            audio_processor._extract_audio_file_info(message)


class TestAudioFileValidation:
    """Test audio file validation logic."""

    def test_validate_valid_file(self, audio_processor):
        """Test validation passes for valid file."""
        file_info = AudioFileInfo(
            file_id="test_123",
            file_unique_id="unique_123",
            duration=300,  # 5 minutes
            mime_type="audio/ogg",
            file_size=10 * 1024 * 1024,  # 10MB
        )
        # Should not raise any exception
        audio_processor._validate_audio_file(file_info)

    def test_validate_file_too_large(self, audio_processor):
        """Test validation fails for oversized file."""
        file_info = AudioFileInfo(
            file_id="test_123",
            file_unique_id="unique_123",
            file_size=30 * 1024 * 1024,  # 30MB (over 25MB limit)
        )
        with pytest.raises(AudioValidationError, match="Audio file too large"):
            audio_processor._validate_audio_file(file_info)

    def test_validate_file_too_long(self, audio_processor):
        """Test validation fails for overly long audio."""
        file_info = AudioFileInfo(
            file_id="test_123",
            file_unique_id="unique_123",
            duration=15 * 60,  # 15 minutes (over 10 minute limit)
        )
        with pytest.raises(AudioValidationError, match="Audio file too long"):
            audio_processor._validate_audio_file(file_info)

    def test_validate_unsupported_format(self, audio_processor):
        """Test validation fails for unsupported format."""
        file_info = AudioFileInfo(
            file_id="test_123",
            file_unique_id="unique_123",
            mime_type="audio/flac",  # Unsupported format
        )
        with pytest.raises(AudioValidationError, match="Unsupported audio format"):
            audio_processor._validate_audio_file(file_info)

    def test_validate_missing_optional_fields(self, audio_processor):
        """Test validation passes when optional fields are missing."""
        file_info = AudioFileInfo(
            file_id="test_123",
            file_unique_id="unique_123",
            # No duration, mime_type, or file_size
        )
        # Should not raise any exception
        audio_processor._validate_audio_file(file_info)


class TestFilenameGeneration:
    """Test filename generation for different message types."""

    def test_voice_message_filename(self, audio_processor):
        """Test filename generation for voice message."""
        file_info = AudioFileInfo(
            file_id="test_123",
            file_unique_id="unique_123",
            mime_type="audio/ogg",
        )
        filename = audio_processor._determine_filename(file_info, "voice")
        assert filename == "voice_message.ogg"

    def test_audio_message_filename(self, audio_processor):
        """Test filename generation for audio message."""
        file_info = AudioFileInfo(
            file_id="test_123",
            file_unique_id="unique_123",
            mime_type="audio/mpeg",
        )
        filename = audio_processor._determine_filename(file_info, "audio")
        assert filename == "audio_file.mp3"

    def test_video_note_filename(self, audio_processor):
        """Test filename generation for video note."""
        file_info = AudioFileInfo(
            file_id="test_123",
            file_unique_id="unique_123",
            mime_type="audio/mp4",
        )
        filename = audio_processor._determine_filename(file_info, "video_note")
        assert filename == "video_note.mp4"

    def test_unknown_mime_type_filename(self, audio_processor):
        """Test filename generation with unknown mime type."""
        file_info = AudioFileInfo(
            file_id="test_123",
            file_unique_id="unique_123",
            mime_type="audio/unknown",
        )
        filename = audio_processor._determine_filename(file_info, "voice")
        assert filename == "voice_message.ogg"  # Falls back to default


class TestAudioDownload:
    """Test audio file download functionality."""

    @pytest.mark.asyncio
    async def test_download_success(self, audio_processor, mock_telegram_client):
        """Test successful audio file download."""
        mock_telegram_client.get_file.return_value = {"file_path": "voice/file_123.ogg"}
        mock_telegram_client.download_file.return_value = b"audio_data_content"

        result = await audio_processor._download_audio_file("test_file_id")

        assert result == b"audio_data_content"
        mock_telegram_client.get_file.assert_called_once_with("test_file_id")
        mock_telegram_client.download_file.assert_called_once_with("voice/file_123.ogg")

    @pytest.mark.asyncio
    async def test_download_get_file_fails(self, audio_processor, mock_telegram_client):
        """Test download fails when get_file returns None."""
        mock_telegram_client.get_file.return_value = None

        with pytest.raises(AudioDownloadError, match="Failed to get file info"):
            await audio_processor._download_audio_file("test_file_id")

    @pytest.mark.asyncio
    async def test_download_no_file_path(self, audio_processor, mock_telegram_client):
        """Test download fails when no file path returned."""
        mock_telegram_client.get_file.return_value = {"file_id": "test_123"}  # No file_path

        with pytest.raises(AudioDownloadError, match="No file path returned"):
            await audio_processor._download_audio_file("test_file_id")

    @pytest.mark.asyncio
    async def test_download_file_fails(self, audio_processor, mock_telegram_client):
        """Test download fails when file download returns None."""
        mock_telegram_client.get_file.return_value = {"file_path": "voice/file_123.ogg"}
        mock_telegram_client.download_file.return_value = None

        with pytest.raises(AudioDownloadError, match="Failed to download file"):
            await audio_processor._download_audio_file("test_file_id")


class TestTranscription:
    """Test audio transcription functionality."""

    @pytest.mark.asyncio
    async def test_transcribe_success(self, audio_processor):
        """Test successful audio transcription."""
        with patch.object(audio_processor, "_get_openai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.transcribe_audio.return_value = {
                "text": "Hello, this is a test transcription.",
                "language": "en",
                "duration": 5.2,
            }
            mock_get_client.return_value = mock_client

            result = await audio_processor._transcribe_audio(b"audio_data", "test.ogg")

            assert isinstance(result, TranscriptionResult)
            assert result.text == "Hello, this is a test transcription."
            assert result.language == "en"
            assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_transcribe_empty_result(self, audio_processor):
        """Test transcription fails with empty result."""
        with patch.object(audio_processor, "_get_openai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.transcribe_audio.return_value = {"text": ""}
            mock_get_client.return_value = mock_client

            with pytest.raises(TranscriptionError, match="Empty transcription result"):
                await audio_processor._transcribe_audio(b"audio_data", "test.ogg")

    @pytest.mark.asyncio
    async def test_transcribe_api_error(self, audio_processor):
        """Test transcription handles API errors."""
        with patch.object(audio_processor, "_get_openai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.transcribe_audio.side_effect = Exception("API Error")
            mock_get_client.return_value = mock_client

            with pytest.raises(TranscriptionError, match="Transcription failed"):
                await audio_processor._transcribe_audio(b"audio_data", "test.ogg")


class TestTextImprovement:
    """Test text improvement functionality."""

    @pytest.mark.asyncio
    async def test_improve_text_success(self, audio_processor):
        """Test successful text improvement."""
        with patch.object(audio_processor, "_get_openai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.improve_text.return_value = {
                "text": "Hello, this is an improved transcription.",
                "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
            }
            mock_get_client.return_value = mock_client

            improved_text, usage = await audio_processor._improve_transcription("hello this is test")

            assert improved_text == "Hello, this is an improved transcription."
            assert usage["prompt_tokens"] == 50
            assert usage["completion_tokens"] == 25

    @pytest.mark.asyncio
    async def test_improve_text_empty_result(self, audio_processor):
        """Test text improvement with empty result falls back to original."""
        with patch.object(audio_processor, "_get_openai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.improve_text.return_value = {"text": "", "usage": {}}
            mock_get_client.return_value = mock_client

            original_text = "hello this is test"
            improved_text, usage = await audio_processor._improve_transcription(original_text)

            assert improved_text == original_text
            assert usage["prompt_tokens"] == 0

    @pytest.mark.asyncio
    async def test_improve_text_api_error(self, audio_processor):
        """Test text improvement handles API errors gracefully."""
        with patch.object(audio_processor, "_get_openai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.improve_text.side_effect = Exception("API Error")
            mock_get_client.return_value = mock_client

            original_text = "hello this is test"
            improved_text, usage = await audio_processor._improve_transcription(original_text)

            # Should fall back to original text
            assert improved_text == original_text
            assert usage["prompt_tokens"] == 0


class TestCostCalculation:
    """Test cost calculation functionality."""

    def test_calculate_costs(self, audio_processor, mock_cost_tracker):
        """Test cost calculation with valid inputs."""
        token_usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

        costs = audio_processor._calculate_costs(120.0, token_usage)  # 2 minutes

        assert costs["audio_duration_minutes"] == 2.0
        assert costs["gpt_tokens_input"] == 100
        assert costs["gpt_tokens_output"] == 50
        assert "whisper_cost" in costs
        assert "gpt_cost" in costs
        assert "total_cost" in costs

        # Verify cost tracker methods were called
        mock_cost_tracker.calculate_whisper_cost.assert_called_once_with(2.0)
        mock_cost_tracker.calculate_gpt_cost.assert_called_once_with(100, 50)


class TestFullAudioProcessing:
    """Test complete audio processing workflow."""

    @pytest.mark.asyncio
    async def test_process_audio_message_disabled(self, disabled_settings, mock_telegram_client, mock_cost_tracker):
        """Test processing fails when audio processing is disabled."""
        processor = AudioProcessor(disabled_settings, mock_telegram_client, mock_cost_tracker)

        with pytest.raises(AudioProcessingError, match="Audio processing is disabled"):
            await processor.process_audio_message({})

    @pytest.mark.asyncio
    async def test_process_audio_message_success(self, audio_processor, sample_voice_message, mock_cost_tracker):
        """Test successful complete audio processing workflow."""
        # Mock all the async methods
        with (
            patch.object(audio_processor, "_download_audio_file") as mock_download,
            patch.object(audio_processor, "_transcribe_audio") as mock_transcribe,
            patch.object(audio_processor, "_improve_transcription") as mock_improve,
        ):

            mock_download.return_value = b"audio_data"
            mock_transcribe.return_value = TranscriptionResult(
                text="Original transcription",
                language="en",
                processing_time=2.5,
            )
            mock_improve.return_value = ("Improved transcription", {"prompt_tokens": 50, "completion_tokens": 25})

            result = await audio_processor.process_audio_message(sample_voice_message)

            assert result == "Improved transcription"
            mock_cost_tracker.log_audio_processing_cost.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_audio_message_validation_error(self, audio_processor):
        """Test processing handles validation errors."""
        # Create message with oversized file
        message = {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 456, "username": "test"},
                "voice": {
                    "file_id": "test_123",
                    "file_unique_id": "unique_123",
                    "file_size": 30 * 1024 * 1024,  # 30MB - over limit
                },
            }
        }

        with pytest.raises(AudioValidationError):
            await audio_processor.process_audio_message(message)


class TestResourceCleanup:
    """Test resource cleanup functionality."""

    @pytest.mark.asyncio
    async def test_close_resources(self, audio_processor):
        """Test resource cleanup closes OpenAI client."""
        # Create a mock OpenAI client
        mock_client = AsyncMock()
        audio_processor._openai_client = mock_client

        await audio_processor.close()

        mock_client.close.assert_called_once()


class TestTranscriptionQualityAssessment:
    """Test transcription quality assessment functionality."""

    def test_assess_good_quality_transcription(self, audio_processor):
        """Test quality assessment for good transcription."""
        original = "Hello, this is a clear and well-transcribed message with good quality."
        improved = "Hello, this is a clear and well-transcribed message with good quality."

        warning_needed = audio_processor._assess_transcription_quality(original, improved)
        assert not warning_needed

    def test_assess_poor_quality_short_text(self, audio_processor):
        """Test quality assessment for very short transcription."""
        original = "uh um"
        improved = "Excuse me."

        warning_needed = audio_processor._assess_transcription_quality(original, improved)
        assert warning_needed

    def test_assess_poor_quality_excessive_repetition(self, audio_processor):
        """Test quality assessment for repetitive transcription."""
        original = "the the the the the same word repeated many times"
        improved = "The same word repeated many times."

        warning_needed = audio_processor._assess_transcription_quality(original, improved)
        assert warning_needed

    def test_assess_poor_quality_many_special_chars(self, audio_processor):
        """Test quality assessment for transcription with many special characters."""
        original = "h3ll0 w0rld @@@ ### $$$ %%% ^^^ &&& *** ((( )))"
        improved = "Hello world, this is much better text."

        warning_needed = audio_processor._assess_transcription_quality(original, improved)
        assert warning_needed

    def test_assess_poor_quality_large_length_difference(self, audio_processor):
        """Test quality assessment for large difference in text length."""
        original = "short"
        improved = (
            "This is a much longer and more detailed transcription that is significantly different from the original."
        )

        warning_needed = audio_processor._assess_transcription_quality(original, improved)
        assert warning_needed

    def test_assess_poor_quality_many_short_words(self, audio_processor):
        """Test quality assessment for many single/short words."""
        original = "a b c d e f g h i j k l m n o p q r s t u v w x y z"
        improved = "This is much better text with proper words."

        warning_needed = audio_processor._assess_transcription_quality(original, improved)
        assert warning_needed

    def test_has_excessive_repetition_word_repetition(self, audio_processor):
        """Test detection of excessive word repetition."""
        text = "hello hello hello hello hello world"
        assert audio_processor._has_excessive_repetition(text)

    def test_has_excessive_repetition_phrase_repetition(self, audio_processor):
        """Test detection of excessive phrase repetition."""
        text = "hello world hello world hello world hello world"
        assert audio_processor._has_excessive_repetition(text)

    def test_has_excessive_repetition_normal_text(self, audio_processor):
        """Test that normal text doesn't trigger repetition detection."""
        text = "This is a normal sentence with varied vocabulary and structure."
        assert not audio_processor._has_excessive_repetition(text)

    def test_has_excessive_repetition_short_text(self, audio_processor):
        """Test that very short text doesn't trigger repetition detection."""
        text = "hello world"
        assert not audio_processor._has_excessive_repetition(text)

    @pytest.mark.asyncio
    async def test_close_no_client(self, audio_processor):
        """Test cleanup when no OpenAI client exists."""
        # Should not raise any exception
        await audio_processor.close()
