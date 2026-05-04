"""
PS3.2 / ADR 0002 — Telemetry ingest via NATS JetStream.

Offsets are **broker-native** (JetStream durable consumer ack positions). Postgres holds
`telemetry_events` written asynchronously by `apps.workers.telemetry_persister`.

PS3.9 note: agent pipelines should use `thread_id` correlated with `event_id` / `run_id`
when consuming the same stream — design in PS3.9; persister stays independent.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI

from config import settings

if TYPE_CHECKING:
    from nats.js import JetStreamContext

logger = logging.getLogger(__name__)

_nats_lock = asyncio.Lock()


def _nats_servers() -> list[str]:
    return [s.strip() for s in settings.nats_url.split(",") if s.strip()]


async def setup_jetstream_stream(js: Any) -> None:
    """Create ingest stream if missing (idempotent)."""
    from nats.js.api import StreamConfig
    from nats.js.errors import NotFoundError

    try:
        await js.stream_info(settings.jetstream_stream_name)
    except NotFoundError:
        await js.add_stream(
            StreamConfig(
                name=settings.jetstream_stream_name,
                subjects=[settings.jetstream_telemetry_subject],
            )
        )
        logger.info(
            "Created JetStream %s subject=%s",
            settings.jetstream_stream_name,
            settings.jetstream_telemetry_subject,
        )


async def get_or_create_js(app: FastAPI) -> JetStreamContext:
    """Lazy JetStream handle on FastAPI app.state (short-lived connections avoided per request)."""
    async with _nats_lock:
        js_existing = getattr(app.state, "nats_js", None)
        if js_existing is not None:
            return js_existing

        servers = _nats_servers()
        if not servers:
            raise RuntimeError("nats_url is empty")

        import nats

        nc = await nats.connect(servers=servers)
        js = nc.jetstream()
        await setup_jetstream_stream(js)
        app.state.nats_nc = nc
        app.state.nats_js = js
        logger.info("Connected NATS JetStream servers=%s", servers)
        return js


async def publish_telemetry_records(
    js: JetStreamContext, records: list[dict[str, Any]]
) -> tuple[int, int, int]:
    """
    Publish validated telemetry rows.

    Returns ``(accepted_new, duplicates_in_batch, duplicates_at_broker)``.
    Broker duplicates come from JetStream ``Nats-Msg-Id`` dedupe (same ``event_id``).
    """
    seen_in_batch: set[str] = set()
    duplicates_in_batch = 0
    accepted_new = 0
    duplicates_at_broker = 0
    subject = settings.jetstream_telemetry_subject

    for rec in records:
        eid = str(rec.get("event_id") or "").strip()
        if not eid:
            duplicates_in_batch += 1
            continue
        if eid in seen_in_batch:
            duplicates_in_batch += 1
            continue
        seen_in_batch.add(eid)

        payload = json.dumps(rec, sort_keys=True, ensure_ascii=False).encode("utf-8")
        headers = {"Nats-Msg-Id": eid[:240]}
        pa = await js.publish(subject, payload, headers=headers)
        if getattr(pa, "duplicate", False):
            duplicates_at_broker += 1
        else:
            accepted_new += 1

    return accepted_new, duplicates_in_batch, duplicates_at_broker


async def close_nats(app: FastAPI) -> None:
    nc = getattr(app.state, "nats_nc", None)
    if nc is None:
        return
    try:
        await nc.drain()
    except Exception:
        pass
    try:
        await nc.close()
    except Exception:
        pass
    app.state.nats_nc = None
    app.state.nats_js = None
