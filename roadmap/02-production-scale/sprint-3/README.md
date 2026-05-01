# Production Scale — Sprint 3 (PS3)

**Goal:** introduce streaming/backpressure realism and resilient processing with offset tracking,
DLQ handling, and replay support over queued events.

---

## Outcomes

- Queue/offset processing model with idempotent consumer semantics.
- DLQ capture for failed processing and retry/replay path.
- Backpressure behavior tested (ingest remains stable under burst load).
- Space-like disruptions simulated (drop/dup/out-of-order/contact-window effects).

---

## Tasks

See **[BOARD.md](BOARD.md)** for status of PS3.1-PS3.8.

---

## Definition of done (sprint)

- [ ] Backpressure does not crash ingest or corrupt offsets.
- [ ] DLQ captures failed events with diagnosable reasons.
- [ ] Replay works for queued events and preserves incident traceability.
- [ ] At least one disruption scenario is covered by automated tests.
