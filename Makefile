.PHONY: run test

run:
	uv run uvicorn catmandu.main:app --reload --app-dir src --port 8187

test:
	uv run pytest
