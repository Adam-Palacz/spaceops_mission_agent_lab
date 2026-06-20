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

## Variant A — queue-driven worker (PS7.3)

When `AGENT_WORKER_ENABLED=true` on the **api** Deployment:

- `POST /runs` enqueues to Postgres table `agent_run_queue` (202 Accepted).
- **`agentWorker`** Deployment (`python -m apps.workers.agent_graph`) claims jobs with
  `FOR UPDATE SKIP LOCKED` + lease (`agent_run_queue_lease_seconds`).
- Checkpointing is enabled on the **worker** (`agentWorker.checkpoint.enabled`); api may keep
  checkpoint disabled.
- Worker kill mid-run: expired lease → reclaim → `run_pipeline(..., resume=True)` from checkpoint.
- Idempotency: completed checkpoint rows skip re-execution; PS3.2 side-effect guards unchanged.

Helm overlay: `values-checkpoint-variant-a.yaml`. Status API: `GET /runs/queue/{run_id}`.

## Retention

PS3.9 scope stores checkpoints without TTL cleanup automation.
Operational retention/cleanup policy is implemented as an operator stub in PS6.11:
`scripts/checkpoint_retention.py` and [graph_worker_checkpoint_ops.md](../../../docs/runbooks/graph_worker_checkpoint_ops.md).

## Consequences

- Positive:
  - Mid-run restart can resume from latest durable node boundary.
  - Correlates with existing `run_id` observability/replay model.
- Trade-offs:
  - Extra Postgres writes per node.
  - Requires Postgres availability for checkpoint-enabled mode.
  - Completion cleanup strategy is not automated yet (explicitly deferred).

