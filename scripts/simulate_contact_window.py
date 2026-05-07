from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import httpx
import psycopg2

from apps.load.contact_window import ContactWindowConfig, apply_contact_windows
from apps.load.stream_disruption import DisruptionConfig, generate_base_events
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
        description="PS3.7 simulate contact-window ON/OFF hooks for telemetry ingest."
    )
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--total-events", type=int, default=120)
    parser.add_argument("--cycle-on-events", type=int, default=20)
    parser.add_argument("--cycle-off-events", type=int, default=40)
    parser.add_argument("--off-mode", choices=("buffer", "drop"), default="buffer")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--event-prefix", default="ps37")
    parser.add_argument("--sat-id", default="SAT-PS37")
    parser.add_argument("--max-missing-after-persist", type=int, default=0)
    args = parser.parse_args()

    base = generate_base_events(
        DisruptionConfig(
            total_events=max(1, int(args.total_events)),
            seed=int(args.seed),
            sat_id=str(args.sat_id),
            event_prefix=str(args.event_prefix),
            drop_probability=0.0,
            duplicate_probability=0.0,
        )
    )
    windowed = apply_contact_windows(
        base,
        ContactWindowConfig(
            cycle_on_events=max(1, int(args.cycle_on_events)),
            cycle_off_events=max(1, int(args.cycle_off_events)),
            off_mode=str(args.off_mode),
            dedupe_on_flush=True,
        ),
    )
    emitted = windowed.emitted
    expected_unique = len(
        {str(ev.get("event_id") or "") for ev in emitted if ev.get("event_id")}
    )

    posted_ok, posted_fail = asyncio.run(_post_events(args.api_base_url, emitted))
    persisted_unique = _query_persisted_unique(str(args.event_prefix))
    missing_after_persist = max(0, expected_unique - persisted_unique)

    payload: dict[str, Any] = {
        "config": {
            "total_events": int(args.total_events),
            "cycle_on_events": int(args.cycle_on_events),
            "cycle_off_events": int(args.cycle_off_events),
            "off_mode": str(args.off_mode),
            "event_prefix": str(args.event_prefix),
            "sat_id": str(args.sat_id),
            "seed": int(args.seed),
        },
        "contact_window": {
            "buffered_total": windowed.buffered_total,
            "flushed_total": windowed.flushed_total,
            "dropped_total": windowed.dropped_total,
            "duplicates_filtered": windowed.duplicates_filtered,
            "emitted_total": len(emitted),
            "expected_unique": expected_unique,
        },
        "ingest_http": {"successes": posted_ok, "failures": posted_fail},
        "durability": {
            "persisted_unique": persisted_unique,
            "missing_after_persist": missing_after_persist,
            "stable": missing_after_persist == 0,
        },
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if missing_after_persist > int(args.max_missing_after_persist):
        print(
            "PS3.7 FAILED: missing_after_persist="
            f"{missing_after_persist} > max={int(args.max_missing_after_persist)}"
        )
        return 2
    print("PS3.7 contact-window scenario PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
