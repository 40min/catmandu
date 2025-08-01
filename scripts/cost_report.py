#!/usr/bin/env python3
"""
Cost reporting script for audio processing expenses.

This script provides functionality to calculate and display cost reports
for audio processing operations by day, week, or month.
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from catmandu.core.config import Settings  # noqa;
from catmandu.core.cost_tracker import CostTracker  # noqa;


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"${amount:.4f}"


def format_duration(minutes: float) -> str:
    """Format duration in minutes to human-readable format."""
    if minutes < 1:
        return f"{minutes * 60:.1f} seconds"
    elif minutes < 60:
        return f"{minutes:.1f} minutes"
    else:
        hours = minutes / 60
        return f"{hours:.1f} hours"


def print_daily_report(cost_tracker: CostTracker, date: str):
    """Print a daily cost report."""
    costs = cost_tracker.get_daily_costs(date)

    print(f"\n📊 Daily Cost Report for {date}")
    print("=" * 50)

    if costs["total_requests"] == 0:
        print("No audio processing requests found for this date.")
        return

    print(f"Total Requests: {costs['total_requests']}")
    print(f"Total Audio Duration: {format_duration(costs['total_audio_duration'])}")
    print(f"Total File Size: {costs['total_file_size'] / (1024 * 1024):.1f} MB")
    print(f"Average Processing Time: {costs['average_processing_time']:.2f} seconds")
    print()
    print("💰 Cost Breakdown:")
    print(f"  Whisper API: {format_currency(costs['whisper_cost'])}")
    print(f"  GPT-4o-mini: {format_currency(costs['gpt_cost'])}")
    print(f"  Total Cost:  {format_currency(costs['total_cost'])}")
    print()
    print("🔢 Token Usage:")
    print(f"  Input Tokens:  {costs['total_tokens_input']:,}")
    print(f"  Output Tokens: {costs['total_tokens_output']:,}")


def print_range_report(cost_tracker: CostTracker, start_date: str, end_date: str, period_name: str):
    """Print a date range cost report."""
    costs = cost_tracker.get_date_range_costs(start_date, end_date)

    print(f"\n📊 {period_name} Cost Report ({start_date} to {end_date})")
    print("=" * 60)

    if costs["total_requests"] == 0:
        print(f"No audio processing requests found for this {period_name.lower()}.")
        return

    print(f"Days with Data: {costs['days_with_data']}")
    print(f"Total Requests: {costs['total_requests']}")
    print(f"Total Audio Duration: {format_duration(costs['total_audio_duration'])}")
    print(f"Total File Size: {costs['total_file_size'] / (1024 * 1024):.1f} MB")
    print(f"Average Processing Time: {costs['average_processing_time']:.2f} seconds")

    if costs["days_with_data"] > 0:
        avg_requests_per_day = costs["total_requests"] / costs["days_with_data"]
        avg_cost_per_day = costs["total_cost"] / costs["days_with_data"]
        print(f"Average Requests per Day: {avg_requests_per_day:.1f}")
        print(f"Average Cost per Day: {format_currency(avg_cost_per_day)}")

    print()
    print("💰 Cost Breakdown:")
    print(f"  Whisper API: {format_currency(costs['whisper_cost'])}")
    print(f"  GPT-4o-mini: {format_currency(costs['gpt_cost'])}")
    print(f"  Total Cost:  {format_currency(costs['total_cost'])}")
    print()
    print("🔢 Token Usage:")
    print(f"  Input Tokens:  {costs['total_tokens_input']:,}")
    print(f"  Output Tokens: {costs['total_tokens_output']:,}")


def get_week_range(date_str: str) -> tuple[str, str]:
    """Get the start and end dates for the week containing the given date."""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    # Get Monday of the week
    start_of_week = date - timedelta(days=date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.strftime("%Y-%m-%d"), end_of_week.strftime("%Y-%m-%d")


def get_month_range(date_str: str) -> tuple[str, str]:
    """Get the start and end dates for the month containing the given date."""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    # First day of the month
    start_of_month = date.replace(day=1)
    # Last day of the month
    if date.month == 12:
        end_of_month = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = date.replace(month=date.month + 1, day=1) - timedelta(days=1)

    return start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d")


def main():
    """Main function to handle command line arguments and generate reports."""
    parser = argparse.ArgumentParser(
        description="Generate cost reports for audio processing operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Daily report for today
  python scripts/cost_report.py --daily

  # Daily report for specific date
  python scripts/cost_report.py --daily --date 2024-01-15

  # Weekly report for current week
  python scripts/cost_report.py --weekly

  # Monthly report for current month
  python scripts/cost_report.py --monthly

  # Custom date range
  python scripts/cost_report.py --range --start-date 2024-01-01 --end-date 2024-01-31
        """,
    )

    # Report type arguments (mutually exclusive)
    report_group = parser.add_mutually_exclusive_group(required=True)
    report_group.add_argument("--daily", action="store_true", help="Generate daily report")
    report_group.add_argument("--weekly", action="store_true", help="Generate weekly report")
    report_group.add_argument("--monthly", action="store_true", help="Generate monthly report")
    report_group.add_argument("--range", action="store_true", help="Generate custom date range report")

    # Date arguments
    parser.add_argument(
        "--date", type=str, help="Date for daily/weekly/monthly reports (YYYY-MM-DD format, defaults to today)"
    )
    parser.add_argument("--start-date", type=str, help="Start date for range reports (YYYY-MM-DD format)")
    parser.add_argument("--end-date", type=str, help="End date for range reports (YYYY-MM-DD format)")

    args = parser.parse_args()

    # Validate arguments
    if args.range and (not args.start_date or not args.end_date):
        parser.error("--range requires both --start-date and --end-date")

    # Set default date to today if not provided
    if not args.date and not args.range:
        args.date = datetime.now().strftime("%Y-%m-%d")

    try:
        # Initialize settings and cost tracker
        settings = Settings()
        cost_tracker = CostTracker(settings)

        print("🎯 Catmandu Audio Processing Cost Report")
        print(f"📁 Cost logs directory: {settings.cost_logs_dir}")

        if args.daily:
            print_daily_report(cost_tracker, args.date)

        elif args.weekly:
            start_date, end_date = get_week_range(args.date)
            print_range_report(cost_tracker, start_date, end_date, "Weekly")

        elif args.monthly:
            start_date, end_date = get_month_range(args.date)
            print_range_report(cost_tracker, start_date, end_date, "Monthly")

        elif args.range:
            print_range_report(cost_tracker, args.start_date, args.end_date, "Custom Range")

    except Exception as e:
        print(f"❌ Error generating cost report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
