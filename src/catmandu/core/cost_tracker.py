import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import structlog

from catmandu.core.config import Settings

logger = structlog.get_logger(__name__)


class CostTracker:
    """Handles cost tracking and logging for audio processing operations."""

    def __init__(self, settings: Settings):
        """Initialize the cost tracker with configuration settings.

        Args:
            settings: Application settings containing cost tracking configuration
        """
        self.settings = settings
        self.cost_logs_dir = Path(settings.cost_logs_dir)
        self._ensure_logs_directory()

    def _ensure_logs_directory(self) -> None:
        """Ensure the cost logs directory exists."""
        self.cost_logs_dir.mkdir(parents=True, exist_ok=True)

    def calculate_whisper_cost(self, duration_minutes: float) -> float:
        """Calculate Whisper API cost based on audio duration.

        Args:
            duration_minutes: Audio duration in minutes

        Returns:
            Estimated cost in USD
        """
        return duration_minutes * self.settings.whisper_cost_per_minute

    def calculate_gpt_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate GPT-4o-mini cost based on token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * self.settings.gpt4o_mini_input_cost_per_1m_tokens
        output_cost = (output_tokens / 1_000_000) * self.settings.gpt4o_mini_output_cost_per_1m_tokens
        return input_cost + output_cost

    def log_audio_processing_cost(self, cost_data: Dict) -> None:
        """Log cost information for audio processing.

        Args:
            cost_data: Dictionary containing cost and processing information
                Expected keys:
                - timestamp: datetime object
                - chat_id: int
                - user_info: dict with user information
                - audio_duration: float (in minutes)
                - whisper_cost: float
                - gpt_tokens_input: int
                - gpt_tokens_output: int
                - gpt_cost: float
                - total_cost: float
                - file_size: int (in bytes)
                - processing_time: float (in seconds)
        """
        try:
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

            # Prepare enhanced log entry with additional metadata
            log_entry = {
                "timestamp": cost_data["timestamp"].isoformat(),
                "chat_id": cost_data["chat_id"],
                "message_id": cost_data.get("message_id"),
                "user_info": cost_data["user_info"],
                "audio_duration_minutes": cost_data["audio_duration"],
                "audio_duration_seconds": cost_data["audio_duration"] * 60,
                "whisper_cost_usd": cost_data["whisper_cost"],
                "gpt_tokens_input": cost_data["gpt_tokens_input"],
                "gpt_tokens_output": cost_data["gpt_tokens_output"],
                "gpt_total_tokens": cost_data["gpt_tokens_input"] + cost_data["gpt_tokens_output"],
                "gpt_cost_usd": cost_data["gpt_cost"],
                "total_cost_usd": cost_data["total_cost"],
                "file_size_bytes": cost_data["file_size"],
                "file_size_mb": round(cost_data["file_size"] / (1024 * 1024), 3),
                "processing_time_seconds": cost_data["processing_time"],
                "message_type": cost_data.get("message_type"),
                "mime_type": cost_data.get("mime_type"),
                "transcription_language": cost_data.get("transcription_language"),
                "original_text_length": cost_data.get("original_text_length"),
                "improved_text_length": cost_data.get("improved_text_length"),
                "transcription_time_seconds": cost_data.get("transcription_time"),
                "cost_per_minute": (
                    round(cost_data["total_cost"] / cost_data["audio_duration"], 4)
                    if cost_data["audio_duration"] > 0
                    else 0
                ),
                "cost_per_mb": (
                    round(cost_data["total_cost"] / (cost_data["file_size"] / (1024 * 1024)), 4)
                    if cost_data["file_size"] > 0
                    else 0
                ),
                "processing_speed_ratio": (
                    round((cost_data["audio_duration"] * 60) / cost_data["processing_time"], 2)
                    if cost_data["processing_time"] > 0
                    else None
                ),
            }

            # Write to daily log file
            log_date = cost_data["timestamp"].date()
            log_file = self.cost_logs_dir / f"costs-{log_date.isoformat()}.jsonl"

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            # Enhanced structured logging for monitoring
            logger.info(
                "Audio processing cost logged successfully",
                log_file=str(log_file),
                chat_id=cost_data["chat_id"],
                message_id=cost_data.get("message_id"),
                user_id=cost_data["user_info"].get("user_id"),
                username=cost_data["user_info"].get("username"),
                message_type=cost_data.get("message_type"),
                audio_duration_minutes=cost_data["audio_duration"],
                file_size_mb=round(cost_data["file_size"] / (1024 * 1024), 2),
                mime_type=cost_data.get("mime_type"),
                transcription_language=cost_data.get("transcription_language"),
                whisper_cost_usd=cost_data["whisper_cost"],
                gpt_cost_usd=cost_data["gpt_cost"],
                total_cost_usd=cost_data["total_cost"],
                gpt_tokens_total=cost_data["gpt_tokens_input"] + cost_data["gpt_tokens_output"],
                processing_time_seconds=cost_data["processing_time"],
                cost_per_minute=(
                    round(cost_data["total_cost"] / cost_data["audio_duration"], 4)
                    if cost_data["audio_duration"] > 0
                    else 0
                ),
                processing_speed_ratio=(
                    round((cost_data["audio_duration"] * 60) / cost_data["processing_time"], 2)
                    if cost_data["processing_time"] > 0
                    else None
                ),
            )

        except Exception as e:
            logger.error(
                "Failed to log audio processing cost",
                error=str(e),
                error_type=type(e).__name__,
                chat_id=cost_data.get("chat_id"),
                user_id=cost_data.get("user_info", {}).get("user_id"),
                timestamp=cost_data.get("timestamp"),
                exc_info=True,
            )
            raise

    def get_daily_costs(self, target_date: str) -> Dict:
        """Get aggregated costs for a specific date.

        Args:
            target_date: Date string in YYYY-MM-DD format

        Returns:
            Dictionary with aggregated cost information
        """
        try:
            # Parse and validate date
            datetime.strptime(target_date, "%Y-%m-%d").date()
            log_file = self.cost_logs_dir / f"costs-{target_date}.jsonl"

            if not log_file.exists():
                return {
                    "date": target_date,
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

            # Read and aggregate data
            total_cost = 0.0
            whisper_cost = 0.0
            gpt_cost = 0.0
            total_requests = 0
            total_audio_duration = 0.0
            total_tokens_input = 0
            total_tokens_output = 0
            total_processing_time = 0.0
            total_file_size = 0

            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line.strip())
                        total_cost += entry["total_cost_usd"]
                        whisper_cost += entry["whisper_cost_usd"]
                        gpt_cost += entry["gpt_cost_usd"]
                        total_requests += 1
                        total_audio_duration += entry["audio_duration_minutes"]
                        total_tokens_input += entry["gpt_tokens_input"]
                        total_tokens_output += entry["gpt_tokens_output"]
                        total_processing_time += entry["processing_time_seconds"]
                        total_file_size += entry["file_size_bytes"]

            average_processing_time = total_processing_time / total_requests if total_requests > 0 else 0.0

            return {
                "date": target_date,
                "total_cost": round(total_cost, 4),
                "whisper_cost": round(whisper_cost, 4),
                "gpt_cost": round(gpt_cost, 4),
                "total_requests": total_requests,
                "total_audio_duration": round(total_audio_duration, 2),
                "total_tokens_input": total_tokens_input,
                "total_tokens_output": total_tokens_output,
                "average_processing_time": round(average_processing_time, 2),
                "total_file_size": total_file_size,
            }

        except Exception as e:
            logger.error("Failed to get daily costs", date=target_date, error=str(e))
            raise

    def get_date_range_costs(self, start_date: str, end_date: str) -> Dict:
        """Get aggregated costs for a date range.

        Args:
            start_date: Start date string in YYYY-MM-DD format
            end_date: End date string in YYYY-MM-DD format

        Returns:
            Dictionary with aggregated cost information for the date range
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

            if start > end:
                raise ValueError("Start date must be before or equal to end date")

            # Aggregate costs across date range
            total_cost = 0.0
            whisper_cost = 0.0
            gpt_cost = 0.0
            total_requests = 0
            total_audio_duration = 0.0
            total_tokens_input = 0
            total_tokens_output = 0
            total_processing_time = 0.0
            total_file_size = 0
            days_with_data = 0

            current_date = start
            while current_date <= end:
                date_str = current_date.isoformat()
                daily_costs = self.get_daily_costs(date_str)

                if daily_costs["total_requests"] > 0:
                    days_with_data += 1
                    total_cost += daily_costs["total_cost"]
                    whisper_cost += daily_costs["whisper_cost"]
                    gpt_cost += daily_costs["gpt_cost"]
                    total_requests += daily_costs["total_requests"]
                    total_audio_duration += daily_costs["total_audio_duration"]
                    total_tokens_input += daily_costs["total_tokens_input"]
                    total_tokens_output += daily_costs["total_tokens_output"]
                    total_processing_time += daily_costs["average_processing_time"] * daily_costs["total_requests"]
                    total_file_size += daily_costs["total_file_size"]

                current_date = current_date + timedelta(days=1)

            average_processing_time = total_processing_time / total_requests if total_requests > 0 else 0.0

            return {
                "start_date": start_date,
                "end_date": end_date,
                "days_with_data": days_with_data,
                "total_cost": round(total_cost, 4),
                "whisper_cost": round(whisper_cost, 4),
                "gpt_cost": round(gpt_cost, 4),
                "total_requests": total_requests,
                "total_audio_duration": round(total_audio_duration, 2),
                "total_tokens_input": total_tokens_input,
                "total_tokens_output": total_tokens_output,
                "average_processing_time": round(average_processing_time, 2),
                "total_file_size": total_file_size,
            }

        except Exception as e:
            logger.error("Failed to get date range costs", start_date=start_date, end_date=end_date, error=str(e))
            raise
