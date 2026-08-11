from __future__ import annotations

import pandas as pd


def apply_filters(df: pd.DataFrame, service: str | None, level: str | None) -> pd.DataFrame:
    """Apply optional exact service and case-insensitive level filters."""
    filtered = df
    if service:
        filtered = filtered[filtered["service"] == str(service)]
    if level:
        filtered = filtered[filtered["level"] == str(level).upper()]
    return filtered.reset_index(drop=True)


def build_export_logs(df: pd.DataFrame) -> pd.DataFrame:
    """Build the normalized row-level export shown in the logs worksheet."""
    out = df.copy()
    out["date"] = out["timestamp"].dt.date
    out["time"] = out["timestamp"].dt.strftime("%H:%M:%S")
    return out[["date", "time", "service", "level", "message", "response_ms"]]


def build_summary_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the original key-metric, level-count, and service-count tables."""
    total_rows = len(df)
    error_count = int((df["level"] == "ERROR").sum())
    summary = pd.DataFrame(
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
    return summary, per_level, per_service


def build_daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build daily row totals independently of message completeness."""
    columns = ["date", "total_rows", "error_count", "INFO", "WARN", "ERROR"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    counts = (
        df.assign(date=df["timestamp"].dt.date)
        .groupby(["date", "level"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reset_index()
        .sort_values("date")
    )
    level_columns = [column for column in counts.columns if column != "date"]
    counts["total_rows"] = counts[level_columns].sum(axis=1)
    counts["error_count"] = counts["ERROR"] if "ERROR" in counts.columns else 0
    for level in ("INFO", "WARN", "ERROR"):
        if level not in counts.columns:
            counts[level] = 0
    extras = [column for column in level_columns if column not in {"INFO", "WARN", "ERROR"}]
    return counts[columns + extras]
