from pathlib import Path

import pandas as pd
import pytest

from src.report_utils import apply_filters, load_logs, validate_logs


def test_validate_logs_missing_column_raises():
    df = pd.DataFrame(
        [
            {"timestamp": "2025-01-01 10:00:00", "service": "api", "level": "INFO", "message": "ok"}
            # missing response_ms
        ]
    )
    with pytest.raises(ValueError, match="Missing columns: response_ms"):
        validate_logs(df)


def test_validate_logs_accepts_required_columns():
    df = pd.DataFrame(columns=["timestamp", "service", "level", "message", "response_ms"])

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
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    assert pd.api.types.is_numeric_dtype(df["response_ms"])


def test_load_logs_normalizes_level_and_sorts_timestamp(tmp_path: Path):
    path = tmp_path / "logs.csv"
    path.write_text(
        "timestamp,service,level,message,response_ms\n"
        "2025-01-02T10:00:00Z,api,error,later,22\n"
        "2025-01-01T10:00:00Z,auth,info,earlier,12\n",
        encoding="utf-8",
    )

    df = load_logs(path)

    assert df["level"].tolist() == ["INFO", "ERROR"]
    assert df["message"].tolist() == ["earlier", "later"]


def test_load_logs_coerces_invalid_timestamp_and_response(tmp_path: Path):
    path = tmp_path / "logs.csv"
    path.write_text(
        "timestamp,service,level,message,response_ms\n" "not-a-date,api,INFO,ok,not-a-number\n",
        encoding="utf-8",
    )

    df = load_logs(path)

    assert pd.isna(df.loc[0, "timestamp"])
    assert pd.isna(df.loc[0, "response_ms"])


@pytest.fixture
def filter_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"service": "api", "level": "INFO"},
            {"service": "api", "level": "ERROR"},
            {"service": "auth", "level": "ERROR"},
        ]
    )


def test_apply_filters_by_service(filter_df: pd.DataFrame):
    result = apply_filters(filter_df, service="api", level=None)

    assert len(result) == 2
    assert set(result["service"]) == {"api"}


def test_apply_filters_level_case_insensitively(filter_df: pd.DataFrame):
    result = apply_filters(filter_df, service=None, level="error")

    assert len(result) == 2
    assert set(result["level"]) == {"ERROR"}


def test_apply_filters_combines_filters(filter_df: pd.DataFrame):
    result = apply_filters(filter_df, service="api", level="ERROR")

    assert result.to_dict("records") == [{"service": "api", "level": "ERROR"}]


def test_apply_filters_can_return_empty_result(filter_df: pd.DataFrame):
    result = apply_filters(filter_df, service="missing", level=None)

    assert result.empty
