#!/usr/bin/env python3
"""PS6.11 checkpoint retention stub — delete terminal rows older than N days."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Prune old agent_graph_checkpoints rows (terminal statuses only)."
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Report rows that would be deleted (default if --apply not set).",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Execute DELETE (requires DATABASE_URL / Postgres).",
    )
    p.add_argument(
        "--older-than-days",
        type=int,
        default=int(os.getenv("CHECKPOINT_RETENTION_DAYS", "30") or 30),
        help="Delete terminal checkpoints older than this many days.",
    )
    return p.parse_args()


def _conn():
    from apps.agent.checkpointing import _conn

    return _conn()


def main() -> int:
    from apps.agent.checkpointing import ensure_checkpoint_table

    args = _parse_args()
    dry_run = args.dry_run or not args.apply
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.older_than_days)
    terminal = ("completed", "failed")

    ensure_checkpoint_table()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM agent_graph_checkpoints
                WHERE status = ANY(%s) AND updated_at < %s
                """,
                (list(terminal), cutoff),
            )
            count = int(cur.fetchone()[0])
            print(f"older_than_days={args.older_than_days}")
            print(f"cutoff_utc={cutoff.isoformat()}")
            print(f"terminal_statuses={terminal}")
            print(f"candidate_rows={count}")
            if dry_run:
                print("mode=dry-run (pass --apply to delete)")
                return 0
            cur.execute(
                """
                DELETE FROM agent_graph_checkpoints
                WHERE status = ANY(%s) AND updated_at < %s
                """,
                (list(terminal), cutoff),
            )
            deleted = cur.rowcount
            conn.commit()
            print(f"deleted_rows={deleted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
