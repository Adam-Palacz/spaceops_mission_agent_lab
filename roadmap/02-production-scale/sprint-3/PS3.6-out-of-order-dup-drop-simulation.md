# PS3.6 — Out-of-order / dup / drop simulation (telemetry stream)

| Field | Value |
|-------|-------|
| **Task ID** | PS3.6 |
| **Status** | Done |

---

## Description

Prove robustness of **telemetry stream handling** when transport exhibits **drops**, **duplicates**, or
**out-of-order** arrival — ground IT realism without full CCSDS. Distinct from **PS3.10** (MCP HTTP transport chaos).

---

## Requirements

- [x] Fault injector / test harness with configurable probabilities for reorder/dup/drop.
- [x] Assertions: duplicates do not inflate durable state (idempotency by `event_id` from PS3.2), disruption does not corrupt persistence.
- [x] Sequence/validity hook via transport metadata (`metadata.seq`, `metadata.sat_id`) compatible with future adapter checks (CRC-like check can be layered without breaking API).

---

## Checklist

- [x] Separate doc note vs PS3.10 scope boundary.

Scope boundary note:
- **PS3.6** validates telemetry stream behavior under ordering/disruption at ingest + persistence path.
- **PS3.10** covers MCP/HTTP transport resilience and escalation-proof behavior on tool links, not telemetry queue durability semantics.

---

## Test / acceptance

- [x] Automated disruption scenario: `python -m scripts.simulate_stream_disruption --api-base-url http://localhost:8000 --event-prefix ps36demo`.

Implemented artifacts:
- `apps/load/stream_disruption.py` — generator + fault injector + durability health summary.
- `scripts/simulate_stream_disruption.py` — executable scenario against `/ingest` + Postgres verification.
- `tests/test_stream_disruption.py` — deterministic unit coverage of generator/disruption/health logic.

---

## Dependencies

- **PS3.2** idempotency semantics.
