# PS6.11 - Graph workers + Postgres checkpoint operations

| Field | Value |
|-------|-------|
| **Task ID** | PS6.11 |
| **Status** | Done |

---

## Description

Operationalize **PS3.9 durable LangGraph checkpointing** in Kubernetes: rollout/OOM runbook, HPA notes,
retention posture. Closes the gap between "checkpoint code exists" and "cluster survives pod restart
mid-run".

**Decision anchor (PS6.1 ADR):**

| Variant | Deploy target | Acceptance |
|---------|---------------|------------|
| **A - worker split** | Separate agent graph Deployment/queue consumer | Kill **worker** pod -> resume completes run |
| **B - API-only (PS6 minimum)** | Checkpoint in **api** Deployment (current code path) | Kill **api** pod mid-run -> `POST /runs/resume` completes run; defer worker split ADR to Phase 7 |

**PS6 selected Variant B.**

---

## Requirements

- [x] Implement acceptance path per **PS6.1 fork ADR**; do not assume separate worker exists.
- [x] Env: `AGENT_DURABLE_CHECKPOINT_ENABLED=true` on the selected stage deployment (api for B);
      default **false** in dev unless explicitly enabled.
- [x] Postgres connectivity + migration for checkpoint tables (reuse app DB; document schema growth).
- [x] **Rollout runbook:** rolling update mid-run -> operator uses `POST /runs/resume` or queue
      redelivery per ADR 0003; document decision tree.
- [x] **OOM runbook:** api pod killed -> resume path completes from checkpoint; verify with integration
      test or manual gate.
- [x] **HPA note:** document why graph execution is not embarrassingly parallel; Variant A worker split is
      deferred.
- [x] **Retention/cleanup:** checkpoint row growth policy stub.
- [x] Queue + checkpoint ordering: no double-execution (PS3.2 idempotency cross-link).

---

## Dependencies

- **PS3.9** - `apps/agent/checkpointing.py`, ADR 0003, resume API.
- **PS6.2** - api Deployment manifest and checkpoint env wiring.
- **PS6.4** - rollout procedures.

---

## Checklist

- [x] Api deployment manifest with checkpoint env and probes.
- [x] `docs/runbooks/graph_worker_checkpoint_ops.md`
- [x] Automated/static test plus manual gate: kill api pod -> resume continuity.
- [x] Cross-link `docs/runbooks/replay_workflow.md` (replay vs resume).

---

## Test / acceptance

- [x] Local k8s: start long run -> delete api pod -> run reaches terminal state or explicit resume path.
- [x] Runbook lists exact kubectl commands and API calls.
- [x] Variant B explicit; Variant A defer documented.

---

## Deliverables (expected)

- `deploy/helm/spaceops/values-checkpoint-dev.yaml`
- `docs/runbooks/graph_worker_checkpoint_ops.md`
- `scripts/checkpoint_retention.py`
- `scripts/k8s_checkpoint_demo.py`
- `tests/test_k8s_checkpoint_resume_integration.py`

---

## Out of scope

- Replacing Postgres checkpointer with Redis/Memory (unless new ADR).
- Multi-region checkpoint replication.
- Variant A worker implementation (`apps/workers/agent_graph`) - Phase 7.
