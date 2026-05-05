"""Insert validated telemetry JSON into Postgres (idempotent) + DLQ helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import Json, RealDictCursor


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


def _error_hash(message: str) -> str:
    payload = (message or "").strip().encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def insert_dlq_event(
    conn: PGConnection,
    *,
    event_id: str,
    reason: str,
    retry_count: int,
    next_retry_at: datetime | None,
    last_error: str,
    payload: dict[str, Any] | None = None,
    incident_id: str | None = None,
    run_id: str | None = None,
    subject: str | None = None,
) -> None:
    """Persist a dead-letter event row for operator triage."""
    eid = (event_id or "").strip() or "unknown"
    why = (reason or "").strip() or "unknown_error"
    err = (last_error or "").strip()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dlq_events (
                event_id, reason, retry_count, next_retry_at, last_error, last_error_hash,
                run_id, incident_id, subject, payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                eid,
                why,
                int(retry_count),
                next_retry_at,
                err,
                _error_hash(err),
                run_id,
                incident_id,
                subject,
                Json(payload or {}),
            ),
        )
    conn.commit()


def list_dlq_events(conn: PGConnection, *, limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = min(max(int(limit), 1), 1000)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT event_id, reason, retry_count, next_retry_at, last_error,
                   last_error_hash, run_id, incident_id, subject, payload, created_at
            FROM dlq_events
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (safe_limit,),
        )
        rows = cur.fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        for key in ("created_at", "next_retry_at"):
            dt = item.get(key)
            if isinstance(dt, datetime):
                item[key] = dt.isoformat()
        payload = item.get("payload")
        if isinstance(payload, str):
            try:
                item["payload"] = json.loads(payload)
            except json.JSONDecodeError:
                pass
        out.append(item)
    return out
