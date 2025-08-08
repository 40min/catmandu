# QNAP Deployment and Log Analysis

This document describes how to deploy Catmandu on QNAP systems and analyze logs and costs from the host machine.

## QNAP Deployment

The QNAP deployment configuration extends the main Docker Compose setup with host volume mounts, allowing direct access to logs and data from the QNAP host system.

### Quick Start

1. **Setup log directories:**

   ```bash
   make docker-qnap-setup
   ```

2. **Start services:**

   ```bash
   make docker-qnap
   ```

3. **Monitor logs:**
   ```bash
   make docker-qnap-logs
   ```

### Directory Structure

The QNAP setup creates the following host directories:

```
./logs/
├── chats/          # Chat interaction logs
├── costs/          # Cost tracking logs for audio processing
└── cattackles/     # Cattackle-specific logs

./.data/            # Application data (Telegram update IDs, etc.)
```

## Log Analysis from Host

With the QNAP setup, logs are directly accessible from the host machine, enabling analysis without entering containers.

### Cost Analysis Commands

#### Basic Cost Reports

```bash
# Daily cost analysis
make analyze-qnap-costs-daily

# Weekly cost analysis
make analyze-qnap-costs-weekly

# Monthly cost analysis
make analyze-qnap-costs-monthly
```

#### Standard Cost Analysis (for comparison)

```bash
# Standard daily cost analysis (from container)
make analyze-costs-daily

# Detailed daily analysis with user and API breakdowns
make analyze-costs-daily-detailed
```

### Chat Analysis Commands

```bash
# Analyze chat logs from host-mounted directory
make analyze-qnap-chats

# Standard chat analysis (from container)
make analyze-chats
```

## QNAP-Specific Docker Commands

### Service Management

```bash
# Start QNAP configuration
make docker-qnap

# Stop QNAP configuration
make docker-qnap-down

# Restart QNAP services
make docker-qnap-restart

# Check service status
make docker-qnap-ps
```

### Log Monitoring

```bash
# Follow all service logs
make docker-qnap-logs

# Standard Docker logs (for comparison)
make docker-logs
```

## Volume Configuration

The QNAP configuration (`docker-compose.qnap.yaml`) overrides the standard volume configuration:

### Standard Configuration (Named Volumes)

```yaml
volumes:
  - update_data:/app/.data
  - chat_logs:/app/logs
  - cost_logs:/app/logs/costs
```

### QNAP Configuration (Host Bind Mounts)

```yaml
volumes:
  - ./logs:/app/logs
  - ./logs/costs:/app/logs/costs
  - ./.data:/app/.data
```

## Benefits of QNAP Setup

1. **Direct Log Access**: Analyze logs without entering containers
2. **Persistent Storage**: Logs survive container recreation
3. **Host Integration**: Easy backup and monitoring from QNAP system
4. **Performance**: Direct file system access for analysis scripts
5. **Debugging**: Easier troubleshooting with direct log access

## Cost Analysis Features

The cost analysis system tracks audio processing expenses with detailed breakdowns:

### Available Reports

- **Daily Reports**: Costs for specific dates
- **Weekly Reports**: Costs for week ranges
- **Monthly Reports**: Costs for month ranges
- **Custom Range Reports**: Costs for any date range

### Report Details

- Total requests and audio duration
- Whisper API costs (transcription)
- OpenAI model costs (processing)
- User-specific breakdowns
- API usage analysis
- Efficiency metrics

### Example Output

```
📊 Daily Cost Report for 2024-01-15
==================================================
Total Requests: 25
Total Audio Duration: 45.2 minutes
Total File Size: 123.4 MB
Average Processing Time: 3.2 seconds

💰 Cost Breakdown:
  Whisper API: $0.2712
  OpenAI Model: $0.0890
  Total Cost:  $0.3602

👥 User Breakdown (5 users)
================================================================================
User                      Requests   Duration     Cost       Avg/Min
--------------------------------------------------------------------------------
John Doe                  10         18.5 minutes $0.1456    $0.0079
Jane Smith                8          12.3 minutes $0.0987    $0.0080
...
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure log directories have proper permissions

   ```bash
   chmod -R 755 logs/
   chmod -R 755 .data/
   ```

2. **Missing Directories**: Run setup command

   ```bash
   make docker-qnap-setup
   ```

3. **No Cost Data**: Verify audio processing is enabled and configured
   ```bash
   # Check environment variables
   grep AUDIO_PROCESSING_ENABLED .env
   grep OPENAI_API_KEY .env
   ```

### Log Locations

- **Container logs**: `docker compose logs`
- **Application logs**: `./logs/` (host directory)
- **Cost logs**: `./logs/costs/` (host directory)
- **Chat logs**: `./logs/chats/` (host directory)

## Integration with Analysis Scripts

The analysis scripts automatically detect the QNAP environment and use host-mounted logs when available:

```bash
# These commands automatically use host logs in QNAP setup
make analyze-qnap-costs-daily
make analyze-qnap-chats

# Environment variable override for custom paths
COST_LOGS_DIR=./custom/path make analyze-costs-daily
```
