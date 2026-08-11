# Log Report Automation

A small Python CLI that converts structured CSV operational logs into validated,
stakeholder-friendly Excel reports with reliability analytics and data-quality visibility.

## What it solves

Operational log exports are useful to engineers but awkward to review with stakeholders. This tool
turns a predictable CSV schema into a polished workbook with row-level logs, error and latency
metrics, service comparisons, daily trends, and an audit-friendly validation summary.

It is intended for support engineers, operations analysts, DevOps teams, and Python developers who
need a lightweight reporting step without a database, web application, or BI platform.

```text
CSV logs
   |
   v
Validation and UTC normalization
   |
   v
Optional service/level filtering
   |
   v
Operational analytics
   |
   v
Formatted Excel report
```

## Highlights

- Strict and lenient row validation with actionable CLI summaries
- Reliability metrics: total logs, errors, error rate, and slow requests
- Latency metrics: average, median, P95, and P99 response time
- Service performance and daily operational trend tables
- Native Excel charts for errors by service and daily errors
- Formula-injection protection for untrusted exported text
- Frozen headers, filters, readable widths, number formats, and ERROR-row highlighting
- Deterministic fictional demo data, pytest coverage, packaging, Ruff, Black, and matrix CI

## Installation

Python 3.10 or later is required.

```bash
python -m pip install -e .
```

For development:

```bash
python -m pip install -r requirements-dev.txt
```

The editable install exposes the `log-report` command.

## Quick start

Generate the included demo report:

```bash
log-report \
  --input sample_data/demo_production_logs.csv \
  --output reports/demo-report.xlsx \
  --slow-threshold-ms 500
```

The report opens on `summary` and contains these sheets in order:

1. `summary` - KPI dashboard, service performance, and errors-by-service chart
2. `logs` - normalized, filterable log rows with ERROR highlighting
3. `daily_summary` - daily reliability/latency metrics and error trend chart
4. `data_quality` - stable issue counts and affected source-row details

### Filters

Filters are applied after validation. Level matching is case-insensitive; service matching is exact.

```bash
log-report \
  --input sample_data/demo_production_logs.csv \
  --output reports/api-errors.xlsx \
  --service api \
  --level error
```

If no usable rows match, the command exits successfully without creating a misleading empty report.

## Validation modes

Strict validation is the default:

```bash
log-report --input logs.csv --output reports/report.xlsx --validation strict
```

Strict mode reports issue counts, exits non-zero, and does not generate a workbook when invalid
required operational data is present.

Lenient mode reports the same findings, removes rows that cannot support trustworthy analytics, and
generates a workbook from usable rows:

```bash
log-report --input logs.csv --output reports/report.xlsx --validation lenient
```

The following issues are tracked:

- Invalid timestamp
- Invalid response_ms
- Missing service
- Missing level
- Unknown level (supported values are `INFO`, `WARN`, and `ERROR`)
- Negative response_ms
- Missing message
- Rejected rows

Missing messages are visible as a quality issue but remain usable for operational counts. Rows with
invalid timestamps, invalid/negative response times, missing service/level, or unknown levels are
rejected in lenient mode.

### Invalid-data demo

The repository includes a small fictional file with controlled problems:

```bash
log-report \
  --input sample_data/demo_invalid_logs.csv \
  --output reports/demo-invalid-report.xlsx \
  --validation lenient
```

Run the same command with `--validation strict` to demonstrate the non-zero validation path.

## Input schema

CSV files must contain all five columns:

| Column | Expected value | Handling |
|---|---|---|
| `timestamp` | ISO-like timestamp | Parsed and normalized to UTC |
| `service` | Non-empty service name | Whitespace trimmed; exact-match filtering |
| `level` | `INFO`, `WARN`, or `ERROR` | Trimmed and normalized to uppercase |
| `message` | Log message text | Missing values are preserved and reported |
| `response_ms` | Non-negative number | Converted to numeric for analytics |

Example:

```csv
timestamp,service,level,message,response_ms
2026-01-01T08:00:00Z,api,INFO,Request completed,125
```

Malformed CSV input and missing required columns produce clear errors and non-zero exit codes.

## Analytics

The summary dashboard includes:

- Total logs
- Error count and error rate
- Average and median response time
- P95 and P99 response time
- Slow-request count and configured threshold

Configure the threshold with `--slow-threshold-ms`; a request at or above the threshold is counted
as slow. The default is 500 ms.

Service performance contains request count, error count, error rate, average response time, and P95
response time. It is sorted by highest error rate, then P95 latency, for troubleshooting.

Daily summary contains total rows, errors, error rate, average/P95 response time, and level counts.
Totals use actual rows rather than non-null message values.

## Timestamp behavior

- Timezone-aware timestamps are converted to UTC.
- Timezone-naive timestamps are accepted and interpreted as UTC.
- Demo timestamps use the `Z` UTC suffix.

This deliberately avoids a larger timezone configuration system and gives every report a consistent
timeline.

## Spreadsheet security

Untrusted text beginning with `=` would be emitted by openpyxl as an Excel formula. The exporter
prefixes only that case with an apostrophe so Excel stores it as text. Values beginning with `+`,
`-`, or `@` are already written as text by openpyxl and are preserved unchanged. Tests verify all
four prefixes and scan generated workbooks for unintended formula cells.

## Reproducible demo data

Generate 500 fictional rows covering multiple services, warnings, errors, incident periods, latency
variation, and long-tail response times:

```bash
python tools/generate_demo_csv.py --rows 500 --days 14 --seed 42
```

The fixed seed and fixed UTC start date make repeated output deterministic. No real logs or sensitive
data are used.

## Development and testing

```bash
python -m ruff check .
python -m black . --check
python -m pytest
python -m build
log-report --help
```

Or run the Makefile targets:

```bash
make check
make demo
make report
```

Tests cover schema and row validation, strict/lenient CLI behavior, filtering, row-count regression,
formula safety, reliability/latency calculations, workbook structure, styling hooks, and chart
existence.

GitHub Actions runs the package on Python 3.10, 3.11, and 3.12. Each matrix job installs the actual
package, runs Ruff/Black/pytest, checks the installed CLI, generates a smoke-test workbook, and builds
the wheel/source distribution.

## Project structure

```text
src/log_report/
    __init__.py
    analytics.py
    cli.py
    excel_writer.py
    validation.py
tests/
tools/generate_demo_csv.py
sample_data/
.github/workflows/ci.yml
pyproject.toml
```

## Portfolio screenshots

The workbook and CLI are prepared for these manually captured files:

```text
docs/screenshots/
    01-cli-report-generation.png
    02-summary-dashboard.png
    03-filterable-log-report.png
    04-daily-operational-trends.png
    05-data-quality-validation.png
    06-github-actions-ci.png
```

Older screenshots currently in the folder predate the final validation/dashboard layout. They are
not embedded here; recapture the six views above before publishing the portfolio page.

## Limitations

- The input schema and supported levels are intentionally fixed and small.
- The tool processes one CSV file at a time and keeps data in memory.
- Naive timestamps are assumed to be UTC rather than inferred from local time.
- Lenient mode removes invalid operational rows; it does not attempt to repair source values.
- This is a focused reporting utility, not a live monitoring or log-ingestion platform.
