.PHONY: fmt lint test build demo report check

fmt:
	python -m ruff check . --fix
	python -m black .

lint:
	python -m ruff check .
	python -m black . --check

test:
	python -m pytest

build:
	python -m build

demo:
	python tools/generate_demo_csv.py --rows 500 --days 14 --seed 42

report:
	log-report --input sample_data/demo_production_logs.csv --output reports/demo-report.xlsx --slow-threshold-ms 500

check: lint test build
