# PS6.1 — Environment strategy (`dev` / `stage` / `prod`)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.1 |
| **Status** | Done |

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

- [x] Document three environments: `dev`, `stage`, `prod` — purpose, data sensitivity, who deploys.
- [x] **Shared cluster / isolated namespaces** as default (Phase 6); upgrade path to dedicated
      clusters documented (Phase 7 migration stages).
- [x] Config layering: base → env overlay → secret refs (no secrets in Git plain text).
- [x] **LLM backend matrix** per env (extends PS5.5):
  - `dev`: `openai` default; optional local `gpu` for engineer machines only.
  - `stage`: `openai` default; optional `gpu` canary on named worker pool after PS5.8 parity pass.
  - `prod`: policy-driven; `gpu` only after promotion checklist + parity evidence.
- [x] **Budget mode:** `process` default everywhere; `postgres` ledger — **deferred** with trigger in ADR 0005.
- [x] **PS6.11 checkpoint fork:** **Variant B (API-only)** accepted for PS6; Variant A deferred Phase 7.
- [x] **Portfolio checklist stub** (feeds PS6.10): in ADR 0005 appendix.
- [x] Promotion rules: `dev → stage → prod` (what must pass: CI hard gates, optional parity artifact
      for GPU changes, manual approver for prod).
- [x] Freeze **`LLM_PROVIDER`** in K8s templates; deprecated in `.env.example` only.

---

## Dependencies

- **PS5.5** — rollout ADR and runbook baseline.
- **PS5.6** — budget semantics documentation.
- **PS5.8** — parity required before stage/prod GPU promotion.

---

## Checklist

- [x] ADR: environment topology, namespace layout, promotion gates.
- [x] Table: env × `LLM_BACKEND` × secrets backend × GPU allowed (yes/no/canary).
- [x] Cross-link `docs/runbooks/llm_backend_rollout.md` with K8s/GitOps path.
- [x] `.env.example` / values template comments aligned with env strategy (no second config schema).

---

## Test / acceptance

- [x] Reviewer can answer “what runs in prod vs stage?” from ADR alone.
- [x] Reviewer can answer “fork PR without GPU?” and “how to promote GPU to stage?” from docs.
- [x] No conflicting env var precedence documented elsewhere.

---

## Deliverables

- [docs/adr/0005-environment-strategy-dev-stage-prod.md](../../../docs/adr/0005-environment-strategy-dev-stage-prod.md)
- [docs/runbooks/environment_promotion.md](../../../docs/runbooks/environment_promotion.md)
- [roadmap/02-production-scale/sprint-6/README.md](README.md) — environment matrix table

---

## Out of scope

- Terraform/GCP project creation (PS6.8).
- GitOps tool choice implementation (PS6.7).
