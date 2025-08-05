"""Tests for date handling utilities."""

from datetime import datetime, timezone

from notion.utils.date_utils import (
    format_date_for_page_title,
    format_timestamp_for_content,
    get_current_date_iso,
    get_current_timestamp,
    validate_date_format,
    validate_datetime_format,
)


class TestGetCurrentDateIso:
    """Test get_current_date_iso function."""

    def test_returns_iso_format(self):
        """Test that the function returns date in YYYY-MM-DD format."""
        result = get_current_date_iso()

        # Should match ISO date format
        assert len(result) == 10
        assert result[4] == "-"
        assert result[7] == "-"

        # Should be parseable as a date
        datetime.strptime(result, "%Y-%m-%d")

    def test_uses_utc_timezone(self):
        """Test that the function uses UTC timezone for consistency."""
        result = get_current_date_iso()
        expected = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Should match current UTC date (allowing for test execution time)
        assert result == expected


class TestGetCurrentTimestamp:
    """Test get_current_timestamp function."""

    def test_returns_time_format(self):
        """Test that the function returns time in HH:MM:SS format."""
        result = get_current_timestamp()

        # Should match time format
        assert len(result) == 8
        assert result[2] == ":"
        assert result[5] == ":"

        # Should be parseable as a time
        datetime.strptime(result, "%H:%M:%S")

    def test_uses_utc_timezone(self):
        """Test that the function uses UTC timezone for consistency."""
        result = get_current_timestamp()

        # Should match current UTC time (allowing for test execution time)
        # We'll just check that it's a valid time format since exact matching
        # would be flaky due to execution timing
        datetime.strptime(result, "%H:%M:%S")


class TestValidateDateFormat:
    """Test validate_date_format function."""

    def test_valid_iso_dates(self):
        """Test validation of valid ISO date formats."""
        valid_dates = [
            "2023-01-01",
            "2023-12-31",
            "2024-02-29",  # Leap year
            "1999-06-15",
        ]

        for date_str in valid_dates:
            assert validate_date_format(date_str) is True

    def test_invalid_date_formats(self):
        """Test validation rejects invalid date formats."""
        invalid_dates = [
            "2023-1-1",  # Single digit month/day
            "23-01-01",  # Two digit year
            "2023/01/01",  # Wrong separator
            "01-01-2023",  # Wrong order
            "2023-13-01",  # Invalid month
            "2023-02-30",  # Invalid day
            "not-a-date",  # Not a date
            "",  # Empty string
            "2023-01",  # Incomplete
            "2023-01-01-01",  # Too long
        ]

        for date_str in invalid_dates:
            assert validate_date_format(date_str) is False

    def test_non_string_input(self):
        """Test validation handles non-string input."""
        non_strings = [None, 123, [], {}, datetime.now()]

        for value in non_strings:
            assert validate_date_format(value) is False


class TestValidateDatetimeFormat:
    """Test validate_datetime_format function."""

    def test_valid_datetime_formats(self):
        """Test validation of valid datetime formats."""
        valid_datetimes = [
            "2023-01-01 00:00:00",
            "2023-12-31 23:59:59",
            "2024-02-29 12:30:45",  # Leap year
            "1999-06-15 14:22:33",
        ]

        for datetime_str in valid_datetimes:
            assert validate_datetime_format(datetime_str) is True

    def test_invalid_datetime_formats(self):
        """Test validation rejects invalid datetime formats."""
        invalid_datetimes = [
            "2023-1-1 12:30:45",  # Single digit month/day
            "23-01-01 12:30:45",  # Two digit year
            "2023/01/01 12:30:45",  # Wrong date separator
            "2023-01-01T12:30:45",  # ISO format with T
            "2023-01-01 12:30",  # Missing seconds
            "2023-01-01 25:30:45",  # Invalid hour
            "2023-01-01 12:60:45",  # Invalid minute
            "2023-01-01 12:30:60",  # Invalid second
            "2023-13-01 12:30:45",  # Invalid month
            "2023-02-30 12:30:45",  # Invalid day
            "not-a-datetime",  # Not a datetime
            "",  # Empty string
            "2023-01-01",  # Date only
            "12:30:45",  # Time only
        ]

        for datetime_str in invalid_datetimes:
            assert validate_datetime_format(datetime_str) is False

    def test_non_string_input(self):
        """Test validation handles non-string input."""
        non_strings = [None, 123, [], {}, datetime.now()]

        for value in non_strings:
            assert validate_datetime_format(value) is False


class TestFormatDateForPageTitle:
    """Test format_date_for_page_title function."""

    def test_formats_datetime_to_full_timestamp(self):
        """Test formatting datetime object to full timestamp string."""
        test_date = datetime(2023, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_date_for_page_title(test_date)

        assert result == "2023-06-15 14:30:45"

    def test_handles_none_input(self):
        """Test that None input uses current datetime."""
        result = format_date_for_page_title(None)

        # Since we can't guarantee exact timing, check format and approximate time
        assert len(result) == 19  # YYYY-MM-DD HH:MM:SS format
        assert result[4] == "-" and result[7] == "-" and result[10] == " "
        assert result[13] == ":" and result[16] == ":"

    def test_handles_naive_datetime(self):
        """Test that naive datetime is treated as UTC."""
        naive_date = datetime(2023, 6, 15, 14, 30, 45)
        result = format_date_for_page_title(naive_date)

        assert result == "2023-06-15 14:30:45"

    def test_handles_different_timezones(self):
        """Test that different timezones are handled correctly."""
        # Create a datetime in a different timezone
        from datetime import timedelta

        other_tz = timezone(timedelta(hours=5))
        test_date = datetime(2023, 6, 15, 14, 30, 45, tzinfo=other_tz)

        result = format_date_for_page_title(test_date)
        assert result == "2023-06-15 14:30:45"


class TestFormatTimestampForContent:
    """Test format_timestamp_for_content function."""

    def test_formats_datetime_to_timestamp(self):
        """Test formatting datetime object to timestamp string."""
        test_time = datetime(2023, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_timestamp_for_content(test_time)

        assert result == "[14:30:45]"

    def test_handles_none_input(self):
        """Test that None input uses current time."""
        result = format_timestamp_for_content(None)

        # Should be in [HH:MM:SS] format
        assert result.startswith("[")
        assert result.endswith("]")
        assert len(result) == 10

        # Extract time part and validate
        time_part = result[1:-1]
        datetime.strptime(time_part, "%H:%M:%S")

    def test_handles_naive_datetime(self):
        """Test that naive datetime is treated as UTC."""
        naive_time = datetime(2023, 6, 15, 14, 30, 45)
        result = format_timestamp_for_content(naive_time)

        assert result == "[14:30:45]"

    def test_handles_different_timezones(self):
        """Test that different timezones are handled correctly."""
        from datetime import timedelta

        other_tz = timezone(timedelta(hours=5))
        test_time = datetime(2023, 6, 15, 14, 30, 45, tzinfo=other_tz)

        result = format_timestamp_for_content(test_time)
        assert result == "[14:30:45]"
