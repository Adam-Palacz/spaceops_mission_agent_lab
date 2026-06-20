# BL-001 — Monitoring improvement analysis

**Backlog item** — use this spec to create a sprint task (e.g. P4.x) when you schedule this work. The backlog has no statuses.

> **Note (2026-05-31):** PS1.9 delivered **distributed tracing**, not this analysis. Scheduled as **[PS7.4](../02-production-scale/sprint-7/PS7.4-monitoring-production-analysis.md)** — see [TRIAGE.md](TRIAGE.md).
>
> **Done (2026-06-03):** Delivered via PS7.4 → [docs/monitoring-production-analysis.md](../../docs/monitoring-production-analysis.md).

| Field | Value |
|-------|--------|
| **Backlog ID** | BL-001 |
| **Source** | Verifies deliverable from [01-core/sprint-1/S1.2-docker-compose.md](../01-foundation-mvp/01-core/sprint-1/S1.2-docker-compose.md) |

---

## Description

**Objective:** Analyse whether the current monitoring and observability setup from S1.2 (Postgres, OTel Collector, Jaeger, `infra/docker-compose.yml`, `infra/otel-collector.yaml`) is suitable for production, and document gaps and improvement options.

Review the tools and configuration introduced in S1.2 and assess: production readiness, security, scalability, retention, resilience, and operational fit. Output is an analysis document (or section in docs) with findings and recommended improvements; implementation of those improvements can be separate tasks.

---

## Requirements

- [x] Review **infra/docker-compose.yml** and **infra/otel-collector.yaml** (and any related S1.2/S1.10/S2.9 setup).
- [x] Assess against production criteria: single-command run (goals.md §4.5), security (no default creds in prod, TLS where needed), scalability (e.g. Jaeger all-in-one vs distributed), retention (trace/log retention, sampling), resilience (healthchecks, restarts, resource limits).
- [x] Compare with goals: observability (OTel, Jaeger, Prometheus/Grafana in roadmap), audit/trace (NF2), structured logging.
- [x] Document findings: what is OK for prod as-is, what is not, and what to change (with concrete options, e.g. “use managed Postgres”, “add TLS to OTLP”, “add Prometheus + Grafana for metrics”).
- [x] Optionally: add a short “Production checklist” for monitoring (to be met before going to production) or link to existing docs.

---

## Checklist

- [x] Read S1.2 task and current `infra/docker-compose.yml`, `infra/otel-collector.yaml`.
- [x] List components: Postgres (pgvector), OTel Collector, Jaeger; note versions and exposed ports.
- [x] Assess each for production: defaults (e.g. passwords), TLS, persistence, resource limits, high availability / single point of failure.
- [x] Check alignment with project goals (goals.md §4.5, NF2, roadmap observability) and with S1.10 (traces), S2.9 (Prometheus/Grafana).
- [x] Write analysis: “Production readiness of current monitoring stack” — OK / gaps / recommendations.
- [x] Save under `docs/` (e.g. `docs/monitoring-production-analysis.md`) or add section to `docs/architecture.md`; link from backlog BOARD when done.
- [x] If concrete improvements are identified, optionally create follow-up backlog tasks (e.g. BL-002: “Add TLS for OTLP”) or note them in the doc.

---

## Test requirements

- Analysis document exists and is readable.
- Each component (Postgres, OTel Collector, Jaeger) is explicitly assessed (production-ready or not; what is missing).
- Recommendations are actionable (clear next steps or new tasks); no open “TBD” without a proposed direction.

**Verified:** `tests/test_monitoring_production_analysis_ps74.py`.
