# PS6.4 — Rollout and rollback playbook

| Field | Value |
|-------|-------|
| **Task ID** | PS6.4 |
| **Status** | Done |

---

## Description

Document and **demonstrate** safe deploy, rollback, and emergency backend rollback (PS5.5) on the
K8s path. Operators must not guess `helm upgrade` flags under incident pressure.

---

## Requirements

- [x] Standard deploy flow: pre-checks → deploy → post-checks → smoke.
- [x] Rollback flow: `helm rollback` / GitOps revert / image pin — pick primary and document fallback.
- [x] **LLM emergency rollback:** set `LLM_BACKEND=openai` via values + rollout restart; `gpu` scale
      to zero — no application code deploy (PS5.5).
- [x] **Atomic or canary:** document chosen strategy (`helm upgrade --atomic` for lab).
- [x] Post-deploy smoke: `/health`, one `POST /runs` or eval hard gate subset, trace visible in Jaeger.
- [x] Incident template: what to capture when rollback happens (version, values diff, trace ids).

---

## Dependencies

- **PS6.3** — local cluster for demonstration.
- **PS6.2** — packaged release name and revision history.
- **PS5.5** — backend rollback runbook cross-link.

---

## Checklist

- [x] `docs/runbooks/k8s_rollout_rollback.md`
- [x] Scripted demo or Makefile target: `k8s-rollout-demo` (local only).
- [x] Cross-link `docs/runbooks/llm_backend_rollout.md` § emergency rollback.
- [x] GitOps path (PS6.7) references same rollback semantics if enabled.

---

## Test / acceptance

- [x] Local demo: deploy v1 → deploy v2 → rollback → `/health` OK (`make k8s-rollout-demo`).
- [x] Local demo: force bad `LLM_BACKEND` value → rollback to openai → `/health` OK (Part B of demo).
- [x] Runbook readable standalone (no repo code archaeology required).

---

## Deliverables (expected)

- `docs/runbooks/k8s_rollout_rollback.md`
- `scripts/k8s_rollout_demo.py` + `make k8s-rollout-demo`
- `tests/test_k8s_rollout_ps64.py`

---

## Out of scope

- Blue/green across two clusters (Phase 7).
