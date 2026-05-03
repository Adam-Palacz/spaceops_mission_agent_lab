# PS3.3 — Retry workflow + DLQ

| Field | Value |
|-------|-------|
| **Task ID** | PS3.3 |
| **Status** | Todo |

---

## Description

Add **bounded retries** and a **dead-letter path** for events/runs that fail processing after policy-defined
attempts. Operators need structured fields to triage: reason codes, retry counts, next retry window,
correlation to `run_id` / `event_id`.

---

## Requirements

- [ ] DLQ persistence (`dlq_events` table or broker DLQ topic per PS3.1).
- [ ] Fields minimally: `event_id`, `reason`, `retry_count`, `next_retry_at`, `last_error` / hash, linkage to incident/run where known.
- [ ] Retry policy configurable (max attempts, backoff); visible in settings or env documentation.
- [ ] API or CLI hook to **inspect** DLQ rows (read-only minimum).

---

## Checklist

- [ ] Audit trail: DLQ insertion emits structured log / audit row where repo pattern exists.

---

## Test / acceptance

- [ ] Tests simulate transient failure → retry succeeds → no DLQ row (or DLQ cleared).
- [ ] Tests simulate permanent failure → DLQ row with stable reason classification.

---

## Dependencies

- **PS3.2** offset/commit semantics so retries do not corrupt offsets.
