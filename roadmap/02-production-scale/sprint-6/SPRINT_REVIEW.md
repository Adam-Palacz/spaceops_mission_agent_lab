# PS6 — Sprint review

**Sprint:** Production Scale — Sprint 6 (PS6.1–PS6.11)  
**Board:** [BOARD.md](BOARD.md) — **11 / 11 Done**  
**Date:** 2026-05-31 (review)

---

## Executive summary

PS6 delivered **platform operations packaging** for SpaceOps: environment strategy and promotion gates
(PS6.1), a portable **Helm** chart with minimal local dev profile (PS6.2), **kind** local proof via
`make k8s-up` (PS6.3), rollout/rollback and isolation runbooks (PS6.4–PS6.5), secrets without plain-text
Git (PS6.6), optional **Argo CD** GitOps (PS6.7), GCP Terraform skeleton + cost hygiene at **design**
level (PS6.8–PS6.9), portfolio-grade reviewer bundle (PS6.10), and **Variant B** checkpoint ops on the
api Deployment (PS6.11).

Sprint goal from [README.md](README.md) is **met** at the agreed **minimum** bar: local K8s proof,
documented ops path, and review-ready portfolio. **Live GKE stage deploy** and **wired cloud budget
alerts** remain **stretch** — explicitly not required to close PS6.

---

## Goals vs outcomes

| README outcome | Status |
|----------------|--------|
| Environment model (`dev` / `stage` / `prod`) + promotion path | Done (PS6.1); [ADR 0005](../../../docs/adr/0005-environment-strategy-dev-stage-prod.md), [environment_promotion.md](../../../docs/runbooks/environment_promotion.md) |
| K8s local proof + deploy/rollback runbooks + baseline policies | Done (PS6.2–PS6.4); `deploy/helm/spaceops/`, `make k8s-up`, [k8s_rollout_rollback.md](../../../docs/runbooks/k8s_rollout_rollback.md) |
| Cloud deployment baseline (GCP-first, portable manifests) | Done **minimum** (PS6.8); `infra/terraform/gcp/`, CI `gcp-terraform-validate.yml` |
| Portfolio docs (ADR index, threat model, runbook pack, demo README) | Done (PS6.10); `docs/portfolio/README.md`, `tests/test_portfolio_ps610.py` |
| Durable checkpoint ops in-cluster (PS6.11 fork) | Done **Variant B** (api + `POST /runs/resume`); [graph_worker_checkpoint_ops.md](../../../docs/runbooks/graph_worker_checkpoint_ops.md) |

---

## Board summary

| Task | Status |
|------|--------|
| PS6.1 Environment strategy | Done |
| PS6.2 Deployment packaging (Helm) | Done |
| PS6.3 Local K8s baseline (kind / k3d) | Done |
| PS6.4 Rollout and rollback playbook | Done |
| PS6.5 Isolation controls (RBAC, network, quotas) | Done |
| PS6.6 Secrets strategy (SOPS / ESO) | Done |
| PS6.7 Optional GitOps bootstrap | Done |
| PS6.8 GCP baseline deploy plan | Done (minimum) |
| PS6.9 Billing and shutdown controls | Done (minimum) |
| PS6.10 Portfolio artifacts bundle | Done |
| PS6.11 Graph workers + Postgres checkpoint ops | Done (Variant B) |

---

## Definition of Done (sprint checklist)

**Hard gates (local / docs)**

1. **Local K8s deploy + safe rollback** — `make k8s-up` / `k8s-down`, `k8s-rollout-demo`, runbooks PS6.3–PS6.4; unit gates `tests/test_k8s_ps63.py`, `tests/test_k8s_rollout_ps64.py`.
2. **Isolation on local/stage form** — NetworkPolicy, quota, RBAC templates + `make k8s-isolation-verify`; `tests/test_helm_ps65.py`.
3. **Secrets without plain-text Git** — Helm secret refs, SOPS/ESO design, `make k8s-secrets-bootstrap`; `tests/test_helm_ps66.py`.
4. **PS6.11 checkpoint** — Variant **B** accepted in ADR 0005; `values-checkpoint-dev.yaml`, integration test `tests/test_k8s_checkpoint_resume_integration.py`, operator runbook.
5. **Portfolio checklist** — `docs/portfolio/README.md`, `docs/threat_model.md`, `docs/adr/README.md`, `portfolio-docs-lint.yml`.

**Cloud — minimum (no live GCP required)**

6. **PS6.8** — ADR 0009 + `infra/terraform/gcp/`; `terraform validate` via `gcp-terraform-validate.yml` and `tests/test_gcp_ps68.py`.
7. **PS6.9** — [cloud_cost_hygiene.md](../../../docs/runbooks/cloud_cost_hygiene.md) + `budget.tf` stub; `tests/test_cloud_cost_ps69.py`.

**Cloud — stretch (not claimed for PS6 close)**

- Live stage GKE deploy from PS6.2 chart — documented in [gcp_stage_deploy.md](../../../docs/runbooks/gcp_stage_deploy.md); not a merge gate.
- Live budget alert in GCP project — Terraform stub present; operator wiring deferred.

---

## What shipped (by theme)

- **PS6.1** — Env matrix, `LLM_BACKEND` per env, `LLM_BUDGET_MODE=process` defer, Variant B checkpoint decision, portfolio stub in ADR appendix.
- **PS6.2** — `deploy/helm/spaceops/` chart, `values-minimal-dev.yaml`, optional profiles (MCP, otel, GPU off by default); `helm-template` / `helm-lint` Makefile targets.
- **PS6.3** — `scripts/k8s_local.py`, `make k8s-up|down|status|smoke`; optional `k8s-local-smoke.yml` (manual/self-hosted).
- **PS6.4** — [k8s_rollout_rollback.md](../../../docs/runbooks/k8s_rollout_rollback.md), `scripts/k8s_rollout_demo.py`, static tests.
- **PS6.5** — Calico-ready NetworkPolicy, ResourceQuota, RBAC; isolation verify script.
- **PS6.6** — [k8s_secrets_bootstrap.md](../../../docs/runbooks/k8s_secrets_bootstrap.md), [ADR 0007](../../../docs/adr/0007-secrets-management-k8s.md); ExternalSecret templates; no keys in chart values for stage/prod path.
- **PS6.7** — Argo CD app-of-apps under `deploy/gitops/`, ADR 0008, `gitops_bootstrap.md`, `gitops-manifest-lint.yml`.
- **PS6.8** — `infra/terraform/gcp/` (GKE + AR skeleton), `values-gcp-stage.yaml`, optional `gcp-artifact-registry-push.yml`.
- **PS6.9** — Infra cost runbook, labels, shutdown checklist; distinct from PS5.6 LLM token budget.
- **PS6.10** — Portfolio README, threat model, ADR index, link-check pytest.
- **PS6.11** — API-only checkpoint env wiring, retention stub `scripts/checkpoint_retention.py`, demo `scripts/k8s_checkpoint_demo.py`.

---

## CI architecture (PS6 additions)

Default PR path unchanged for GPU — platform lint is **cluster-free** on merge.

```text
ci.yml (unchanged core: lint → golden → safety → semantic → test → docker-build)

Parallel / path-filtered PS6 workflows (manifest & docs gates):
  k8s-manifest-lint.yml      — helm template/lint + test_helm_ps62/ps66 + checkpoint integration
  gcp-terraform-validate.yml — terraform validate + test_gcp_ps68 + test_cloud_cost_ps69
  portfolio-docs-lint.yml    — test_portfolio_ps610 + checkpoint integration
  gitops-manifest-lint.yml   — test_gitops_ps67

Off PR path (operator / self-hosted):
  k8s-local-smoke.yml        — full kind smoke (PS6.3)
  gcp-artifact-registry-push.yml — image push (PS6.8 stretch helper)
```

---

## Operational lessons

| Topic | Lesson |
|-------|--------|
| **Minimal dev profile ≠ compose** | First `k8s-up` installs api + postgres + opa + telemetry slice only; enable full MCP/otel via values overlays. |
| **Checkpoint Variant B** | Resume is operator-driven (`POST /runs/resume`) after api pod loss; worker split (Variant A) is Phase 7. |
| **GitOps vs Makefile** | PS6 DoD does not require Argo on every laptop; imperative Helm remains valid for dev. |
| **GCP state** | Terraform skeleton validates in CI; live `apply` needs project credentials and cost review (PS6.9). |
| **Windows operators** | kind/Docker smoke and some integration tests are documented as Linux/macOS-first; use WSL2 or CI for full gate. |

---

## Risks and carryover

| Risk | Mitigation |
|------|------------|
| **Local K8s not on every PR** | Rely on `k8s-manifest-lint.yml` + periodic `make k8s-up` / `k8s-local-smoke.yml` on self-hosted runner. |
| **Stretch GKE never exercised** | Run [gcp_stage_deploy.md](../../../docs/runbooks/gcp_stage_deploy.md) once before any prod cloud promotion. |
| **Variant A worker split** | Deferred; queue + separate graph Deployment needs new ADR and PS3.2 ordering proof. |
| **`LLM_BUDGET_MODE=postgres`** | Deferred ADR 0005; all PS6 values use `process`. |
| **GPU in cloud** | Default off; PS5.8 parity required before stage/prod `LLM_BACKEND=gpu`. |
| **Checkpoint table growth** | Retention stub only; schedule cleanup before long-running stage. |

---

## Recommendation

**Close PS6** for planning and delivery. Platform packaging, local proof, ops runbooks, portfolio bundle,
and checkpoint Variant B are integrated and CI-backed at the **docs/manifest** layer.

**Next (Phase 7 / follow-on):** live stage GKE + budget alert (stretch), Variant A graph worker Deployment,
postgres LLM budget ledger if org-cap requires it, and cloud GPU node pools after PS5.8 parity evidence.

---

## Actions captured in repo

- [README.md](README.md) — Definition of Done checkboxes updated for sprint sign-off (stretch items left open).
- [BOARD.md](BOARD.md) — 11/11 Done.
- [SPRINT_REVIEW.md](SPRINT_REVIEW.md) — this file.
