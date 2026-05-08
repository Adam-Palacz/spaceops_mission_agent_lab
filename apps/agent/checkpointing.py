from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from config import settings


CHECKPOINT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_graph_checkpoints (
    run_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    incident_id TEXT NOT NULL,
    status TEXT NOT NULL,
    next_node TEXT,
    state JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_agent_graph_checkpoints_thread_id
    ON agent_graph_checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS ix_agent_graph_checkpoints_status_updated_at
    ON agent_graph_checkpoints(status, updated_at DESC);
"""


@dataclass
class CheckpointRecord:
    run_id: str
    thread_id: str
    incident_id: str
    status: str
    next_node: str | None
    state: dict[str, Any]
    updated_at: str


def durable_checkpoint_enabled() -> bool:
    return bool(getattr(settings, "agent_durable_checkpoint_enabled", False))


def _conn():
    return psycopg2.connect(settings.postgres_dsn)


def ensure_checkpoint_table() -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(CHECKPOINT_TABLE_SQL)


def upsert_checkpoint(
    *,
    run_id: str,
    thread_id: str,
    incident_id: str,
    status: str,
    next_node: str | None,
    state: dict[str, Any],
) -> None:
    ensure_checkpoint_table()
    now = datetime.now(timezone.utc)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_graph_checkpoints
                    (run_id, thread_id, incident_id, status, next_node, state, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO UPDATE
                SET
                    thread_id = EXCLUDED.thread_id,
                    incident_id = EXCLUDED.incident_id,
                    status = EXCLUDED.status,
                    next_node = EXCLUDED.next_node,
                    state = EXCLUDED.state,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    run_id,
                    thread_id,
                    incident_id,
                    status,
                    next_node,
                    Json(state),
                    now,
                ),
            )


def load_checkpoint(run_id: str) -> CheckpointRecord | None:
    rid = (run_id or "").strip()
    if not rid:
        return None
    ensure_checkpoint_table()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT run_id, thread_id, incident_id, status, next_node, state, updated_at
                FROM agent_graph_checkpoints
                WHERE run_id = %s
                """,
                (rid,),
            )
            row = cur.fetchone()
    if not row:
        return None
    state = row.get("state")
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except Exception:
            state = {}
    if not isinstance(state, dict):
        state = {}
    return CheckpointRecord(
        run_id=str(row.get("run_id") or ""),
        thread_id=str(row.get("thread_id") or ""),
        incident_id=str(row.get("incident_id") or ""),
        status=str(row.get("status") or ""),
        next_node=str(row.get("next_node") or "") or None,
        state=state,
        updated_at=str(row.get("updated_at") or ""),
    )
