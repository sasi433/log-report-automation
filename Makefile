.PHONY: fmt lint test check

fmt:
	python -m ruff check . --fix
	python -m black .

lint:
	python -m ruff check .
	python -m black . --check

test:
	python -m pytest

check: lint test
