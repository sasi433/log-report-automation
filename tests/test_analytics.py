from __future__ import annotations

import pandas as pd

from log_report.analytics import build_daily_summary


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
