# Production Scale — Sprint 6 (PS6)

**Goal:** package the system for **platform operations** (K8s / GitOps / cloud path) and close
**portfolio-grade** artifacts for external demonstration and production-readiness review.

**Strategic source:** [Phase 6 — Kubernetes + GitOps](../../02-production-scale.md#phase-6--kubernetes--gitops-after-mvp-is-stable) and [Phase 7 — Cloud Deployment (GCP-first)](../../02-production-scale.md#phase-7--cloud-deployment-gcp-first-k8s-portable).

**Sprint shape:** PS6 is a **platform release** (packaging, ops, cloud plan, portfolio) — not a single
vertical slice like PS5. Close it with strict ordering, explicit defer ADRs (PS6.7, PS6.11 fork,
optional GCP), and a **local K8s proof** as the hard gate; cloud live deploy is stretch.

**Sprint review:** [SPRINT_REVIEW.md](SPRINT_REVIEW.md) (2026-05-31).

---

## Configuration model (read first)

| Knob | Scope | Role |
|------|--------|------|
| **Environment** | `dev` \| `stage` \| `prod` | Namespace isolation, promotion path (PS6.1) |
| **`LLM_BACKEND`** | per env values | From PS5.5 matrix — `openai` default; `gpu` canary only where approved |
| **Secrets** | SOPS / ESO / GSM | No plain-text keys in Git (PS6.6) |
| **`AGENT_DURABLE_CHECKPOINT_ENABLED`** | api or worker deploy | PS3.9 resume after rollout/OOM (PS6.11 fork) |
| **`LLM_BUDGET_MODE`** | process (default) \| postgres | Shared ledger — **deferred** (ADR 0005); all PS6 envs use `process` |

### Environment matrix (PS6.1 — [ADR 0005](../../../docs/adr/0005-environment-strategy-dev-stage-prod.md))

| | **dev** | **stage** | **prod** |
|---|---------|-----------|----------|
| Runtime | Compose, local kind/k3d | Shared K8s namespace | Shared or dedicated K8s |
| `LLM_BACKEND` | `openai`; `gpu` local smoke only | `openai`; GPU canary after PS5.8 | `openai`; GPU by approver + parity only |
| Secrets | `.env` | ESO / SOPS (PS6.6) | ESO / SOPS (required) |
| Checkpoint (PS6.11) | off default | Variant **B** (api pod + resume) | after stage proof |
| Promotion | — | CI + manifest lint | + manual approver |

Promotion runbook: [environment_promotion.md](../../../docs/runbooks/environment_promotion.md).

---

## Outcomes

- Environment model (`dev` / `stage` / `prod`) with documented promotion path.
- K8s local proof (`make k8s-up`) with deploy/rollback runbooks and baseline policies.
- Cloud deployment baseline (GCP-first, portable manifests / IaC boundaries).
- Portfolio docs: ADR index, threat model, runbook pack, demo README.
- **Durable checkpoint ops:** in-cluster resume after pod restart per PS6.11 fork (api for B, worker for A).

---

## Suggested implementation order

1. **PS6.1** — environment ADR + LLM/budget matrix + **PS6.11 fork** + portfolio checklist stub (blocks everything else).
2. **PS6.2** — Helm package (portable manifests; **minimal dev profile** first).
3. **PS6.3** — local kind/k3d proof using PS6.2.
4. **PS6.6** + **PS6.5** — secrets refs first, then isolation on local cluster.
5. **PS6.4** — rollout/rollback demos on local cluster.
6. **PS6.11** — checkpoint ops per ADR from PS6.1 (depends on PS6.4 rollout procedures).
7. **PS6.7** — GitOps (optional; defer with ADR if needed).
8. **PS6.8** + **PS6.9** — GCP plan/IaC skeleton + billing runbook (live deploy = stretch).
9. **PS6.10** — portfolio bundle (capstone index).

### Minimal local K8s profile (PS6.2 / PS6.3)

First `make k8s-up` (PS6.3) deploys the **PS6.2** Helm **minimal dev** profile — a safe platform baseline, not full compose parity:

| Tier | Workloads | Notes |
|------|-----------|--------|
| **Required (dev profile)** | `api`, `postgres`, `opa`, `telemetry-mcp` (or slim mock), `telemetry-persister` worker | OPA stays in — fail-closed policy path is part of the baseline |
| **Optional profiles** | `kb-mcp`, full MCP set, `otel-collector`, `jaeger`, `nats`, NIM/GPU | Enable via Helm values; off by default locally |
| **PS6.11 decision** | Agent graph worker split vs API-only checkpoint | Chosen in PS6.1 ADR — not implied by minimal profile |

---

## Tasks

See **[BOARD.md](BOARD.md)** for status.

| Task | Spec |
|------|------|
| PS6.1 | [Environment strategy](PS6.1-environment-strategy-dev-stage-prod.md) |
| PS6.2 | [Deployment packaging](PS6.2-deployment-packaging-helm.md) |
| PS6.3 | [Local K8s baseline](PS6.3-local-k8s-baseline-kind-k3d.md) |
| PS6.4 | [Rollout / rollback playbook](PS6.4-rollout-rollback-playbook.md) |
| PS6.5 | [Isolation controls](PS6.5-isolation-controls-rbac-network-quotas.md) |
| PS6.6 | [Secrets strategy](PS6.6-secrets-strategy-sops-eso.md) |
| PS6.7 | [Optional GitOps](PS6.7-optional-gitops-bootstrap.md) |
| PS6.8 | [GCP baseline deploy](PS6.8-gcp-baseline-deploy-plan.md) |
| PS6.9 | [Billing and shutdown](PS6.9-billing-shutdown-controls.md) |
| PS6.10 | [Portfolio artifacts](PS6.10-portfolio-artifacts-bundle.md) |
| PS6.11 | [Graph workers + checkpoint ops](PS6.11-graph-workers-postgres-checkpoint-ops.md) |

---

## Definition of done (sprint)

**Hard gates (local / docs)**

- [x] Local K8s deploy works with safe rollback and documented procedures (PS6.3 + PS6.4).
- [x] Environment isolation controls defined and verified on local/stage form (PS6.5).
- [x] Secrets enter cluster without plain-text Git commits (PS6.6 minimal path).
- [x] **PS6.11:** checkpoint pattern validated in-cluster per PS6.1 ADR — **Variant B (API-only resume)**; Variant A worker split deferred Phase 7.
- [x] Portfolio artifact checklist complete and review-ready (PS6.10).

**Cloud — minimum (no live GCP required)**

- [x] PS6.8: ADR + `infra/terraform/gcp/` skeleton; `terraform validate` in CI (`gcp-terraform-validate.yml`).
- [x] PS6.9: `docs/runbooks/cloud_cost_hygiene.md` — budgets, scale-down, labels — **design validated**.

**Cloud — stretch (requires GCP credentials + budget)**

- [ ] PS6.8: reproducible deploy to stage GKE using PS6.2 chart + values overlays.
- [ ] PS6.9: live budget alert wired in cloud project.

---

## Upstream / downstream

- **Upstream:** PS1–PS5 (compose baseline, safety gates, queue, checkpoint code PS3.9, LLM PS5).
- **Downstream:** Phase 7 cloud GPU pools, multi-cluster, enterprise secrets rotation.
- **Cross-phase index:** [Phase README — Cross-cutting](../README.md#cross-cutting-durability-safety-and-evals).

---

## Cross-phase

- [Phase README — Cross-cutting](../README.md#cross-cutting-durability-safety-and-evals)
