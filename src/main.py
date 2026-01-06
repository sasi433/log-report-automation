from __future__ import annotations

import argparse
from pathlib import Path

from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

import pandas as pd

REQUIRED_COLUMNS = ["timestamp", "service", "level", "message", "response_ms"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Log Report Automation - generate simple reports from CSV logs."
    )
    parser.add_argument(
        "--input",
        default="sample_data/example.csv",
        help="Path to input CSV file (default: sample_data/example.csv)",
    )
    parser.add_argument(
        "--output",
        default="reports/report.xlsx",
        help="Path to output Excel report (default: reports/report.xlsx)",
    )
    parser.add_argument(
        "--service",
        default=None,
        help="Filter by service name (e.g., api, auth, db)",
    )
    parser.add_argument(
        "--level",
        default=None,
        help="Filter by level (e.g., INFO, ERROR)",
    )
    return parser.parse_args()


def apply_filters(df: pd.DataFrame, service: str | None, level: str | None) -> pd.DataFrame:
    filtered = df

    if service:
        filtered = filtered[filtered["service"].astype(str) == service]

    if level:
        filtered = filtered[filtered["level"].astype(str).str.upper() == level.upper()]

    return filtered.reset_index(drop=True)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "CSV schema invalid. Missing columns: "
            + ", ".join(missing)
            + f"\nExpected columns: {', '.join(REQUIRED_COLUMNS)}"
        )

    # Basic cleanup / type handling
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["response_ms"] = pd.to_numeric(df["response_ms"], errors="coerce")
    df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
    df["date"] = df["timestamp"].dt.date

    return df


def print_stats(df: pd.DataFrame) -> None:
    print("\n--- Basic stats ---")
    print(f"Total rows: {len(df)}")

    # Count by level (INFO/ERROR)
    print("\nCount by level:")
    print(df["level"].value_counts(dropna=False).to_string())

    # Count by service
    print("\nCount by service:")
    print(df["service"].value_counts(dropna=False).to_string())

    # Optional: how many invalid timestamps / response_ms
    bad_ts = int(df["timestamp"].isna().sum())
    bad_ms = int(df["response_ms"].isna().sum())
    if bad_ts or bad_ms:
        print("\nData quality warnings:")
        if bad_ts:
            print(f"- Invalid timestamps: {bad_ts}")
        if bad_ms:
            print(f"- Invalid response_ms values: {bad_ms}")


def format_worksheet_columns(ws) -> None:
    # Auto-size columns based on max length (simple + good enough)
    for col_idx, col_cells in enumerate(ws.columns, start=1):
        max_len = 0
        for cell in col_cells:
            if cell.value is None:
                continue
            max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 40)


def write_excel_report(df: pd.DataFrame, output_path: Path) -> None:
    # Make sure parent folder exists (important for reports/ later too)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_rows = len(df)
    error_count = int((df["level"] == "ERROR").sum())

    per_level = (
        df["level"]
        .value_counts(dropna=False)
        .rename_axis("level")
        .reset_index(name="count")
    )
    per_service = (
        df["service"]
        .value_counts(dropna=False)
        .rename_axis("service")
        .reset_index(name="count")
    )

    summary_df = pd.DataFrame(
        [
            {"metric": "total_rows", "value": total_rows},
            {"metric": "error_count", "value": error_count},
        ]
    )

    df_export = df.copy()
    df_export["date"] = df_export["timestamp"].dt.date
    df_export["time"] = df_export["timestamp"].dt.strftime("%H:%M:%S")
    df_export = df_export[["date", "time", "service", "level", "message", "response_ms"]]
    
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_export.to_excel(writer, sheet_name="logs", index=False)
        summary_df.to_excel(writer, sheet_name="summary", index=False, startrow=0)
        per_level.to_excel(writer, sheet_name="summary", index=False, startrow=5)
        per_service.to_excel(writer, sheet_name="summary", index=False, startrow=5 + len(per_level) + 3)

        ws_logs = writer.sheets["logs"]
        ws_summary = writer.sheets["summary"]

        # Freeze header row
        ws_logs.freeze_panes = "A2"

        # Enable filter on header row
        ws_logs.auto_filter.ref = ws_logs.dimensions

        # Align columns (make date/time look like text alignment)
        left = Alignment(horizontal="left")
        for row in ws_logs.iter_rows(min_row=2, max_row=ws_logs.max_row, min_col=1, max_col=ws_logs.max_column):
            for cell in row:
                cell.alignment = left

        # Optional: Force timestamp format + width
        #ws_logs.column_dimensions["A"].width = 22
        #for cell in ws_logs["A"][1:]:  # skip header cell
        #    cell.number_format = "yyyy-mm-dd hh:mm:ss"


        # Optional: auto-size all columns nicely
        format_worksheet_columns(ws_logs)
        format_worksheet_columns(ws_summary)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    print("✅ Log Report Automation")
    print(f"Input : {input_path.resolve()}")
    print(f"Output: {output_path.resolve()}")

    try:
        df = load_csv(input_path)
        df = apply_filters(df, args.service, args.level)

        if args.service or args.level:
            print("\n--- Active filters ---")
            if args.service:
                print(f"service = {args.service}")
            if args.level:
                print(f"level   = {args.level.upper()}")

        if df.empty:
            print("\n⚠️ No rows match the given filters.")
            return 0
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        return 1

    print_stats(df)
    try:
        write_excel_report(df, output_path)
    except Exception as exc:
        print(f"\n❌ Failed to write Excel report: {exc}")
        return 1

    print(f"\n✅ Excel report generated: {output_path.resolve()} (sheets: logs, summary)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
