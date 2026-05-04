# PS3.1 — Queue strategy decision (ADR)

| Field | Value |
|-------|-------|
| **Task ID** | PS3.1 |
| **Status** | Done |

---

## Description

Choose and document how SpaceOps **decouples ingest from workers**: DB-backed offsets (Phase 2 Option A)
vs external broker (**NATS JetStream**, Redpanda/Kafka — Option B per parent roadmap). The ADR locks
partitioning keys (`sat_id`, subsystem), consumer groups, and the migration path from today’s
mostly synchronous/file-backed flows.

---

## Requirements

- [x] ADR under `docs/adr/` (or equivalent): decision, alternatives rejected, operational implications (backup, replay).
- [x] Explicit **default for lab**: minimal DB-offset worker vs broker — must match what PS3.2–PS3.4 implement first.
- [x] Compatibility statement vs existing **telemetry_events** append-only model and **Alembic** migrations.
- [x] Handoff notes for **PS6** (cluster deployment): broker Helm/GitOps expectations if Option B wins.

---

## Checklist

- [x] Record latency/throughput assumptions (burst telemetry scenarios — deferred quantification to PS3.5).
- [x] Align naming with Phase README sprint goal ([README.md](README.md)).

---

## Test / acceptance

- [x] ADR merged + linked from [BOARD.md](BOARD.md) and sprint [README.md](README.md).

---

## Delivered

- **[ADR 0001](../../../docs/adr/0001-queue-strategy-postgres-first-jetstream-later.md)** — initial Postgres-first lab decision (historical).
- **[ADR 0002](../../../docs/adr/0002-ingest-nats-first-postgres-evidence-store.md)** — **accepted strategy:** NATS JetStream–first ingest, **no dual-write**, Postgres as state/evidence store; supersedes 0001.
- Index: [`docs/adr/README.md`](../../../docs/adr/README.md).
- Cross-links: [`docs/architecture.md`](../../../docs/architecture.md) (intro + ingest bullet).

---

## Dependencies

- None (blocks PS3.2–PS3.4 scope clarity).
