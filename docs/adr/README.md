# Architecture Decision Records (ADRs)

Short-lived decisions live in roadmap task specs; **cross-cutting choices** that affect multiple sprints live here.

ADR entries are **append-only**: superseded documents keep full text; status updates point forward — same spirit as JetStream logs.

| ADR | Title | Status |
|-----|-------|--------|
| [0001-queue-strategy-postgres-first-jetstream-later.md](0001-queue-strategy-postgres-first-jetstream-later.md) | Queue / Postgres-first lab path (PS3.1 v1) | **Superseded** |
| [0002-ingest-nats-first-postgres-evidence-store.md](0002-ingest-nats-first-postgres-evidence-store.md) | **Ingest NATS-first; Postgres evidence store** | **Accepted** |

**Current ingest / queue strategy:** read **ADR 0002** first.
