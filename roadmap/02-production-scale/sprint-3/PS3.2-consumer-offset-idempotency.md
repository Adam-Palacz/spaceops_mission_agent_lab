# PS3.2 — Consumer offset store + idempotency keys

| Field | Value |
|-------|-------|
| **Task ID** | PS3.2 |
| **Status** | Todo |

---

## Description

Implement **consumer offsets** and **idempotency** so workers can process queued/ordered telemetry
without double-invoking downstream effects (duplicate agent runs, duplicate incidents). Exactly-once is
not assumed from infrastructure alone — application-level keys bridge gaps.

---

## Requirements

- [ ] Persistence model aligned with PS3.1 ADR (table `consumer_offsets` and/or broker-native offsets).
- [ ] Idempotency key derived from **`event_id`** (and/or `(sat_id, sequence)` where applicable).
- [ ] Worker loop semantics documented: fetch → validate idempotency → process → commit offset **transactionally** where DB allows.
- [ ] Tests: duplicate delivery does not create duplicate incidents/runs.

---

## Checklist

- [ ] Interaction with **PS3.9** checkpoint keys documented (same run/thread identity rules).

---

## Test / acceptance

- [ ] Automated tests cover duplicate consume and restart-at-offset scenarios.

---

## Dependencies

- **PS3.1** ADR approved for storage/broker choice.
