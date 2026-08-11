from __future__ import annotations

import sys

from src.main import EXIT_INPUT_MISSING, EXIT_OK, main


def test_cli_missing_input_returns_distinct_exit_code(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["log-report", "--input", str(tmp_path / "missing.csv")],
    )

    assert main() == EXIT_INPUT_MISSING
    assert "Input file not found" in capsys.readouterr().out


def test_cli_empty_filter_does_not_create_report(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "report.xlsx"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "log-report",
            "--input",
            "sample_data/example.csv",
            "--output",
            str(output_path),
            "--service",
            "missing-service",
        ],
    )

    assert main() == EXIT_OK
    assert not output_path.exists()
    assert "No rows match" in capsys.readouterr().out
