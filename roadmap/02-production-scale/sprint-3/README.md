# Production Scale — Sprint 3 (PS3)

**Goal:** introduce streaming/backpressure realism and resilient processing with offset tracking,
DLQ handling, and replay support over queued events — **plus** durable agent execution and proven
MCP behaviour under unreliable links (so platform stress does not “lose the incident”).

---

## Outcomes

- Queue/offset processing model with idempotent consumer semantics.
- DLQ capture for failed processing and retry/replay path.
- Backpressure behavior tested (ingest remains stable under burst load).
- Space-like disruptions simulated (drop/dup/out-of-order/contact-window effects).
- **Durable LangGraph checkpointing** (Postgres-backed or ADR-equivalent) and **resume semantics** after process restarts (**PS3.9**).
- **MCP transport** proven under lossy-link / breaker-open scenarios with correct **escalation / audit**
  outcomes, building on existing S3.4 retry+circuit code (**PS3.10**).

---

## Tasks

See **[BOARD.md](BOARD.md)** for status.

| Task | Spec |
|------|------|
| PS3.1 | [Queue strategy ADR](PS3.1-queue-strategy-decision.md) → current: [**ADR 0002** — NATS-first ingest](../../../docs/adr/0002-ingest-nats-first-postgres-evidence-store.md); [ADR 0001](../../../docs/adr/0001-queue-strategy-postgres-first-jetstream-later.md) superseded |
| PS3.2 | [Offsets + idempotency](PS3.2-consumer-offset-idempotency.md) |
| PS3.3 | [Retry + DLQ](PS3.3-retry-workflow-dlq.md) |
| PS3.4 | [Replay queued events](PS3.4-replay-queued-events.md) |
| PS3.5 | [Burst / backpressure scenario](PS3.5-burst-backpressure-scenario.md) |
| PS3.6 | [Out-of-order / dup / drop](PS3.6-out-of-order-dup-drop-simulation.md) |
| PS3.7 | [Contact-window hooks](PS3.7-contact-window-simulation-hooks.md) |
| PS3.8 | [Runbook queue + DLQ recovery](PS3.8-runbook-queue-dlq-recovery.md) |
| PS3.9 | [LangGraph durable checkpoint](PS3.9-langgraph-durable-checkpoint.md) |
| PS3.10 | [MCP lossy-link resilience](PS3.10-mcp-resilience-lossy-links.md) |

---

## Definition of done (sprint)

- [x] Backpressure does not crash ingest or corrupt offsets.
- [x] DLQ captures failed events with diagnosable reasons.
- [x] Replay works for queued events and preserves incident traceability.
- [x] At least one disruption scenario is covered by automated tests.
- [x] **PS3.9:** ADR + checkpoint integration path documented; resume or explicit limitation covered by tests.
- [x] **PS3.10:** At least one automated scenario proves breaker/retry + escalation path for MCP failures.

---

## Handoff

- **PS4:** expands OPA/HITL **integration tests** and CI gating on evidence/audit semantics (see sprint-4 README).
- **PS6:** operationalizes checkpointed workers in cluster (see sprint-6 BOARD PS6.11).
