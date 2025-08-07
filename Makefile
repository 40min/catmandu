.PHONY: run test test-core test-echo analyze-chats analyze-chats-json analyze-participants analyze-commands docker-build docker-up docker-down docker-logs docker-restart docker-test docker-clean docker-ps docker-exec-core docker-exec-echo help help-docker get-update-id set-update-id

run:
	uv run uvicorn catmandu.main:create_app --reload --app-dir src --port 8187

test: test-core test-echo

test-core:
	@echo "=== Running Core Tests ==="
	uv run pytest

test-echo:
	@echo "=== Running Echo Cattackle Tests ==="
	cd cattackles/echo && PYTHONPATH=../../:src uv run pytest

test-notion-config:
	@echo "=== Testing Notion Cattackle Configuration ==="
	python3 scripts/manage_notion_users.py test

test-notion-config-user:
	@echo "=== Testing Notion Configuration for User: $(USER) ==="
	python3 scripts/manage_notion_users.py test "$(USER)"

# Notion user management commands
list-notion-users:
	@echo "=== Listing Notion Users ==="
	@python3 scripts/manage_notion_users.py list

add-notion-user:
	@echo "=== Adding Notion User: $(USER) ==="
	@python3 scripts/manage_notion_users.py add "$(USER)" "$(TOKEN)" "$(PAGE_ID)"

update-notion-user-token:
	@echo "=== Updating Token for Notion User: $(USER) ==="
	@python3 scripts/manage_notion_users.py update "$(USER)" --token "$(TOKEN)"

update-notion-user-page:
	@echo "=== Updating Page ID for Notion User: $(USER) ==="
	@python3 scripts/manage_notion_users.py update "$(USER)" --parent-page-id "$(PAGE_ID)"

remove-notion-user:
	@echo "=== Removing Notion User: $(USER) ==="
	@python3 scripts/manage_notion_users.py remove "$(USER)"

# Show all available commands
help:
	@echo "Catmandu Development Commands:"
	@echo ""
	@echo "Local Development:"
	@echo "  make run             - Run the application locally with uvicorn"
	@echo "  make test            - Run all tests (core + cattackles)"
	@echo "  make test-core       - Run core application tests only"
	@echo "  make test-echo       - Run echo cattackle tests only"
	@echo "  make test-notion-config - Test Notion cattackle configuration"
	@echo "  make test-notion-config-user USER=username - Test specific user config"
	@echo ""
	@echo "Notion User Management:"
	@echo "  make list-notion-users   - List all configured Notion users"
	@echo "  make add-notion-user USER='John Doe' TOKEN=token PAGE_ID=page_id - Add user"
	@echo "  make update-notion-user-token USER='John Doe' TOKEN=new_token - Update token"
	@echo "  make update-notion-user-page USER='John Doe' PAGE_ID=new_page_id - Update page"
	@echo "  make remove-notion-user USER='John Doe' - Remove user"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make help-docker     - Show detailed Docker Compose commands"
	@echo "  make docker-dev      - Start development environment with live reloading"
	@echo "  make docker-debug    - Start services in debug mode"
	@echo "  make docker-up       - Quick start with Docker Compose"
	@echo "  make docker-qnap     - Start with QNAP production configuration"
	@echo "  make docker-down     - Quick stop Docker Compose services"
	@echo "  make docker-logs     - View Docker Compose logs"
	@echo ""
	@echo "Analysis Commands:"
	@echo "  make help-analyze    - Show detailed chat analysis commands"
	@echo "  make help-costs      - Show detailed cost analysis commands"
	@echo "  make analyze-chats   - Quick chat log analysis (local)"
	@echo "  make docker-analyze-chats - Quick chat log analysis (Docker)"
	@echo "  make docker-qnap-analyze-costs-daily - QNAP Docker daily cost analysis"
	@echo ""
	@echo "Data Management Commands:"
	@echo "  make get-update-id   - View current Telegram update_id"
	@echo "  make set-update-id VALUE=123 - Set Telegram update_id"
	@echo ""
	@echo "For detailed help on specific categories, use:"
	@echo "  make help-docker     - Docker Compose commands"
	@echo "  make help-analyze    - Chat analysis commands"
	@echo "  make help-costs      - Cost analysis commands"
	@echo ""
	@echo "QNAP Quick Start:"
	@echo "  make docker-qnap        - Start QNAP deployment"
	@echo "  make docker-qnap-analyze-costs-daily - Analyze costs from container logs"

# Chat log analysis commands
analyze-chats:
	@echo "=== Chat Log Analysis ==="
	@uv run python scripts/analyze_chats.py --output summary

analyze-chats-json:
	@echo "=== Chat Log Analysis (JSON) ==="
	@uv run python scripts/analyze_chats.py --output summary --format json

analyze-participants:
	@echo "=== Unique Participants Analysis ==="
	@uv run python scripts/analyze_chats.py --output participants

analyze-commands:
	@echo "=== Commands Usage Analysis ==="
	@uv run python scripts/analyze_chats.py --output commands

# Analysis with date filter (usage: make analyze-chats-date DATE=2024-01-15)
analyze-chats-date:
	@echo "=== Chat Log Analysis for $(DATE) ==="
	@uv run python scripts/analyze_chats.py --output summary --date $(DATE)

# Cost analysis commands
analyze-costs-daily:
	@echo "=== Daily Cost Analysis ==="
	@uv run python scripts/cost_report.py --daily

analyze-costs-weekly:
	@echo "=== Weekly Cost Analysis ==="
	@uv run python scripts/cost_report.py --weekly

analyze-costs-monthly:
	@echo "=== Monthly Cost Analysis ==="
	@uv run python scripts/cost_report.py --monthly

analyze-costs-daily-detailed:
	@echo "=== Daily Cost Analysis (Detailed) ==="
	@uv run python scripts/cost_report.py --daily --user-breakdown --api-breakdown

analyze-costs-weekly-detailed:
	@echo "=== Weekly Cost Analysis (Detailed) ==="
	@uv run python scripts/cost_report.py --weekly --user-breakdown --api-breakdown

analyze-costs-monthly-detailed:
	@echo "=== Monthly Cost Analysis (Detailed) ==="
	@uv run python scripts/cost_report.py --monthly --user-breakdown --api-breakdown

# Cost analysis with date filter (usage: make analyze-costs-date DATE=2024-01-15)
analyze-costs-date:
	@echo "=== Cost Analysis for $(DATE) ==="
	@uv run python scripts/cost_report.py --daily --date $(DATE) --user-breakdown --api-breakdown

# Cost analysis for date range (usage: make analyze-costs-range START=2024-01-01 END=2024-01-31)
analyze-costs-range:
	@echo "=== Cost Analysis from $(START) to $(END) ==="
	@uv run python scripts/cost_report.py --range --start-date $(START) --end-date $(END) --user-breakdown --api-breakdown

# Docker-based log analysis commands (for containerized logs)
docker-analyze-chats:
	@echo "=== Docker Chat Log Analysis ==="
	docker compose exec catmandu-core uv run python scripts/analyze_chats.py --output summary

docker-analyze-chats-json:
	@echo "=== Docker Chat Log Analysis (JSON) ==="
	docker compose exec catmandu-core uv run python scripts/analyze_chats.py --output summary --format json

docker-analyze-participants:
	@echo "=== Docker Unique Participants Analysis ==="
	docker compose exec catmandu-core uv run python scripts/analyze_chats.py --output participants

docker-analyze-commands:
	@echo "=== Docker Commands Usage Analysis ==="
	docker compose exec catmandu-core uv run python scripts/analyze_chats.py --output commands

docker-analyze-costs-daily:
	@echo "=== Docker Daily Cost Analysis ==="
	docker compose exec catmandu-core uv run python scripts/cost_report.py --daily --user-breakdown --api-breakdown

docker-analyze-costs-weekly:
	@echo "=== Docker Weekly Cost Analysis ==="
	docker compose exec catmandu-core uv run python scripts/cost_report.py --weekly --user-breakdown --api-breakdown

docker-analyze-costs-monthly:
	@echo "=== Docker Monthly Cost Analysis ==="
	docker compose exec catmandu-core uv run python scripts/cost_report.py --monthly --user-breakdown --api-breakdown

# QNAP Docker-based analysis commands
docker-qnap-analyze-chats:
	@echo "=== QNAP Docker Chat Log Analysis ==="
	docker compose -f docker-compose.yml -f docker-compose.qnap.yaml exec catmandu-core uv run python scripts/analyze_chats.py --output summary

docker-qnap-analyze-costs-daily:
	@echo "=== QNAP Docker Daily Cost Analysis ==="
	docker compose -f docker-compose.yml -f docker-compose.qnap.yaml exec catmandu-core uv run python scripts/cost_report.py --daily --user-breakdown --api-breakdown

docker-qnap-analyze-costs-weekly:
	@echo "=== QNAP Docker Weekly Cost Analysis ==="
	docker compose -f docker-compose.yml -f docker-compose.qnap.yaml exec catmandu-core uv run python scripts/cost_report.py --weekly --user-breakdown --api-breakdown

docker-qnap-analyze-costs-monthly:
	@echo "=== QNAP Docker Monthly Cost Analysis ==="
	docker compose -f docker-compose.yml -f docker-compose.qnap.yaml exec catmandu-core uv run python scripts/cost_report.py --monthly --user-breakdown --api-breakdown

# Docker Compose commands
docker-build:
	@echo "=== Building Docker images ==="
	docker compose build

docker-up:
	@echo "=== Starting services with Docker Compose ==="
	docker compose up -d

docker-qnap:
	@echo "=== Starting services with QNAP configuration ==="
	docker compose -f docker-compose.yml -f docker-compose.qnap.yaml up -d

docker-down:
	@echo "=== Stopping Docker Compose services ==="
	docker compose down

docker-qnap-down:
	@echo "=== Stopping QNAP Docker Compose services ==="
	docker compose -f docker-compose.yml -f docker-compose.qnap.yaml down

docker-qnap-logs:
	@echo "=== Viewing QNAP Docker Compose logs ==="
	docker compose -f docker-compose.yml -f docker-compose.qnap.yaml logs -f

docker-qnap-restart:
	@echo "=== Restarting QNAP Docker Compose services ==="
	docker compose -f docker-compose.yml -f docker-compose.qnap.yaml restart

docker-qnap-ps:
	@echo "=== QNAP Docker Compose services status ==="
	docker compose -f docker-compose.yml -f docker-compose.qnap.yaml ps



docker-logs:
	@echo "=== Viewing Docker Compose logs ==="
	docker compose logs -f

docker-restart:
	@echo "=== Restarting Docker Compose services ==="
	docker compose restart

docker-test:
	@echo "=== Testing Docker Compose configuration ==="
	./test-docker compose.sh

docker-clean:
	@echo "=== Cleaning up Docker Compose (including volumes) ==="
	docker compose down -v
	docker compose build --no-cache

docker-ps:
	@echo "=== Docker Compose services status ==="
	docker compose ps

docker-exec-core:
	@echo "=== Opening shell in catmandu-core container ==="
	docker compose exec catmandu-core /bin/bash

docker-exec-echo:
	@echo "=== Opening shell in echo-cattackle container ==="
	docker compose exec echo-cattackle /bin/bash

# Development-specific Docker commands
docker-dev:
	@echo "=== Starting development environment with live reloading ==="
	docker compose up

docker-dev-build:
	@echo "=== Building development images with cache optimization ==="
	DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 docker compose build

docker-debug:
	@echo "=== Starting services in debug mode ==="
	docker compose -f docker-compose.yml -f docker compose.debug.yml up

docker-test-env:
	@echo "=== Starting test environment ==="
	docker compose -f docker-compose.yml -f docker compose.test.yml up -d

docker-run-tests:
	@echo "=== Running tests in containerized environment ==="
	docker compose -f docker-compose.yml -f docker compose.test.yml --profile testing up test-runner

docker-logs-core:
	@echo "=== Viewing core application logs ==="
	docker compose logs -f catmandu-core

docker-logs-echo:
	@echo "=== Viewing echo cattackle logs ==="
	docker compose logs -f echo-cattackle

docker-health:
	@echo "=== Checking service health ==="
	@echo "Core application health:"
	@curl -f http://localhost:8000/health 2>/dev/null && echo " ✓ Core is healthy" || echo " ✗ Core is unhealthy"
	@echo "Echo cattackle health (internal):"
	@docker compose exec catmandu-core curl -f http://echo-cattackle:8001/health 2>/dev/null && echo " ✓ Echo is healthy" || echo " ✗ Echo is unhealthy"

docker-reset:
	@echo "=== Resetting development environment (removing all containers, volumes, and images) ==="
	docker compose down -v
	docker compose down --rmi all
	@echo "Environment reset complete. Use 'make docker-build' to rebuild images."

# Show help for Docker commands
help-docker:
	@echo "Docker Compose Commands:"
	@echo ""
	@echo "Basic Operations:"
	@echo "  make docker-build       - Build Docker images"
	@echo "  make docker-up          - Start services in detached mode"
	@echo "  make docker-qnap        - Start services with QNAP production configuration"
	@echo "  make docker-down        - Stop and remove containers"
	@echo "  make docker-qnap-down   - Stop QNAP configuration containers"
	@echo "  make docker-logs        - Follow logs from all services"
	@echo "  make docker-qnap-logs   - Follow logs from QNAP configuration services"
	@echo "  make docker-qnap-restart - Restart QNAP configuration services"
	@echo "  make docker-qnap-ps     - Show QNAP configuration services status"

	@echo "  make docker-restart     - Restart all services"
	@echo "  make docker-ps          - Show services status"
	@echo ""
	@echo "Development Workflow:"
	@echo "  make docker-dev         - Start development environment with live reloading"
	@echo "  make docker-dev-build   - Build development images with cache optimization"
	@echo "  make docker-debug       - Start services in debug mode with enhanced logging"
	@echo "  make docker-reset       - Reset development environment (rebuild and restart)"
	@echo ""
	@echo "Testing:"
	@echo "  make docker-test-env    - Start test environment"
	@echo "  make docker-run-tests   - Run tests in containerized environment"
	@echo "  make docker-test        - Test Docker Compose configuration"
	@echo ""
	@echo "Monitoring & Debugging:"
	@echo "  make docker-logs-core   - View core application logs only"
	@echo "  make docker-logs-echo   - View echo cattackle logs only"
	@echo "  make docker-health      - Check service health endpoints"
	@echo "  make docker-exec-core   - Open shell in catmandu-core container"
	@echo "  make docker-exec-echo   - Open shell in echo-cattackle container"
	@echo ""
	@echo "Log Analysis (Docker-based):"
	@echo "  make docker-analyze-chats         - Analyze chat logs from container"
	@echo "  make docker-analyze-costs-daily   - Analyze daily costs from container"
	@echo "  make docker-qnap-analyze-chats    - Analyze chat logs from QNAP container"
	@echo "  make docker-qnap-analyze-costs-daily - Analyze daily costs from QNAP container"
	@echo ""
	@echo "Maintenance:"
	@echo "  make docker-clean       - Stop services, remove volumes, and rebuild images"
	@echo ""
	@echo "Quick Development Workflow:"
	@echo "  1. make docker-dev-build  # Build optimized development images"
	@echo "  2. make docker-dev        # Start with live reloading"
	@echo "  3. make docker-logs       # Monitor logs"
	@echo "  4. make docker-health     # Check service health"
	@echo "  5. make docker-down       # Stop when done"
	@echo ""
	@echo "Troubleshooting:"
	@echo "  make docker-ps          # Check service status"
	@echo "  make docker-health      # Verify service health"
	@echo "  make docker-reset       # Reset everything"

# Show help for chat analysis commands
help-analyze:
	@echo "Chat Log Analysis Commands:"
	@echo ""
	@echo "Local Analysis (requires local logs):"
	@echo "  make analyze-chats          - Show summary analysis of all chat logs"
	@echo "  make analyze-chats-json     - Show summary analysis in JSON format"
	@echo "  make analyze-participants   - Show unique participants analysis"
	@echo "  make analyze-commands       - Show commands usage analysis"
	@echo "  make analyze-chats-date DATE=YYYY-MM-DD - Show analysis for specific date"
	@echo ""
	@echo "Docker-based Analysis (works with containerized logs):"
	@echo "  make docker-analyze-chats          - Show summary analysis from container"
	@echo "  make docker-analyze-chats-json     - Show summary analysis in JSON format from container"
	@echo "  make docker-analyze-participants   - Show unique participants analysis from container"
	@echo "  make docker-analyze-commands       - Show commands usage analysis from container"
	@echo ""
	@echo "QNAP Docker Analysis:"
	@echo "  make docker-qnap-analyze-chats     - Show summary analysis from QNAP container"
	@echo ""
	@echo "Direct script usage:"
	@echo "  uv run python scripts/analyze_chats.py --help"

# Update ID management commands
get-update-id:
	@echo "=== Current Telegram update_id ==="
	@docker run --rm -v catmandu-update-data:/data alpine cat /data/update_id.txt 2>/dev/null || echo "File not found"

set-update-id:
	@echo "=== Setting update_id to $(VALUE) ==="
	@docker run --rm -v catmandu-update-data:/data alpine sh -c "mkdir -p /data && echo '$(VALUE)' > /data/update_id.txt"
	@echo "Update ID set to $(VALUE)"

# Show help for cost analysis commands
help-costs:
	@echo "Cost Analysis Commands:"
	@echo ""
	@echo "Local Analysis (requires local logs):"
	@echo "  make analyze-costs-daily    - Show daily cost summary for today"
	@echo "  make analyze-costs-weekly   - Show weekly cost summary for current week"
	@echo "  make analyze-costs-monthly  - Show monthly cost summary for current month"
	@echo "  make analyze-costs-daily-detailed   - Detailed daily cost analysis"
	@echo "  make analyze-costs-weekly-detailed  - Detailed weekly cost analysis"
	@echo "  make analyze-costs-monthly-detailed - Detailed monthly cost analysis"
	@echo "  make analyze-costs-date DATE=YYYY-MM-DD - Detailed analysis for specific date"
	@echo "  make analyze-costs-range START=YYYY-MM-DD END=YYYY-MM-DD - Analysis for date range"
	@echo ""
	@echo "Docker-based Analysis (works with containerized logs):"
	@echo "  make docker-analyze-costs-daily    - Daily cost analysis from container"
	@echo "  make docker-analyze-costs-weekly   - Weekly cost analysis from container"
	@echo "  make docker-analyze-costs-monthly  - Monthly cost analysis from container"
	@echo ""
	@echo "QNAP Docker Analysis:"
	@echo "  make docker-qnap-analyze-costs-daily   - Daily cost analysis from QNAP container"
	@echo "  make docker-qnap-analyze-costs-weekly  - Weekly cost analysis from QNAP container"
	@echo "  make docker-qnap-analyze-costs-monthly - Monthly cost analysis from QNAP container"
	@echo ""
	@echo "Examples:"
	@echo "  make analyze-costs-date DATE=2024-01-15"
	@echo "  make analyze-costs-range START=2024-01-01 END=2024-01-31"
	@echo ""
	@echo "Direct script usage:"
	@echo "  uv run python scripts/cost_report.py --help"
