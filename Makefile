.PHONY: run test analyze-chats analyze-chats-json analyze-participants analyze-commands

run:
	uv run uvicorn catmandu.main:create_app --reload --app-dir src --port 8187

test:
	uv run pytest

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
