from __future__ import annotations

from apps.workers.telemetry_persist import insert_dlq_event


def test_insert_dlq_event_executes_insert():
    calls: list[tuple[tuple, dict]] = []

    class DummyCursor:
        def execute(self, *args, **kwargs):
            calls.append((args, kwargs))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class DummyConn:
        committed = False

        def cursor(self):
            return DummyCursor()

        def commit(self):
            self.committed = True

    conn = DummyConn()
    insert_dlq_event(
        conn,
        event_id="evt-1",
        reason="persist_failure",
        retry_count=3,
        next_retry_at=None,
        last_error="boom",
        payload={"event_id": "evt-1"},
        incident_id="inc-1",
        run_id=None,
        subject="ingest.telemetry",
    )
    assert conn.committed is True
    assert len(calls) == 1
