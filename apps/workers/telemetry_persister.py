"""
JetStream → Postgres telemetry persister (PS3.2 / ADR 0002).

Run: ``python -m apps.workers.telemetry_persister`` (requires ``NATS_URL`` + Postgres).

Broker retains ack positions for durable ``telemetry-persister``; no SQL ``consumer_offsets`` table.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import psycopg2

from apps.ingest_jetstream import setup_jetstream_stream
from apps.workers.telemetry_persist import insert_telemetry_event
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
                try:
                    row = json.loads(msg.data.decode("utf-8"))
                    insert_telemetry_event(conn, row)
                    await msg.ack()
                except json.JSONDecodeError as je:
                    logger.warning("invalid json, nak: %s", je)
                    await msg.nak()
                except Exception as exc:
                    logger.exception("persist failed, nak: %s", exc)
                    conn.rollback()
                    await msg.nak()
    finally:
        await nc.drain()
        await nc.close()
        conn.close()


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
