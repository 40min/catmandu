#!/usr/bin/env python3
"""
Chat log analysis script.

Analyzes chat interaction logs to extract statistics about unique chat IDs,
participant names, commands usage, and other metrics.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List


class ChatLogAnalyzer:
    """Analyzer for chat interaction logs."""

    def __init__(self, logs_dir: str = "logs/chats"):
        self.logs_dir = Path(logs_dir)
        self.entries: List[Dict] = []

    def load_logs(self, date_filter: str = None) -> None:
        """Load log entries from files.

        Args:
            date_filter: Optional date filter (YYYY-MM-DD format)
        """
        log_files = sorted(self.logs_dir.glob("*.jsonl"))

        if date_filter:
            log_files = [f for f in log_files if f.stem == date_filter]

        if not log_files:
            print(f"No log files found in {self.logs_dir}")
            if date_filter:
                print(f"Date filter: {date_filter}")
            return

        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            self.entries.append(entry)
            except Exception as e:
                print(f"Error reading {log_file}: {e}")

        print(f"Loaded {len(self.entries)} log entries from {len(log_files)} files")

    def analyze_unique_chats(self) -> Dict:
        """Analyze unique chat IDs."""
        chat_ids = set()
        chat_details = {}

        for entry in self.entries:
            chat_id = entry.get("chat_id")
            if chat_id:
                chat_ids.add(chat_id)
                if chat_id not in chat_details:
                    chat_details[chat_id] = {
                        "first_seen": entry.get("timestamp"),
                        "participants": set(),
                        "message_count": 0,
                        "command_count": 0,
                    }

                chat_details[chat_id]["participants"].add(entry.get("participant_name", "Unknown"))
                chat_details[chat_id]["message_count"] += 1
                if entry.get("message_type") == "command":
                    chat_details[chat_id]["command_count"] += 1

        return {
            "unique_count": len(chat_ids),
            "chat_ids": sorted(chat_ids),
            "details": {
                chat_id: {**details, "participants": list(details["participants"])}
                for chat_id, details in chat_details.items()
            },
        }

    def analyze_unique_participants(self) -> Dict:
        """Analyze unique participant names."""
        participants = Counter()
        participant_details = defaultdict(
            lambda: {"chat_ids": set(), "message_count": 0, "command_count": 0, "first_seen": None, "last_seen": None}
        )

        for entry in self.entries:
            participant = entry.get("participant_name", "Unknown")
            chat_id = entry.get("chat_id")
            timestamp = entry.get("timestamp")

            participants[participant] += 1

            details = participant_details[participant]
            details["chat_ids"].add(chat_id)
            details["message_count"] += 1

            if entry.get("message_type") == "command":
                details["command_count"] += 1

            if not details["first_seen"] or timestamp < details["first_seen"]:
                details["first_seen"] = timestamp
            if not details["last_seen"] or timestamp > details["last_seen"]:
                details["last_seen"] = timestamp

        return {
            "unique_count": len(participants),
            "participants": dict(participants.most_common()),
            "details": {
                name: {**details, "chat_ids": list(details["chat_ids"]), "unique_chats": len(details["chat_ids"])}
                for name, details in participant_details.items()
            },
        }

    def analyze_commands(self) -> Dict:
        """Analyze command usage."""
        commands = Counter()
        cattackles = Counter()
        command_details = defaultdict(lambda: {"users": set(), "chats": set(), "total_usage": 0})

        for entry in self.entries:
            if entry.get("message_type") == "command":
                command = entry.get("command")
                cattackle = entry.get("cattackle_name")
                participant = entry.get("participant_name", "Unknown")
                chat_id = entry.get("chat_id")

                if command:
                    commands[command] += 1
                    details = command_details[command]
                    details["users"].add(participant)
                    details["chats"].add(chat_id)
                    details["total_usage"] += 1

                if cattackle:
                    cattackles[cattackle] += 1

        return {
            "total_commands": sum(commands.values()),
            "unique_commands": len(commands),
            "command_usage": dict(commands.most_common()),
            "cattackle_usage": dict(cattackles.most_common()),
            "command_details": {
                cmd: {
                    **details,
                    "users": list(details["users"]),
                    "chats": list(details["chats"]),
                    "unique_users": len(details["users"]),
                    "unique_chats": len(details["chats"]),
                }
                for cmd, details in command_details.items()
            },
        }

    def analyze_activity_by_date(self) -> Dict:
        """Analyze activity by date."""
        daily_stats = defaultdict(
            lambda: {
                "total_messages": 0,
                "commands": 0,
                "regular_messages": 0,
                "unique_users": set(),
                "unique_chats": set(),
            }
        )

        for entry in self.entries:
            timestamp = entry.get("timestamp", "")
            if timestamp:
                date = timestamp.split("T")[0]  # Extract date part
                stats = daily_stats[date]

                stats["total_messages"] += 1
                if entry.get("message_type") == "command":
                    stats["commands"] += 1
                else:
                    stats["regular_messages"] += 1

                stats["unique_users"].add(entry.get("participant_name", "Unknown"))
                stats["unique_chats"].add(entry.get("chat_id"))

        return {
            date: {**stats, "unique_users": len(stats["unique_users"]), "unique_chats": len(stats["unique_chats"])}
            for date, stats in sorted(daily_stats.items())
        }

    def generate_summary(self) -> Dict:
        """Generate overall summary statistics."""
        if not self.entries:
            return {"error": "No log entries found"}

        chats_analysis = self.analyze_unique_chats()
        participants_analysis = self.analyze_unique_participants()
        commands_analysis = self.analyze_commands()
        daily_analysis = self.analyze_activity_by_date()

        return {
            "summary": {
                "total_entries": len(self.entries),
                "unique_chats": chats_analysis["unique_count"],
                "unique_participants": participants_analysis["unique_count"],
                "total_commands": commands_analysis["total_commands"],
                "unique_commands": commands_analysis["unique_commands"],
                "date_range": {
                    "first": min(entry.get("timestamp", "") for entry in self.entries),
                    "last": max(entry.get("timestamp", "") for entry in self.entries),
                },
            },
            "chats": chats_analysis,
            "participants": participants_analysis,
            "commands": commands_analysis,
            "daily_activity": daily_analysis,
        }


def main():
    parser = argparse.ArgumentParser(description="Analyze chat interaction logs")
    parser.add_argument("--logs-dir", default="logs/chats", help="Directory containing log files")
    parser.add_argument("--date", help="Filter by specific date (YYYY-MM-DD)")
    parser.add_argument(
        "--output",
        choices=["summary", "chats", "participants", "commands", "daily"],
        default="summary",
        help="Type of analysis to output",
    )
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")

    args = parser.parse_args()

    analyzer = ChatLogAnalyzer(args.logs_dir)
    analyzer.load_logs(args.date)

    if args.output == "summary":
        result = analyzer.generate_summary()
    elif args.output == "chats":
        result = analyzer.analyze_unique_chats()
    elif args.output == "participants":
        result = analyzer.analyze_unique_participants()
    elif args.output == "commands":
        result = analyzer.analyze_commands()
    elif args.output == "daily":
        result = analyzer.analyze_activity_by_date()

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Text format output
        if args.output == "summary":
            summary = result.get("summary", {})
            print("=== CHAT LOG ANALYSIS SUMMARY ===")
            print(f"Total log entries: {summary.get('total_entries', 0)}")
            print(f"Unique chats: {summary.get('unique_chats', 0)}")
            print(f"Unique participants: {summary.get('unique_participants', 0)}")
            print(f"Total commands executed: {summary.get('total_commands', 0)}")
            print(f"Unique commands: {summary.get('unique_commands', 0)}")

            date_range = summary.get("date_range", {})
            if date_range.get("first"):
                print(f"Date range: {date_range['first'][:10]} to {date_range['last'][:10]}")

            print("\n=== TOP PARTICIPANTS ===")
            participants = result.get("participants", {}).get("participants", {})
            for name, count in list(participants.items())[:10]:
                print(f"{name}: {count} messages")

            print("\n=== TOP COMMANDS ===")
            commands = result.get("commands", {}).get("command_usage", {})
            for cmd, count in list(commands.items())[:10]:
                print(f"/{cmd}: {count} times")

        elif args.output == "chats":
            print("=== UNIQUE CHAT IDS ===")
            print(f"Total unique chats: {result.get('unique_count', 0)}")
            for chat_id in result.get("chat_ids", []):
                details = result.get("details", {}).get(chat_id, {})
                print(
                    f"Chat {chat_id}: {details.get('message_count', 0)} messages, "
                    f"{len(details.get('participants', []))} participants"
                )

        elif args.output == "participants":
            print("=== UNIQUE PARTICIPANTS ===")
            print(f"Total unique participants: {result.get('unique_count', 0)}")
            for name, count in result.get("participants", {}).items():
                details = result.get("details", {}).get(name, {})
                print(f"{name}: {count} messages across {details.get('unique_chats', 0)} chats")

        elif args.output == "commands":
            print("=== COMMAND USAGE ANALYSIS ===")
            print(f"Total commands: {result.get('total_commands', 0)}")
            print(f"Unique commands: {result.get('unique_commands', 0)}")
            print("\nCommand usage:")
            for cmd, count in result.get("command_usage", {}).items():
                print(f"/{cmd}: {count} times")

        elif args.output == "daily":
            print("=== DAILY ACTIVITY ===")
            for date, stats in result.items():
                print(
                    f"{date}: {stats['total_messages']} messages "
                    f"({stats['commands']} commands, {stats['regular_messages']} regular), "
                    f"{stats['unique_users']} users, {stats['unique_chats']} chats"
                )


if __name__ == "__main__":
    main()
