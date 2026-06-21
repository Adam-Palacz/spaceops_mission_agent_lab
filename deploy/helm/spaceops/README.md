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

# Stage with PR1.1 monitoring stack
helm template spaceops deploy/helm/spaceops \
  -f deploy/helm/spaceops/values.yaml \
  -f deploy/helm/spaceops/values-stage.yaml \
  -f deploy/helm/spaceops/values-monitoring-stage.yaml
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
| `prometheus` | Deployment + Service + scrape ConfigMap | `observability.prometheus.enabled` |
| `grafana` | Deployment + Service + provisioning ConfigMap | `observability.grafana.enabled` |
| `postgres-exporter` | Deployment + Service | `observability.postgresExporter.enabled` |
| `nim-llm` | Deployment + Service | `nim.enabled` (+ nodeSelector/tolerations) |
| `ui` | — | out of chart scope |
| Agent graph worker (future) | Deployment stub | `agentWorker.enabled` (Variant A / Phase 7) |

## Profiles

| Profile file | Purpose |
|--------------|---------|
| `values.yaml` | Base defaults |
| `values-minimal-dev.yaml` | Safe baseline: api, postgres, opa, telemetry-mcp, persister, nats |
| `values-dev.yaml` | Namespace `spaceops-dev`, lab secrets |
| `values-stage.yaml` | Integration, checkpoint on api, optional observability |
| `values-monitoring-stage.yaml` | PR1.1 monitoring overlay: Prometheus, Grafana, postgres exporter, OTel sampling/mesh-ready TLS |
| `values-stage-full.yaml` | All in-cluster MCPs (kb/ticket/gitops) for GKE stage demo |
| `values-gcp-stage.yaml` | Artifact Registry repos + LoadBalancer API |
| `values-prod.yaml` | Stricter persistence, full MCP set optional |

GKE deploy/demo: [gcp_stage_deploy.md](../../../docs/runbooks/gcp_stage_deploy.md) — `make gcp-stage-deploy`, `make gcp-stage-demo`.

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

Enable on **api** Deployment: `api.checkpoint.enabled: true` (stage overlay). Local proof:

```bash
-f values-checkpoint-dev.yaml   # or make k8s-checkpoint-demo
```

Sets `AGENT_DURABLE_CHECKPOINT_ENABLED` via `_api-env.tpl`. Retention stub: `scripts/checkpoint_retention.py`.
Runbook: [graph_worker_checkpoint_ops.md](../../../docs/runbooks/graph_worker_checkpoint_ops.md).

No separate agent worker unless `agentWorker.enabled` (Variant A — `values-checkpoint-variant-a.yaml`, PS7.3).

## Production Readiness monitoring (PR1.1)

`values-monitoring-stage.yaml` adds the K8s monitoring stack that was intentionally absent from
the PS6/PS7 lab baseline:

- Prometheus scrapes `spaceops-api:/metrics`, NATS `/varz`, the OTel collector internal metrics,
  and `postgres-exporter`.
- Grafana is provisioned with a Prometheus datasource and a compact SpaceOps SLO dashboard.
- Prometheus loads PR1.2 alert rules from `spaceops-prometheus-rules`.
- The OTel collector gets health probes, resource limits, memory limiting, probabilistic sampling,
  and `tlsMode: mesh-sidecar` for stage/prod service-mesh TLS termination.

Create the Grafana admin Secret before enabling the overlay:

```bash
kubectl create secret generic spaceops-stage-monitoring-secrets \
  -n spaceops-stage \
  --from-literal=grafana-admin-password='REPLACE_ME'
```

Render or install with:

```bash
helm upgrade --install spaceops deploy/helm/spaceops \
  -n spaceops-stage \
  -f deploy/helm/spaceops/values.yaml \
  -f deploy/helm/spaceops/values-stage.yaml \
  -f deploy/helm/spaceops/values-monitoring-stage.yaml
```

Access during stage drills:

```bash
kubectl port-forward -n spaceops-stage svc/spaceops-prometheus 9090:9090
kubectl port-forward -n spaceops-stage svc/spaceops-grafana 3000:3000
```

Alert rules and SLOs: [slo-production-readiness.md](../../../docs/slo-production-readiness.md).

Variant A agent-worker still has no standalone HTTP metrics endpoint; PR1.1 treats worker scrape as
an accepted gap. Worker progress is visible through API run metrics, queue/DLQ metrics, traces, and
the PR1.4 failure-test pack until a worker metrics sidecar or endpoint is added.
