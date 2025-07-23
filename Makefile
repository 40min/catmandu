.PHONY: run test

run:
	uv run uvicorn catmandu.main:create_app --reload --app-dir src --port 8187

test:
	uv run pytest
