from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

SERVICES = ["api", "auth", "db", "payments", "notifications", "search"]
LEVELS = ["INFO", "WARN", "ERROR"]

INFO_MESSAGES = [
    "Request completed",
    "Cache hit",
    "Cache miss",
    "Session refreshed",
    "User profile loaded",
    "Feature flag evaluated",
    "Background job finished",
]

WARN_MESSAGES = [
    "Upstream latency high",
    "Retrying request",
    "Rate limit nearing threshold",
    "Queue depth rising",
    "Slow query detected",
    "Circuit breaker half-open",
]

ERROR_MESSAGES = [
    "Upstream timeout",
    "Database connection failed",
    "Payment provider error",
    "JWT validation failed",
    "Null reference in handler",
    "Out of memory (worker restart)",
    "503 Service unavailable",
]


def weighted_choice(rng: random.Random, items: list[str], weights: list[float]) -> str:
    return rng.choices(items, weights=weights, k=1)[0]


def generate_logs(
    *,
    rows: int,
    days: int,
    seed: int,
    start_utc: datetime | None,
) -> pd.DataFrame:
    rng = random.Random(seed)

    if start_utc is None:
        # Start 'days' ago at 00:00 UTC
        now = datetime.now(timezone.utc)
        start_utc = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Make daily pattern: business hours have more traffic
    # Also inject a couple "incident windows" with more errors.
    incident_days = {rng.randrange(0, days) for _ in range(2)}
    incident_hours = {10, 11, 12, 18}  # typical spike windows

    timestamps: list[datetime] = []
    services: list[str] = []
    levels: list[str] = []
    messages: list[str] = []
    response_ms: list[int] = []

    for _ in range(rows):
        # Pick a random time within the range, biased toward daytime hours
        day_offset = rng.randrange(0, days)
        hour = weighted_choice(
            rng,
            list(range(24)),
            # weights: daytime heavier
            [0.5] * 7 + [1.5] * 10 + [0.9] * 5 + [0.6] * 2,  # 0-6,7-16,17-21,22-23
        )
        minute = rng.randrange(0, 60)
        second = rng.randrange(0, 60)

        ts = start_utc + timedelta(days=day_offset, hours=int(hour), minutes=minute, seconds=second)

        svc = weighted_choice(
            rng,
            SERVICES,
            # api/auth/payments more frequent than db/search/notifications
            [2.5, 2.0, 1.2, 1.8, 1.0, 1.0],
        )

        # Base level distribution: mostly INFO, some WARN, fewer ERROR
        base_level = weighted_choice(rng, LEVELS, [0.82, 0.13, 0.05])

        # Incident boosting: more ERROR during incident windows
        if day_offset in incident_days and int(hour) in incident_hours:
            base_level = weighted_choice(rng, LEVELS, [0.60, 0.20, 0.20])

        lvl = base_level

        if lvl == "INFO":
            msg = weighted_choice(rng, INFO_MESSAGES, [2, 1, 1, 1, 1, 1, 1])
        elif lvl == "WARN":
            msg = weighted_choice(rng, WARN_MESSAGES, [2, 2, 1, 1, 1, 1])
        else:
            msg = weighted_choice(rng, ERROR_MESSAGES, [2, 1, 1, 1, 1, 1, 1])

        # Response time model: depends on service and level
        # Start with a baseline and add noise + spikes
        base = {
            "api": 120,
            "auth": 90,
            "db": 40,
            "payments": 180,
            "notifications": 70,
            "search": 160,
        }[svc]

        jitter = int(abs(rng.gauss(0, 40)))
        ms = base + jitter

        if lvl == "WARN":
            ms += rng.randrange(80, 300)
        elif lvl == "ERROR":
            ms += rng.randrange(200, 1200)

        # occasional long-tail outliers
        if rng.random() < 0.02:
            ms += rng.randrange(1500, 4000)

        timestamps.append(ts)
        services.append(svc)
        levels.append(lvl)
        messages.append(msg)
        response_ms.append(int(ms))

    df = pd.DataFrame(
        {
            "timestamp": [t.isoformat().replace("+00:00", "Z") for t in timestamps],
            "service": services,
            "level": levels,
            "message": messages,
            "response_ms": response_ms,
        }
    )

    # Sort for realism
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def main() -> int:
    parser = argparse.ArgumentParser(prog="generate_demo_csv")
    parser.add_argument("--rows", type=int, default=400)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="sample_data/demo_production_logs.csv")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_logs(rows=args.rows, days=args.days, seed=args.seed, start_utc=None)
    df.to_csv(out_path, index=False)

    print(f"✅ Wrote {len(df)} rows to: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
