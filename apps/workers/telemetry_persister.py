"""
JetStream → Postgres telemetry persister (PS3.2 / ADR 0002).

Run: ``python -m apps.workers.telemetry_persister`` (requires ``NATS_URL`` + Postgres).

Broker retains ack positions for durable ``telemetry-persister``; no SQL ``consumer_offsets`` table.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import sys
from datetime import datetime, timedelta, timezone

import psycopg2

from apps.ingest_jetstream import setup_jetstream_stream
from apps.workers.telemetry_persist import insert_dlq_event, insert_telemetry_event
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _delivery_attempt(msg: object) -> int:
    meta = getattr(msg, "metadata", None)
    delivered = getattr(meta, "num_delivered", None)
    if delivered is None:
        return 1
    try:
        return int(delivered)
    except (TypeError, ValueError):
        return 1


def _calc_backoff_seconds(attempt: int, base: float) -> float:
    p = max(0, attempt - 1)
    return max(0.0, float(base) * (2.0**p))


def _reason_from_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "json" in text:
        return "invalid_json"
    if "schema" in text or "validation" in text:
        return "validation_error"
    return "persist_failure"


async def run_forever() -> None:
    servers = [s.strip() for s in settings.nats_url.split(",") if s.strip()]
    if not servers:
        logger.error("NATS_URL / settings.nats_url is empty — exiting.")
        sys.exit(1)

    import nats

    pg_dsn = settings.postgres_dsn
    conn = psycopg2.connect(pg_dsn)
    conn.autocommit = False

    nc = await nats.connect(servers=servers)
    js = nc.jetstream()
    await setup_jetstream_stream(js)

    psub = await js.pull_subscribe(
        settings.jetstream_telemetry_subject,
        durable=settings.jetstream_persister_durable,
        stream=settings.jetstream_stream_name,
    )
    logger.info(
        "Persister subscribed stream=%s durable=%s subject=%s",
        settings.jetstream_stream_name,
        settings.jetstream_persister_durable,
        settings.jetstream_telemetry_subject,
    )

    try:
        while True:
            try:
                msgs = await psub.fetch(32, timeout=5)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception as fetch_exc:
                logger.warning("fetch error: %s", fetch_exc)
                await asyncio.sleep(1)
                continue

            for msg in msgs:
                attempt = _delivery_attempt(msg)
                row: dict[str, object] = {}
                try:
                    row = json.loads(msg.data.decode("utf-8"))
                    insert_telemetry_event(conn, row)
                    await msg.ack()
                except json.JSONDecodeError as je:
                    reason = "invalid_json"
                    if attempt >= settings.jetstream_persister_max_retries:
                        insert_dlq_event(
                            conn,
                            event_id="unknown",
                            reason=reason,
                            retry_count=attempt,
                            next_retry_at=None,
                            last_error=str(je),
                            payload={"raw": msg.data.decode("utf-8", errors="ignore")},
                            subject=getattr(msg, "subject", None),
                        )
                        logger.error(
                            "DLQ invalid json after %s attempts subject=%s",
                            attempt,
                            getattr(msg, "subject", None),
                        )
                        await msg.ack()
                    else:
                        backoff = _calc_backoff_seconds(
                            attempt, settings.jetstream_persister_retry_base_seconds
                        )
                        logger.warning(
                            "invalid json, retry attempt=%s delay=%.1fs: %s",
                            attempt,
                            backoff,
                            je,
                        )
                        try:
                            await msg.nak(delay=math.ceil(backoff))
                        except TypeError:
                            await msg.nak()
                except Exception as exc:
                    reason = _reason_from_error(exc)
                    event_id = str(row.get("event_id") or "unknown")
                    if attempt >= settings.jetstream_persister_max_retries:
                        next_retry = None
                        insert_dlq_event(
                            conn,
                            event_id=event_id,
                            reason=reason,
                            retry_count=attempt,
                            next_retry_at=next_retry,
                            last_error=str(exc),
                            payload=row,
                            subject=getattr(msg, "subject", None),
                        )
                        logger.exception(
                            "persist failed permanently; moved to DLQ event_id=%s attempts=%s",
                            event_id,
                            attempt,
                        )
                        await msg.ack()
                    else:
                        backoff = _calc_backoff_seconds(
                            attempt, settings.jetstream_persister_retry_base_seconds
                        )
                        next_retry_at = datetime.now(timezone.utc) + timedelta(
                            seconds=backoff
                        )
                        logger.exception(
                            "persist failed; retry attempt=%s delay=%.1fs next_retry_at=%s",
                            attempt,
                            backoff,
                            next_retry_at.isoformat(),
                        )
                        try:
                            await msg.nak(delay=math.ceil(backoff))
                        except TypeError:
                            await msg.nak()
    finally:
        await nc.drain()
        await nc.close()
        conn.close()


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
