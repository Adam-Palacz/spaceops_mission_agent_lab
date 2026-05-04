# ADR 0001 — Queue strategy: Postgres-first consumers, NATS JetStream when scale demands

| Field | Value |
|-------|-------|
| **Status** | Superseded |
| **Date** | 2026-05-03 |
| **Context** | Production Scale Phase — Sprint PS3 ([PS3.1](../../roadmap/02-production-scale/sprint-3/PS3.1-queue-strategy-decision.md)) |
| **Supersedes** | — |
| **Superseded by** | [ADR 0002 — Ingest NATS-first, Postgres evidence store](0002-ingest-nats-first-postgres-evidence-store.md) (2026-05-04) |

---

> **Note:** This document is **historical**. The operational queue and ingest boundary described here were superseded by ADR 0002. Do not implement new work against this ADR without reading 0002.

---

## Context

SpaceOps today exhibits a **split ingest path**:

1. **`POST /ingest`** validates telemetry (`TelemetryEventV1`), dedupes by `event_id`, and persists **NDJSON files** under `data/telemetry/` (and siblings). See `apps/api/main.py` (`_persist_ndjson`).
2. **Postgres** already defines an append-only **`telemetry_events`** table (Alembic baseline `20260501_0001_ps13_baseline`) aligned with **TelemetryEvent v1**, but **application code does not yet insert rows** on ingest — the durable relational stream is schema-ready, not wired.

Runs are triggered explicitly via **`POST /runs`** with payloads; there is **no asynchronous worker** that consumes an event backlog and fans out agent runs.

Goals from [roadmap/02-production-scale.md](../../roadmap/02-production-scale.md) Phase 2 and [sprint-3 README](../../roadmap/02-production-scale/sprint-3/README.md):

- Decouple **ingest burst** from **downstream processing** (backpressure, retries).
- Keep **traceability**: `event_id`, offsets, replay, DLQ — implemented in PS3.2–PS3.4.
- Preserve compatibility with **contracts v1**, **replay** (PS1.5), and future **Kubernetes/GitOps** packaging (PS6).

---

## Decision

### Default for this repository (lab → staged prod): **Option A — Postgres-backed logical queue**

1. **System of record for telemetry events** is **`telemetry_events`** in Postgres (append-only; PK `event_id`; matches existing migration philosophy).
2. **Ingest path** evolves so validated telemetry is **persisted to Postgres** (and optionally mirrored to NDJSON for debugging/dev parity — implementation detail of PS3.2+, not mandated here).
3. **Consumers** pull work from Postgres using a **safe queue pattern**, not a naive shared monotonic offset while multiple workers compete blindly.
   - **Preferred for parallel workers:** **row claiming** — e.g. `SELECT … FOR UPDATE SKIP LOCKED`, or a **`processing_tasks`** / outbox table with `status` (`PENDING` → `PROCESSING` → `DONE` / `FAILED`), **`locked_at` / `lease_until`**, and a **reaper** that returns expired leases to `PENDING`. This avoids losing in-flight ranges when one worker stalls and another advances a single global offset.
   - **Optional `consumer_offsets`** (PS3.2) may still record **high-water marks for replay/export**, or serve **single-consumer-per-partition** deployments — but **must not** be the only coordination primitive when multiple agents share one partition without leases.
   - **Partition key** for routing / fairness: **`sat_id`** from event metadata where present, else **`subsystem`**, else **`global`** for lab traffic.
4. **DB transactions and LangGraph:** Claiming or marking a row must use a **short** transaction; **do not** hold a DB connection or transaction open for the duration of LLM/MCP/OPA work (often tens of seconds). Flow: **txn: claim → commit → run agent off-pool → txn: persist outcome / DLQ / release lease**. Pool exhaustion and long locks are otherwise guaranteed under burst (external review rightly flags this).
5. **Idempotency** uses **`event_id`** at the persistence boundary and **domain-level guards** for external effects (`create_ticket`, GitOps, etc.). **LangGraph PostgresSaver / thread_id** (PS3.9) helps **resume** and dedupe **graph execution** but **does not replace** idempotency for side-effecting tools — a redelivered message can still invoke expensive paths unless tool calls are keyed or skipped when already recorded in audit/outbox.
6. **DLQ** is Postgres-first (**`dlq_events`** or equivalent — PS3.3), not a separate product day one.

### Evolution path: **NATS JetStream** (Option B from parent roadmap)

**Clarification:** JetStream is **not** Kafka-class ops: single Go binary, small footprint, common in edge/IoT — closer to SpaceOps “lab + edge” narrative than a JVM cluster. The ADR previously undersold that distinction.

Introduce **NATS JetStream** when at least one trigger is met (team may pull this forward voluntarily):

| Trigger | Rationale |
|---------|-----------|
| Multiple heterogeneous consumers need **independent replay** and **fan-out** beyond comfortable Postgres polling | JetStream streams + durable consumers |
| **Edge / disconnected** deployments where Postgres is not co-located with ingest | Broker nearer ingest |
| Team wants **broker-native** redelivery / NAK / limits without maintaining reclaim logic in SQL | Fewer bespoke queue bugs |
| Sustained throughput **above** comfortable Postgres limits (measure in PS3.5) | Scaling headroom |

**Scope honesty:** JetStream removes **some** bespoke SQL queue logic (acks, retries, subjects); it does **not** eliminate **consumer configuration**, **observability**, **poison-message policy**, or **agent idempotency** — PS3.x remains relevant, shifted from “implement offsets in Python” to “wire JetStream + semantics”.

Until triggers bite, **avoid Kafka/Redpanda** as the default reference stack — ops and JVM footprint remain disproportionate for this repo’s MVP footprint (**not** equivalent warning to NATS).

### Explicitly rejected (for now)

| Alternative | Reason |
|-------------|--------|
| **Kafka / Redpanda as default** | Heavy ops for reference repo; revisit if JetStream proves insufficient. |
| **Redis Streams as SoT** | Durability / backup story weaker than Postgres for single-stack labs; optional cache layer only. |
| **Files-only backlog forever** | NDJSON under `data/` remains useful for fixtures and smoke tests, but **not** the authoritative queue for PS3 durability goals. |

---

## Consequences

### Positive

- One operational database (**Postgres** already required for KB/pgvector, migrations, CI).
- **Exactly-once-ish effects** come from **PK + explicit claim/lease + short transactions**, not from pretending WAL is Kafka.
- Clear **migration narrative**: wire ingest → Postgres → worker loop; files remain reproducible fixtures.

### Negative / risks

- Postgres remains **hot path** for ingest bursts — PS3.5 must validate backpressure (pool sizing, batch inserts, shedding).
- **Rolling your own** reclaim/timeouts in SQL is real engineering — peer review and chaos tests matter; JetStream is a legitimate shortcut **when** triggers justify another moving part.
- **Multi-region** replication is **not** solved by this ADR; defer to PS6/cloud patterns.

### Documentation & implementation hooks

- PS3.2 implements **claim/lease or SKIP LOCKED** semantics (and optional offsets only where semantically safe); PS3.3 DLQ aligns with reclaimed `PROCESSING` staleness.
- PS6.11 (cluster hardening) may introduce JetStream Helm charts **without** contradicting Postgres-first lab defaults.

---

## Compliance

- **Contracts:** `TelemetryEventV1` remains normative; optional `sat_id` should live in **`metadata`** until a schema revision promotes it (separate ADR if columns are added).
- **Replay:** Input replay (PS1.5) remains orthogonal; queue replay (PS3.4) adds **offset/DLQ** replay semantics documented separately.

---

## References

- [roadmap/02-production-scale.md](../../roadmap/02-production-scale.md) — Phase 2 Option A/B.
- [docs/architecture.md](../architecture.md) — data flow overview.
- [data/README.md](../../data/README.md) — current NDJSON ingest layout.
