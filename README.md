# Log Report Automation

A small Python tool that reads log data from a CSV file and generates an Excel report.

## Project structure

- `src/` - source code
- `sample_data/` - sample input data
- `reports/` - generated Excel reports
- `requirements.txt` - python dependencies

## Setup

```bash
python -m pip install -r requirements.txt
```

## Usage

```bash
python src/main.py --input sample_data/example.csv --output reports/report.xlsx
```

## Optional filter

Filter by service name:

```bash
python src/main.py --service api
```

Filter by log level:

```bash
python src/main.py --level ERROR
```

Combine filters:

```bash
python src/main.py --service auth --level INFO
```

## Report output

The generated Excel file contains the following sheets:

### logs

- Raw log rows with columns: date, time, service, level, message, response_ms
- Includes frozen header row and Excel filters for easy exploration

### summary

Overall metrics including:
- total rows
- error count
- counts by log level
- counts by service

### daily_summary

Per-day aggregation showing:
- total rows per day
- error count per day
- level-based counts (INFO, ERROR, etc.)

## Exit codes

The CLI returns meaningful exit codes:
- 0 – success
- 1 – invalid CSV or processing error
- 2 – input file not found
- 3 – failed to write output report

## Notes
- All summaries respect applied CLI filters (--service, --level)
- Output files are written to the reports/ directory by default
- Designed to be extended with additional report formats and analytics