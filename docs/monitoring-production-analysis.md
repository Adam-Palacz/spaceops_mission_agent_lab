# Production monitoring stack analysis (PS7.4 / BL-001)

Analysis of the **observability and data plane** used by SpaceOps in local Compose and Helm/K8s
deployments. This document answers whether the current stack is suitable for **production** and
what to change before a pilot or external demo at scale.

**Not in scope:** W3C trace propagation and span wiring — that is **PS1.9** /
[distributed_tracing_ps19.md](runbooks/distributed_tracing_ps19.md). This doc covers **operational
readiness** of Postgres, OTel Collector, Jaeger, Prometheus, and Grafana.

**Sources reviewed:** `infra/docker-compose.yml`, `infra/otel-collector.yaml`, `infra/prometheus.yml`,
`deploy/helm/spaceops/` (observability templates + env overlays), [behavior_metrics.md](behavior_metrics.md),
[S2.9 metrics](../roadmap/01-foundation-mvp/01-core/sprint-2/S2.9-metrics-dashboard.md).

---

## Executive summary

| Layer | Compose (dev/lab) | Helm stage | Production-ready? |
|-------|-------------------|------------|-------------------|
| **Postgres** | Single container + volume | StatefulSet + PVC | **Lab OK** · prod needs managed DB + backup |
| **OTel Collector** | Single, OTLP plaintext | Single Deployment, ClusterIP | **Lab OK** · prod needs TLS + HA + sampling |
| **Jaeger** | all-in-one, in-memory traces | all-in-one in-cluster | **Lab OK** · prod needs persistent/managed backend |
| **Prometheus** | Compose-only scrape | PR1.1 overlay (`values-monitoring-stage.yaml`) | **PR gated** for production pilot |
| **Grafana** | Compose-only, default creds | PR1.1 overlay (`values-monitoring-stage.yaml`) | **PR gated** for production pilot |

**Verdict:** The stack is **appropriate for dev, portfolio demos, and stage proof** (traces + metrics
on Compose; traces on GKE stage via port-forward). It is **not production-complete** without managed
Postgres, secured OTLP, trace/metrics retention policy, PR1.1 monitoring overlay (or cloud
equivalents), and PR1.2 SLO dashboards.

---

## Component assessment

Legend: **OK** = acceptable for stated environment · **Gap** = missing for production ·
**Recommendation** = concrete next step.

### Postgres (evidence store + checkpoints)

| Aspect | Compose | Helm (stage) | OK / Gap | Recommendation |
|--------|---------|--------------|----------|----------------|
| **Image** | `pgvector/pgvector:pg15` | Same pattern in chart | OK lab | Pin digest in prod; track CVEs |
| **Credentials** | `.env` required; port 5432 exposed | K8s Secret / ESO | OK stage | Never commit secrets; rotate in prod |
| **Persistence** | Named volume `postgres_data` | PVC 10Gi (`values-stage.yaml`) | OK single-node | Managed Cloud SQL / RDS + PITR for prod |
| **HA** | Single instance | Single replica StatefulSet | Gap prod | Managed HA or Patroni; not in lab scope |
| **Backup / PITR** | None automated | None in chart | Gap prod | Cloud backup or `pg_dump` CronJob + restore drill |
| **Resource limits** | None in compose | Configurable via `postgres.resources` | Gap default | Set requests/limits on stage/prod overlays |
| **Monitoring** | App uses DB; no postgres_exporter | Same | Gap | Add exporter or managed-DB metrics in prod |

**Production readiness owner:** [PR2.1](../roadmap/02.5-production-readiness/sprint-2/PR2.1-postgres-ha-backup-restore.md)
for HA posture, backup, restore drill, encryption, RTO/RPO, and data integrity checks.

---

### OpenTelemetry Collector

| Aspect | Compose | Helm | OK / Gap | Recommendation |
|--------|---------|------|----------|----------------|
| **Config** | `infra/otel-collector.yaml` | ConfigMap mirror in `observability.yaml` | OK | Keep single source; consider Helm subchart later |
| **Receivers** | OTLP gRPC/HTTP on 4317/4318 | ClusterIP only | OK in-cluster | Do not expose 4317 on public LB |
| **TLS** | `tls.insecure: true` → Jaeger | Same | Gap prod | PR1.1: OTLP mTLS or sidecar TLS termination |
| **Processors** | `batch` only | `batch` only | Gap prod | Add `memory_limiter`, `probabilistic_sampler` |
| **Sampling** | Head sampling not configured (100%) | Same | Gap prod | Tail or probabilistic sampling (e.g. 10% + error boost) |
| **HA** | Single container | `replicas: 1` | Gap prod | Multiple collectors + k8s service or agent sidecar pattern |
| **Health / limits** | No healthcheck in compose | No probes in template | Gap | Add `/` health extension or k8s probes + CPU/mem limits |
| **Metrics pipeline** | Traces only | Traces only | Gap | Optional metrics exporter → Prometheus (OTLP metrics) |

**Production readiness owner:** [PR1.1](../roadmap/02.5-production-readiness/sprint-1/PR1.1-k8s-monitoring-stack.md)
for secured OTLP ingress, sampling policy, collector resource limits, and export-failure alerts.

---

### Jaeger (trace storage + UI)

| Aspect | Compose | Helm | OK / Gap | Recommendation |
|--------|---------|------|----------|----------------|
| **Deployment model** | `jaegertracing/all-in-one:1.55` | Same image in Deployment | OK lab/stage | Not for high-volume prod |
| **Storage** | In-memory (default all-in-one) | In-memory | Gap prod | Badger/local PVC, Elasticsearch, or **managed** (Cloud Trace, Grafana Tempo, Jaeger operator) |
| **Retention** | Lost on restart | Lost on pod restart | Gap | Configure storage backend + retention (e.g. 7–30d) |
| **UI access** | `localhost:16686` exposed | ClusterIP; port-forward on GKE | OK stage | Ingress with auth or VPN only in prod |
| **HA** | Single | Single replica | Gap prod | Distributed Jaeger or managed alternative |
| **Correlation** | `trace_id` in API/report/UI (PS2.5) | Same | OK | Keep deep links; add service.name filters in runbooks |

**Production readiness owner:** [PR2.4](../roadmap/02.5-production-readiness/sprint-2/PR2.4-retention-privacy.md)
for persistent or managed trace backend decision, minimum implementation path, and defined retention.

---

### Prometheus (metrics)

| Aspect | Compose | Helm | OK / Gap | Recommendation |
|--------|---------|------|----------|----------------|
| **Presence** | `prom/prometheus:v3.10.0` service | PR1.1 overlay | OK compose | Enable `values-monitoring-stage.yaml` for stage/prod pilot |
| **Scrape config** | `host.docker.internal:8000/metrics` | Static in-cluster scrape config | OK PR1.1 | Move to ServiceMonitor if adopting Prometheus Operator |
| **Metrics exposed** | S2.9 + PS4.6 behavior metrics on `/metrics` | API, NATS, OTel, postgres exporter | OK PR1.1 | Worker endpoint remains accepted gap |
| **Retention** | Default 15d (Prometheus default) | Explicit overlay value | OK PR1.1 | Review retention in PR2.4 |
| **HA** | Single | N/A | Gap prod | Thanos / Mimir / managed Prometheus |
| **Alerting** | None in compose baseline | PR1.2 Prometheus rules | OK pilot baseline | Alertmanager or managed alert routing remains prod follow-up |

**Production readiness owner:** [PR1.1](../roadmap/02.5-production-readiness/sprint-1/PR1.1-k8s-monitoring-stack.md)
for Prometheus or managed metrics deployment and [PR1.2](../roadmap/02.5-production-readiness/sprint-1/PR1.2-slo-alerts.md)
for SLO dashboards and alert rules.

---

### Grafana (dashboards)

| Aspect | Compose | Helm | OK / Gap | Recommendation |
|--------|---------|------|----------|----------------|
| **Presence** | `grafana/grafana:12.4.0` | PR1.1 overlay | OK PR1.1 | SLO board added in PR1.2 |
| **Auth** | `admin/admin` default | Admin password from Secret, anonymous disabled | OK PR1.1 | SSO remains prod follow-up |
| **Dashboards** | Provisioned JSON (`infra/grafana/provisioning/`) | PR1.2 production-readiness SLO dashboard | OK pilot baseline | Error-budget burn, recent incidents, and backend fallback panels remain follow-up work |
| **Datasource** | Prometheus at `http://prometheus:9090` | In-cluster Prometheus Service | OK PR1.1 | Managed metrics alternative allowed |

**Production readiness owner:** [PR1.2](../roadmap/02.5-production-readiness/sprint-1/PR1.2-slo-alerts.md)
for production-pilot SLO panels and Prometheus alert-rule visibility. Authenticated Grafana is
covered by the PR1.1 overlay secret defaults; Alertmanager, recent-incident panels, backend fallback
panels, and error-budget burn calculations remain follow-up work.

---

## Cross-cutting themes

### Security

| Item | Status | Recommendation |
|------|--------|----------------|
| Default Grafana password | Gap (compose) | Change before any shared demo host |
| OTLP plaintext | Gap | TLS for collector ingress in prod (PS7b) |
| Jaeger UI unauthenticated | Gap if exposed | NetworkPolicy + ingress auth |
| Postgres port on host (compose) | Gap | Bind to localhost or remove host port in shared env |

### Retention

| Data | Current | Recommendation |
|------|---------|----------------|
| Traces (Jaeger) | Ephemeral | 7–30d in persistent backend |
| Metrics (Prometheus) | Default ~15d | Explicit retention + cardinality review |
| Postgres (runs, telemetry, checkpoints) | Until manual delete | Backup + checkpoint retention script (PS6.11) |
| Audit log (NDJSON) | File-based | Ship to immutable store in prod |

### Resilience

| Item | Compose | Helm | Recommendation |
|------|---------|------|----------------|
| Healthchecks | Postgres yes; otel/jaeger partial | Postgres yes; jaeger readiness | Add otel-collector probes |
| Restart policy | Docker default | K8s Deployment default | OK |
| Single points of failure | All components single-node | Same | Accept for lab; document for prod |

### Alignment with project goals

| Goal | Coverage |
|------|----------|
| NF2 audit/trace | OTel + Jaeger + audit NDJSON — OK for lab |
| MoP latency (goals §4.4) | Prometheus histograms + Grafana — OK compose only |
| PS4.6 behavior metrics | Documented PromQL — needs scrape on K8s |
| PS6.10 portfolio | Jaeger/Grafana URLs in portfolio README — OK compose path |

---

## Environment matrix

| Capability | Compose dev | Helm minimal-dev | Helm stage / GKE (baseline) | GKE + PR1.1 overlay |
|------------|-------------|------------------|-----------------------------|---------------------|
| Traces → Jaeger | Yes (4317 exposed) | Optional (off default) | Yes (`observability.*.enabled: true`) | Same |
| Jaeger UI | `:16686` | port-forward | port-forward / optional ingress | Same |
| Prometheus | Yes | No | No (opt-in overlay) | Yes — `values-monitoring-stage.yaml` + PR1.2 SLO rules |
| Grafana | Yes | No | No (opt-in overlay) | Yes — admin from Secret, anonymous off, PR1.2 SLO dashboard |
| Behavior metrics scrape | Yes (host scrape) | Manual if api port-forward | Wired when overlay enabled (API `/metrics`, NATS, postgres exporter, OTel) | Same |
| postgres_exporter | No | No | No (opt-in overlay) | Yes — PR1.1 |
| Worker standalone `/metrics` | N/A | N/A | Accepted gap (Variant A worker) | Accepted gap — see PR1.1 notes |

Baseline stage deploy keeps Jaeger/OTel only. Enable Prometheus/Grafana/postgres-exporter with
`-f deploy/helm/spaceops/values-monitoring-stage.yaml` — see [gcp_stage_deploy.md](runbooks/gcp_stage_deploy.md)
§7 (bring-up, scrape smoke, mesh-sidecar note).

---

## Production checklist (before prod pilot)

Use this as a gate; not all items are required for **stage** or **portfolio** demos.

- [ ] Postgres on managed service with backup restore tested
- [ ] Secrets via ESO/GSM only (no `.env` on servers)
- [ ] OTLP encrypted (TLS or mesh)
- [ ] Trace sampling policy documented and enabled
- [ ] Jaeger (or equivalent) with persistent storage and retention
- [ ] Prometheus scraping all api replicas; Alertmanager or cloud alerts
- [ ] Grafana (or cloud dashboards) with auth; SLO panels for escalation rate and p95 latency
- [ ] Resource requests/limits on otel-collector, jaeger, postgres
- [ ] Runbook: [distributed_tracing_ps19.md](runbooks/distributed_tracing_ps19.md) + incident response for observability outage

---

## Production Readiness follow-up mapping

PS7.4 originally identified PS7b-M* monitoring follow-ups. They are now owned by the dedicated
[Production Readiness](../roadmap/02.5-production-readiness/) phase so they do not remain optional
or compete with Next-Gen Autonomy work.

| Former ID | Production Readiness owner | Rationale |
|-----------|----------------------------|-----------|
| PS7b-M1 | [PR1.1](../roadmap/02.5-production-readiness/sprint-1/PR1.1-k8s-monitoring-stack.md) | Helm/GitOps or managed Prometheus + Grafana closes the K8s metrics gap. |
| PS7b-M2 | [PR1.1](../roadmap/02.5-production-readiness/sprint-1/PR1.1-k8s-monitoring-stack.md) | OTLP TLS, collector limits, and sampling are part of the K8s monitoring baseline. |
| PS7b-M3 | [PR2.4](../roadmap/02.5-production-readiness/sprint-2/PR2.4-retention-privacy.md) | Persistent/managed traces, retention, and privacy belong with trace/log retention policy. |
| PS7b-M4 | [PR1.2](../roadmap/02.5-production-readiness/sprint-1/PR1.2-slo-alerts.md) | SLO dashboards and alert rules use PS4.6 behavior metrics and PromQL. |
| PS7b-M5 | [PR1.1](../roadmap/02.5-production-readiness/sprint-1/PR1.1-k8s-monitoring-stack.md) | `postgres_exporter` or managed DB metrics close data-plane visibility gaps. |

---

## References

- [distributed_tracing_ps19.md](runbooks/distributed_tracing_ps19.md) — operator trace workflow (PS1.9)
- [behavior_metrics.md](behavior_metrics.md) — metric catalog and PromQL (PS4.6)
- [local_k8s_dev.md](runbooks/local_k8s_dev.md) — enable otel/jaeger on kind
- [gcp_stage_deploy.md](runbooks/gcp_stage_deploy.md) — stage observability parity table
- [BL-001](../roadmap/backlog/BL-001-monitoring-improvement-analysis.md) — backlog source
- [PS7.4](../roadmap/02-production-scale/sprint-7/PS7.4-monitoring-production-analysis.md) — sprint task
