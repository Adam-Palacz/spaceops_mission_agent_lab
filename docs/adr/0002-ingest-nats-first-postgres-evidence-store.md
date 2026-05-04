# ADR 0002 — Ingest NATS JetStream–first; Postgres as state / evidence store

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2026-05-04 |
| **Context** | Production Scale Phase — Sprint PS3 (follow-up to [PS3.1](../../roadmap/02-production-scale/sprint-3/PS3.1-queue-strategy-decision.md)) |
| **Supersedes** | [ADR 0001 — Postgres-first consumers…](0001-queue-strategy-postgres-first-jetstream-later.md) |

---

## Context

ADR 0001 chose a **Postgres-first** logical queue for the lab, with JetStream deferred until scale triggers. After review, SpaceOps targets **distributed-systems best practice** for:

- **Acquisition-of-signal (AOS)–style bursts** — short, intense telemetry dumps that must not block on DB commit latency at the HTTP edge.
- **Decoupled time-scales** — ingest must succeed in milliseconds; **persist** and **reason** may run slower without holding the caller.
- **Clear failure domains** — avoid hand-rolled queue semantics in SQL when JetStream provides **append log, durable consumers, ack/nak, redelivery limits** with a **small operational footprint** (single binary; not Kafka-class ops).

Postgres remains essential for **KB/pgvector**, **incidents**, **runs**, **audit**, and **queryable `telemetry_events`** — but it is **not** the first write boundary for ingest.

---

## Decision

### 1. JetStream at the ingest boundary (NATS-first)

1. External systems call the API ingest endpoint (e.g. `POST /ingest` in `apps/api/main.py`).
2. The API performs **minimal validation** (protocol, size limits, schema sanity) and **publishes** the accepted payload to **NATS JetStream** (example subject family: `ingest.telemetry`, with room for `ingest.events`, etc.).
3. The API responds with **`202 Accepted`** (or equivalent) **immediately after** the message is **acknowledged by JetStream** (publish ack), not after Postgres persistence.
4. **No dual-write at request time:** the handler **does not** “INSERT into Postgres then publish” nor “publish then INSERT” in one synchronous user-facing transaction. Dual-write creates ** inevitable inconsistency** (e.g. DB succeeds, broker times out — operators see rows agents never consumed).

### 2. Postgres role: **state / evidence store**

- **`telemetry_events`** (and related tables) are populated **only by asynchronous consumers** that pull from JetStream — primarily a **Persister** worker.
- Postgres remains the **system of record for queries, compliance-style evidence, replay correlation**, and joins with incidents/runs — **after** messages have entered the durable stream.

### 3. Workers (conceptual split)

| Consumer | Responsibility |
|----------|----------------|
| **Persister worker** | Reads JetStream messages; **idempotent `INSERT`** into Postgres (`telemetry_events`, PK `event_id`); **acks** JetStream after durable DB commit (or nak/retry per policy). |
| **Agent pipeline (LangGraph)** | Separate **durable consumer** on the **same stream** (or explicit duplicate policy via JetStream tooling — subject/stream design is an implementation detail of PS3.x). Runs triage/investigate/OPA/MCP logic **without** holding open ingest HTTP connections or long-lived DB transactions during LLM calls — claim/stream semantics live at JetStream + short DB transactions for outcomes. |

Exact consumer names, stream names, and whether agents consume **copy** vs **same messages** with multiple durable consumers follow JetStream rules (multiple durable consumers may each maintain independent ack positions on compatible configurations — PS3 backlog must nail stream + consumer topology).

### 4. Idempotency and ordering

- **`event_id`** remains the primary **dedupe key** at Postgres ingress (`ON CONFLICT DO NOTHING` / equivalent).
- JetStream **message IDs** or dedupe headers should be used where applicable to reduce duplicate publishes from flaky clients.
- **Ordering:** partition by **`sat_id`** (or subsystem) via **subject suffixing** or **stream keys** where ordering per asset is required (PS3 implementation task).

---

## Rejected alternatives

| Pattern | Why rejected |
|---------|----------------|
| **Dual-write** (Postgres + NATS in one request) | Classic distributed inconsistency; violated if one leg fails after the other succeeds. |
| **Postgres as primary queue** (SKIP LOCKED / offsets as main path) | Valid pattern in some labs; superseded here by **broker-first** best practice for SpaceOps burst/async goals. Files in `data/` remain dev fixtures only — not authoritative vs stream. |

---

## Consequences

### Positive

- Ingest path **absorbs spikes** without coupling to Postgres pool depth at accept time.
- **Single source of truth for “accepted for processing”** is the **durable stream**, not split across DB and broker.
- Aligns with **edge / IoT–class** deployments where NATS is already a natural fit.

### Negative / risks

- **Operational component:** JetStream must run in **compose / k8s** with backup and monitoring (lighter than Kafka, non-zero).
- **Eventual consistency:** callers may get `202` before a row appears in Postgres — document **observability** (trace/message id in response body) for support.
- **Two failure modes to operate:** stream backpressure vs persister lag — dashboards and lag alerts needed (PS3.5 / runbooks).

---

## Migration notes (from current code)

- Today `POST /ingest` persists NDJSON under `data/` and does not insert `telemetry_events`. PS3 tasks should **introduce JetStream publish + 202**, then persister → Postgres, while preserving **contracts v1** validation at the edge where feasible without defeating latency goals.

---

## References

- [ADR 0001](0001-queue-strategy-postgres-first-jetstream-later.md) — superseded rationale (historical).
- [roadmap/02-production-scale.md](../../roadmap/02-production-scale.md) — Phase 2 streaming goals.
- [docs/architecture.md](../architecture.md) — system overview.
