# PS7.4 — Production monitoring stack analysis (BL-001)

| Field | Value |
|-------|--------|
| **Task ID** | PS7.4 |
| **Status** | Done |
| **Backlog** | [BL-001](../../backlog/BL-001-monitoring-improvement-analysis.md) |

## Description

**Correct** delivery of BL-001: analyze Postgres, OTel Collector, Jaeger, Prometheus/Grafana (compose + Helm)
for production: security, retention, HA, sampling, TLS, resource limits.

**Do not conflate with PS1.9** (W3C tracing) — separate deliverable.

## Deliverables

- [x] `docs/monitoring-production-analysis.md`
- [x] Optional: follow-up tasks in PS7b (TLS OTLP, managed Jaeger, SLO dashboard)

## Acceptance

- [x] Each component: OK / gap / recommendation.
- [x] Linked from `docs/portfolio/README.md` or `docs/README.md`.

## Summary

| Component | Lab/stage | Main prod gap |
|-----------|-----------|---------------|
| Postgres | OK with secrets + PVC | Managed HA + backup |
| OTel Collector | OK in-cluster | TLS, sampling, HA |
| Jaeger | OK all-in-one | Persistent storage / managed trace backend |
| Prometheus | Compose only | Not in Helm — scrape gap on K8s/GKE |
| Grafana | Compose only; default creds | Not in Helm; auth + SLO dashboards |

Full analysis: [monitoring-production-analysis.md](../../../docs/monitoring-production-analysis.md).
