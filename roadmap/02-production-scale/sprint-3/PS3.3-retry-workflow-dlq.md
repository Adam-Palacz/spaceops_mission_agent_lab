# PS3.3 — Retry workflow + DLQ

| Field | Value |
|-------|-------|
| **Task ID** | PS3.3 |
| **Status** | Done |

---

## Description

Add **bounded retries** and a **dead-letter path** for events/runs that fail processing after policy-defined
attempts. Operators need structured fields to triage: reason codes, retry counts, next retry window,
correlation to `run_id` / `event_id`.

---

## Requirements

- [x] DLQ persistence (`dlq_events` table via Alembic `20260505_0002_ps33_dlq`).
- [x] Fields: `event_id`, `reason`, `retry_count`, `next_retry_at`, `last_error`, `last_error_hash`, `subject`, optional `incident_id` / `run_id`, `payload`.
- [x] Retry policy configurable (env-backed settings).
- [x] API hook to inspect DLQ rows (read-only): `GET /dlq/telemetry`.

---

## Checklist

- [x] DLQ insertion emits structured logs from persister (`persist failed permanently; moved to DLQ ...`).

---

## Test / acceptance

- [x] Tests cover transient path primitives and DLQ insert plumbing:
  - `tests/test_telemetry_persist.py` helper behavior
  - `tests/test_telemetry_dlq.py` DLQ insert call/commit
- [x] API read-only inspection tests:
  - `tests/test_api.py::test_dlq_telemetry_endpoint_returns_rows`
  - `tests/test_api.py::test_dlq_telemetry_endpoint_db_unavailable`

---

## Delivered

- Worker retry/backoff + DLQ escalation in `apps/workers/telemetry_persister.py`.
- DLQ storage + listing helpers in `apps/workers/telemetry_persist.py`.
- API endpoint `GET /dlq/telemetry` in `apps/api/main.py`.
- Config knobs in `config.py`:
  - `jetstream_persister_max_retries`
  - `jetstream_persister_retry_base_seconds`
- Env docs in `.env.example`.
- Migration adding `dlq_events` table:
  - `alembic/versions/20260505_0002_ps33_dlq.py`

---

## Dependencies

- **PS3.2** offset/commit semantics so retries do not corrupt offsets.
