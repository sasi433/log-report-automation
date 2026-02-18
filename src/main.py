from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.report_utils import apply_filters, load_logs, write_excel_report

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INPUT_MISSING = 2
EXIT_OUTPUT_ERROR = 3


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments for `log-report`.

    Returns:
        argparse.Namespace with input/output/service/level
    """
    parser = argparse.ArgumentParser(
        prog="log-report",
        description="Log Report Automation - generate simple reports from CSV logs.",
    )
    parser.add_argument("--input", default="sample_data/example.csv", help="Path to input CSV")
    parser.add_argument("--output", default="reports/report.xlsx", help="Path to output XLSX")
    parser.add_argument(
        "--service", default=None, help="Filter by service name (e.g., api, auth, db)"
    )
    parser.add_argument("--level", default=None, help="Filter by level (e.g., INFO, ERROR)")
    return parser.parse_args()


def print_stats(df: pd.DataFrame) -> None:
    """
    Print basic stats to console for quick verification.
    """
    print("\n--- Basic stats ---")
    print(f"Total rows: {len(df)}")

    print("\nCount by level:")
    print(df["level"].value_counts(dropna=False).to_string())

    print("\nCount by service:")
    print(df["service"].value_counts(dropna=False).to_string())

    bad_ts = int(df["timestamp"].isna().sum())
    bad_ms = int(df["response_ms"].isna().sum())
    if bad_ts or bad_ms:
        print("\nData quality warnings:")
        if bad_ts:
            print(f"- Invalid timestamps: {bad_ts}")
        if bad_ms:
            print(f"- Invalid response_ms values: {bad_ms}")


def main() -> int:
    """
    Main CLI flow:
      - load CSV
      - apply filters
      - write XLSX report
    """
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    print("✅ Log Report Automation")
    print(f"Input : {input_path.resolve()}")
    print(f"Output: {output_path.resolve()}")

    if args.service or args.level:
        print("\n--- Active filters ---")
        if args.service:
            print(f"service = {args.service}")
        if args.level:
            print(f"level   = {args.level.upper()}")

    try:
        df = load_logs(input_path)
        df = apply_filters(df, args.service, args.level)
    except FileNotFoundError as exc:
        print(f"\n❌ {exc}")
        return EXIT_INPUT_MISSING
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        return EXIT_ERROR

    if df.empty:
        print("\n⚠️ No rows match the given filters. No report generated.")
        return EXIT_OK

    print_stats(df)

    try:
        write_excel_report(df, output_path)
    except Exception as exc:
        print(f"\n❌ Failed to write Excel report: {exc}")
        return EXIT_OUTPUT_ERROR

    print("\n✅ Excel report generated successfully.")
    print("Sheets: logs, summary, daily_summary")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
