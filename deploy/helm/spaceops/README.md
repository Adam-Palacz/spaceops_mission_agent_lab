# SpaceOps Helm chart (PS6.2)

Kubernetes packaging for SpaceOps. **Helm-only** per [ADR 0006](../../../docs/adr/0006-kubernetes-packaging-helm.md).

## Quick render (no cluster)

```bash
# Minimal local dev baseline (PS6.3 target profile)
helm template spaceops deploy/helm/spaceops \
  -f deploy/helm/spaceops/values.yaml \
  -f deploy/helm/spaceops/values-dev.yaml \
  -f deploy/helm/spaceops/values-minimal-dev.yaml \
  --set secrets.postgresPassword=dev-only

# Stage / prod overlays
helm template spaceops deploy/helm/spaceops -f deploy/helm/spaceops/values.yaml -f deploy/helm/spaceops/values-stage.yaml
helm template spaceops deploy/helm/spaceops -f deploy/helm/spaceops/values.yaml -f deploy/helm/spaceops/values-prod.yaml
```

Makefile: `make helm-template`

Local cluster: `make k8s-up` (PS6.3) — see [docs/runbooks/local_k8s_dev.md](../../../docs/runbooks/local_k8s_dev.md).

Deploy / rollback on K8s: [docs/runbooks/k8s_rollout_rollback.md](../../../docs/runbooks/k8s_rollout_rollback.md) — local demo: `make k8s-rollout-demo`.

Environment isolation (PS6.5): [docs/runbooks/k8s_environment_isolation.md](../../../docs/runbooks/k8s_environment_isolation.md) — verify: `make k8s-isolation-verify`.

Secrets (PS6.6): [docs/runbooks/k8s_secrets_bootstrap.md](../../../docs/runbooks/k8s_secrets_bootstrap.md) — bootstrap: `make k8s-secrets-bootstrap`.

GitOps (PS6.7, optional): [docs/runbooks/gitops_bootstrap.md](../../../docs/runbooks/gitops_bootstrap.md) — `make gitops-install`, `make gitops-bootstrap`.

## Compose → Kubernetes mapping

| Docker Compose service | K8s workload | Values toggle |
|------------------------|--------------|---------------|
| `api` | Deployment + Service `*-api` | `api.enabled` |
| `postgres` | StatefulSet + Service `*-postgres` | `postgres.enabled` |
| `opa` | Deployment + Service + ConfigMap | `opa.enabled` |
| `telemetry-mcp` | Deployment + Service | `telemetryMcp.enabled` |
| `telemetry-persister` | Deployment | `telemetryPersister.enabled` |
| `nats` | Deployment + Service | `nats.enabled` (on in minimal-dev for persister) |
| `kb-mcp` | Deployment + Service | `kbMcp.enabled` |
| `ticket-mcp` | Deployment + Service | `ticketMcp.enabled` |
| `gitops-mcp` | Deployment + Service | `gitopsMcp.enabled` |
| `otel-collector` | Deployment + ConfigMap | `observability.otelCollector.enabled` |
| `jaeger` | Deployment + Service | `observability.jaeger.enabled` |
| `nim-llm` | Deployment + Service | `nim.enabled` (+ nodeSelector/tolerations) |
| `prometheus` / `grafana` / `ui` | — | out of PS6.2 scope |
| Agent graph worker (future) | Deployment stub | `agentWorker.enabled` (Variant A / Phase 7) |

## Profiles

| Profile file | Purpose |
|--------------|---------|
| `values.yaml` | Base defaults |
| `values-minimal-dev.yaml` | Safe baseline: api, postgres, opa, telemetry-mcp, persister, nats |
| `values-dev.yaml` | Namespace `spaceops-dev`, lab secrets |
| `values-stage.yaml` | Integration, checkpoint on api, optional observability |
| `values-prod.yaml` | Stricter persistence, full MCP set optional |

## Images

Align tags with Compose builds (`make docker-build`):

- `spaceops-api:local` ← `apps/api/Dockerfile`
- `spaceops-mcp:local` ← `apps/mcp/Dockerfile`

Set in values: `images.api.repository`, `images.api.tag`, etc.

## LLM / secrets (ADR 0005)

- Set `api.llm.backend` per env (`openai` default; `gpu` requires `nim.enabled`).
- **No plain-text secrets in Git** — dev uses `secrets.create` + `--set` at install; stage/prod use `existingSecret` + ESO/SOPS ([PS6.6](../../../docs/runbooks/k8s_secrets_bootstrap.md)).
- **`LLM_BACKEND` only** — do not set deprecated `LLM_PROVIDER` in manifests.

## PS5.7 GPU activity file

API mounts `/app/var` via `emptyDir` by default (`api.persistence.var.emptyDir`). For durable activity across restarts with GPU profile, set `api.persistence.var.existingClaim`.

## NIM (optional)

`nim.enabled: false` by default. When enabled, configure `nim.nodeSelector` and `nim.tolerations` for GPU nodes (Phase 7). Health path: `/v1/health/ready` (PS5.4).

## Checkpoint (PS6.11 Variant B)

Enable on **api** Deployment: `api.checkpoint.enabled: true` (stage overlay). No separate agent worker unless `agentWorker.enabled` (Variant A defer).
