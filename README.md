# Log Report Automation

A small Python tool that reads log data from a CSV file and generates an Excel report.

## Project structure

- `src/` - source code
- `sample_data/` - sample input data
- `requirements.txt` - python dependencies

## Setup

```bash
python -m pip install -r requirements.txt

Run with the sample CSV:

```bash
python src/main.py --input sample_data/example.csv --output report.xlsx