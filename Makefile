.PHONY: install lint format typecheck test check

install:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

test:
	uv run pytest --cov --cov-report=term-missing

check: lint typecheck test
