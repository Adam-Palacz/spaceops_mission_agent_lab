# PS3.1 — Queue strategy decision (ADR)

| Field | Value |
|-------|-------|
| **Task ID** | PS3.1 |
| **Status** | Todo |

---

## Description

Choose and document how SpaceOps **decouples ingest from workers**: DB-backed offsets (Phase 2 Option A)
vs external broker (**NATS JetStream**, Redpanda/Kafka — Option B per parent roadmap). The ADR locks
partitioning keys (`sat_id`, subsystem), consumer groups, and the migration path from today’s
mostly synchronous/file-backed flows.

---

## Requirements

- [ ] ADR under `docs/adr/` (or equivalent): decision, alternatives rejected, operational implications (backup, replay).
- [ ] Explicit **default for lab**: minimal DB-offset worker vs broker — must match what PS3.2–PS3.4 implement first.
- [ ] Compatibility statement vs existing **telemetry_events** append-only model and **Alembic** migrations.
- [ ] Handoff notes for **PS6** (cluster deployment): broker Helm/GitOps expectations if Option B wins.

---

## Checklist

- [ ] Record latency/throughput assumptions (burst telemetry scenarios).
- [ ] Align naming with Phase README sprint goal ([README.md](README.md)).

---

## Test / acceptance

- [ ] ADR merged + linked from [BOARD.md](BOARD.md) and sprint [README.md](README.md).

---

## Dependencies

- None (blocks PS3.2–PS3.4 scope clarity).
