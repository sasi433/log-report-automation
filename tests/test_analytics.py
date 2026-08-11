from __future__ import annotations

import pandas as pd
import pytest

from log_report.analytics import (
    DAILY_COLUMNS,
    build_daily_summary,
    build_errors_by_service,
    build_service_performance,
    calculate_summary_metrics,
)


def analytics_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2025-01-01T10:00:00Z",
                    "2025-01-01T11:00:00Z",
                    "2025-01-02T10:00:00Z",
                    "2025-01-02T11:00:00Z",
                    "2025-01-02T12:00:00Z",
                ],
                utc=True,
            ),
            "service": ["api", "api", "auth", "auth", "auth"],
            "level": ["INFO", "ERROR", "INFO", "WARN", "ERROR"],
            "message": ["a", "b", "c", "d", "e"],
            "response_ms": [100, 200, 300, 400, 1000],
        }
    )


def test_summary_metrics_include_reliability_latency_and_slow_requests():
    metrics = calculate_summary_metrics(analytics_frame(), slow_threshold_ms=500)

    assert metrics["Total logs"] == 5
    assert metrics["Error count"] == 2
    assert metrics["Error rate %"] == 40
    assert metrics["Average response time"] == 400
    assert metrics["Median response time"] == 300
    assert metrics["P95 response time"] == pytest.approx(880)
    assert metrics["P99 response time"] == pytest.approx(976)
    assert metrics["Slow-request count"] == 1
    assert metrics["Slow-request threshold"] == 500


def test_summary_metrics_handle_empty_dataset():
    empty = analytics_frame().iloc[0:0]

    metrics = calculate_summary_metrics(empty)

    assert all(value == 0 for name, value in metrics.items() if name != "Slow-request threshold")
    assert metrics["Slow-request threshold"] == 500


def test_service_performance_is_sorted_by_error_rate():
    performance = build_service_performance(analytics_frame())

    assert performance["service"].tolist() == ["api", "auth"]
    assert performance.loc[0, "request_count"] == 2
    assert performance.loc[0, "error_count"] == 1
    assert performance.loc[0, "error_rate_pct"] == 50
    assert performance.loc[0, "avg_response_ms"] == 150
    assert performance.loc[0, "p95_response_ms"] == 195


def test_errors_by_service_includes_zero_error_services():
    errors = build_errors_by_service(analytics_frame())

    assert errors.to_dict("records") == [
        {"service": "api", "error_count": 1},
        {"service": "auth", "error_count": 1},
    ]


def test_daily_summary_counts_rows_with_missing_messages():
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2025-01-01T10:00:00Z", "2025-01-01T11:00:00Z"],
                utc=True,
            ),
            "service": ["api", "api"],
            "level": ["INFO", "ERROR"],
            "message": ["ok", pd.NA],
            "response_ms": [10, 20],
        }
    )

    daily = build_daily_summary(df)

    assert daily.loc[0, "total_rows"] == 2
    assert daily.loc[0, "error_count"] == 1
    assert daily.loc[0, "INFO"] == 1
    assert daily.loc[0, "ERROR"] == 1


def test_daily_summary_includes_error_rate_and_latency_metrics():
    daily = build_daily_summary(analytics_frame())

    assert list(daily.columns) == DAILY_COLUMNS
    assert daily.loc[0, "total_rows"] == 2
    assert daily.loc[0, "error_count"] == 1
    assert daily.loc[0, "error_rate_pct"] == 50
    assert daily.loc[0, "avg_response_ms"] == 150
    assert daily.loc[0, "p95_response_ms"] == 195
    assert daily.loc[1, "INFO"] == 1
    assert daily.loc[1, "WARN"] == 1
    assert daily.loc[1, "ERROR"] == 1
