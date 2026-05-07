# PS3.7 — Contact-window simulation hooks

| Field | Value |
|-------|-------|
| **Task ID** | PS3.7 |
| **Status** | Done |

---

## Description

Introduce hooks to simulate **intermittent downlink / contact windows**: telemetry arrives in bursts tied to
simulated visibility periods; buffering + replay aligns with parent roadmap **Phase 2 space-like simulation**.

---

## Requirements

- [x] Configuration model for ON/OFF windows: cyclic ON/OFF plus explicit interval schedule for tests.
- [x] Simulation driver respects “no contact” periods with documented semantics: `off_mode=buffer|drop`.
- [x] Buffered telemetry replay on contact restore implemented by deterministic flush hook; aligns with PS3.4 replay/dedupe pattern (event-id based).
- [x] Operator bullets added here; PS3.8 remains owner of consolidated recovery runbook.

---

## Checklist

- [x] Non-invasive implementation via simulation hooks and script; MVP ingest path remains unchanged.

---

## Test / acceptance

- [x] Automated test: `tests/test_contact_window.py::test_buffered_events_flush_on_contact_open_without_duplication`.

Implemented artifacts:
- `apps/load/contact_window.py` — ON/OFF schedule hooks with `buffer`/`drop` semantics.
- `scripts/simulate_contact_window.py` — executable PS3.7 scenario posting to `/ingest` and validating durable uniqueness.
- `tests/test_contact_window.py` — automated coverage for buffered flush, drop mode, and explicit intervals.

Operator bullets (interim, PS3.8 will consolidate):
- Use `off_mode=buffer` for realism when expecting delayed downlink and later flush.
- Use `off_mode=drop` to stress observability alerts and loss accounting paths.
- Always isolate test runs by unique `--event-prefix` and verify `missing_after_persist=0` before comparing metrics.

---

## Dependencies

- **PS3.2**–**PS3.4** foundations recommended before deep coupling.
