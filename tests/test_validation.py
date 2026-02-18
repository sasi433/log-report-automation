from pathlib import Path

import pandas as pd
import pytest

from src.report_utils import load_logs, validate_logs


def test_validate_logs_missing_column_raises():
    df = pd.DataFrame(
        [
            {"timestamp": "2025-01-01 10:00:00", "service": "api", "level": "INFO", "message": "ok"}
            # missing response_ms
        ]
    )
    with pytest.raises(ValueError):
        validate_logs(df)


def test_load_logs_file_not_found(tmp_path: Path):
    missing = tmp_path / "nope.csv"
    with pytest.raises(FileNotFoundError):
        load_logs(missing)


def test_load_logs_happy_path(tmp_path: Path):
    p = tmp_path / "logs.csv"
    p.write_text(
        "timestamp,service,level,message,response_ms\n" "2025-01-01 10:00:00,api,INFO,ok,12\n"
    )
    df = load_logs(p)
    assert len(df) == 1
    assert list(df.columns) == ["timestamp", "service", "level", "message", "response_ms"]
