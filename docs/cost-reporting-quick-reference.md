# Cost Reporting Quick Reference

## Common Commands

### Daily Reports

```bash
# Today's costs
python scripts/cost_report.py --daily

# Specific date with user breakdown
python scripts/cost_report.py --daily --date 2024-01-15 --user-breakdown

# Today with full analysis
python scripts/cost_report.py --daily --user-breakdown --api-breakdown
```

### Weekly Reports

```bash
# Current week
python scripts/cost_report.py --weekly

# Week containing specific date
python scripts/cost_report.py --weekly --date 2024-01-15

# Weekly with user analysis
python scripts/cost_report.py --weekly --user-breakdown
```

### Monthly Reports

```bash
# Current month
python scripts/cost_report.py --monthly

# Specific month with full breakdown
python scripts/cost_report.py --monthly --date 2024-01-15 --user-breakdown --api-breakdown
```

### Custom Ranges

```bash
# Last 7 days
python scripts/cost_report.py --range --start-date 2024-01-08 --end-date 2024-01-15

# Full quarter analysis
python scripts/cost_report.py --range --start-date 2024-01-01 --end-date 2024-03-31 --user-breakdown --api-breakdown
```

## Report Options

| Option                    | Description                                              |
| ------------------------- | -------------------------------------------------------- |
| `--daily`                 | Generate daily report                                    |
| `--weekly`                | Generate weekly report                                   |
| `--monthly`               | Generate monthly report                                  |
| `--range`                 | Custom date range (requires --start-date and --end-date) |
| `--date YYYY-MM-DD`       | Specific date for daily/weekly/monthly reports           |
| `--start-date YYYY-MM-DD` | Start date for range reports                             |
| `--end-date YYYY-MM-DD`   | End date for range reports                               |
| `--user-breakdown`        | Include detailed user statistics                         |
| `--api-breakdown`         | Include API usage analysis                               |

## Quick Analysis Workflows

### Daily Monitoring

```bash
# Morning cost check
python scripts/cost_report.py --daily --date $(date -d "yesterday" +%Y-%m-%d)

# Detailed daily analysis
python scripts/cost_report.py --daily --user-breakdown --api-breakdown
```

### Weekly Review

```bash
# Weekly team usage
python scripts/cost_report.py --weekly --user-breakdown

# Weekly efficiency analysis
python scripts/cost_report.py --weekly --api-breakdown
```

### Monthly Budget Review

```bash
# Complete monthly analysis
python scripts/cost_report.py --monthly --user-breakdown --api-breakdown

# Compare with previous month
python scripts/cost_report.py --range --start-date 2024-01-01 --end-date 2024-01-31 --user-breakdown
python scripts/cost_report.py --range --start-date 2024-02-01 --end-date 2024-02-29 --user-breakdown
```

## Key Metrics to Monitor

### Cost Efficiency

- **Cost per minute**: Should remain consistent (~$0.006/minute for Whisper)
- **API cost distribution**: Whisper typically 99%+, GPT-4o-mini <1%
- **Processing speed**: Higher ratios indicate better performance

### Usage Patterns

- **Requests per day**: Track usage trends
- **Average audio duration**: Monitor typical usage patterns
- **User distribution**: Identify heavy users for potential optimization

### Performance Indicators

- **Processing time**: Should be consistently fast
- **File size efficiency**: Cost per MB should be stable
- **Token usage**: Monitor GPT-4o-mini efficiency

## Automation Examples

### Daily Cost Alert (Bash)

```bash
#!/bin/bash
# daily-cost-check.sh
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
REPORT=$(python scripts/cost_report.py --daily --date $YESTERDAY)
COST=$(echo "$REPORT" | grep "Total Cost:" | awk '{print $3}' | tr -d '$')

if (( $(echo "$COST > 1.00" | bc -l) )); then
    echo "High daily cost alert: $COST" | mail -s "Catmandu Cost Alert" admin@example.com
fi
```

### Weekly Summary (Cron)

```bash
# Add to crontab for Monday morning reports
0 9 * * 1 cd /path/to/catmandu && python scripts/cost_report.py --weekly --user-breakdown | mail -s "Weekly Audio Processing Report" team@example.com
```
