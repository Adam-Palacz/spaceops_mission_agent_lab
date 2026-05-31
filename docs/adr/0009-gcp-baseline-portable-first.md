# ADR 0009 — GCP baseline deploy (portable-first)

- **Status:** Accepted
- **Date:** 2026-05-31
- **Related:** PS6.8, [ADR 0005](0005-environment-strategy-dev-stage-prod.md), [ADR 0006](0006-kubernetes-packaging-helm.md), [ADR 0007](0007-secrets-management-k8s.md), [ADR 0008](0008-gitops-argocd.md), PS6.9

## Context

PS6 delivers Helm-packaged SpaceOps with local kind (PS6.3), secrets (PS6.6), and optional GitOps
(PS6.7). Phase 7 targets cloud deployment; PS6.8 needs a **minimal GCP-first path** without locking
application code to GKE-only APIs.

We need Terraform skeleton, Artifact Registry design, optional small GKE for **stage**, and
documentation so an engineer can recreate/destroy a lab cluster without a full landing zone.

**Done without live GCP:** ADR + `terraform validate` in CI + runbook. **Stretch:** deploy PS6.2
chart to real GKE with same `values-stage.yaml` overlays.

## Decision

### 1. Portable-first stack

| Layer | Choice | Portability note |
|-------|--------|------------------|
| **App** | Unchanged Python/FastAPI | No GKE-specific SDKs in `apps/` |
| **Package** | Helm chart PS6.2 | Same chart on kind and GKE |
| **Values** | `values-stage.yaml` + optional `values-gcp-stage.yaml` (image registry only) | Env semantics from ADR 0005 |
| **Secrets** | GSM + ESO (PS6.6 design) | Same K8s Secret keys |
| **Deploy** | Helm imperative **or** Argo CD (PS6.7) | GitOps optional |
| **IaC** | Terraform in `infra/terraform/gcp/` | Replaceable by Pulumi/OpenTofu; no app coupling |

### 2. GCP resources (stage baseline)

- **GKE** — regional cluster, single small node pool (`e2-standard-2`, 1–2 nodes), no GPU pool (Phase 7).
- **Artifact Registry** — Docker repo `spaceops` for `api` and `mcp` images.
- **Service accounts** — `spaceops-deploy` (CI/Helm push), Workload Identity binding stub for ESO reader (PS6.6).
- **Labels** — `env=stage`, `app=spaceops`, `managed-by=terraform` (cost allocation; PS6.9).

### 3. Ingress and TLS

- **Lab/stage:** `LoadBalancer` Service on API (Helm default `ClusterIP` → override in runbook) or GKE Ingress.
- **TLS:** deferred for PS6.8 lab; document cert-manager / Google-managed cert as Phase 7 follow-up.

### 4. Cloud Run fallback (Phase 7 showcase)

Documented only — API-only demo without Postgres/NATS in-cluster. Not PS6.8 default; keeps
portfolio narrative for serverless path without changing Helm core.

### 5. State and CI

- Terraform state: **GCS backend** documented in README; local `terraform.tfstate` gitignored for dev.
- CI: `terraform validate` on PR (no GCP credentials required with `-backend=false`).
- Optional `workflow_dispatch` workflow to build/push images to Artifact Registry (requires GCP secrets).

## Consequences

- **Positive:** Clear path from kind → GKE stage with same Helm; portfolio-ready IaC skeleton.
- **Negative:** Not multi-region HA; no live GCP required for sprint DoD minimum.
- **Follow-up:** PS6.9 billing/shutdown; Phase 7 GPU node pools and Cloud Run reference impl.

## References

- `infra/terraform/gcp/README.md`
- `docs/runbooks/gcp_stage_deploy.md`
- `deploy/helm/spaceops/values-gcp-stage.yaml`
