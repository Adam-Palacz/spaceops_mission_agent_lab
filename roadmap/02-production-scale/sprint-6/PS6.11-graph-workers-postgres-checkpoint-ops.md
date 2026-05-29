# PS6.11 — Graph workers + Postgres checkpoint operations

| Field | Value |
|-------|-------|
| **Task ID** | PS6.11 |
| **Status** | Todo |

---

## Description

Operationalize **PS3.9 durable LangGraph checkpointing** in Kubernetes: rollout/OOM runbook, HPA notes,
retention posture. Closes the gap between “checkpoint code exists” and “cluster survives pod restart
mid-run”.

**Decision anchor (PS6.1 ADR — pick one before implementation):**

| Variant | Deploy target | Acceptance |
|---------|---------------|------------|
| **A — worker split** | Separate agent graph Deployment/queue consumer | Kill **worker** pod → resume completes run |
| **B — API-only (PS6 minimum)** | Checkpoint in **api** Deployment (current code path) | Kill **api** pod mid-run → `POST /runs/resume` completes run; defer worker split ADR to Phase 7 |

Today’s compose/API path is **variant B**; variant A is additional scope (queue + consumer).

---

## Requirements

- [ ] Implement acceptance path per **PS6.1 fork ADR** (A or B); do not assume separate worker exists.
- [ ] Env: `AGENT_DURABLE_CHECKPOINT_ENABLED=true` on the selected stage deployment (api for B, worker for A); default **false** in dev
      unless explicitly enabled (PS6.1).
- [ ] Postgres connectivity + migration for checkpoint tables (reuse app DB; document schema growth).
- [ ] **Rollout runbook:** rolling update mid-run → operator uses `POST /runs/resume` or queue
      redelivery per ADR 0003 — document decision tree.
- [ ] **OOM runbook:** selected pod killed (api for B, worker for A) → resume path completes from checkpoint; verify with integration test or manual gate.
- [ ] **HPA (variant A mainly):** scale selected deployment on CPU/custom metric; document why scaling
      graph workers is not embarrassingly parallel (caution note; variant B usually single api replica).
- [ ] **Retention/cleanup:** checkpoint row growth — policy stub (PS3 sprint review carry-forward).
- [ ] Queue + checkpoint ordering: no double-execution (PS3.2 idempotency cross-link).

---

## Dependencies

- **PS3.9** — `apps/agent/checkpointing.py`, ADR 0003, resume API.
- **PS6.2** — selected deployment manifest (api for B, worker for A).
- **PS6.4** — rollout procedures.

---

## Checklist

- [ ] Selected deployment manifest (api for B, worker for A) with checkpoint env and probes.
- [ ] `docs/runbooks/graph_worker_checkpoint_ops.md`
- [ ] Automated or manual test: kill selected pod (api for B, worker for A) → resume continuity (best-effort CI).
- [ ] Cross-link `docs/runbooks/replay_workflow.md` (replay vs resume).

---

## Test / acceptance

- [ ] Local k8s: start long run → delete selected pod → run reaches terminal state or explicit resume path.
- [ ] Runbook lists exact kubectl commands and API calls.
- [ ] If deferred: ADR with explicit trigger (“defer PS6.11 Done”) — **not** silent skip.

---

## Deliverables (expected)

- Selected deploy templates (api for B, worker for A) in PS6.2 package
- `docs/runbooks/graph_worker_checkpoint_ops.md`
- `tests/test_k8s_checkpoint_resume_integration.py` (optional; may be manual gate)

---

## Out of scope

- Replacing Postgres checkpointer with Redis/Memory (unless new ADR).
- Multi-region checkpoint replication.
