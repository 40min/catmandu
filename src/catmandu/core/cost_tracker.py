import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import structlog

from catmandu.core.config import Settings

logger = structlog.get_logger(__name__)


class CostTracker:
    """Handles cost tracking and calculation for audio processing operations."""

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
        try:
            self.cost_logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("Failed to create cost logs directory", error=str(e))

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

    def get_user_breakdown(self, start_date: str, end_date: str) -> Dict:
        """Get cost breakdown by user for a date range.

        Args:
            start_date: Start date string in YYYY-MM-DD format
            end_date: End date string in YYYY-MM-DD format

        Returns:
            Dictionary with user-specific cost breakdowns
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

            if start > end:
                raise ValueError("Start date must be before or equal to end date")

            user_stats = {}
            current_date = start

            while current_date <= end:
                date_str = current_date.isoformat()
                log_file = self.cost_logs_dir / f"costs-{date_str}.jsonl"

                if log_file.exists():
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                entry = json.loads(line.strip())
                                user_info = entry["user_info"]
                                user_id = user_info.get("user_id", "unknown")
                                username = user_info.get("username", "unknown")
                                first_name = user_info.get("first_name", "")
                                last_name = user_info.get("last_name", "")

                                # Create user key
                                user_key = f"{user_id}"
                                if user_key not in user_stats:
                                    user_stats[user_key] = {
                                        "user_id": user_id,
                                        "username": username,
                                        "first_name": first_name,
                                        "last_name": last_name,
                                        "display_name": self._get_display_name(user_info),
                                        "total_cost": 0.0,
                                        "whisper_cost": 0.0,
                                        "gpt_cost": 0.0,
                                        "total_requests": 0,
                                        "total_audio_duration": 0.0,
                                        "total_tokens_input": 0,
                                        "total_tokens_output": 0,
                                        "total_processing_time": 0.0,
                                        "total_file_size": 0,
                                        "average_file_size": 0.0,
                                        "average_duration": 0.0,
                                        "cost_per_minute": 0.0,
                                    }

                                # Aggregate user stats
                                stats = user_stats[user_key]
                                stats["total_cost"] += entry["total_cost_usd"]
                                stats["whisper_cost"] += entry["whisper_cost_usd"]
                                stats["gpt_cost"] += entry["gpt_cost_usd"]
                                stats["total_requests"] += 1
                                stats["total_audio_duration"] += entry["audio_duration_minutes"]
                                stats["total_tokens_input"] += entry["gpt_tokens_input"]
                                stats["total_tokens_output"] += entry["gpt_tokens_output"]
                                stats["total_processing_time"] += entry["processing_time_seconds"]
                                stats["total_file_size"] += entry["file_size_bytes"]

                current_date = current_date + timedelta(days=1)

            # Calculate averages and round values
            for user_key, stats in user_stats.items():
                if stats["total_requests"] > 0:
                    stats["average_file_size"] = stats["total_file_size"] / stats["total_requests"]
                    stats["average_duration"] = stats["total_audio_duration"] / stats["total_requests"]
                    stats["cost_per_minute"] = (
                        stats["total_cost"] / stats["total_audio_duration"]
                        if stats["total_audio_duration"] > 0
                        else 0.0
                    )

                # Round values
                stats["total_cost"] = round(stats["total_cost"], 4)
                stats["whisper_cost"] = round(stats["whisper_cost"], 4)
                stats["gpt_cost"] = round(stats["gpt_cost"], 4)
                stats["total_audio_duration"] = round(stats["total_audio_duration"], 2)
                stats["total_processing_time"] = round(stats["total_processing_time"], 2)
                stats["average_file_size"] = round(stats["average_file_size"], 0)
                stats["average_duration"] = round(stats["average_duration"], 2)
                stats["cost_per_minute"] = round(stats["cost_per_minute"], 4)

            return {
                "start_date": start_date,
                "end_date": end_date,
                "users": user_stats,
                "total_users": len(user_stats),
            }

        except Exception as e:
            logger.error("Failed to get user breakdown", start_date=start_date, end_date=end_date, error=str(e))
            raise

    def _get_display_name(self, user_info: Dict) -> str:
        """Generate a display name for a user.

        Args:
            user_info: Dictionary containing user information

        Returns:
            Human-readable display name
        """
        username = user_info.get("username", "")
        first_name = user_info.get("first_name", "")
        last_name = user_info.get("last_name", "")

        if username:
            return f"@{username}"
        elif first_name or last_name:
            return f"{first_name} {last_name}".strip()
        else:
            return f"User {user_info.get('user_id', 'Unknown')}"
