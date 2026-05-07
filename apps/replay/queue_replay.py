from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor


@dataclass
class ReplayItem:
    source: str
    key: str
    event_id: str
    payload: dict[str, Any]


def parse_id_csv(raw: str | None) -> list[int]:
    text = (raw or "").strip()
    if not text:
        return []
    out: list[int] = []
    for part in text.split(","):
        p = part.strip()
        if not p:
            continue
        out.append(int(p))
    return out


def parse_iso(raw: str | None) -> datetime | None:
    txt = (raw or "").strip()
    if not txt:
        return None
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    return datetime.fromisoformat(txt)


def load_dlq_candidates(
    conn: PGConnection,
    *,
    dlq_ids: list[int] | None,
    after: datetime | None,
    before: datetime | None,
    limit: int,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if dlq_ids:
        where.append("id = ANY(%s)")
        params.append(dlq_ids)
    if after is not None:
        where.append("created_at >= %s")
        params.append(after)
    if before is not None:
        where.append("created_at <= %s")
        params.append(before)

    sql = """
        SELECT id, event_id, payload, created_at, reason, retry_count
        FROM dlq_events
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id ASC LIMIT %s"
    params.append(max(1, min(int(limit), 5000)))

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def dedupe_replay_items(items: list[ReplayItem]) -> tuple[list[ReplayItem], int]:
    seen: set[str] = set()
    out: list[ReplayItem] = []
    dup = 0
    for item in items:
        eid = (item.event_id or "").strip()
        if not eid:
            dup += 1
            continue
        if eid in seen:
            dup += 1
            continue
        seen.add(eid)
        out.append(item)
    return out, dup


def build_items_from_dlq(rows: list[dict[str, Any]]) -> list[ReplayItem]:
    items: list[ReplayItem] = []
    for row in rows:
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        event_id = str(payload.get("event_id") or row.get("event_id") or "").strip()
        if not event_id:
            continue
        items.append(
            ReplayItem(
                source="dlq",
                key=f"dlq:{row.get('id')}",
                event_id=event_id,
                payload=payload,
            )
        )
    return items
