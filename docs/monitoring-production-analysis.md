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
| **Prometheus** | Compose-only scrape | **Not in Helm chart** | **Gap** on K8s/stage/GKE |
| **Grafana** | Compose-only, default creds | **Not in Helm chart** | **Gap** on K8s/stage/GKE |

**Verdict:** The stack is **appropriate for dev, portfolio demos, and stage proof** (traces + metrics
on Compose; traces on GKE stage via port-forward). It is **not production-complete** without managed
Postgres, secured OTLP, trace/metrics retention policy, Prometheus/Grafana on cluster (or cloud
equivalents), and SLO dashboards.

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

**Production checklist item:** evidence DB on **managed Postgres** with backup, encryption at rest,
and connection pooling (PgBouncer or managed proxy) before prod pilot.

---

### OpenTelemetry Collector

| Aspect | Compose | Helm | OK / Gap | Recommendation |
|--------|---------|------|----------|----------------|
| **Config** | `infra/otel-collector.yaml` | ConfigMap mirror in `observability.yaml` | OK | Keep single source; consider Helm subchart later |
| **Receivers** | OTLP gRPC/HTTP on 4317/4318 | ClusterIP only | OK in-cluster | Do not expose 4317 on public LB |
| **TLS** | `tls.insecure: true` → Jaeger | Same | Gap prod | PS7b: OTLP mTLS or sidecar TLS termination |
| **Processors** | `batch` only | `batch` only | Gap prod | Add `memory_limiter`, `probabilistic_sampler` |
| **Sampling** | Head sampling not configured (100%) | Same | Gap prod | Tail or probabilistic sampling (e.g. 10% + error boost) |
| **HA** | Single container | `replicas: 1` | Gap prod | Multiple collectors + k8s service or agent sidecar pattern |
| **Health / limits** | No healthcheck in compose | No probes in template | Gap | Add `/` health extension or k8s probes + CPU/mem limits |
| **Metrics pipeline** | Traces only | Traces only | Gap | Optional metrics exporter → Prometheus (OTLP metrics) |

**Production checklist item:** secured OTLP ingress, sampling policy documented, collector resource
limits, and alert on export failures.

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

**Production checklist item:** persistent trace backend with defined retention; do not rely on
all-in-one for prod traffic.

---

### Prometheus (metrics)

| Aspect | Compose | Helm | OK / Gap | Recommendation |
|--------|---------|------|----------|----------------|
| **Presence** | `prom/prometheus:v3.10.0` service | **Not packaged** (PS6.2 scope) | OK compose | Gap K8s/GKE |
| **Scrape config** | `host.docker.internal:8000/metrics` | N/A | OK compose | In K8s: ServiceMonitor or Pod annotation scrape |
| **Metrics exposed** | S2.9 + PS4.6 behavior metrics on `/metrics` | Same endpoint on api Deployment | OK app | Wire scrape target in cluster |
| **Retention** | Default 15d (Prometheus default) | N/A | Gap | Set `--storage.tsdb.retention.time` explicitly |
| **HA** | Single | N/A | Gap prod | Thanos / Mimir / managed Prometheus |
| **Alerting** | None in repo | N/A | Gap | Alertmanager rules for escalation rate, error rate (see behavior_metrics.md) |

**Production checklist item:** deploy Prometheus (or GCP Cloud Monitoring scrape) on stage/prod;
dashboards for SLOs in [behavior_metrics.md](behavior_metrics.md).

---

### Grafana (dashboards)

| Aspect | Compose | Helm | OK / Gap | Recommendation |
|--------|---------|------|----------|----------------|
| **Presence** | `grafana/grafana:12.4.0` | **Not packaged** | OK compose | Gap K8s/GKE |
| **Auth** | `admin/admin` default | N/A | Gap prod | SSO or strong secret + disable anonymous |
| **Dashboards** | Provisioned JSON (`infra/grafana/provisioning/`) | N/A | OK baseline | Extend with PS4.6 panels; add SLO board (PS7b) |
| **Datasource** | Prometheus at `http://prometheus:9090` | N/A | OK compose | Point to in-cluster Prometheus or cloud metrics |

**Production checklist item:** Grafana behind auth; link from portfolio only for lab; use managed
dashboards or GitOps-provisioned dashboards in prod.

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

| Capability | Compose dev | Helm minimal-dev | Helm stage / GKE |
|------------|-------------|------------------|------------------|
| Traces → Jaeger | Yes (4317 exposed) | Optional (off default) | Yes (`observability.*.enabled: true`) |
| Jaeger UI | `:16686` | port-forward | port-forward / optional ingress |
| Prometheus | Yes | No | No |
| Grafana | Yes | No | No |
| Behavior metrics scrape | Yes (host scrape) | Manual if api port-forward | **Not wired** — gap |

See [gcp_stage_deploy.md](runbooks/gcp_stage_deploy.md) — Jaeger/OTel yes; Grafana/Prometheus no on GKE.

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

## PS7b follow-up tasks (optional)

| ID | Task | Rationale |
|----|------|-----------|
| PS7b-M1 | Helm subchart or values overlay for Prometheus + Grafana | Close K8s metrics gap |
| PS7b-M2 | OTel Collector: TLS + probabilistic sampling | Cost and security |
| PS7b-M3 | Jaeger → persistent storage or migrate to Cloud Trace / Tempo | Retention on GKE |
| PS7b-M4 | SLO dashboard (escalation rate, stage p95, tool failure rate) | PS4.6 + behavior_metrics PromQL |
| PS7b-M5 | `postgres_exporter` + disk/connection alerts | Data plane visibility |

---

## References

- [distributed_tracing_ps19.md](runbooks/distributed_tracing_ps19.md) — operator trace workflow (PS1.9)
- [behavior_metrics.md](behavior_metrics.md) — metric catalog and PromQL (PS4.6)
- [local_k8s_dev.md](runbooks/local_k8s_dev.md) — enable otel/jaeger on kind
- [gcp_stage_deploy.md](runbooks/gcp_stage_deploy.md) — stage observability parity table
- [BL-001](../roadmap/backlog/BL-001-monitoring-improvement-analysis.md) — backlog source
- [PS7.4](../roadmap/02-production-scale/sprint-7/PS7.4-monitoring-production-analysis.md) — sprint task
