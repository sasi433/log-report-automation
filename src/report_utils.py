from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["timestamp", "service", "level", "message", "response_ms"]


def load_logs(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path)
    validate_logs(df)

    # Normalize types
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["response_ms"] = pd.to_numeric(df["response_ms"], errors="coerce")

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


def apply_filters(df: pd.DataFrame, service: str | None, level: str | None) -> pd.DataFrame:
    filtered = df

    if service:
        filtered = filtered[filtered["service"].astype(str) == service]

    if level:
        filtered = filtered[filtered["level"].astype(str).str.upper() == level.upper()]

    return filtered.reset_index(drop=True)


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
        df.assign(
            date=df["timestamp"].dt.date,
            level=df["level"].astype(str).str.upper(),
        )
        .pivot_table(index="date", columns="level", values="message", aggfunc="count", fill_value=0)
        .reset_index()
        .sort_values("date")
    )

    level_cols = [c for c in daily_pivot.columns if c != "date"]
    daily_pivot["total_rows"] = daily_pivot[level_cols].sum(axis=1) if level_cols else 0
    daily_pivot["error_count"] = daily_pivot["ERROR"] if "ERROR" in daily_pivot.columns else 0

    ordered_cols = ["date", "total_rows", "error_count"] + [c for c in level_cols if c not in ("total_rows", "error_count")]
    return daily_pivot[ordered_cols]
