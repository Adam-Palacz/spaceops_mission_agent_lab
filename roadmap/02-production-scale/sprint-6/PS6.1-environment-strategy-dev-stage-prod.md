# PS6.1 — Environment strategy (`dev` / `stage` / `prod`)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.1 |
| **Status** | Todo |

---

## Description

Define the **environment model** for platform operations: separate configs, secrets, promotion flow,
and LLM backend policy per environment. This task is the **decision anchor** for PS6.2–PS6.11 — no
cluster work without a written matrix.

**Carry-forward from PS5:** per-env `LLM_BACKEND` (see PS5.5 ADR), optional `LLM_BUDGET_MODE=postgres`
ledger semantics (deferred from PS5.6), and GPU default **off** outside approved stage canaries.

Parent: [Phase 6 — Kubernetes + GitOps](../../02-production-scale.md#phase-6--kubernetes--gitops-after-mvp-is-stable).

---

## Requirements

- [ ] Document three environments: `dev`, `stage`, `prod` — purpose, data sensitivity, who deploys.
- [ ] **Shared cluster / isolated namespaces** as default (Phase 6); upgrade path to dedicated
      clusters documented (Phase 7 migration stages).
- [ ] Config layering: base → env overlay → secret refs (no secrets in Git plain text).
- [ ] **LLM backend matrix** per env (extends PS5.5):
  - `dev`: `openai` default; optional local `gpu` for engineer machines only.
  - `stage`: `openai` default; optional `gpu` canary on named worker pool after PS5.8 parity pass.
  - `prod`: policy-driven; `gpu` only after promotion checklist + parity evidence.
- [ ] **Budget mode:** `process` default everywhere; `postgres` ledger — implement in PS6.3/PS6.11
      worker deploy or explicit defer ADR with trigger conditions.
- [ ] **PS6.11 checkpoint fork** (required before PS6.11 work):
  - **Variant A — worker split:** dedicated agent graph Deployment/consumer; OOM/rollout proof on worker pod.
  - **Variant B — API-only (PS6 minimum):** checkpoint + `POST /runs/resume` after API pod kill; defer worker split to Phase 7 with ADR trigger.
- [ ] **Portfolio checklist stub** (feeds PS6.10): ADR index gaps, threat model outline, runbook pack list, demo README sections — draft here, finalize in PS6.10.
- [ ] Promotion rules: `dev → stage → prod` (what must pass: CI hard gates, optional parity artifact
      for GPU changes, manual approver for prod).
- [ ] Remove or freeze **`LLM_PROVIDER`-only** configs from env templates (PS5.5 migration timeline).

---

## Dependencies

- **PS5.5** — rollout ADR and runbook baseline.
- **PS5.6** — budget semantics documentation.
- **PS5.8** — parity required before stage/prod GPU promotion.

---

## Checklist

- [ ] ADR: environment topology, namespace layout, promotion gates.
- [ ] Table: env × `LLM_BACKEND` × secrets backend × GPU allowed (yes/no/canary).
- [ ] Cross-link `docs/runbooks/llm_backend_rollout.md` with K8s/GitOps path.
- [ ] `.env.example` / values template comments aligned with env strategy (no second config schema).

---

## Test / acceptance

- [ ] Reviewer can answer “what runs in prod vs stage?” from ADR alone.
- [ ] Reviewer can answer “fork PR without GPU?” and “how to promote GPU to stage?” from docs.
- [ ] No conflicting env var precedence documented elsewhere.

---

## Deliverables (expected)

- `docs/adr/0005-environment-strategy-dev-stage-prod.md` (or next ADR number)
- `docs/runbooks/environment_promotion.md`
- Update `roadmap/02-production-scale/sprint-6/README.md` env summary table

---

## Out of scope

- Terraform/GCP project creation (PS6.8).
- GitOps tool choice implementation (PS6.7).
