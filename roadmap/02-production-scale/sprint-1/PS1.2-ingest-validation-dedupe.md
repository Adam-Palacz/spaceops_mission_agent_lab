wytlumacz# PS1.2 — Ingest validation + event dedupe

| Field | Value |
|-------|--------|
| **Task ID** | PS1.2 |
| **Status** | Done |

---

## Description

Harden ingest so malformed events are rejected early and repeated events do not create duplicate
records. Primary dedupe key: `event_id` (or deterministic hash fallback for legacy payloads).

---

## Requirements

- [x] Ingest validates incoming events against `TelemetryEvent.v1`.
- [x] Dedupe enforced by unique `event_id` semantics.
- [x] Duplicate ingest calls are idempotent (no duplicate rows).
- [x] API responses distinguish accepted, duplicate, and invalid records.
- [x] Audit/metrics expose dedupe and validation outcomes.

---

## Checklist

- [x] Add ingest validation step before persistence.
- [x] Add uniqueness protection in storage layer/index.
- [x] Implement conflict handling policy for duplicates.
- [x] Return structured ingest summary (`accepted`, `duplicates`, `rejected`).
- [x] Add tests for valid, invalid, and duplicate batches.

---

## Test requirements

- [x] Reposting the same event batch keeps row count unchanged.
- [x] Invalid schema events return 4xx and are not stored.
- [x] Mixed batch processing reports correct counters.
