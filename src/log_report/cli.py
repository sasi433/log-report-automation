from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .analytics import apply_filters
from .excel_writer import write_excel_report
from .validation import ISSUE_ORDER, LogValidationError, ValidationResult, load_logs

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INPUT_MISSING = 2
EXIT_OUTPUT_ERROR = 3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for ``log-report``."""
    parser = argparse.ArgumentParser(
        prog="log-report",
        description="Validate CSV operational logs and generate an Excel report.",
    )
    parser.add_argument("--input", default="sample_data/example.csv", help="Path to input CSV")
    parser.add_argument("--output", default="reports/report.xlsx", help="Path to output XLSX")
    parser.add_argument("--service", default=None, help="Filter by exact service name")
    parser.add_argument("--level", default=None, help="Filter by level (INFO, WARN, ERROR)")
    parser.add_argument(
        "--validation",
        choices=("strict", "lenient"),
        default="strict",
        help="Validation behavior for invalid rows (default: strict)",
    )
    return parser.parse_args(argv)


def print_stats(df: pd.DataFrame) -> None:
    """Print basic row counts for quick command-line verification."""
    print("\n--- Report stats ---")
    print(f"Total rows: {len(df)}")
    print("\nCount by level:")
    print(df["level"].value_counts(dropna=False).to_string())
    print("\nCount by service:")
    print(df["service"].value_counts(dropna=False).to_string())


def print_quality(result: ValidationResult) -> None:
    """Print a concise validation summary for lenient report generation."""
    if not result.issues:
        return
    print(f"\nValidation issues: {result.affected_rows} affected rows")
    counts = result.issue_counts
    for issue in ISSUE_ORDER:
        if counts[issue]:
            print(f"- {issue}: {counts[issue]}")
    print(f"- Rejected rows: {result.rejected_rows}")


def main(argv: list[str] | None = None) -> int:
    """Load, validate, filter, and export operational log data."""
    args = parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)

    print("Log Report Automation")
    print(f"Input : {input_path.resolve()}")
    print(f"Output: {output_path.resolve()}")

    if args.service or args.level:
        print("\n--- Active filters ---")
        if args.service:
            print(f"service = {args.service}")
        if args.level:
            print(f"level   = {args.level.upper()}")

    try:
        validation = load_logs(input_path, mode=args.validation)
        df = apply_filters(validation.data, args.service, args.level)
    except FileNotFoundError as exc:
        print(f"\nError: {exc}")
        return EXIT_INPUT_MISSING
    except LogValidationError as exc:
        print(f"\n{exc}")
        return EXIT_ERROR
    except Exception as exc:
        print(f"\nError: {exc}")
        return EXIT_ERROR

    print_quality(validation)
    if df.empty:
        print("\nNo usable rows match the given filters. No report generated.")
        return EXIT_OK

    print_stats(df)
    try:
        write_excel_report(df, output_path, validation)
    except Exception as exc:
        print(f"\nFailed to write Excel report: {exc}")
        return EXIT_OUTPUT_ERROR

    print("\nExcel report generated successfully.")
    print("Sheets: summary, logs, daily_summary, data_quality")
    return EXIT_OK


def run() -> None:
    """Console-script entrypoint for the ``log-report`` command."""
    raise SystemExit(main())


if __name__ == "__main__":
    run()
