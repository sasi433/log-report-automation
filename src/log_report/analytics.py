from __future__ import annotations

import pandas as pd

SUMMARY_METRICS = [
    "Total logs",
    "Error count",
    "Error rate %",
    "Average response time",
    "Median response time",
    "P95 response time",
    "P99 response time",
    "Slow-request count",
    "Slow-request threshold",
]
DAILY_COLUMNS = [
    "date",
    "total_rows",
    "error_count",
    "error_rate_pct",
    "avg_response_ms",
    "p95_response_ms",
    "INFO",
    "WARN",
    "ERROR",
]


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


def calculate_summary_metrics(df: pd.DataFrame, slow_threshold_ms: float = 500) -> dict[str, float]:
    """Calculate stakeholder-facing reliability and latency metrics."""
    total = len(df)
    errors = int(df["level"].eq("ERROR").sum()) if "level" in df else 0
    latency = pd.to_numeric(df.get("response_ms", pd.Series(dtype=float)), errors="coerce").dropna()

    def percentile(value: float) -> float:
        return float(latency.quantile(value)) if not latency.empty else 0.0

    return {
        "Total logs": float(total),
        "Error count": float(errors),
        "Error rate %": (errors / total * 100) if total else 0.0,
        "Average response time": float(latency.mean()) if not latency.empty else 0.0,
        "Median response time": float(latency.median()) if not latency.empty else 0.0,
        "P95 response time": percentile(0.95),
        "P99 response time": percentile(0.99),
        "Slow-request count": float(latency.ge(slow_threshold_ms).sum()),
        "Slow-request threshold": float(slow_threshold_ms),
    }


def build_summary_metrics(df: pd.DataFrame, slow_threshold_ms: float = 500) -> pd.DataFrame:
    metrics = calculate_summary_metrics(df, slow_threshold_ms)
    return pd.DataFrame([{"metric": name, "value": metrics[name]} for name in SUMMARY_METRICS])


def build_service_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate reliability and latency by service for troubleshooting."""
    columns = [
        "service",
        "request_count",
        "error_count",
        "error_rate_pct",
        "avg_response_ms",
        "p95_response_ms",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    grouped = df.groupby("service", dropna=False, sort=False)
    performance = grouped.agg(
        request_count=("level", "size"),
        error_count=("level", lambda values: int(values.eq("ERROR").sum())),
        avg_response_ms=("response_ms", "mean"),
        p95_response_ms=("response_ms", lambda values: values.quantile(0.95)),
    ).reset_index()
    performance["error_rate_pct"] = performance["error_count"] / performance["request_count"] * 100
    return performance[columns].sort_values(
        ["error_rate_pct", "p95_response_ms", "request_count"],
        ascending=[False, False, False],
        kind="mergesort",
        ignore_index=True,
    )


def build_errors_by_service(df: pd.DataFrame) -> pd.DataFrame:
    """Return service error counts sorted for the summary bar chart."""
    if df.empty:
        return pd.DataFrame(columns=["service", "error_count"])
    return (
        df.assign(is_error=df["level"].eq("ERROR").astype(int))
        .groupby("service", as_index=False, dropna=False)["is_error"]
        .sum()
        .rename(columns={"is_error": "error_count"})
        .sort_values(["error_count", "service"], ascending=[False, True], ignore_index=True)
    )


def build_daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build daily reliability, latency, and level counts using actual rows."""
    if df.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    dated = df.assign(date=df["timestamp"].dt.date)
    daily = (
        dated.groupby("date", as_index=False)
        .agg(
            total_rows=("level", "size"),
            error_count=("level", lambda values: int(values.eq("ERROR").sum())),
            avg_response_ms=("response_ms", "mean"),
            p95_response_ms=("response_ms", lambda values: values.quantile(0.95)),
        )
        .sort_values("date")
    )
    daily["error_rate_pct"] = daily["error_count"] / daily["total_rows"] * 100

    level_counts = pd.crosstab(dated["date"], dated["level"]).reset_index()
    daily = daily.merge(level_counts, on="date", how="left")
    for level in ("INFO", "WARN", "ERROR"):
        if level not in daily.columns:
            daily[level] = 0
    extras = [
        column for column in level_counts.columns if column not in {"date", "INFO", "WARN", "ERROR"}
    ]
    return daily[DAILY_COLUMNS + extras]
