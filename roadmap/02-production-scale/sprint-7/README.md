# Production Scale — Sprint 7 (PS7)

**Goal:** close **PS6 stretch** (live cloud) and **operational debt** from the backlog
(monitoring analysis, READMEs) before L3 multi-agent (NG). Deferred platform work
stays optional unless the sprint is explicitly expanded.

**Strategic source:** [Phase 7 — Cloud Deployment](../../02-production-scale.md#phase-7--cloud-deployment-gcp-first-k8s-portable), [PS6 SPRINT_REVIEW](../sprint-6/SPRINT_REVIEW.md), [backlog TRIAGE](../../backlog/TRIAGE.md).

**Sprint shape:** **ops + cloud proof** — smaller than PS6, larger than a single hotfix. Estimate: **2 weeks**.
Hard scope is PS7.1, PS7.2, PS7.4, and PS7.5. PS7.3 and PS7.6–PS7.8 are PS7b/defer candidates.

---

## Outcomes

- Stage GKE deploy reproducible from docs (scenarios A/B in cloud with traces).
- GCP budget/alerts verified on a real project (minimum: one alert + runbook drill).
- Production monitoring analysis ([BL-001](../../backlog/BL-001-monitoring-improvement-analysis.md) — correct scope).
- READMEs in key folders ([BL-002](../../backlog/BL-002-readme-per-folder.md)).
- Optional/defer: Variant A worker, postgres LLM budget, platform ops triage (BL-005), multi-cloud ADR (BL-004).

---

## Suggested order

1. **PS7.4** + **PS7.5** — documentation / analysis (no GCP credentials).
2. **PS7.1** + **PS7.2** — live GCP (requires project + budget).
3. **PS7.3** — worker split (depends on PS6.4 rollout + PS3.2 queue).
4. **PS7.6–PS7.8** — default to PS7b unless hard scope finishes early.

---

## Definition of done (sprint)

**Hard**

- [x] PS7.1: stage GKE + Helm with `values-gcp-stage.yaml`; demo A/B from runbook passed on `spaceops-project-498213` (2026-06-03).
- [x] PS7.2: budget alert in project + runbook entry (dated drill on `spaceops-project-498213`, 2026-06-14).
- [x] PS7.4: `docs/monitoring-production-analysis.md` with recommendations.
- [x] PS7.5: READMEs for BL-002 folder list (minimum: `data/`, `kb/`, `evals/`, `infra/` subfolders).

**PS7b / optional (explicit defer OK)**

- [x] PS7.3: Variant A graph worker + test kill worker → resume.
- [x] PS7.6: `LLM_BUDGET_MODE=postgres` per ADR 0005 trigger.
- [x] PS7.7: multi-cloud burst ADR (BL-004).
- [ ] PS7.8: platform ops triage CLI (BL-005) read-only MVP.

---

## Upstream / downstream

- **Upstream:** PS6 closed (Helm, Terraform skeleton, portfolio).
- **Downstream:** [NG sprint 1](../../03-next-gen-autonomy/sprint-1/) — multi-agent can start locally; stage/cloud optional.
