# Cost Reporting Documentation

This document provides comprehensive guidance on using Catmandu's cost reporting system to monitor and analyze audio processing expenses.

## Overview

Catmandu includes a robust cost tracking and reporting system that logs all audio processing operations and provides detailed analysis tools. The system tracks costs for both Whisper API (transcription) and GPT-4o-mini (text improvement) usage.

## Cost Tracking

### Automatic Logging

All audio processing operations are automatically logged with the following information:

- **User Information**: User ID, username, first/last name
- **Audio Details**: Duration, file size, processing time
- **API Costs**: Whisper transcription costs, GPT token usage and costs
- **Performance Metrics**: Processing speed, efficiency ratios
- **Metadata**: Message type, MIME type, transcription language

### Log Storage

Cost logs are stored in JSONL format (one JSON object per line) in the `logs/costs/` directory:

- Daily log files: `costs-YYYY-MM-DD.jsonl`
- Each entry contains comprehensive metadata for analysis

## Cost Reporting Script

The `scripts/cost_report.py` script provides flexible reporting capabilities for analyzing audio processing costs.

### Basic Usage

```bash
# Generate a daily report for today
python scripts/cost_report.py --daily

# Generate a weekly report for the current week
python scripts/cost_report.py --weekly

# Generate a monthly report for the current month
python scripts/cost_report.py --monthly
```

### Date-Specific Reports

```bash
# Daily report for a specific date
python scripts/cost_report.py --daily --date 2024-01-15

# Weekly report for the week containing a specific date
python scripts/cost_report.py --weekly --date 2024-01-15

# Monthly report for the month containing a specific date
python scripts/cost_report.py --monthly --date 2024-01-15
```

### Custom Date Ranges

```bash
# Custom date range report
python scripts/cost_report.py --range --start-date 2024-01-01 --end-date 2024-01-31
```

## Advanced Analysis Options

### User Breakdown Analysis

Add `--user-breakdown` to any report to get detailed per-user statistics:

```bash
python scripts/cost_report.py --monthly --user-breakdown
```

**User breakdown includes:**

- Individual user costs and usage statistics
- Audio duration and file size metrics per user
- Token usage breakdown by user
- Cost efficiency metrics (cost per minute, average file size)
- Ranking by total cost for identifying high-usage users

### API Usage Analysis

Add `--api-breakdown` to any report for detailed API cost analysis:

```bash
python scripts/cost_report.py --weekly --api-breakdown
```

**API breakdown includes:**

- Cost distribution between Whisper API and GPT-4o-mini
- Average metrics per request (duration, tokens, processing cost)
- Efficiency metrics (cost per minute, cost per MB)
- Processing performance statistics

### Combined Analysis

Use both breakdown options for comprehensive analysis:

```bash
python scripts/cost_report.py --monthly --user-breakdown --api-breakdown
```

## Report Examples

### Basic Daily Report

```
🎯 Catmandu Audio Processing Cost Report
📁 Cost logs directory: logs/costs

📊 Daily Cost Report for 2024-01-15
==================================================
Total Requests: 25
Total Audio Duration: 45.3 minutes
Total File Size: 52.1 MB
Average Processing Time: 7.2 seconds

💰 Cost Breakdown:
  Whisper API: $0.2715
  GPT-4o-mini: $0.0023
  Total Cost:  $0.2738

🔢 Token Usage:
  Input Tokens:  3,250
  Output Tokens: 4,180
```

### User Breakdown Report

```
👥 User Breakdown (8 users)
================================================================================
User                      Requests   Duration     Cost       Avg/Min
--------------------------------------------------------------------------------
@poweruser               12         25.2 minutes $0.1512    $0.0060
@regularuser             8          15.1 minutes $0.0906    $0.0060
@occasionaluser          3          3.8 minutes  $0.0228    $0.0060

📈 Detailed User Statistics:
================================================================================

1. @poweruser
   User ID: 12345
   Username: @poweruser
   📊 Usage Statistics:
      Total Requests: 12
      Total Audio Duration: 25.2 minutes
      Average Duration per Request: 2.1 minutes
      Total File Size: 28.5 MB
      Average File Size: 2.4 MB
   💰 Cost Breakdown:
      Total Cost: $0.1512
      Whisper API: $0.1512
      GPT-4o-mini: $0.0012
      Cost per Minute: $0.0060
   🔢 Token Usage:
      Input Tokens: 1,850
      Output Tokens: 2,340
      Total Tokens: 4,190
```

### API Usage Analysis

```
🔧 API Usage Analysis
==================================================
🎯 Cost Distribution:
  Whisper API: $0.2715 (99.2%)
  GPT-4o-mini: $0.0023 (0.8%)

📊 Average per Request:
  Audio Duration: 1.8 minutes
  Token Usage: 297 tokens
  Processing Cost: $0.0110

⚡ Efficiency Metrics:
  Cost per Minute: $0.0060
  Cost per MB: $0.0053
  Processing Time: 7.2s average
```

## Use Cases and Best Practices

### Daily Monitoring

Use daily reports for routine cost monitoring:

```bash
# Quick daily check
python scripts/cost_report.py --daily

# Detailed daily analysis
python scripts/cost_report.py --daily --user-breakdown --api-breakdown
```

### Weekly Analysis

Weekly reports help identify usage patterns and trends:

```bash
# Weekly summary with user breakdown
python scripts/cost_report.py --weekly --user-breakdown
```

### Monthly Budget Tracking

Monthly reports are ideal for budget planning and cost optimization:

```bash
# Comprehensive monthly analysis
python scripts/cost_report.py --monthly --user-breakdown --api-breakdown
```

### Cost Optimization

Use the reporting data to:

1. **Identify High-Usage Users**: User breakdown shows who generates the most costs
2. **Analyze API Efficiency**: API breakdown reveals cost distribution between services
3. **Monitor Trends**: Compare reports across different time periods
4. **Budget Planning**: Use historical data for future cost projections

### Custom Analysis Periods

For specific analysis needs:

```bash
# Quarter analysis
python scripts/cost_report.py --range --start-date 2024-01-01 --end-date 2024-03-31 --user-breakdown

# Specific event period
python scripts/cost_report.py --range --start-date 2024-02-15 --end-date 2024-02-20 --api-breakdown
```

## Understanding Cost Metrics

### Key Metrics Explained

- **Total Cost**: Combined Whisper API and GPT-4o-mini costs
- **Cost per Minute**: Total cost divided by audio duration (efficiency metric)
- **Cost per MB**: Total cost divided by file size (storage efficiency)
- **Processing Speed Ratio**: Audio duration vs. processing time (performance metric)
- **Average Processing Time**: Time taken to process each request

### Cost Components

1. **Whisper API Costs**: Based on audio duration (typically 99%+ of total cost)
2. **GPT-4o-mini Costs**: Based on token usage for text improvement (small percentage)

### Efficiency Indicators

- **Low cost per minute**: Indicates efficient audio processing
- **High processing speed ratio**: Shows fast processing relative to audio length
- **Consistent metrics across users**: Suggests stable system performance

## Troubleshooting

### No Data Found

If reports show "No audio processing requests found":

- Verify the date range includes actual usage
- Check that cost logging is enabled in the system
- Ensure the `logs/costs/` directory exists and is writable

### Missing User Information

If user breakdown shows "unknown" users:

- This indicates incomplete user information in the original logs
- Recent logs should have complete user data

### Inconsistent Costs

If costs seem inconsistent:

- Check the configuration settings for API pricing
- Verify that all processing operations are being logged
- Compare with actual API billing statements

## Integration with Monitoring

The cost reporting system can be integrated with monitoring and alerting systems:

1. **Automated Daily Reports**: Schedule daily reports via cron jobs
2. **Cost Alerts**: Set up alerts when daily/weekly costs exceed thresholds
3. **Usage Analytics**: Export data for integration with business intelligence tools
4. **Budget Tracking**: Use reports for automated budget monitoring

## Configuration

Cost tracking behavior is configured through the application settings:

- `cost_logs_dir`: Directory for storing cost logs (default: `logs/costs`)
- `whisper_cost_per_minute`: Whisper API pricing
- `gpt4o_mini_input_cost_per_1m_tokens`: GPT-4o-mini input token pricing
- `gpt4o_mini_output_cost_per_1m_tokens`: GPT-4o-mini output token pricing

These settings ensure accurate cost calculations based on current API pricing.
