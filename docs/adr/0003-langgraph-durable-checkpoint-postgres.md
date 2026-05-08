# ADR 0003 — Durable agent checkpointing in Postgres

- **Status:** Accepted
- **Date:** 2026-05-07
- **Deciders:** SpaceOps Mission Agent Lab maintainers
- **Related:** [ADR 0002](0002-ingest-nats-first-postgres-evidence-store.md), PS3.2, PS3.4, PS3.9

## Context

Replay (`run_id`-based) re-executes from inputs, but does not restore in-flight orchestration state
after process loss (OOM kill, rollout restart). For longer investigations, we need explicit
checkpoint/resume semantics to avoid silent loss of progress.

## Decision

We use a Postgres-backed durable checkpoint store for the agent pipeline state, feature-flagged:

- `AGENT_DURABLE_CHECKPOINT_ENABLED=false` by default (MVP-safe).
- Checkpoint key: `run_id` (unique per pipeline execution).
- Thread key: `thread_id = "<prefix>:<incident_id>"` where prefix defaults to `incident`.
- Persisted payload: full agent state snapshot after each node and `next_node`.
- Storage table: `agent_graph_checkpoints` in operational Postgres.
- Resume trigger: run the same `run_id` with `resume=true`; execution continues from saved `next_node`.

## Ordering and idempotency semantics

For queue-driven workloads (PS3.2+):

1. Message accepted from queue for processing.
2. Graph step executes.
3. Checkpoint snapshot is persisted.
4. External side effects (ticket/PR/etc.) remain guarded by existing policy/idempotency controls.
5. Queue ack/commit policy must continue to avoid double side effects.

Checkpointing helps resume control flow, but does not replace domain-level idempotency for tool calls.

## Retention

PS3.9 scope stores checkpoints without TTL cleanup automation.
Operational retention/cleanup policy is deferred to PS6.x hardening tasks.

## Consequences

- Positive:
  - Mid-run restart can resume from latest durable node boundary.
  - Correlates with existing `run_id` observability/replay model.
- Trade-offs:
  - Extra Postgres writes per node.
  - Requires Postgres availability for checkpoint-enabled mode.
  - Completion cleanup strategy is not automated yet (explicitly deferred).

