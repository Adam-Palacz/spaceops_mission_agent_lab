from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import psycopg2

from apps.replay.queue_replay import (
    ReplayItem,
    build_items_from_dlq,
    dedupe_replay_items,
    load_dlq_candidates,
    parse_id_csv,
    parse_iso,
)
from config import settings


def _nats_servers() -> list[str]:
    return [s.strip() for s in settings.nats_url.split(",") if s.strip()]


async def _publish_items(items: list[ReplayItem]) -> tuple[int, int]:
    import nats

    servers = _nats_servers()
    if not servers:
        raise RuntimeError("NATS_URL is empty")
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()
    published = 0
    dup_at_broker = 0
    try:
        for item in items:
            pa = await js.publish(
                settings.jetstream_telemetry_subject,
                json.dumps(item.payload, sort_keys=True, ensure_ascii=False).encode(
                    "utf-8"
                ),
                headers={"Nats-Msg-Id": item.event_id[:240]},
            )
            if getattr(pa, "duplicate", False):
                dup_at_broker += 1
            else:
                published += 1
    finally:
        await nc.drain()
        await nc.close()
    return published, dup_at_broker


async def _load_items_from_seq_range(seq_start: int, seq_end: int) -> list[ReplayItem]:
    import nats

    servers = _nats_servers()
    if not servers:
        raise RuntimeError("NATS_URL is empty")
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()
    items: list[ReplayItem] = []
    try:
        for seq in range(seq_start, seq_end + 1):
            msg = await js.get_msg(settings.jetstream_stream_name, seq=seq)
            data = getattr(msg, "data", None)
            if not isinstance(data, (bytes, bytearray)):
                continue
            payload = json.loads(data.decode("utf-8"))
            if not isinstance(payload, dict):
                continue
            event_id = str(payload.get("event_id") or "").strip()
            if not event_id:
                continue
            items.append(
                ReplayItem(
                    source="stream_seq",
                    key=f"seq:{seq}",
                    event_id=event_id,
                    payload=payload,
                )
            )
    finally:
        await nc.drain()
        await nc.close()
    return items


def _collect_items(
    *,
    dlq_ids: list[int],
    after: str | None,
    before: str | None,
    seq_start: int | None,
    seq_end: int | None,
    limit: int,
) -> list[ReplayItem]:
    items: list[ReplayItem] = []
    if dlq_ids or after or before:
        conn = psycopg2.connect(settings.postgres_dsn)
        try:
            rows = load_dlq_candidates(
                conn,
                dlq_ids=dlq_ids,
                after=parse_iso(after),
                before=parse_iso(before),
                limit=limit,
            )
            items.extend(build_items_from_dlq(rows))
        finally:
            conn.close()
    if seq_start is not None or seq_end is not None:
        if seq_start is None or seq_end is None:
            raise ValueError(
                "Both --seq-start and --seq-end are required for stream replay"
            )
        if seq_start > seq_end:
            raise ValueError("--seq-start must be <= --seq-end")
        items.extend(asyncio.run(_load_items_from_seq_range(seq_start, seq_end)))
    return items


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay queued telemetry events from DLQ subset and/or JetStream sequence range."
    )
    parser.add_argument(
        "--dlq-ids", default="", help="Comma-separated dlq_events.id values"
    )
    parser.add_argument(
        "--after", default="", help="DLQ created_at lower bound (ISO8601)"
    )
    parser.add_argument(
        "--before", default="", help="DLQ created_at upper bound (ISO8601)"
    )
    parser.add_argument(
        "--seq-start", type=int, default=None, help="JetStream sequence start"
    )
    parser.add_argument(
        "--seq-end", type=int, default=None, help="JetStream sequence end"
    )
    parser.add_argument("--limit", type=int, default=200, help="Max DLQ rows to load")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute publish to JetStream. Without this flag script is dry-run only.",
    )
    args = parser.parse_args()

    try:
        dlq_ids = parse_id_csv(args.dlq_ids)
        items_raw = _collect_items(
            dlq_ids=dlq_ids,
            after=args.after or None,
            before=args.before or None,
            seq_start=args.seq_start,
            seq_end=args.seq_end,
            limit=args.limit,
        )
    except Exception as exc:
        print(f"Replay queue failed while collecting candidates: {exc}")
        return 1

    items, dup_local = dedupe_replay_items(items_raw)
    summary: dict[str, Any] = {
        "mode": "apply" if args.apply else "dry-run",
        "loaded_candidates": len(items_raw),
        "local_duplicates_filtered": dup_local,
        "to_replay": len(items),
        "sources": sorted({it.source for it in items}),
    }

    if not args.apply:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print("Dry-run only. Re-run with --apply to publish.")
        return 0

    try:
        published, dup_broker = asyncio.run(_publish_items(items))
    except Exception as exc:
        print(f"Replay queue apply failed: {exc}")
        return 1

    summary["published"] = published
    summary["broker_duplicates"] = dup_broker
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
