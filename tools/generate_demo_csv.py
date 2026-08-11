from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

SERVICES = ["api", "auth", "db", "payments", "notifications", "search"]
LEVELS = ["INFO", "WARN", "ERROR"]
DEMO_START_UTC = datetime(2026, 1, 1, tzinfo=timezone.utc)

SERVICE_MESSAGES = {
    "api": {
        "INFO": [
            "HTTP request completed",
            "Response served from cache",
            "API health check passed",
        ],
        "WARN": [
            "Upstream response latency elevated",
            "Request queue utilization high",
            "Client rate limit nearing threshold",
        ],
        "ERROR": [
            "Upstream gateway timeout",
            "Request handler failed",
            "Dependency returned 503",
        ],
    },
    "auth": {
        "INFO": [
            "Access token issued",
            "Session refreshed",
            "Identity cache hit",
        ],
        "WARN": [
            "Token verification latency elevated",
            "Login rate limit nearing threshold",
            "Identity provider retry scheduled",
        ],
        "ERROR": [
            "JWT signature validation failed",
            "Identity provider timeout",
            "Session store unavailable",
        ],
    },
    "db": {
        "INFO": [
            "Database query completed",
            "Connection returned to pool",
            "Replica health check passed",
        ],
        "WARN": [
            "Slow query detected",
            "Connection pool utilization high",
            "Replica lag above threshold",
        ],
        "ERROR": [
            "Primary database connection failed",
            "Transaction deadlock retry exhausted",
            "Read replica unavailable",
        ],
    },
    "payments": {
        "INFO": [
            "Payment authorization completed",
            "Payment status reconciled",
            "Payment webhook processed",
        ],
        "WARN": [
            "Payment provider latency elevated",
            "Retrying idempotent authorization",
            "Webhook delivery delayed",
        ],
        "ERROR": [
            "Payment provider timeout",
            "Authorization gateway unavailable",
            "Payment webhook signature invalid",
        ],
    },
    "notifications": {
        "INFO": [
            "Email notification queued",
            "Push notification delivered",
            "Notification template rendered",
        ],
        "WARN": [
            "Delivery queue depth rising",
            "Email provider rate limit nearing",
            "Retrying notification delivery",
        ],
        "ERROR": [
            "Email provider unavailable",
            "Notification worker exhausted retries",
            "Push gateway rejected request",
        ],
    },
    "search": {
        "INFO": [
            "Search query completed",
            "Search result cache hit",
            "Index refresh checkpoint saved",
        ],
        "WARN": [
            "Search query latency elevated",
            "Indexing backlog rising",
            "Search replica retry scheduled",
        ],
        "ERROR": [
            "Search cluster timeout",
            "Index shard unavailable",
            "Search service returned 503",
        ],
    },
}

INCIDENT_PROFILES = [
    {
        "service": "payments",
        "hours": {10, 11, 12, 13},
        "service_weight_multiplier": 5,
        "level_weights": [0.25, 0.30, 0.45],
        "warn_message": "Regional payment provider latency elevated",
        "error_message": "Regional payment provider timeout",
    },
    {
        "service": "db",
        "hours": {17, 18, 19, 20, 21, 22},
        "service_weight_multiplier": 8,
        "level_weights": [0.20, 0.35, 0.45],
        "warn_message": "Database connection pool saturation",
        "error_message": "Primary database unavailable in failover",
    },
]

SERVICE_WEIGHTS = [2.5, 2.0, 1.2, 1.8, 1.0, 1.0]


def weighted_choice(rng: random.Random, items: list[str], weights: list[float]) -> str:
    return rng.choices(items, weights=weights, k=1)[0]


def choose_message(
    rng: random.Random,
    service: str,
    level: str,
    incident: dict[str, object] | None,
) -> str:
    """Choose a service-specific message, with coherent incident wording."""
    if incident and service == incident["service"]:
        if level == "WARN":
            return str(incident["warn_message"])
        if level == "ERROR":
            return str(incident["error_message"])
    return rng.choice(SERVICE_MESSAGES[service][level])


def generate_logs(
    *,
    rows: int,
    days: int,
    seed: int,
    start_utc: datetime | None,
) -> pd.DataFrame:
    rng = random.Random(seed)

    if start_utc is None:
        # A fixed start date keeps portfolio output reproducible across runs.
        start_utc = DEMO_START_UTC

    # Assign two reproducible, service-specific incident scenarios to distinct days.
    incident_days = sorted(rng.sample(range(days), k=min(2, days)))
    incidents_by_day = {day: INCIDENT_PROFILES[index] for index, day in enumerate(incident_days)}

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

        incident = incidents_by_day.get(day_offset)
        active_incident = incident if incident and int(hour) in incident["hours"] else None

        # Keep the normal traffic mix, but make the affected service prominent
        # during its incident window so the scenario is visible in the report.
        service_weights = SERVICE_WEIGHTS.copy()
        if active_incident:
            affected_index = SERVICES.index(str(active_incident["service"]))
            service_weights[affected_index] *= float(active_incident["service_weight_multiplier"])
        svc = weighted_choice(rng, SERVICES, service_weights)

        # Base level distribution: mostly INFO, some WARN, fewer ERROR
        base_level = weighted_choice(rng, LEVELS, [0.82, 0.13, 0.05])

        # Only the affected service receives the incident severity distribution.
        if active_incident and svc == active_incident["service"]:
            base_level = weighted_choice(rng, LEVELS, list(active_incident["level_weights"]))

        lvl = base_level

        msg = choose_message(rng, svc, lvl, active_incident)

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

        if active_incident and svc == active_incident["service"]:
            incident_latency = {
                "INFO": (120, 350),
                "WARN": (400, 900),
                "ERROR": (900, 1800),
            }[lvl]
            ms += rng.randrange(*incident_latency)

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

    print(f"Wrote {len(df)} rows to: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
