# Graph checkpoint operations (PS6.11)

Operational playbook for **Postgres-backed LangGraph checkpoints** (PS3.9 / ADR 0003) on Kubernetes.
PS6.1 selected **Variant B — API-only**: checkpoint state lives in the **api** Deployment; there is
no separate graph worker in PS6.

**Related:** [k8s_rollout_rollback.md](k8s_rollout_rollback.md) (PS6.4),
[replay_workflow.md](replay_workflow.md) (resume vs replay),
[ADR 0003](../adr/0003-langgraph-durable-checkpoint-postgres.md),
[ADR 0005](../adr/0005-environment-strategy-dev-stage-prod.md).

---

## Architecture (Variant B)

| Component | Role |
|-----------|------|
| **api Deployment** | Runs agent graph inline on `POST /runs`; persists checkpoints when enabled |
| **Postgres** | Table `agent_graph_checkpoints` (same DB as app; auto-created on first write) |
| **`POST /runs/resume`** | Operator trigger to continue from saved `next_node` + `run_id` |
| **agentWorker** | **Disabled** by default (`agentWorker.enabled: false`) — enable via `values-checkpoint-variant-a.yaml` (PS7.3) |

Enable checkpointing:

```yaml
# values-stage.yaml (already true) or local overlay:
api:
  checkpoint:
    enabled: true
```

Helm sets `AGENT_DURABLE_CHECKPOINT_ENABLED` on the api container
(`deploy/helm/spaceops/templates/_api-env.tpl`).

**Dev default:** `false` in `values.yaml` / `values-minimal-dev.yaml`. Local proof overlay:
`values-checkpoint-dev.yaml`.

---

## Postgres schema

Table created by `apps/agent/checkpointing.py` (`ensure_checkpoint_table()`):

| Column | Purpose |
|--------|---------|
| `run_id` | Primary key — one row per pipeline execution |
| `thread_id` | LangGraph thread (`incident:<incident_id>` by default) |
| `incident_id` | Operator correlation |
| `status` | e.g. `in_progress`, `completed`, `failed` |
| `next_node` | Resume entry point |
| `state` | JSONB agent state snapshot |
| `updated_at` / `created_at` | Retention / audit |

**Migration:** no separate migration file — DDL runs on first checkpoint write. Document growth in
monitoring; use retention stub below.

Verify in cluster:

```bash
kubectl exec -n spaceops-dev deploy/spaceops-api -- \
  python -c "from apps.agent.checkpointing import ensure_checkpoint_table; ensure_checkpoint_table(); print('ok')"
```

Inspect rows (port-forward Postgres or exec into postgres pod):

```sql
SELECT run_id, incident_id, status, next_node, updated_at
FROM agent_graph_checkpoints
ORDER BY updated_at DESC
LIMIT 10;
```

---

## Decision tree: rollout mid-run

```
Rolling update / pod delete during active run?
│
├─ AGENT_DURABLE_CHECKPOINT_ENABLED=true AND row exists for run_id?
│   └─ YES → POST /runs/resume with same run_id + incident_id
│             (continue from next_node; do NOT re-POST /runs with new run_id)
│
├─ Checkpoint disabled OR no row?
│   └─ Use replay from stored input (POST /replays/{run_id}/run)
│       OR start fresh POST /runs (new execution)
│
└─ Queue consumer (Variant A — PS7.3)?
    └─ Worker lease reclaim + checkpoint resume; PS3.2 idempotency still required
```

### Rolling Helm upgrade (api pod restart)

Follow [k8s_rollout_rollback.md](k8s_rollout_rollback.md). After upgrade, if a run was interrupted:

```bash
curl -X POST http://localhost:8000/runs/resume \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "<original-run-id>",
    "incident_id": "<incident-id>",
    "payload": {}
  }'
```

With port-forward:

```bash
kubectl port-forward svc/spaceops-api -n spaceops-dev 8000:8000
```

**Caution:** With `replicas: 2` (stage), in-flight run is tied to one pod; after kill, resume goes
through any healthy api pod — state is in Postgres, not pod memory.

---

## OOM / pod kill procedure (acceptance gate)

Manual or scripted gate for local kind (`make k8s-up` + checkpoint overlay).

### 1. Enable checkpoint on dev cluster

```bash
helm upgrade spaceops deploy/helm/spaceops \
  --namespace spaceops-dev \
  -f deploy/helm/spaceops/values.yaml \
  -f deploy/helm/spaceops/values-dev.yaml \
  -f deploy/helm/spaceops/values-minimal-dev.yaml \
  -f deploy/helm/spaceops/values-checkpoint-dev.yaml \
  --set secrets.postgresPassword="${K8S_POSTGRES_PASSWORD:-spaceops}" \
  --wait
```

Or: `make k8s-checkpoint-demo` (dry-run prints commands; `--execute` runs gate).

### 2. Start a run (capture `run_id` from response)

```bash
curl -s -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "ckpt-oom-test",
    "payload": {
      "time_range_start": "2025-02-14T09:00:00Z",
      "time_range_end": "2025-02-14T11:00:00Z",
      "message": "checkpoint oom test"
    }
  }'
```

### 3. Kill api pod mid-run (simulate OOM/eviction)

```bash
kubectl delete pod -n spaceops-dev -l app.kubernetes.io/component=api --wait=false
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/component=api -n spaceops-dev --timeout=120s
```

### 4. Resume

```bash
curl -s -X POST http://localhost:8000/runs/resume \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "<run_id-from-step-2>",
    "incident_id": "ckpt-oom-test",
    "payload": {}
  }'
```

**Pass:** response `status: resumed` or terminal report; checkpoint row reaches `completed` (or
explicit escalation). **Fail:** 404/422 on resume with no checkpoint row — check env flag and Postgres.

---

## Resume vs replay

| Action | Use when | API |
|--------|----------|-----|
| **Resume** | Mid-run interrupt; checkpoint row exists | `POST /runs/resume` |
| **Replay** | Re-run from stored **input** for regression | `POST /replays/{run_id}/run` |

Full detail: [replay_workflow.md](replay_workflow.md#mid-run-restart-resume-vs-replay-ps39).

---

## Queue + idempotency (PS3.2)

Checkpoint restore resumes **graph control flow** only. NATS message ack, ticket creation, and GitOps
PR actions still require PS3.2 idempotency keys / OPA gates. Do not assume resume suppresses duplicate
side effects.

Cross-link: [queue_dlq_recovery.md](queue_dlq_recovery.md).

---

## HPA note (Variant A — deferred)

**Variant B (PS6):** api Deployment is usually **1 replica** on dev, **2** on stage — HPA on api is
**not enabled** by default. Scaling api horizontally does not make a single LangGraph run
embarrassingly parallel; each `run_id` is single-threaded through one request handler.

**Variant A (Phase 7):** separate `agentWorker` Deployment + queue consumer would use HPA on worker
replicas with **caution**:

- Scale on CPU only when queue depth metric unavailable.
- Max replicas bounded — graph steps are not independent map tasks.
- Checkpoint + consumer ack ordering must prevent double execution (ADR 0003).

Helm stub: `agentWorker.enabled: false` in `values.yaml`; template `agent-worker.yaml` for Phase 7.

---

## Retention / cleanup (stub)

Checkpoint rows accumulate (~1 upsert per graph node per run). PS6.11 adds an **operator stub** —
no automated CronJob in chart yet.

```bash
# List candidates older than 30 days (terminal statuses only)
python scripts/checkpoint_retention.py --dry-run --older-than-days 30

# Apply delete (requires DATABASE_URL / Postgres reachable)
python scripts/checkpoint_retention.py --apply --older-than-days 30
```

**Policy (recommended):**

| Status | Retention |
|--------|-----------|
| `completed`, `failed` | Delete after 30–90 days (env-specific) |
| `in_progress` | Investigate manually — may be stale after crash |

Optional Helm value `api.checkpoint.retentionDays` documents intent; enforcement is the script above
or a future CronJob (Phase 7).

Monitor cardinality:

```sql
SELECT status, count(*) FROM agent_graph_checkpoints GROUP BY status;
```

---

## Probes and resources

Api Deployment includes `/health` **readiness** and **liveness** probes (`api.yaml`). Long runs may
hold the request open — probes still hit `/health` on a separate port/thread; if runs exceed timeout,
tune `AGENT_RUN_TIMEOUT_SECONDS` rather than disabling probes.

For checkpoint-enabled stage, ensure Postgres persistence (`values-stage.yaml` 10Gi PVC) survives pod
restarts.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Resume 404 / no checkpoint | `AGENT_DURABLE_CHECKPOINT_ENABLED` on pod env; Postgres connectivity |
| Duplicate side effects after resume | Idempotency on tools — not a checkpoint bug |
| Table missing | First run with checkpoint enabled; or run `ensure_checkpoint_table()` |
| Rollout killed all progress | Was checkpoint enabled **before** run started? |
| `agent-worker` pod CrashLoop | Check `AGENT_DURABLE_CHECKPOINT_ENABLED` on worker; Postgres URL; disable worker if using Variant B only |

---

## Cross-links

- [local_k8s_dev.md](local_k8s_dev.md) — `make k8s-up`
- [environment_promotion.md](environment_promotion.md) — enable checkpoint in stage acceptance
- [portfolio README](../portfolio/README.md) — Scenario A/B demos

---

## Variant A — queue-driven worker (PS7.3)

| Component | Role |
|-----------|------|
| **api Deployment** | `POST /runs` → 202 + `agent_run_queue` row when `AGENT_WORKER_ENABLED=true` |
| **agentWorker Deployment** | `python -m apps.workers.agent_graph` — claims jobs, runs graph with checkpoints |
| **Postgres `agent_run_queue`** | Claim/lease queue (ADR 0001 pattern) |
| **`GET /runs/queue/{run_id}`** | Poll queue + checkpoint status |

Enable locally:

```bash
helm upgrade spaceops deploy/helm/spaceops -n spaceops-dev \
  -f deploy/helm/spaceops/values.yaml \
  -f deploy/helm/spaceops/values-dev.yaml \
  -f deploy/helm/spaceops/values-minimal-dev.yaml \
  -f deploy/helm/spaceops/values-checkpoint-variant-a.yaml \
  --set secrets.postgresPassword="${K8S_POSTGRES_PASSWORD:-spaceops}" \
  --wait
```

### Kill worker mid-run (acceptance)

1. `POST /runs` → capture `run_id` (202).
2. `kubectl delete pod -n spaceops-dev -l app.kubernetes.io/component=agent-worker --wait=false`
3. Wait for new worker pod Ready; lease reclaims stale job.
4. `GET /runs/queue/{run_id}` → `queue_status: done`, `checkpoint_status: completed`
   (or `POST /runs/resume` to enqueue explicit resume).

Or: `make k8s-checkpoint-demo K8S_CHECKPOINT_DEMO_ARGS="--variant-a --dry-run"`

**Idempotency:** worker skips runs whose checkpoint is already `completed`; tool side effects still
require PS3.2 guards.

---

## Variant A deferral (superseded by PS7.3)

Separate queue-driven graph worker is **optional** — default remains Variant B (`agentWorker.enabled: false`).
Use `values-checkpoint-variant-a.yaml` when validating PS7.3.
