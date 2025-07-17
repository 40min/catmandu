.PHONY: run test

run:
	uv run uvicorn catmandu.main:app --reload --app-dir .

test:
	uv run pytest
