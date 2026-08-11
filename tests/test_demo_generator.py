from __future__ import annotations

from tools.generate_demo_csv import DEMO_START_UTC, generate_logs


def test_demo_generation_is_deterministic():
    first = generate_logs(rows=50, days=7, seed=42, start_utc=None)
    second = generate_logs(rows=50, days=7, seed=42, start_utc=None)

    assert first.equals(second)
    assert first["timestamp"].min().startswith(DEMO_START_UTC.date().isoformat())
    assert set(first["level"]).issubset({"INFO", "WARN", "ERROR"})
