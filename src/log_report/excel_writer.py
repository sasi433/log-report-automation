from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill

from .analytics import build_daily_summary, build_export_logs, build_summary_tables
from .validation import ValidationResult, build_issue_details, build_quality_summary

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def sanitize_excel_text(value: object) -> object:
    """Prevent openpyxl from turning untrusted text into an Excel formula.

    openpyxl marks strings beginning with ``=`` as formula cells. Strings
    beginning with ``+``, ``-``, or ``@`` remain ordinary string cells and are
    intentionally preserved.
    """
    if isinstance(value, str) and value.startswith("="):
        return "'" + value
    return value


def _sanitize_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.apply(lambda column: column.map(sanitize_excel_text))


def _autofit_columns(ws, max_width: int = 60, scan_limit: int = 2000) -> None:
    for column in ws.columns:
        first_cell = column[0]
        if not hasattr(first_cell, "column_letter"):
            continue
        width = max(
            (len("" if cell.value is None else str(cell.value)) for cell in column[:scan_limit]),
            default=0,
        )
        ws.column_dimensions[first_cell.column_letter].width = min(width + 2, max_width)


def _style_header_row(ws, row: int = 1) -> None:
    for cell in ws[row]:
        if cell.value is None:
            continue
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
    ws.row_dimensions[row].height = 20


def _add_section_title(ws, row: int, title: str) -> None:
    cell = ws.cell(row=row, column=1, value=title)
    cell.font = Font(bold=True, size=12, color="1F4E79")


def _highlight_error_rows(ws) -> None:
    headers = [cell.value for cell in ws[1]]
    if "level" not in headers or ws.max_row < 2:
        return
    level_column = ws.cell(row=1, column=headers.index("level") + 1).column_letter
    last_column = ws.cell(row=1, column=ws.max_column).column_letter
    rule = FormulaRule(
        formula=[f'${level_column}2="ERROR"'],
        fill=PatternFill("solid", fgColor="F8D7DA"),
    )
    ws.conditional_formatting.add(f"A2:{last_column}{ws.max_row}", rule)


def _style_tabular_sheet(ws, *, highlight_errors: bool = False) -> None:
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    ws.sheet_view.showGridLines = False
    _style_header_row(ws)
    if highlight_errors:
        _highlight_error_rows(ws)
    _autofit_columns(ws)


def _style_summary(ws, per_level_len: int) -> None:
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A3"
    ws["A1"] = "Log Report Summary"
    ws["A1"].font = Font(bold=True, size=18, color="1F4E79")
    _style_header_row(ws, 2)
    _add_section_title(ws, 6, "Counts by Level")
    _style_header_row(ws, 7)
    service_title_row = 9 + per_level_len
    _add_section_title(ws, service_title_row, "Counts by Service")
    _style_header_row(ws, service_title_row + 1)
    _autofit_columns(ws)


def _style_quality(ws) -> None:
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A3"
    ws["A1"] = "Data Quality"
    ws["A1"].font = Font(bold=True, size=18, color="1F4E79")
    _style_header_row(ws, 2)
    _add_section_title(ws, 12, "Affected Rows")
    _style_header_row(ws, 13)
    _autofit_columns(ws)


def style_workbook(path: Path, per_level_len: int) -> None:
    wb = load_workbook(path)
    wb.active = wb.sheetnames.index("summary")
    _style_summary(wb["summary"], per_level_len)
    _style_tabular_sheet(wb["logs"], highlight_errors=True)
    _style_tabular_sheet(wb["daily_summary"])
    _style_quality(wb["data_quality"])
    wb.save(path)


def write_excel_report(
    df: pd.DataFrame,
    output_path: Path,
    validation: ValidationResult | None = None,
) -> None:
    """Write the stakeholder workbook and apply its presentation styling."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if validation is None:
        validation = ValidationResult(df, (), 0)

    summary, per_level, per_service = (_sanitize_frame(table) for table in build_summary_tables(df))
    logs = _sanitize_frame(build_export_logs(df))
    daily = _sanitize_frame(build_daily_summary(df))
    quality = _sanitize_frame(build_quality_summary(validation))
    issue_details = _sanitize_frame(build_issue_details(validation))

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="summary", index=False, startrow=1)
        per_level.to_excel(writer, sheet_name="summary", index=False, startrow=6)
        per_service.to_excel(
            writer,
            sheet_name="summary",
            index=False,
            startrow=9 + len(per_level),
        )
        logs.to_excel(writer, sheet_name="logs", index=False)
        daily.to_excel(writer, sheet_name="daily_summary", index=False)
        quality.to_excel(writer, sheet_name="data_quality", index=False, startrow=1)
        issue_details.to_excel(writer, sheet_name="data_quality", index=False, startrow=12)

    style_workbook(output_path, per_level_len=len(per_level))
