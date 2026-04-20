.PHONY: install test lint format check run

install:
	uv sync --extra dev

test:
	uv run pytest --tb=short -q

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run mypy src

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

check: lint test

run:
	uv run mcp-business-workflows
