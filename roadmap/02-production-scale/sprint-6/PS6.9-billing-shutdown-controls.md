# PS6.9 — Billing and shutdown controls

| Field | Value |
|-------|-------|
| **Task ID** | PS6.9 |
| **Status** | Todo |

---

## Description

Cloud **cost guardrails**: budgets, alerts, and shutdown routines so stage/GKE does not run unbounded.
Complements PS5.7 host idle TTL (lab compose) with **platform-level** hygiene.

**Done levels:**

- **Minimum:** `docs/runbooks/cloud_cost_hygiene.md` + optional Terraform/gcloud stubs — **design validated** without live project.
- **Stretch:** budget alert wired in real GCP project (depends on PS6.8 stretch).

---

## Requirements

- [ ] GCP (or chosen cloud) **budget** with email/alert threshold (document setup).
- [ ] **Cluster scale-down** runbook: min node pool, stop non-prod clusters overnight (scheduled).
- [ ] Tie-in to PS5.7: NIM/GPU in cloud deferred to Phase 7; document “no GPU node pool by default”.
- [ ] Label resources by env (`env=dev|stage|prod`) for cost allocation.
- [ ] Monthly review checklist: orphaned disks, unused static IPs, old AR images.
- [ ] Document difference from **LLM token budget** (PS5.6 process mode) — infra $ vs model $.

---

## Dependencies

- **PS6.8** — cloud plan (live project only for stretch acceptance).
- **PS5.7** — conceptual alignment on scale-to-zero.

---

## Checklist

- [ ] `docs/runbooks/cloud_cost_hygiene.md`
- [ ] Terraform or gcloud script stubs for budget alert (optional automation).
- [ ] Cross-link `docs/runbooks/gpu_cost_hygiene.md` (compose/lab) vs cloud doc.

---

## Test / acceptance

- [ ] **Minimum:** reviewer can explain infra cost vs LLM API cost controls from the runbook.
- [ ] **Minimum:** runbook includes budget alert setup, labels, shutdown, and orphan cleanup checklist.
- [ ] **Stretch:** budget alert configured on stage project (screenshot or IaC reference in PR).
- [ ] **Stretch:** runbook shutdown procedure executed once on non-prod (record date in PR).

---

## Deliverables (expected)

- `docs/runbooks/cloud_cost_hygiene.md`
- Optional `scripts/cloud/schedule_scale_down.sh` (documented, not necessarily automated CI)

---

## Out of scope

- FinOps dashboard product integration.
- Hard org-wide spending caps enforced in application code.
