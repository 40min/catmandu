.PHONY: run test test-core test-echo analyze-chats analyze-chats-json analyze-participants analyze-commands docker-build docker-up docker-down docker-logs docker-restart docker-test docker-clean docker-ps docker-exec-core docker-exec-echo help help-docker

run:
	uv run uvicorn catmandu.main:create_app --reload --app-dir src --port 8187

test: test-core test-echo

test-core:
	@echo "=== Running Core Tests ==="
	uv run pytest

test-echo:
	@echo "=== Running Echo Cattackle Tests ==="
	cd cattackles/echo && PYTHONPATH=../../ uv run pytest

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
	@echo "Development & Debugging:"
	@echo "  make docker-exec-core   - Open shell in catmandu-core container"
	@echo "  make docker-exec-echo   - Open shell in echo-cattackle container"
	@echo "  make docker-test        - Test Docker Compose configuration"
	@echo "  make docker-clean       - Stop services, remove volumes, and rebuild images"
	@echo ""
	@echo "Development workflow:"
	@echo "  1. make docker-build    # Build images"
	@echo "  2. make docker-up       # Start services"
	@echo "  3. make docker-logs     # Monitor logs"
	@echo "  4. make docker-down     # Stop when done"
	@echo ""
	@echo "Troubleshooting:"
	@echo "  make docker-ps          # Check service status"
	@echo "  make docker-exec-core   # Debug core service"
	@echo "  make docker-clean       # Reset everything"

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
