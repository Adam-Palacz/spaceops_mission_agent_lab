# PS7.3 — Graph worker Variant A

| **Task ID** | PS7.3 | **Status** | Done |

## Description

Separate `agentWorker` Deployment + Postgres run queue; kill worker mid-run → resume without
breaking idempotency (PS3.2). Amends ADR 0003 / ADR 0005 checkpoint fork.

## Requirements

- [x] `apps/workers/agent_graph.py` — queue consumer running `run_pipeline` with checkpoints.
- [x] `apps/agent/run_queue.py` — Postgres claim/lease queue (`FOR UPDATE SKIP LOCKED`).
- [x] API enqueue mode when `AGENT_WORKER_ENABLED=true` (`POST /runs` → 202).
- [x] Helm `values-checkpoint-variant-a.yaml` + `agentWorker.enabled` template wired.
- [x] Tests: enqueue API, worker resume logic, optional DB roundtrip, helm render.

## Acceptance

- [x] Kill worker mid-run → lease expires → reclaim resumes from checkpoint (documented + unit-tested).
- [x] Completed checkpoint skips double execution (idempotency guard in worker).
- [x] Runbook + ADR 0003/0005 updated; Variant B remains default for stage/dev.

## Operator quick path (local kind)

```bash
make k8s-up
helm upgrade spaceops deploy/helm/spaceops -n spaceops-dev \
  -f deploy/helm/spaceops/values.yaml \
  -f deploy/helm/spaceops/values-dev.yaml \
  -f deploy/helm/spaceops/values-minimal-dev.yaml \
  -f deploy/helm/spaceops/values-checkpoint-variant-a.yaml \
  --set secrets.postgresPassword=spaceops --wait

# POST /runs → 202; worker completes; kill worker pod → reclaim + resume
make k8s-checkpoint-demo K8S_CHECKPOINT_DEMO_ARGS="--variant-a --dry-run"
```

Runbook: [graph_worker_checkpoint_ops.md](../../../docs/runbooks/graph_worker_checkpoint_ops.md) § Variant A.

## Implementation notes

| Artifact | Purpose |
|----------|---------|
| `apps/agent/run_queue.py` | `agent_run_queue` table + enqueue/claim/complete |
| `apps/workers/agent_graph.py` | Worker loop |
| `apps/api/main.py` | Enqueue mode + `GET /runs/queue/{run_id}` |
| `values-checkpoint-variant-a.yaml` | Enable worker + `AGENT_WORKER_ENABLED` on api |
| `tests/test_agent_worker_ps73.py` | PS7.3 tests |
