"""Postgres-backed agent run queue (PS7.3 Variant A / ADR 0001 claim-lease pattern)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from config import settings

RUN_QUEUE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_run_queue (
    run_id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending',
    resume BOOLEAN NOT NULL DEFAULT FALSE,
    replay_source TEXT NOT NULL DEFAULT 'api',
    worker_id TEXT,
    leased_until TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_agent_run_queue_status_created
    ON agent_run_queue(status, created_at);
CREATE INDEX IF NOT EXISTS ix_agent_run_queue_leased_until
    ON agent_run_queue(leased_until)
    WHERE status = 'processing';
"""

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_DONE = "done"
STATUS_FAILED = "failed"


@dataclass
class RunQueueJob:
    run_id: str
    incident_id: str
    payload: dict[str, Any]
    resume: bool
    replay_source: str
    status: str
    worker_id: str | None = None


def agent_worker_enabled() -> bool:
    return bool(getattr(settings, "agent_worker_enabled", False))


def _conn():
    return psycopg2.connect(settings.postgres_dsn)


def ensure_run_queue_table() -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(RUN_QUEUE_TABLE_SQL)
        conn.commit()


def new_run_id() -> str:
    return uuid.uuid4().hex


def enqueue_run(
    *,
    run_id: str,
    incident_id: str,
    payload: dict[str, Any] | None,
    resume: bool = False,
    replay_source: str = "api",
) -> RunQueueJob:
    """Enqueue a graph run for the agent worker. Idempotent on run_id (no duplicate enqueue)."""
    ensure_run_queue_table()
    rid = (run_id or "").strip() or new_run_id()
    pl = dict(payload or {})
    now = datetime.now(timezone.utc)
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO agent_run_queue
                    (run_id, incident_id, payload, status, resume, replay_source, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO NOTHING
                RETURNING run_id, incident_id, payload, status, resume, replay_source, worker_id
                """,
                (
                    rid,
                    incident_id,
                    Json(pl),
                    STATUS_PENDING,
                    resume,
                    replay_source,
                    now,
                ),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    SELECT run_id, incident_id, payload, status, resume, replay_source, worker_id
                    FROM agent_run_queue
                    WHERE run_id = %s
                    """,
                    (rid,),
                )
                row = cur.fetchone()
        conn.commit()
    assert row
    return _row_to_job(row)


def get_queue_job(run_id: str) -> RunQueueJob | None:
    rid = (run_id or "").strip()
    if not rid:
        return None
    ensure_run_queue_table()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT run_id, incident_id, payload, status, resume, replay_source, worker_id
                FROM agent_run_queue
                WHERE run_id = %s
                """,
                (rid,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return _row_to_job(row)


def claim_next_job(
    *, worker_id: str, lease_seconds: int | None = None
) -> RunQueueJob | None:
    """Claim one pending or expired-lease job (SKIP LOCKED)."""
    ensure_run_queue_table()
    lease = lease_seconds or int(
        getattr(settings, "agent_run_queue_lease_seconds", 300)
    )
    wid = (worker_id or "").strip() or "worker"
    now = datetime.now(timezone.utc)
    leased_until = now + timedelta(seconds=max(30, lease))
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                WITH candidate AS (
                    SELECT run_id
                    FROM agent_run_queue
                    WHERE status = %s
                       OR (status = %s AND leased_until IS NOT NULL AND leased_until < %s)
                    ORDER BY created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE agent_run_queue q
                SET status = %s,
                    worker_id = %s,
                    leased_until = %s,
                    updated_at = %s
                FROM candidate
                WHERE q.run_id = candidate.run_id
                RETURNING q.run_id, q.incident_id, q.payload, q.status, q.resume, q.replay_source, q.worker_id
                """,
                (
                    STATUS_PENDING,
                    STATUS_PROCESSING,
                    now,
                    STATUS_PROCESSING,
                    wid,
                    leased_until,
                    now,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        return None
    return _row_to_job(row)


def complete_job(run_id: str, *, worker_id: str) -> bool:
    """Mark a claimed job done only if this worker still owns the lease."""
    wid = (worker_id or "").strip()
    if not wid:
        return False
    now = datetime.now(timezone.utc)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE agent_run_queue
                SET status = %s, leased_until = NULL, updated_at = %s, error_message = NULL
                WHERE run_id = %s
                  AND status = %s
                  AND worker_id = %s
                """,
                (STATUS_DONE, now, run_id, STATUS_PROCESSING, wid),
            )
            updated = cur.rowcount
        conn.commit()
    return updated == 1


def fail_job(run_id: str, error_message: str, *, worker_id: str) -> bool:
    """Mark a claimed job failed only if this worker still owns the lease."""
    wid = (worker_id or "").strip()
    if not wid:
        return False
    now = datetime.now(timezone.utc)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE agent_run_queue
                SET status = %s, leased_until = NULL, updated_at = %s, error_message = %s
                WHERE run_id = %s
                  AND status = %s
                  AND worker_id = %s
                """,
                (
                    STATUS_FAILED,
                    now,
                    error_message[:2000],
                    run_id,
                    STATUS_PROCESSING,
                    wid,
                ),
            )
            updated = cur.rowcount
        conn.commit()
    return updated == 1


def _row_to_job(row: dict[str, Any]) -> RunQueueJob:
    payload = row.get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return RunQueueJob(
        run_id=str(row.get("run_id") or ""),
        incident_id=str(row.get("incident_id") or ""),
        payload=payload,
        resume=bool(row.get("resume")),
        replay_source=str(row.get("replay_source") or "api"),
        status=str(row.get("status") or ""),
        worker_id=str(row.get("worker_id") or "") or None,
    )
