.PHONY: run test test-core test-echo analyze-chats analyze-chats-json analyze-participants analyze-commands docker-build docker-up docker-down docker-logs docker-restart docker-test docker-clean docker-ps docker-exec-core docker-exec-echo help help-docker

run:
	uv run uvicorn catmandu.main:create_app --reload --app-dir src --port 8187

test: test-core test-echo

test-core:
	@echo "=== Running Core Tests ==="
	uv run pytest

test-echo:
	@echo "=== Running Echo Cattackle Tests ==="
	cd cattackles/echo && PYTHONPATH=../../:src uv run pytest

# Show all available commands
help:
	@echo "Catmandu Development Commands:"
	@echo ""
	@echo "Local Development:"
	@echo "  make run             - Run the application locally with uvicorn"
	@echo "  make test            - Run all tests (core + cattackles)"
	@echo "  make test-core       - Run core application tests only"
	@echo "  make test-echo       - Run echo cattackle tests only"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make help-docker     - Show detailed Docker Compose commands"
	@echo "  make docker-dev      - Start development environment with live reloading"
	@echo "  make docker-debug    - Start services in debug mode"
	@echo "  make docker-up       - Quick start with Docker Compose"
	@echo "  make docker-down     - Quick stop Docker Compose services"
	@echo "  make docker-logs     - View Docker Compose logs"
	@echo ""
	@echo "Analysis Commands:"
	@echo "  make help-analyze    - Show detailed chat analysis commands"
	@echo "  make analyze-chats   - Quick chat log analysis"
	@echo ""
	@echo "For detailed help on specific categories, use:"
	@echo "  make help-docker     - Docker Compose commands"
	@echo "  make help-analyze    - Chat analysis commands"

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

# Docker Compose commands
docker-build:
	@echo "=== Building Docker images ==="
	docker-compose build

docker-up:
	@echo "=== Starting services with Docker Compose ==="
	docker-compose up -d

docker-down:
	@echo "=== Stopping Docker Compose services ==="
	docker-compose down

docker-logs:
	@echo "=== Viewing Docker Compose logs ==="
	docker-compose logs -f

docker-restart:
	@echo "=== Restarting Docker Compose services ==="
	docker-compose restart

docker-test:
	@echo "=== Testing Docker Compose configuration ==="
	./test-docker-compose.sh

docker-clean:
	@echo "=== Cleaning up Docker Compose (including volumes) ==="
	docker-compose down -v
	docker-compose build --no-cache

docker-ps:
	@echo "=== Docker Compose services status ==="
	docker-compose ps

docker-exec-core:
	@echo "=== Opening shell in catmandu-core container ==="
	docker-compose exec catmandu-core /bin/bash

docker-exec-echo:
	@echo "=== Opening shell in echo-cattackle container ==="
	docker-compose exec echo-cattackle /bin/bash

# Development-specific Docker commands
docker-dev:
	@echo "=== Starting development environment with live reloading ==="
	docker-compose up

docker-dev-build:
	@echo "=== Building development images with cache optimization ==="
	DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 docker-compose build

docker-debug:
	@echo "=== Starting services in debug mode ==="
	docker-compose -f docker-compose.yml -f docker-compose.debug.yml up

docker-test-env:
	@echo "=== Starting test environment ==="
	docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d

docker-run-tests:
	@echo "=== Running tests in containerized environment ==="
	docker-compose -f docker-compose.yml -f docker-compose.test.yml --profile testing up test-runner

docker-logs-core:
	@echo "=== Viewing core application logs ==="
	docker-compose logs -f catmandu-core

docker-logs-echo:
	@echo "=== Viewing echo cattackle logs ==="
	docker-compose logs -f echo-cattackle

docker-health:
	@echo "=== Checking service health ==="
	@echo "Core application health:"
	@curl -f http://localhost:8000/health 2>/dev/null && echo " ✓ Core is healthy" || echo " ✗ Core is unhealthy"
	@echo "Echo cattackle health (internal):"
	@docker-compose exec catmandu-core curl -f http://echo-cattackle:8001/health 2>/dev/null && echo " ✓ Echo is healthy" || echo " ✗ Echo is unhealthy"

docker-reset:
	@echo "=== Resetting development environment ==="
	docker-compose down -v
	docker-compose build
	docker-compose up -d

# Show help for Docker commands
help-docker:
	@echo "Docker Compose Commands:"
	@echo ""
	@echo "Basic Operations:"
	@echo "  make docker-build       - Build Docker images"
	@echo "  make docker-up          - Start services in detached mode"
	@echo "  make docker-down        - Stop and remove containers"
	@echo "  make docker-logs        - Follow logs from all services"
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
	@echo "  make analyze-chats          - Show summary analysis of all chat logs"
	@echo "  make analyze-chats-json     - Show summary analysis in JSON format"
	@echo "  make analyze-participants   - Show unique participants analysis"
	@echo "  make analyze-commands       - Show commands usage analysis"
	@echo "  make analyze-chats-date DATE=YYYY-MM-DD - Show analysis for specific date"
	@echo ""
	@echo "Direct script usage:"
	@echo "  uv run python scripts/analyze_chats.py --help"
