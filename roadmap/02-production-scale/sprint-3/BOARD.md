# PS3 — Board

| Task | Title | Status | Spec |
|------|-------|--------|------|
| PS3.1 | Queue strategy decision (DB offsets vs NATS/Redpanda) | Done | [PS3.1-queue-strategy-decision.md](PS3.1-queue-strategy-decision.md) · [ADR 0001](../../../docs/adr/0001-queue-strategy-postgres-first-jetstream-later.md) (superseded) · [**ADR 0002** — current](../../../docs/adr/0002-ingest-nats-first-postgres-evidence-store.md) |
| PS3.2 | Consumer offset store + idempotency keys | Done | [PS3.2-consumer-offset-idempotency.md](PS3.2-consumer-offset-idempotency.md) |
| PS3.3 | Retry workflow + DLQ table/topic | Done | [PS3.3-retry-workflow-dlq.md](PS3.3-retry-workflow-dlq.md) |
| PS3.4 | Replay tooling for queued events | Done | [PS3.4-replay-queued-events.md](PS3.4-replay-queued-events.md) |
| PS3.5 | Burst/backpressure load scenario | Done | [PS3.5-burst-backpressure-scenario.md](PS3.5-burst-backpressure-scenario.md) |
| PS3.6 | Out-of-order/dup/drop simulation | Done | [PS3.6-out-of-order-dup-drop-simulation.md](PS3.6-out-of-order-dup-drop-simulation.md) |
| PS3.7 | Contact-window simulation hooks | Done | [PS3.7-contact-window-simulation-hooks.md](PS3.7-contact-window-simulation-hooks.md) |
| PS3.8 | Ops runbook for queue + DLQ recovery | Done | [PS3.8-runbook-queue-dlq-recovery.md](PS3.8-runbook-queue-dlq-recovery.md) |
| PS3.9 | LangGraph durable checkpoint (Postgres) + resume | Todo | [PS3.9-langgraph-durable-checkpoint.md](PS3.9-langgraph-durable-checkpoint.md) |
| PS3.10 | MCP resilience under lossy links + escalation proofs | Todo | [PS3.10-mcp-resilience-lossy-links.md](PS3.10-mcp-resilience-lossy-links.md) |

**Status key:** Todo | In progress | Done | Blocked

**Suggested order:** PS3.1 → PS3.2 → PS3.3 → PS3.4 → (PS3.5–PS3.8 in parallel after core queue exists) → PS3.9 / PS3.10 with documented ordering deps per specs.

**Carryover visibility:** PS3.9 / PS3.10 are indexed in [phase README — Cross-cutting](../README.md#cross-cutting-durability-safety-and-evals).
