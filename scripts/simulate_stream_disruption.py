from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import httpx
import psycopg2

from apps.load.stream_disruption import (
    DisruptionConfig,
    apply_disruptions,
    generate_base_events,
    summarize_sequence_health,
)
from config import settings


async def _post_events(
    api_base_url: str, events: list[dict[str, Any]]
) -> tuple[int, int]:
    ok = 0
    fail = 0
    url = f"{api_base_url.rstrip('/')}/ingest?source=telemetry"
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for ev in events:
            body = json.dumps(ev, ensure_ascii=False) + "\n"
            try:
                resp = await client.post(
                    url,
                    content=body.encode("utf-8"),
                    headers={"Content-Type": "application/x-ndjson"},
                )
                if 200 <= resp.status_code < 300:
                    ok += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
    return ok, fail


def _query_persisted_unique(prefix: str) -> int:
    conn = psycopg2.connect(settings.postgres_dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM telemetry_events
                WHERE event_id LIKE %s
                """,
                (f"{prefix}-%",),
            )
            row = cur.fetchone()
            return int((row or [0])[0] or 0)
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PS3.6 simulate out-of-order/dup/drop on telemetry ingest."
    )
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--total-events", type=int, default=120)
    parser.add_argument("--drop-prob", type=float, default=0.10)
    parser.add_argument("--dup-prob", type=float, default=0.15)
    parser.add_argument("--reorder-window", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sat-id", default="SAT-PS36")
    parser.add_argument("--event-prefix", default="ps36")
    parser.add_argument("--max-missing-after-persist", type=int, default=0)
    args = parser.parse_args()

    cfg = DisruptionConfig(
        total_events=max(1, int(args.total_events)),
        drop_probability=max(0.0, min(1.0, float(args.drop_prob))),
        duplicate_probability=max(0.0, min(1.0, float(args.dup_prob))),
        reorder_window=max(1, int(args.reorder_window)),
        seed=int(args.seed),
        sat_id=str(args.sat_id),
        event_prefix=str(args.event_prefix),
    )

    base = generate_base_events(cfg)
    emitted, disruption_stats = apply_disruptions(base, cfg)
    expected_unique = len(
        {str(ev.get("event_id") or "") for ev in emitted if ev.get("event_id")}
    )

    posted_ok, posted_fail = asyncio.run(_post_events(args.api_base_url, emitted))
    persisted_unique = _query_persisted_unique(cfg.event_prefix)
    health = summarize_sequence_health(
        expected_unique_after_transport=expected_unique,
        persisted_unique=persisted_unique,
        dropped=disruption_stats["dropped"],
        duplicated=disruption_stats["duplicated"],
    )
    payload: dict[str, Any] = {
        "config": {
            "total_events": cfg.total_events,
            "drop_probability": cfg.drop_probability,
            "duplicate_probability": cfg.duplicate_probability,
            "reorder_window": cfg.reorder_window,
            "seed": cfg.seed,
            "sat_id": cfg.sat_id,
            "event_prefix": cfg.event_prefix,
        },
        "transport": {
            "emitted_total": len(emitted),
            **disruption_stats,
        },
        "ingest_http": {"successes": posted_ok, "failures": posted_fail},
        "durability": health,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if health["missing_after_persist"] > int(args.max_missing_after_persist):
        print(
            "PS3.6 FAILED: missing_after_persist="
            f"{health['missing_after_persist']} > max={int(args.max_missing_after_persist)}"
        )
        return 2
    print("PS3.6 disruption scenario PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
