from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import ParserError

REQUIRED_COLUMNS = ["timestamp", "service", "level", "message", "response_ms"]
SUPPORTED_LEVELS = frozenset({"INFO", "WARN", "ERROR"})
ISSUE_ORDER = [
    "Invalid timestamp",
    "Invalid response_ms",
    "Missing service",
    "Missing level",
    "Unknown level",
    "Negative response_ms",
    "Missing message",
]


@dataclass(frozen=True)
class ValidationIssue:
    """One data-quality problem found in an input row."""

    row_number: int
    field: str
    issue: str
    original_value: object


@dataclass(frozen=True)
class ValidationResult:
    """Normalized report rows and the quality findings for the source CSV."""

    data: pd.DataFrame
    issues: tuple[ValidationIssue, ...]
    rejected_rows: int

    @property
    def affected_rows(self) -> int:
        return len({issue.row_number for issue in self.issues})

    @property
    def issue_counts(self) -> Counter[str]:
        return Counter(issue.issue for issue in self.issues)


class LogValidationError(ValueError):
    """Raised when strict validation finds invalid input data."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = issues
        affected_rows = len({issue.row_number for issue in issues})
        counts = Counter(issue.issue for issue in issues)
        details = "\n".join(f"{name}: {counts[name]}" for name in ISSUE_ORDER if counts[name])
        message = f"Validation failed: {affected_rows} invalid rows\n\n{details}"
        message += "\n\nRun with --validation lenient to generate a report from usable rows."
        super().__init__(message)


def validate_logs(df: pd.DataFrame) -> None:
    """Validate that every required CSV column exists."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "CSV schema invalid. Missing columns: "
            + ", ".join(missing)
            + f"\nExpected columns: {', '.join(REQUIRED_COLUMNS)}"
        )


def _display_value(value: object) -> object:
    return "" if pd.isna(value) else value


def _collect_issues(
    raw: pd.DataFrame,
    mask: pd.Series,
    field: str,
    issue: str,
) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            row_number=int(index) + 2,
            field=field,
            issue=issue,
            original_value=_display_value(raw.at[index, field]),
        )
        for index in raw.index[mask]
    ]


def normalize_and_validate(df: pd.DataFrame, mode: str = "strict") -> ValidationResult:
    """Normalize a log frame and apply strict or lenient row validation.

    Timezone-aware values are converted to UTC. Naive timestamps are interpreted
    as UTC, giving the report one predictable timeline.
    """
    if mode not in {"strict", "lenient"}:
        raise ValueError("validation mode must be 'strict' or 'lenient'")

    validate_logs(df)
    raw = df.reset_index(drop=True).copy()
    normalized = raw.copy()

    service = raw["service"].astype("string").str.strip()
    level = raw["level"].astype("string").str.strip().str.upper()
    message = raw["message"].astype("string")
    timestamp = pd.to_datetime(raw["timestamp"], errors="coerce", utc=True, format="mixed")
    response_ms = pd.to_numeric(raw["response_ms"], errors="coerce")

    missing_service = service.isna() | service.eq("")
    missing_level = level.isna() | level.eq("")
    unknown_level = ~missing_level & ~level.isin(SUPPORTED_LEVELS)
    invalid_timestamp = timestamp.isna()
    invalid_response = response_ms.isna()
    negative_response = response_ms.notna() & response_ms.lt(0)
    missing_message = message.isna() | message.str.strip().eq("")

    issues: list[ValidationIssue] = []
    issue_specs = [
        (invalid_timestamp, "timestamp", "Invalid timestamp"),
        (invalid_response, "response_ms", "Invalid response_ms"),
        (missing_service, "service", "Missing service"),
        (missing_level, "level", "Missing level"),
        (unknown_level, "level", "Unknown level"),
        (negative_response, "response_ms", "Negative response_ms"),
        (missing_message, "message", "Missing message"),
    ]
    for mask, field, issue in issue_specs:
        issues.extend(_collect_issues(raw, mask, field, issue))

    normalized["timestamp"] = timestamp
    normalized["response_ms"] = response_ms
    normalized["service"] = service
    normalized["level"] = level
    normalized["message"] = message

    rejected = (
        invalid_timestamp
        | invalid_response
        | missing_service
        | missing_level
        | unknown_level
        | negative_response
    )
    rejected_rows = int(rejected.sum())
    issue_tuple = tuple(issues)

    if mode == "strict" and issue_tuple:
        raise LogValidationError(issue_tuple)

    usable = normalized.loc[~rejected].copy()
    usable = usable.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
    return ValidationResult(usable, issue_tuple, rejected_rows)


def load_logs(path: Path, mode: str = "strict") -> ValidationResult:
    """Read, normalize, and validate a structured CSV log export."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    try:
        df = pd.read_csv(path)
    except ParserError as exc:
        raise ValueError(f"Unable to parse CSV: {exc}") from exc
    return normalize_and_validate(df, mode=mode)


def build_quality_summary(result: ValidationResult) -> pd.DataFrame:
    """Return stable issue counts for the data-quality worksheet."""
    counts = result.issue_counts
    rows = [{"issue": issue, "count": counts[issue]} for issue in ISSUE_ORDER]
    rows.append({"issue": "Rejected rows", "count": result.rejected_rows})
    return pd.DataFrame(rows)


def build_issue_details(result: ValidationResult) -> pd.DataFrame:
    """Return one row per quality finding with the original CSV row number."""
    columns = ["row_number", "field", "issue", "original_value"]
    return pd.DataFrame(
        [
            {
                "row_number": issue.row_number,
                "field": issue.field,
                "issue": issue.issue,
                "original_value": issue.original_value,
            }
            for issue in result.issues
        ],
        columns=columns,
    )
