"""Insert validated telemetry JSON into Postgres (idempotent by event_id)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import Json


def parse_ts_iso(s: str) -> datetime:
    s = (s or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def coerce_value_to_float(raw: Any) -> float:
    if isinstance(raw, bool):
        return float(int(raw))
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return 0.0


def insert_telemetry_event(conn: PGConnection, row: dict[str, Any]) -> bool:
    """
    Persist one telemetry event. Returns True if a new row was inserted.
    Duplicate ``event_id`` → no-op (ON CONFLICT DO NOTHING).
    """
    event_id = str(row.get("event_id") or "").strip()
    if not event_id:
        return False
    ts = parse_ts_iso(str(row.get("ts") or ""))
    source = str(row.get("source") or "telemetry").strip() or "telemetry"
    channel = str(row.get("channel") or "").strip()
    if not channel:
        return False
    value_f = coerce_value_to_float(row.get("value"))
    unit = row.get("unit")
    unit_s = str(unit).strip() if unit is not None else None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO telemetry_events (
                    event_id, schema_version, ts, source, channel, value, unit, payload
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """,
                (
                    event_id,
                    str(row.get("schema_version") or "v1"),
                    ts,
                    source,
                    channel,
                    value_f,
                    unit_s,
                    Json(row),
                ),
            )
            inserted = cur.rowcount > 0
        conn.commit()
        return inserted
    except Exception:
        conn.rollback()
        raise
