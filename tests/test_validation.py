from pathlib import Path

import pandas as pd
import pytest

from log_report.analytics import apply_filters
from log_report.validation import (
    LogValidationError,
    build_quality_summary,
    load_logs,
    normalize_and_validate,
    validate_logs,
)


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
    df = load_logs(p).data
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

    df = load_logs(path).data

    assert df["level"].tolist() == ["INFO", "ERROR"]
    assert df["message"].tolist() == ["earlier", "later"]


def test_load_logs_rejects_invalid_timestamp_and_response(tmp_path: Path):
    path = tmp_path / "logs.csv"
    path.write_text(
        "timestamp,service,level,message,response_ms\n" "not-a-date,api,INFO,ok,not-a-number\n",
        encoding="utf-8",
    )

    with pytest.raises(LogValidationError) as exc_info:
        load_logs(path)

    assert {issue.issue for issue in exc_info.value.issues} == {
        "Invalid timestamp",
        "Invalid response_ms",
    }


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


def valid_row(**overrides) -> dict[str, object]:
    row = {
        "timestamp": "2025-01-01T10:00:00Z",
        "service": "api",
        "level": "INFO",
        "message": "ok",
        "response_ms": 25,
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    ("overrides", "expected_issue"),
    [
        ({"timestamp": "bad"}, "Invalid timestamp"),
        ({"response_ms": "bad"}, "Invalid response_ms"),
        ({"response_ms": -1}, "Negative response_ms"),
        ({"service": ""}, "Missing service"),
        ({"level": ""}, "Missing level"),
        ({"level": "DEBUG"}, "Unknown level"),
    ],
)
def test_lenient_validation_reports_and_rejects_invalid_operational_rows(overrides, expected_issue):
    result = normalize_and_validate(
        pd.DataFrame([valid_row(), valid_row(**overrides)]),
        mode="lenient",
    )

    assert len(result.data) == 1
    assert result.rejected_rows == 1
    assert result.issue_counts[expected_issue] == 1


def test_strict_validation_summarizes_problem_types():
    df = pd.DataFrame(
        [
            valid_row(timestamp="bad"),
            valid_row(service=""),
            valid_row(response_ms=-5),
        ]
    )

    with pytest.raises(LogValidationError) as exc_info:
        normalize_and_validate(df)

    message = str(exc_info.value)
    assert "Validation failed: 3 invalid rows" in message
    assert "Invalid timestamp: 1" in message
    assert "Negative response_ms: 1" in message
    assert "Missing service: 1" in message


def test_missing_message_is_reported_but_retained_in_lenient_mode():
    result = normalize_and_validate(
        pd.DataFrame([valid_row(message=None)]),
        mode="lenient",
    )

    assert len(result.data) == 1
    assert result.rejected_rows == 0
    assert result.issue_counts["Missing message"] == 1
    assert pd.isna(result.data.loc[0, "message"])
    assert result.data.loc[0, "service"] != "nan"


def test_timestamps_are_normalized_to_utc():
    result = normalize_and_validate(
        pd.DataFrame(
            [
                valid_row(timestamp="2025-01-01 10:00:00"),
                valid_row(timestamp="2025-01-01T12:00:00+02:00"),
            ]
        )
    )

    assert str(result.data["timestamp"].dt.tz) == "UTC"
    assert result.data.loc[0, "timestamp"] == result.data.loc[1, "timestamp"]


def test_quality_summary_includes_stable_zero_counts():
    result = normalize_and_validate(pd.DataFrame([valid_row()]), mode="lenient")

    summary = build_quality_summary(result).set_index("issue")["count"]

    assert summary["Invalid timestamp"] == 0
    assert summary["Unknown level"] == 0
    assert summary["Rejected rows"] == 0
