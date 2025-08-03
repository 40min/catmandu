"""
Centralized logging service for handling complex logging operations.

This service separates logging concerns from business logic, providing
safe logging operations that never interrupt core functionality.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import structlog

from catmandu.core.config import Settings
from catmandu.core.models import AudioFileInfo, TranscriptionResult


class LoggingService:
    """Centralized service for handling all complex logging operations safely."""

    def __init__(self, settings: Settings):
        """Initialize the logging service.

        Args:
            settings: Application settings containing logging configuration
        """
        self.settings = settings
        self.logger = structlog.get_logger(__name__)
        self.cost_logs_dir = Path(settings.cost_logs_dir)
        self.chat_logs_dir = Path(settings.chat_logs_dir)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure logging directories exist."""
        try:
            self.cost_logs_dir.mkdir(parents=True, exist_ok=True)
            self.chat_logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.warning("Failed to create logging directories", error=str(e))

    def _safe_log(self, log_func, message: str, **kwargs) -> None:
        """Safely execute a logging operation without raising exceptions.

        Args:
            log_func: Logger function to call (e.g., logger.info)
            message: Log message
            **kwargs: Additional log context
        """
        try:
            log_func(message, **kwargs)
        except Exception as e:
            # Use basic print as fallback if structured logging fails
            print(f"Logging failed: {e} - Original message: {message}")

    def log_audio_processing_start(self, chat_id: int, message_id: Optional[int], user_info: Dict) -> None:
        """Log the start of audio processing."""
        self._safe_log(
            self.logger.info,
            "Audio processing started",
            chat_id=chat_id,
            message_id=message_id,
            user_id=user_info.get("user_id"),
            username=user_info.get("username"),
        )

    def log_audio_file_info(self, file_info: AudioFileInfo, message_type: str) -> None:
        """Log audio file information extraction."""
        self._safe_log(
            self.logger.info,
            "Audio file info extracted",
            file_id=file_info.file_id,
            duration_minutes=round(file_info.duration / 60, 2) if file_info.duration else None,
            file_size_mb=round(file_info.file_size / (1024 * 1024), 2) if file_info.file_size else None,
            mime_type=file_info.mime_type,
            message_type=message_type,
        )

    def log_audio_download_start(self, file_id: str) -> None:
        """Log start of audio download."""
        self._safe_log(self.logger.info, "Audio download started", file_id=file_id)

    def log_audio_download_complete(self, file_id: str, download_time: float, file_size: int) -> None:
        """Log completion of audio download."""
        self._safe_log(
            self.logger.info,
            "Audio download completed",
            file_id=file_id,
            download_time_seconds=round(download_time, 2),
            file_size_mb=round(file_size / (1024 * 1024), 2),
        )

    def log_transcription_start(self, filename: str, audio_size: int) -> None:
        """Log start of audio transcription."""
        self._safe_log(
            self.logger.info,
            "Transcription started",
            filename=filename,
            audio_size_mb=round(audio_size / (1024 * 1024), 2),
        )

    def log_transcription_complete(self, result: TranscriptionResult, processing_time: float) -> None:
        """Log completion of audio transcription."""
        self._safe_log(
            self.logger.info,
            "Transcription completed",
            language=result.language,
            text_length=len(result.text),
            processing_time_seconds=round(processing_time, 2),
        )

    def log_text_improvement_complete(self, original_length: int, improved_length: int, processing_time: float) -> None:
        """Log completion of text improvement."""
        self._safe_log(
            self.logger.info,
            "Text improvement completed",
            original_length=original_length,
            improved_length=improved_length,
            processing_time_seconds=round(processing_time, 2),
        )

    def log_audio_processing_complete(
        self,
        chat_id: int,
        processing_time: float,
        file_size: int,
        duration: Optional[float],
        total_cost: float,
    ) -> None:
        """Log completion of entire audio processing workflow."""
        self._safe_log(
            self.logger.info,
            "Audio processing completed",
            chat_id=chat_id,
            processing_time_seconds=round(processing_time, 2),
            file_size_mb=round(file_size / (1024 * 1024), 2),
            duration_minutes=round(duration / 60, 2) if duration else None,
            total_cost_usd=total_cost,
        )

    def log_audio_processing_error(self, chat_id: int, error: Exception, processing_time: float) -> None:
        """Log audio processing errors."""
        self._safe_log(
            self.logger.error,
            "Audio processing failed",
            chat_id=chat_id,
            error=str(error),
            error_type=type(error).__name__,
            processing_time_seconds=round(processing_time, 2),
        )

    def log_cost_data_safely(self, cost_data: Dict) -> None:
        """Safely log cost data without interrupting business logic.

        This method ensures that cost logging failures never break audio processing.

        Args:
            cost_data: Dictionary containing cost and processing information
        """
        try:
            self._log_cost_data_to_file(cost_data)
            self._safe_log(
                self.logger.info,
                "Cost data logged",
                chat_id=cost_data.get("chat_id"),
                total_cost=cost_data.get("total_cost"),
                processing_time=cost_data.get("processing_time"),
            )
        except Exception as e:
            # Log the failure but don't raise - this is critical for business logic continuity
            self._safe_log(
                self.logger.error,
                "Cost logging failed but continuing processing",
                error=str(e),
                chat_id=cost_data.get("chat_id"),
            )

    def _log_cost_data_to_file(self, cost_data: Dict) -> None:
        """Write cost data to file with comprehensive error handling."""
        # Validate required fields
        required_fields = [
            "timestamp",
            "chat_id",
            "user_info",
            "audio_duration",
            "whisper_cost",
            "gpt_tokens_input",
            "gpt_tokens_output",
            "gpt_cost",
            "total_cost",
            "file_size",
            "processing_time",
        ]

        for field in required_fields:
            if field not in cost_data:
                raise ValueError(f"Missing required field: {field}")

        # Prepare log entry
        log_entry = {
            "timestamp": cost_data["timestamp"].isoformat(),
            "chat_id": cost_data["chat_id"],
            "message_id": cost_data.get("message_id"),
            "user_info": cost_data["user_info"],
            "audio_duration_minutes": cost_data["audio_duration"],
            "whisper_cost_usd": cost_data["whisper_cost"],
            "gpt_tokens_input": cost_data["gpt_tokens_input"],
            "gpt_tokens_output": cost_data["gpt_tokens_output"],
            "gpt_cost_usd": cost_data["gpt_cost"],
            "total_cost_usd": cost_data["total_cost"],
            "file_size_bytes": cost_data["file_size"],
            "processing_time_seconds": cost_data["processing_time"],
            "message_type": cost_data.get("message_type"),
            "mime_type": cost_data.get("mime_type"),
            "transcription_language": cost_data.get("transcription_language"),
        }

        # Write to daily log file
        log_date = cost_data["timestamp"].date()
        log_file = self.cost_logs_dir / f"costs-{log_date.isoformat()}.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def log_chat_interaction_safely(
        self,
        chat_id: int,
        message_type: str,
        text: str,
        user_info: Optional[Dict] = None,
        command: Optional[str] = None,
        cattackle_name: Optional[str] = None,
        response_length: Optional[int] = None,
        audio_metadata: Optional[Dict] = None,
    ) -> None:
        """Safely log chat interactions without interrupting message processing."""
        try:
            self._log_chat_to_file(
                chat_id, message_type, text, user_info, command, cattackle_name, response_length, audio_metadata
            )
        except Exception as e:
            # Log the failure but don't raise - message processing must continue
            self._safe_log(
                self.logger.error,
                "Chat logging failed but continuing processing",
                error=str(e),
                chat_id=chat_id,
                message_type=message_type,
            )

    def _log_chat_to_file(
        self,
        chat_id: int,
        message_type: str,
        text: str,
        user_info: Optional[Dict],
        command: Optional[str],
        cattackle_name: Optional[str],
        response_length: Optional[int],
        audio_metadata: Optional[Dict],
    ) -> None:
        """Write chat interaction to file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.chat_logs_dir / f"{today}.jsonl"

        # Extract user information
        participant_name = "Unknown"
        if user_info:
            if user_info.get("username"):
                participant_name = f"@{user_info['username']}"
            elif user_info.get("first_name"):
                participant_name = user_info["first_name"]
                if user_info.get("last_name"):
                    participant_name += f" {user_info['last_name']}"

        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "chat_id": chat_id,
            "participant_name": participant_name,
            "message_type": message_type,
            "text_length": len(text),
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
        }

        # Add optional fields
        if command:
            log_entry["command"] = command
        if cattackle_name:
            log_entry["cattackle_name"] = cattackle_name
        if response_length is not None:
            log_entry["response_length"] = response_length
        if user_info:
            log_entry["user_id"] = user_info.get("id")
            log_entry["is_bot"] = user_info.get("is_bot", False)
            if user_info.get("language_code"):
                log_entry["language_code"] = user_info["language_code"]
        if audio_metadata:
            log_entry["audio_metadata"] = audio_metadata

        # Write to file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
