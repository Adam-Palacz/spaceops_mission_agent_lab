# PS6 — Board

| Task | Title | Status | Spec |
|------|-------|--------|------|
| PS6.1 | Environment strategy (`dev` / `stage` / `prod`) | Done | [PS6.1](PS6.1-environment-strategy-dev-stage-prod.md) |
| PS6.2 | Deployment packaging (Helm) | Done | [PS6.2](PS6.2-deployment-packaging-helm.md) |
| PS6.3 | Local K8s baseline (kind / k3d) | Done | [PS6.3](PS6.3-local-k8s-baseline-kind-k3d.md) |
| PS6.4 | Rollout and rollback playbook | Done | [PS6.4](PS6.4-rollout-rollback-playbook.md) |
| PS6.5 | Isolation controls (RBAC, network, quotas) | Todo | [PS6.5](PS6.5-isolation-controls-rbac-network-quotas.md) |
| PS6.6 | Secrets strategy (SOPS / External Secrets) | Todo | [PS6.6](PS6.6-secrets-strategy-sops-eso.md) |
| PS6.7 | Optional GitOps bootstrap (Argo CD / Flux) | Todo | [PS6.7](PS6.7-optional-gitops-bootstrap.md) |
| PS6.8 | GCP baseline deploy plan (portable-first) | Todo | [PS6.8](PS6.8-gcp-baseline-deploy-plan.md) |
| PS6.9 | Billing and shutdown controls | Todo | [PS6.9](PS6.9-billing-shutdown-controls.md) |
| PS6.10 | Portfolio artifacts bundle | Todo | [PS6.10](PS6.10-portfolio-artifacts-bundle.md) |
| PS6.11 | Graph workers + Postgres checkpoint ops | Todo | [PS6.11](PS6.11-graph-workers-postgres-checkpoint-ops.md) |

**Status key:** Todo | In progress | Done | Blocked

**Plan notes**

- **Upstream:** PS5 closed — LLM backends, idle TTL, parity promotion signal; see [PS5 SPRINT_REVIEW](../sprint-5/SPRINT_REVIEW.md).
- **PS6.1 complete:** ADR 0005 sets the env matrix, `process` budget defer, Variant B checkpoint path, and portfolio checklist stub for PS6.2+.
- **PS6.2 default stack:** **Helm** (env values, secret refs, optional NIM profile); close tool choice in first ADR commit.
- **Minimal K8s profile:** api + postgres + **opa** + telemetry-mcp/mock + telemetry-persister; full compose parity via optional Helm profiles.
- **PS6.4 before PS6.11:** rollout runbook is a dependency for checkpoint ops acceptance.
- **PS6.7 optional:** GitOps not required for sprint DoD if defer ADR is explicit.
- **PS6.8 / PS6.9:** sprint **not blocked** without live GCP — Done at minimum = IaC skeleton + validate + cost runbook; live GKE = stretch.
- **PS6.11 decision (ADR 0005):** Variant **B** API-only checkpoint + `POST /runs/resume` is accepted for PS6; Variant **A** worker split is deferred to Phase 7 unless explicitly re-scoped.
- **GPU in cloud:** default off; Phase 7 extends NIM/GPU node pools — not PS6 default path.
- **Postgres LLM budget (`LLM_BUDGET_MODE=postgres`):** deferred by ADR 0005; implement only after shared org-cap trigger.
