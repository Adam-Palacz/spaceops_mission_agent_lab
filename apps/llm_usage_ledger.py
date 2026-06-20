"""PS7.6 — shared daily LLM token ledger in Postgres."""

from __future__ import annotations

from datetime import date, datetime, timezone

import psycopg2

from config import settings

LEDGER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS llm_usage_ledger (
    usage_date DATE NOT NULL PRIMARY KEY,
    tokens_used BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def _conn():
    return psycopg2.connect(settings.postgres_dsn)


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def ensure_ledger_table() -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(LEDGER_TABLE_SQL)
        conn.commit()


def get_daily_tokens_used(*, usage_date: date | None = None) -> int:
    ensure_ledger_table()
    day = usage_date or utc_today()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tokens_used FROM llm_usage_ledger WHERE usage_date = %s",
                (day,),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0


def add_daily_tokens(*, tokens: int, usage_date: date | None = None) -> int:
    ensure_ledger_table()
    amount = max(0, int(tokens or 0))
    day = usage_date or utc_today()
    if amount == 0:
        return get_daily_tokens_used(usage_date=day)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO llm_usage_ledger (usage_date, tokens_used, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (usage_date) DO UPDATE
                SET tokens_used = llm_usage_ledger.tokens_used + EXCLUDED.tokens_used,
                    updated_at = NOW()
                RETURNING tokens_used
                """,
                (day, amount),
            )
            total = int(cur.fetchone()[0])
        conn.commit()
    return total
