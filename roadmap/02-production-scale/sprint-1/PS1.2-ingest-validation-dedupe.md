wytlumacz# PS1.2 — Ingest validation + event dedupe

| Field | Value |
|-------|--------|
| **Task ID** | PS1.2 |
| **Status** | Todo |

---

## Description

Harden ingest so malformed events are rejected early and repeated events do not create duplicate
records. Primary dedupe key: `event_id` (or deterministic hash fallback for legacy payloads).

---

## Requirements

- [ ] Ingest validates incoming events against `TelemetryEvent.v1`.
- [ ] Dedupe enforced by unique `event_id` semantics.
- [ ] Duplicate ingest calls are idempotent (no duplicate rows).
- [ ] API responses distinguish accepted, duplicate, and invalid records.
- [ ] Audit/metrics expose dedupe and validation outcomes.

---

## Checklist

- [ ] Add ingest validation step before persistence.
- [ ] Add uniqueness protection in storage layer/index.
- [ ] Implement conflict handling policy for duplicates.
- [ ] Return structured ingest summary (`accepted`, `duplicates`, `rejected`).
- [ ] Add tests for valid, invalid, and duplicate batches.

---

## Test requirements

- [ ] Reposting the same event batch keeps row count unchanged.
- [ ] Invalid schema events return 4xx and are not stored.
- [ ] Mixed batch processing reports correct counters.
