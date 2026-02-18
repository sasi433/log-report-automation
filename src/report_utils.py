from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill

REQUIRED_COLUMNS = ["timestamp", "service", "level", "message", "response_ms"]


# -------------------------
# Load + validate
# -------------------------
def load_logs(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path)
    validate_logs(df)

    # Normalize types
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["response_ms"] = pd.to_numeric(df["response_ms"], errors="coerce")

    # Normalize casing for consistent downstream reporting
    df["level"] = df["level"].astype(str).str.upper()
    df["service"] = df["service"].astype(str)

    # Sort for stable reporting
    df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
    return df


def validate_logs(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "CSV schema invalid. Missing columns: "
            + ", ".join(missing)
            + f"\nExpected columns: {', '.join(REQUIRED_COLUMNS)}"
        )


# -------------------------
# Filtering
# -------------------------
def apply_filters(df: pd.DataFrame, service: str | None, level: str | None) -> pd.DataFrame:
    filtered = df

    if service:
        filtered = filtered[filtered["service"] == str(service)]

    if level:
        filtered = filtered[filtered["level"] == str(level).upper()]

    return filtered.reset_index(drop=True)


# -------------------------
# Report dataframes
# -------------------------
def build_export_logs(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = out["timestamp"].dt.date
    out["time"] = out["timestamp"].dt.strftime("%H:%M:%S")
    return out[["date", "time", "service", "level", "message", "response_ms"]]


def build_summary_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    total_rows = len(df)
    error_count = int((df["level"] == "ERROR").sum())

    summary_df = pd.DataFrame(
        [
            {"metric": "total_rows", "value": total_rows},
            {"metric": "error_count", "value": error_count},
        ]
    )

    per_level = (
        df["level"].value_counts(dropna=False).rename_axis("level").reset_index(name="count")
    )
    per_service = (
        df["service"].value_counts(dropna=False).rename_axis("service").reset_index(name="count")
    )

    return summary_df, per_level, per_service


def build_daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    daily_pivot = (
        df.assign(date=df["timestamp"].dt.date)
        .pivot_table(index="date", columns="level", values="message", aggfunc="count", fill_value=0)
        .reset_index()
        .sort_values("date")
    )

    level_cols = [c for c in daily_pivot.columns if c != "date"]
    daily_pivot["total_rows"] = daily_pivot[level_cols].sum(axis=1) if level_cols else 0
    daily_pivot["error_count"] = daily_pivot["ERROR"] if "ERROR" in daily_pivot.columns else 0

    ordered_cols = ["date", "total_rows", "error_count"] + [
        c for c in level_cols if c not in ("total_rows", "error_count")
    ]
    return daily_pivot[ordered_cols]


# -------------------------
# Excel styling (post-save)
# -------------------------
def _autofit_columns(ws, max_width: int = 60) -> None:
    for col in ws.columns:
        first_cell = col[0]
        if not hasattr(first_cell, "column_letter"):
            continue

        col_letter = first_cell.column_letter
        max_len = 0
        for cell in col[:2000]:
            val = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = min(max_len + 2, max_width)


def _style_header_row(ws, header_row: int = 1) -> None:
    fill = PatternFill("solid", fgColor="1F4E79")  # dark blue
    font = Font(bold=True, color="FFFFFF")
    align = Alignment(vertical="center", horizontal="center", wrap_text=True)

    for cell in ws[header_row]:
        cell.fill = fill
        cell.font = font
        cell.alignment = align

    ws.row_dimensions[header_row].height = 18


def _add_section_title(ws, row: int, title: str) -> None:
    cell = ws.cell(row=row, column=1, value=title)
    cell.font = Font(bold=True, size=12)
    ws.row_dimensions[row].height = 18


def _highlight_error_rows(ws, level_col_name: str = "level", header_row: int = 1) -> None:
    headers = [c.value for c in ws[header_row]]
    if level_col_name not in headers:
        return

    level_idx = headers.index(level_col_name) + 1
    level_col_letter = ws.cell(row=header_row, column=level_idx).column_letter

    start_row = header_row + 1
    if ws.max_row < start_row:
        return

    last_col_letter = ws.cell(row=header_row, column=ws.max_column).column_letter
    data_range = f"A{start_row}:{last_col_letter}{ws.max_row}"

    fill = PatternFill("solid", fgColor="F8D7DA")  # light red
    # Relative-row formula so it works for every row in the range
    rule = FormulaRule(formula=[f'${level_col_letter}1="ERROR"'], fill=fill)
    ws.conditional_formatting.add(data_range, rule)


def style_workbook(xlsx_path: Path, per_level_len: int) -> None:
    wb = load_workbook(xlsx_path)

    # logs
    if "logs" in wb.sheetnames:
        ws = wb["logs"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        _style_header_row(ws, 1)
        _highlight_error_rows(ws, "level", 1)
        _autofit_columns(ws)

    # daily_summary
    if "daily_summary" in wb.sheetnames:
        ws = wb["daily_summary"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        _style_header_row(ws, 1)
        _autofit_columns(ws)

    # summary
    if "summary" in wb.sheetnames:
        ws = wb["summary"]
        _add_section_title(ws, row=1, title="Key Metrics")
        _add_section_title(ws, row=6, title="Counts by Level")
        _add_section_title(ws, row=6 + per_level_len + 3, title="Counts by Service")
        _autofit_columns(ws)

    wb.save(xlsx_path)


# -------------------------
# Write the full report
# -------------------------
def write_excel_report(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_df, per_level, per_service = build_summary_tables(df)
    daily_summary_df = build_daily_summary(df)
    logs_df = build_export_logs(df)

    # Write content first
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        logs_df.to_excel(writer, sheet_name="logs", index=False)

        summary_df.to_excel(writer, sheet_name="summary", index=False, startrow=0)
        per_level.to_excel(writer, sheet_name="summary", index=False, startrow=5)
        per_service.to_excel(
            writer, sheet_name="summary", index=False, startrow=5 + len(per_level) + 3
        )

        daily_summary_df.to_excel(writer, sheet_name="daily_summary", index=False)

    # Style after saving (reliable)
    style_workbook(output_path, per_level_len=len(per_level))
