"""
Audio processing core module for handling voice messages and audio files.

This module provides the core functionality for processing audio messages from Telegram,
including validation, transcription, and text improvement workflows.
"""

import time
from datetime import datetime
from typing import Dict, Optional, Tuple

import structlog

from catmandu.core.clients.openai_client import OpenAIClient
from catmandu.core.clients.telegram import TelegramClient
from catmandu.core.config import Settings
from catmandu.core.cost_tracker import CostTracker
from catmandu.core.models import AudioFileInfo, TranscriptionResult
from catmandu.core.services.logging_service import LoggingService

logger = structlog.get_logger(__name__)


class AudioProcessingError(Exception):
    """Base exception for audio processing errors."""

    pass


class AudioDownloadError(AudioProcessingError):
    """Error downloading audio file from Telegram."""

    pass


class AudioValidationError(AudioProcessingError):
    """Error validating audio file properties."""

    pass


class TranscriptionError(AudioProcessingError):
    """Error during audio transcription."""

    pass


class TextImprovementError(AudioProcessingError):
    """Error during text improvement."""

    pass


class AudioProcessor:
    """Core audio processing module for handling voice messages and audio files."""

    # Supported audio formats for Whisper API
    SUPPORTED_FORMATS = {
        "audio/ogg",
        "audio/mpeg",
        "audio/mp4",
        "audio/wav",
        "audio/webm",
        "audio/m4a",
        "audio/x-m4a",
        "audio/mp3",
    }

    # File extensions mapping for format detection
    FORMAT_EXTENSIONS = {
        "ogg": "audio/ogg",
        "mp3": "audio/mpeg",
        "mp4": "audio/mp4",
        "wav": "audio/wav",
        "webm": "audio/webm",
        "m4a": "audio/m4a",
    }

    def __init__(
        self,
        settings: Settings,
        telegram_client: TelegramClient,
        cost_tracker: CostTracker,
        logging_service: LoggingService,
    ):
        """Initialize the audio processor with required dependencies.

        Args:
            settings: Application settings containing audio processing configuration
            telegram_client: Telegram client for file operations
            cost_tracker: Cost tracking service for calculating expenses
            logging_service: Centralized logging service for safe logging operations
        """
        self.settings = settings
        self.telegram_client = telegram_client
        self.cost_tracker = cost_tracker
        self.logging_service = logging_service
        self._openai_client: Optional[OpenAIClient] = None

        logger.info(
            "Audio processor initialized",
            max_file_size_mb=self.settings.max_audio_file_size_mb,
            max_duration_minutes=self.settings.max_audio_duration_minutes,
        )

    async def _get_openai_client(self) -> OpenAIClient:
        """Get or create OpenAI client instance."""
        if self._openai_client is None:
            if not self.settings.openai_api_key:
                raise AudioProcessingError("OpenAI API key not configured")
            self._openai_client = OpenAIClient(self.settings.openai_api_key)
        return self._openai_client

    def _extract_audio_file_info(self, message: Dict) -> Tuple[AudioFileInfo, str]:
        """Extract audio file information from Telegram message.

        Args:
            message: Telegram message containing audio data

        Returns:
            Tuple of (AudioFileInfo, message_type)

        Raises:
            AudioValidationError: If no audio data found or invalid format
        """
        audio_data = None
        message_type = None

        # Check for different audio message types
        if "voice" in message:
            audio_data = message["voice"]
            message_type = "voice"
        elif "audio" in message:
            audio_data = message["audio"]
            message_type = "audio"
        elif "video_note" in message:
            audio_data = message["video_note"]
            message_type = "video_note"

        if not audio_data:
            raise AudioValidationError("No audio data found in message")

        # Extract file information
        file_info = AudioFileInfo(
            file_id=audio_data["file_id"],
            file_unique_id=audio_data["file_unique_id"],
            duration=audio_data.get("duration"),
            mime_type=audio_data.get("mime_type"),
            file_size=audio_data.get("file_size"),
        )

        # Log audio file info extraction
        self.logging_service.log_audio_file_info(file_info, message_type)

        return file_info, message_type

    def _validate_audio_file(self, file_info: AudioFileInfo) -> None:
        """Validate audio file against configured limits.

        Args:
            file_info: Audio file information to validate

        Raises:
            AudioValidationError: If file doesn't meet validation criteria
        """
        # Check file size limit
        if file_info.file_size:
            max_size_bytes = self.settings.max_audio_file_size_mb * 1024 * 1024
            if file_info.file_size > max_size_bytes:
                raise AudioValidationError(
                    f"Audio file too large: {file_info.file_size / (1024 * 1024):.1f}MB "
                    f"(max: {self.settings.max_audio_file_size_mb}MB)"
                )

        # Check duration limit
        if file_info.duration:
            max_duration_seconds = self.settings.max_audio_duration_minutes * 60
            if file_info.duration > max_duration_seconds:
                raise AudioValidationError(
                    f"Audio file too long: {file_info.duration / 60:.1f} minutes "
                    f"(max: {self.settings.max_audio_duration_minutes} minutes)"
                )

        # Check format support
        if file_info.mime_type and file_info.mime_type not in self.SUPPORTED_FORMATS:
            raise AudioValidationError(f"Unsupported audio format: {file_info.mime_type}")

        logger.debug("Audio file validation passed", file_id=file_info.file_id)

    def _determine_filename(self, file_info: AudioFileInfo, message_type: str) -> str:
        """Determine appropriate filename for audio file.

        Args:
            file_info: Audio file information
            message_type: Type of message (voice, audio, video_note)

        Returns:
            Filename with appropriate extension
        """
        # Try to determine extension from mime type
        extension = "ogg"  # Default for voice messages
        if file_info.mime_type:
            for ext, mime in self.FORMAT_EXTENSIONS.items():
                if file_info.mime_type == mime:
                    extension = ext
                    break

        # Use message type to determine base filename
        if message_type == "voice":
            return f"voice_message.{extension}"
        elif message_type == "video_note":
            return f"video_note.{extension}"
        else:
            return f"audio_file.{extension}"

    async def _download_audio_file(self, file_id: str) -> bytes:
        """Download audio file from Telegram servers.

        Args:
            file_id: Telegram file ID

        Returns:
            Audio file content as bytes

        Raises:
            AudioDownloadError: If download fails
        """
        download_start_time = time.time()

        try:
            self.logging_service.log_audio_download_start(file_id)

            # Get file information from Telegram
            file_info = await self.telegram_client.get_file(file_id)
            if not file_info:
                logger.error("Failed to get file info from Telegram API", file_id=file_id)
                raise AudioDownloadError(f"Failed to get file info for file_id: {file_id}")

            file_path = file_info.get("file_path")
            if not file_path:
                logger.error("No file path in Telegram API response", file_id=file_id)
                raise AudioDownloadError(f"No file path returned for file_id: {file_id}")

            # Download file content
            audio_data = await self.telegram_client.download_file(file_path)
            if not audio_data:
                logger.error("Download returned empty data", file_id=file_id, file_path=file_path)
                raise AudioDownloadError(f"Failed to download file: {file_path}")

            download_time = time.time() - download_start_time
            self.logging_service.log_audio_download_complete(file_id, download_time, len(audio_data))

            return audio_data

        except Exception as e:
            download_time = time.time() - download_start_time
            logger.error(
                "Audio file download failed",
                file_id=file_id,
                error=str(e),
                error_type=type(e).__name__,
                download_time_seconds=round(download_time, 2),
                exc_info=True,
            )
            if isinstance(e, AudioDownloadError):
                raise
            raise AudioDownloadError(f"Unexpected error downloading file: {str(e)}")

    async def _transcribe_audio(self, audio_data: bytes, filename: str) -> TranscriptionResult:
        """Transcribe audio using OpenAI Whisper API.

        Args:
            audio_data: Audio file content as bytes
            filename: Filename for format detection

        Returns:
            TranscriptionResult with text and metadata

        Raises:
            TranscriptionError: If transcription fails
        """
        transcription_start_time = time.time()

        try:
            self.logging_service.log_transcription_start(filename, len(audio_data))

            openai_client = await self._get_openai_client()

            # Call Whisper API
            response = await openai_client.transcribe_audio(audio_data, filename)
            processing_time = time.time() - transcription_start_time

            # Extract transcription result
            text = response.get("text", "").strip()
            if not text:
                logger.error("Empty transcription result from Whisper API", filename=filename)
                raise TranscriptionError("Empty transcription result")

            result = TranscriptionResult(
                text=text,
                language=response.get("language"),
                confidence=None,  # Whisper doesn't provide confidence scores
                processing_time=processing_time,
            )

            self.logging_service.log_transcription_complete(result, processing_time)
            return result

        except Exception as e:
            processing_time = time.time() - transcription_start_time
            logger.error(
                "Audio transcription failed",
                filename=filename,
                audio_size_bytes=len(audio_data),
                audio_size_mb=round(len(audio_data) / (1024 * 1024), 2),
                transcription_time_seconds=round(processing_time, 2),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            if isinstance(e, TranscriptionError):
                raise
            raise TranscriptionError(f"Transcription failed: {str(e)}")

    async def _improve_transcription(self, text: str) -> Tuple[str, Dict]:
        """Improve transcription quality using GPT-4o-mini.

        Args:
            text: Original transcribed text

        Returns:
            Tuple of (improved_text, usage_info)

        Raises:
            TextImprovementError: If text improvement fails
        """
        improvement_start_time = time.time()

        try:
            openai_client = await self._get_openai_client()

            # Call GPT-4o-mini for text improvement
            response = await openai_client.improve_text(text)
            improvement_time = time.time() - improvement_start_time

            improved_text = response.get("text", "").strip()
            usage_info = response.get("usage", {})

            if not improved_text:
                # Fallback to original text if improvement fails
                logger.warning("Text improvement returned empty result, using original text")
                improved_text = text
                usage_info = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

            self.logging_service.log_text_improvement_complete(len(text), len(improved_text), improvement_time)
            return improved_text, usage_info

        except Exception as e:
            improvement_time = time.time() - improvement_start_time
            logger.error("Text improvement failed", error=str(e), error_type=type(e).__name__)
            # Return original text as fallback
            logger.info("Using original transcription due to improvement failure")
            return text, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _calculate_costs(self, audio_duration: float, token_usage: Dict) -> Dict:
        """Calculate processing costs for audio transcription and text improvement.

        Args:
            audio_duration: Audio duration in seconds
            token_usage: Token usage information from GPT API

        Returns:
            Dictionary with cost breakdown
        """
        # Convert duration to minutes for Whisper cost calculation
        duration_minutes = audio_duration / 60.0

        # Calculate individual costs
        whisper_cost = self.cost_tracker.calculate_whisper_cost(duration_minutes)
        gpt_cost = self.cost_tracker.calculate_gpt_cost(
            token_usage.get("prompt_tokens", 0), token_usage.get("completion_tokens", 0)
        )

        total_cost = whisper_cost + gpt_cost

        return {
            "whisper_cost": whisper_cost,
            "gpt_cost": gpt_cost,
            "total_cost": total_cost,
            "audio_duration_minutes": duration_minutes,
            "gpt_tokens_input": token_usage.get("prompt_tokens", 0),
            "gpt_tokens_output": token_usage.get("completion_tokens", 0),
        }

    def _assess_transcription_quality(self, original_text: str, improved_text: str) -> bool:
        """Assess transcription quality and determine if warning is needed.

        Args:
            original_text: Original transcription from Whisper
            improved_text: Improved text from GPT-4o-mini

        Returns:
            True if quality warning should be shown to user
        """
        # Check for indicators of poor transcription quality
        quality_indicators = [
            # Very short transcriptions might indicate poor audio
            len(original_text.strip()) < 10,
            # High ratio of non-alphabetic characters (excluding spaces and punctuation)
            sum(1 for c in original_text if not (c.isalnum() or c.isspace() or c in ".,!?;:-'\""))
            / max(len(original_text), 1)
            > 0.2,
            # Excessive repetition of words or phrases
            self._has_excessive_repetition(original_text),
            # Large difference between original and improved text length
            abs(len(improved_text) - len(original_text)) / max(len(original_text), 1) > 1.5,
            # Contains many single characters or very short words
            len([word for word in original_text.split() if len(word) <= 2]) / max(len(original_text.split()), 1) > 0.4,
        ]

        # Return warning if any significant quality indicator is present
        return sum(quality_indicators) >= 1

    def _has_excessive_repetition(self, text: str) -> bool:
        """Check if text has excessive repetition of words or phrases.

        Args:
            text: Text to analyze

        Returns:
            True if excessive repetition is detected
        """
        words = text.lower().split()
        if len(words) < 5:
            return False

        # Check for repeated words
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        # If any word appears more than 30% of the time, it's likely repetitive
        max_word_frequency = max(word_counts.values()) / len(words)
        if max_word_frequency > 0.3:
            return True

        # Check for repeated phrases (2-3 words)
        for phrase_length in [2, 3]:
            phrases = []
            for i in range(len(words) - phrase_length + 1):
                phrase = " ".join(words[i : i + phrase_length])
                phrases.append(phrase)

            if phrases:
                phrase_counts = {}
                for phrase in phrases:
                    phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1

                max_phrase_frequency = max(phrase_counts.values()) / len(phrases)
                if max_phrase_frequency > 0.4:
                    return True

        return False

    async def process_audio_message(self, update: Dict) -> Optional[str]:
        """Process audio message and return transcribed text.

        This is the main entry point for audio processing. It handles the complete
        workflow from validation to transcription and text improvement.

        Args:
            update: Telegram update containing audio message

        Returns:
            Processed text ready for routing, or None if processing fails

        Raises:
            AudioProcessingError: For various audio processing failures
        """
        if not self.settings.audio_processing_enabled:
            raise AudioProcessingError("Audio processing is disabled")

        start_time = time.time()
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        user_info = {
            "user_id": message.get("from", {}).get("id"),
            "username": message.get("from", {}).get("username"),
            "first_name": message.get("from", {}).get("first_name"),
            "last_name": message.get("from", {}).get("last_name"),
        }

        # Log audio processing start
        self.logging_service.log_audio_processing_start(chat_id, message_id, user_info)

        try:
            # Extract and validate audio file information
            file_info, message_type = self._extract_audio_file_info(message)
            self._validate_audio_file(file_info)

            # Download audio file
            filename = self._determine_filename(file_info, message_type)
            audio_data = await self._download_audio_file(file_info.file_id)

            # Transcribe audio
            transcription_result = await self._transcribe_audio(audio_data, filename)

            # Improve transcription quality
            improved_text, token_usage = await self._improve_transcription(transcription_result.text)

            # Calculate and log costs
            processing_time = time.time() - start_time
            audio_duration = file_info.duration or 0
            costs = self._calculate_costs(audio_duration, token_usage)

            # Enhanced cost data with additional metadata
            cost_data = {
                "timestamp": datetime.now(),
                "chat_id": chat_id,
                "message_id": message_id,
                "user_info": user_info,
                "audio_duration": costs["audio_duration_minutes"],
                "whisper_cost": costs["whisper_cost"],
                "gpt_tokens_input": costs["gpt_tokens_input"],
                "gpt_tokens_output": costs["gpt_tokens_output"],
                "gpt_cost": costs["gpt_cost"],
                "total_cost": costs["total_cost"],
                "file_size": file_info.file_size or len(audio_data),
                "processing_time": processing_time,
                "message_type": message_type,
                "mime_type": file_info.mime_type,
                "transcription_language": transcription_result.language,
                "original_text_length": len(transcription_result.text),
                "improved_text_length": len(improved_text),
                "transcription_time": transcription_result.processing_time,
            }

            # CRITICAL: Use safe logging to prevent business logic interruption
            self.logging_service.log_cost_data_safely(cost_data)

            # Log processing completion
            self.logging_service.log_audio_processing_complete(
                chat_id,
                processing_time,
                file_info.file_size or len(audio_data),
                file_info.duration,
                costs["total_cost"],
            )

            # Check for potentially low-quality transcriptions
            quality_warning = self._assess_transcription_quality(transcription_result.text, improved_text)

            # Add quality warning to cost data for logging
            cost_data["quality_warning"] = quality_warning

            # Add quality warning to response if needed
            final_text = improved_text
            if quality_warning:
                final_text = f"{improved_text}\n\n⚠️ Note: The audio quality may have affected transcription accuracy."

            return final_text

        except Exception as e:
            processing_time = time.time() - start_time
            self.logging_service.log_audio_processing_error(chat_id, e, processing_time)
            raise

    async def close(self):
        """Close resources and cleanup."""
        if self._openai_client:
            await self._openai_client.close()
            logger.debug("Audio processor resources closed")
