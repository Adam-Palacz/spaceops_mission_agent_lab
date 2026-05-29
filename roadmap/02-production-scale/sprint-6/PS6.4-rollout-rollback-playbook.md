# PS6.4 — Rollout and rollback playbook

| Field | Value |
|-------|-------|
| **Task ID** | PS6.4 |
| **Status** | Todo |

---

## Description

Document and **demonstrate** safe deploy, rollback, and emergency backend rollback (PS5.5) on the
K8s path. Operators must not guess `helm upgrade` flags under incident pressure.

---

## Requirements

- [ ] Standard deploy flow: pre-checks → deploy → post-checks → smoke.
- [ ] Rollback flow: `helm rollback` / GitOps revert / image pin — pick primary and document fallback.
- [ ] **LLM emergency rollback:** set `LLM_BACKEND=openai` via values + rollout restart; `gpu` scale
      to zero — no application code deploy (PS5.5).
- [ ] **Atomic or canary:** document chosen strategy (e.g. `helm upgrade --atomic` for lab).
- [ ] Post-deploy smoke: `/health`, one `POST /runs` or eval hard gate subset, trace visible in Jaeger.
- [ ] Incident template: what to capture when rollback happens (version, values diff, trace ids).

---

## Dependencies

- **PS6.2** — local cluster for demonstration.
- **PS6.3** — packaged release name and revision history.
- **PS5.5** — backend rollback runbook cross-link.

---

## Checklist

- [ ] `docs/runbooks/k8s_rollout_rollback.md`
- [ ] Scripted demo or Makefile target: `k8s-rollout-demo` (local only).
- [ ] Cross-link `docs/runbooks/llm_backend_rollout.md` § emergency rollback.
- [ ] GitOps path (PS6.7) references same rollback semantics if enabled.

---

## Test / acceptance

- [ ] Local demo: deploy v1 → deploy v2 → rollback → `/health` OK.
- [ ] Local demo: force bad `LLM_BACKEND` value → rollback to openai → agent run succeeds.
- [ ] Runbook readable standalone (no repo code archaeology required).

---

## Deliverables (expected)

- `docs/runbooks/k8s_rollout_rollback.md`
- Optional `scripts/k8s_rollout_demo.sh` / `.ps1`

---

## Out of scope

- Blue/green across two clusters (Phase 7).
