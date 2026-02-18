# Log Report Automation

Convert structured CSV log exports into a clean, professional Excel report with summary sheets.

This tool is designed for situations where logs are exported from a system and need to be analyzed or shared in Excel format with non-technical stakeholders.

---

## 🚀 What This Tool Does

Given a CSV log file, this tool generates an Excel report (`.xlsx`) containing:

- **logs** sheet  
  - Full log table  
  - Filterable  
  - Frozen header row  
  - Auto-sized columns  
  - Conditional highlighting for `ERROR` rows  

- **summary** sheet  
  - Key metrics (total rows, error count)  
  - Counts by level  
  - Counts by service  

- **daily_summary** sheet  
  - Daily totals  
  - Daily error counts  
  - Counts per level  

The output file is overwritten each time you run the command with the same output path.

---

## 📦 Installation

### Option 1: Local editable install (recommended for development)

```bash
python -m pip install -e .
```

This exposes the CLI command:

```bash
log-report
```

---

## ▶️ Usage

### Basic usage

```bash
log-report --input sample_data/example.csv --output reports/report.xlsx
```

### With filters

Filter by service:

```bash
log-report --input sample_data/example.csv --output reports/report.xlsx --service api
```

Filter by level:

```bash
log-report --input sample_data/example.csv --output reports/report.xlsx --level ERROR
```

You can combine filters:

```bash
log-report --input sample_data/example.csv --output reports/report.xlsx --service api --level ERROR
```

---

## 📥 Input Format

Input must be a CSV file with the following columns:

- `timestamp`
- `service`
- `level`
- `message`
- `response_ms`

Example:

```csv
timestamp,service,level,message,response_ms
2025-12-30T10:01:00,auth,INFO,Login ok,120
2025-12-30T10:02:00,auth,ERROR,Token expired,0
```

Notes:

- `timestamp` is parsed using `pandas.to_datetime`
- `response_ms` is converted to numeric
- Rows are sorted by timestamp before report generation

If required columns are missing, the tool fails with a clear validation error.

---

## 📤 Output Structure

The generated Excel file contains three sheets:

### 1️⃣ logs

Columns:

- date
- time
- service
- level
- message
- response_ms

Features:

- Header row frozen
- Auto filter enabled
- Conditional formatting for `ERROR` rows
- Auto-sized columns

---

### 2️⃣ summary

Contains:

- Key metrics table  
  - total_rows  
  - error_count  

- Counts by level  
- Counts by service  

---

### 3️⃣ daily_summary

Contains:

- date  
- total_rows  
- error_count  
- Counts per level (e.g., INFO, ERROR)

---

## 🧪 Development

### Run linting

```bash
python -m ruff check . --fix
```

### Format code

```bash
python -m black .
```

### Run tests

```bash
python -m pytest
```

The project includes:

- Unit tests for validation
- Integration test verifying Excel file structure and sheet names

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
│   └── example.csv
│
├── pyproject.toml
└── README.md
```

---

## 🎯 Intended Use Cases

- Teams exporting logs from services into CSV
- Support engineers creating Excel summaries
- DevOps teams needing quick report generation
- Small internal reporting workflows
- Client-facing Excel deliverables from raw log exports

---

## 🧠 Design Goals

- Simple CLI interface
- Clean Excel output
- Predictable structure
- Clear validation errors
- Testable and reproducible
- No external services required

