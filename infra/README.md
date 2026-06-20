# Infra — local stack and platform wiring

Docker Compose, observability configs, OPA, SQL bootstrap, local K8s, and GCP Terraform skeleton.

| Path | Purpose |
|------|---------|
| **docker-compose.yml** | Dev stack: Postgres, NATS, API, MCP, OPA, OTel, Jaeger, Prometheus, Grafana. |
| **otel-collector.yaml** / **prometheus.yml** | Observability pipeline (see [docs/monitoring-production-analysis.md](../docs/monitoring-production-analysis.md)). |
| **opa/** | Rego policy for restricted actions. |
| **sql/** | Postgres one-off scripts (pgvector, KB table). |
| **grafana/** | Dashboard provisioning for compose Grafana. |
| **k8s/local/** | kind cluster config (`make k8s-up`). |
| **terraform/gcp/** | GKE stage skeleton (`make gcp-stage-up`). |

Start locally: `docker compose -f infra/docker-compose.yml --project-directory . up -d`.
