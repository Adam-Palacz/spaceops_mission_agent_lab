# ADR 0005 — Environment strategy (`dev` / `stage` / `prod`)

- **Status:** Accepted
- **Date:** 2026-05-29
- **Related:** PS6.1, [ADR 0004](0004-llm-backend-rollout.md), [ADR 0003](0003-langgraph-durable-checkpoint-postgres.md), PS5.5, PS5.6, PS5.8

## Context

PS1–PS5 delivered a working lab stack on Docker Compose with LLM backends, safety gates, queue
ingest, and durable checkpoint **code**. PS6 packages the system for **platform operations**
(Kubernetes, secrets, promotion, portfolio).

We need one written model for:

- what each environment is for,
- how configuration and secrets layer,
- which LLM/GPU/budget/checkpoint choices apply where,
- and what must pass before `dev → stage → prod` promotion.

Without this ADR, PS6.2–PS6.11 lack a single decision anchor.

## Decision

### 1. Three environments

| Environment | Purpose | Data sensitivity | Who deploys |
|-------------|---------|------------------|-------------|
| **`dev`** | Engineer laptops, local kind/k3d, feature branches | Synthetic / lab incidents only; no customer PII | Individual developers |
| **`stage`** | Integration, demo rehearsals, GPU canary, checkpoint proof | Sanitized fixtures; may use real API keys in isolated namespace | Platform maintainer / CI (GitOps optional PS6.7) |
| **`prod`** | External portfolio demo or controlled production pilot | Highest — treat as production data class even for pilot | Named approver only; no direct laptop deploy |

**Local Compose** and **local K8s** both map to **`dev`** semantics unless explicitly tagged otherwise.

### 2. Cluster topology (Phase 6 default)

- **Default:** one shared cluster per org slice with **isolated namespaces**:
  - `spaceops-dev`, `spaceops-stage`, `spaceops-prod`
- **RBAC:** namespace-scoped roles; prod namespace write restricted to platform role.
- **Upgrade path (Phase 7):** dedicated GKE clusters per env when cost/compliance requires it.
  Migration stages: (1) split stage to own cluster, (2) split prod, (3) retire shared cluster.

### 3. Configuration layering

No plain-text secrets in Git. Apply settings in this order (later wins):

1. **Base** — Helm chart defaults (`deploy/helm/spaceops/values.yaml`)
2. **Environment overlay** — `values-dev.yaml` | `values-stage.yaml` | `values-prod.yaml`
3. **Optional profile** — e.g. `values-minimal-dev.yaml`, NIM/GPU profile (off by default)
4. **Secret refs** — Kubernetes Secret / External Secrets / SOPS-decrypted refs (PS6.6); never commit values

Local `.env` remains **`dev`-only** convenience; stage/prod use cluster secret backends per
[docs/secrets.md](../secrets.md).

**Canonical env vars:** same names as Compose (`LLM_BACKEND`, `LLM_BUDGET_MODE`, …). Helm values
map 1:1 to container env — no second config schema.

### 4. Environment × platform matrix

| | **dev** | **stage** | **prod** |
|---|---------|-----------|----------|
| **`LLM_BACKEND` default** | `openai` | `openai` | `openai` |
| **`gpu` allowed** | Yes — local engineer smoke only (Compose profile or optional Helm toggle) | **Canary** — named Deployment/replica set after PS5.8 parity pass | **No** until promotion checklist + parity artifact + approver sign-off |
| **`cursor_sh`** | Optional experiments | Policy-approved only | Policy-approved only |
| **Secrets backend** | `.env` + `get_secret()` env fallback | ESO / SOPS + GSM (design PS6.6) | ESO / SOPS + GSM (required path) |
| **`LLM_BUDGET_MODE`** | `process` | `process` | `process` |
| **`AGENT_DURABLE_CHECKPOINT_ENABLED`** | `false` default; `true` for checkpoint tests | `true` when PS6.11 acceptance runs | `true` only after PS6.11 runbook validated |
| **GPU node pool / NIM in cluster** | Off (host Compose NIM for lab) | Off by default (Phase 7) | Off by default (Phase 7) |
| **CI / gates** | Unit + integration; GPU-free default | + manifest lint; optional parity artifact for GPU changes | + manual approver; parity required for any GPU promotion |

Extends [ADR 0004](0004-llm-backend-rollout.md) environment matrix with secrets, budget, and checkpoint columns.

### 5. `LLM_BUDGET_MODE=postgres` — defer

**Decision:** keep **`process`** in all environments for PS6.

`LLM_BUDGET_MODE=postgres` (shared `llm_usage_ledger`) is **deferred** until:

- multi-replica API or worker deployments need a **shared daily org cap** that survives pod restart, **and**
- PS6.2 Helm wiring + migration ship in a follow-up task (PS6.2/PS6.11 or Phase 7).

**Trigger to implement:** first production claim of “hard daily token cap across replicas” or stage
incident where process-mode reset caused spend overrun.

Until then, selecting `postgres` continues to raise an explicit unsupported-mode error (PS5.6).

### 6. PS6.11 checkpoint fork — Variant B for PS6; Variant A in PS7.3

**Decision:** PS6 accepts **Variant B — API-only checkpoint proof**. **PS7.3** adds **Variant A**
as an optional Helm overlay for queue-driven graph execution.

| Variant | Deploy target | Status |
|---------|---------------|--------|
| **A — worker split** | Dedicated `agentWorker` Deployment + Postgres `agent_run_queue` | **PS7.3** — `values-checkpoint-variant-a.yaml`; kill worker → lease reclaim + resume |
| **B — API-only** | Checkpoint in **api** Deployment; kill pod → `POST /runs/resume` | **PS6 default** — `values-stage.yaml`, `values-checkpoint-dev.yaml` |

Rationale (PS6): runtime triggered `run_pipeline()` from API; Variant B proved PS3.9 in-cluster without
queue refactor. Rationale (PS7.3): separate worker + claim/lease queue decouples long runs from API
request thread; checkpoint remains in Postgres per ADR 0003.

See [graph_worker_checkpoint_ops.md](../runbooks/graph_worker_checkpoint_ops.md) and PS7.3 spec.

### 7. Promotion rules (`dev → stage → prod`)

| Transition | Required gates |
|------------|----------------|
| **dev → stage** | Default CI green; `helm template` for stage overlay; secrets via PS6.6 path (no plain text); PS6.5 isolation applied on cluster |
| **stage GPU canary** | [PS5.8 parity](../evals_backend_parity.md) `gpu_promotion: allowed`; [llm_backend_rollout](../runbooks/llm_backend_rollout.md) checklist; canary on **one** Deployment/replica only |
| **stage → prod** | All stage gates + **manual approver**; demo scenarios A/B documented; rollback runbook (PS6.4) verified once on stage |
| **prod GPU** | Written approver + parity artifact attached to change ticket; emergency baseline remains `openai` |

**Fork PR without GPU:** any change that does not touch `LLM_BACKEND`, NIM profile, or GPU values
passes on CI only — no parity artifact required.

### 8. `LLM_PROVIDER` migration (PS5.5 carry-forward)

- **Code:** `LLM_PROVIDER` remains deprecated compat when `LLM_BACKEND` is unset (warning logged).
- **PS6.2+ manifests:** use **`LLM_BACKEND` only** — do not set `LLM_PROVIDER` in Helm values or K8s env.
- **`.env.example`:** documents deprecation; local dev should set `LLM_BACKEND=openai`.
- **Removal gate (Phase 7):** no active env relies on provider-only config; grep clean in deploy/.

## Consequences

- PS6.2–PS6.11 can proceed with explicit env overlays and promotion gates.
- Sprint closes locally without GCP or worker-split refactor.
- Portfolio and threat-model work (PS6.10) inherit a stable env narrative.
- Postgres budget and agent worker split have documented defer triggers — not silent backlog.

## Appendix — Portfolio checklist stub (PS6.10 input)

Draft only; finalize in PS6.10.

| Artifact | Status / gap |
|----------|----------------|
| **ADR index** | 0001–0005 in [docs/adr/README.md](README.md); add secrets ADR after PS6.6 |
| **Threat model** | Outline: prompt injection → PS4.3; tool abuse → OPA/HITL; data poisoning → KB ingest; secrets → PS6.6 + `get_secret()` |
| **Runbook pack** | Index all `docs/runbooks/*`; add `environment_promotion`, `local_k8s_dev`, `graph_worker_checkpoint_ops`, `cloud_cost_hygiene`, `gcp_stage_deploy` in PS6 |
| **Demo README** | Sections: compose quickstart, `make k8s-up`, scenario A (report), scenario B (escalation), trace link placeholder |
| **Dependency hygiene** | Pin in requirements; reference Dependabot / `pip audit` in portfolio README |

## References

- [Environment promotion runbook](../runbooks/environment_promotion.md)
- [LLM backend rollout](../runbooks/llm_backend_rollout.md)
- [LLM cost guardrails](../llm_cost_guardrails.md)
- [Backend parity evals](../evals_backend_parity.md)
- [PS6 sprint README](../../roadmap/02-production-scale/sprint-6/README.md)
