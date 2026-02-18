# Log Report Automation

Convert structured CSV log exports into a clean, professional Excel report with structured summary sheets.

This tool transforms operational log data into a stakeholder-friendly Excel report using a simple CLI interface.

---

## 🔎 Overview

`log-report` is a lightweight command-line tool that:

- Reads structured CSV log exports
- Validates schema
- Normalizes and filters data
- Generates a formatted Excel report
- Produces operational summary sheets

The goal is to bridge the gap between raw logs and business-ready reporting.

---

## ✨ Features

### 📄 logs Sheet
- Complete log table
- Auto filter enabled
- Frozen header row
- Auto-sized columns
- Conditional highlighting for `ERROR` rows
- Clean header styling

### 📊 summary Sheet
- Key metrics (total rows, error count)
- Counts by level (INFO / WARN / ERROR)
- Counts by service
- Clear section layout

### 📅 daily_summary Sheet
- Daily totals
- Daily error counts
- Per-level breakdown per day

---

## 📦 Installation

### Editable Install (Recommended for Development)

```bash
python -m pip install -e .
```

This exposes the CLI command:

```bash
log-report
```

---

## ▶️ Usage

### Basic Usage

```bash
log-report --input sample_data/example.csv --output reports/report.xlsx
```

### Generate Production-Like Demo Data

```bash
python tools/generate_demo_csv.py --rows 500 --days 14
```

Then generate the report:

```bash
log-report --input sample_data/demo_production_logs.csv --output reports/report.xlsx
```

### Filter by Service

```bash
log-report --input sample_data/example.csv --output reports/report.xlsx --service api
```

### Filter by Level

```bash
log-report --input sample_data/example.csv --output reports/report.xlsx --level ERROR
```

### Combine Filters

```bash
log-report \
  --input sample_data/demo_production_logs.csv \
  --output reports/report.xlsx \
  --service api \
  --level ERROR
```

The output file is overwritten if the same path is used.

---

## 📥 Input Format

The input must be a CSV file with the following columns:

- `timestamp`
- `service`
- `level`
- `message`
- `response_ms`

Example:

```csv
timestamp,service,level,message,response_ms
2026-02-04T07:51:33Z,search,ERROR,Upstream timeout,1256
```

### Behavior

- `timestamp` is parsed using `pandas.to_datetime`
- `response_ms` is converted to numeric
- `level` is normalized to uppercase
- Rows are sorted chronologically
- Missing required columns trigger a validation error

---

## 📤 Output Structure

The generated Excel file contains three sheets:

---

### 1️⃣ logs

Columns:

- date
- time
- service
- level
- message
- response_ms

Features:

- Header row styled
- Auto filter enabled
- `ERROR` rows conditionally highlighted
- Columns auto-sized

---

### 2️⃣ summary

Contains:

**Key Metrics**
- total_rows
- error_count

**Counts by Level**
- INFO
- WARN
- ERROR

**Counts by Service**
- api
- auth
- db
- payments
- search
- notifications

---

### 3️⃣ daily_summary

Columns:

- date
- total_rows
- error_count
- INFO
- WARN
- ERROR

Provides a daily operational overview.

---

## 🧪 Development

### Lint

```bash
python -m ruff check . --fix
```

### Format

```bash
python -m black .
```

### Run Tests

```bash
python -m pytest
```

Test coverage includes:

- CSV schema validation
- File-not-found handling
- Excel integration test (sheet existence and structure)

---

## 🏗 Project Structure

```
log-report-automation/
│
├── src/
│   ├── cli.py
│   ├── main.py
│   └── report_utils.py
│
├── tests/
│   ├── test_validation.py
│   └── test_report_integration.py
│
├── sample_data/
│   ├── example.csv
│   └── demo_production_logs.csv
│
├── tools/
│   └── generate_demo_csv.py
│
├── pyproject.toml
└── README.md
```

---

## 🎯 Intended Use Cases

- DevOps teams exporting structured logs
- Support engineers creating Excel summaries
- Internal operational reporting
- Incident review reporting
- Client-facing Excel deliverables
- Lightweight reporting without BI tools

---

## 🧠 Design Principles

- Simple CLI interface
- Deterministic output
- Clear validation errors
- Separation of data logic and formatting
- Testable and reproducible
- No external services required
- Works fully offline
