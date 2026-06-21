# PR1.1 - K8s monitoring stack in Helm/GitOps

## Description

Promote monitoring from compose-only to the K8s/stage path. The goal is a repeatable deployment of
Prometheus/Grafana or a managed monitoring equivalent, wired to the SpaceOps API, agent worker,
Postgres, NATS/queue, OTel collector, and platform components.

## Requirements

- Add Helm/GitOps values or documented managed-monitoring integration for stage.
- Scrape `/metrics` for API and worker paths.
- Include Postgres and queue/DLQ metrics either through exporters or managed integrations.
- Secure OTLP collector traffic with TLS or documented sidecar/mesh termination for stage/prod.
- Add collector memory limits, health probes, and sampling policy.
- Document access, credentials, retention, and teardown behavior.
- Keep local compose monitoring working.

## Checklist

- [x] K8s monitoring path implemented or managed-monitoring path documented with manifests.
- [x] API scrape target visible; worker standalone scrape is an accepted gap until a worker metrics endpoint/sidecar exists.
- [x] Postgres and queue metrics visible through `postgres-exporter` and NATS monitoring scrape.
- [x] OTLP sidecar/mesh termination configured for stage/prod path via `tlsMode: mesh-sidecar`.
- [x] Collector sampling and resource-limit policy documented.
- [x] Grafana dashboards or managed dashboard links documented.
- [x] Runbook updated: monitoring bring-up, access, and teardown.

## Test requirements

- Helm template/lint for monitoring-enabled values.
- A smoke command or runbook step showing scrape targets are up.
- Link/documentation test for new runbook references.

## Implementation notes

- Added `deploy/helm/spaceops/values-monitoring-stage.yaml`.
- Added Helm templates for Prometheus, Grafana, and `postgres-exporter`.
- Hardened OTel Collector with health probes, resources, memory limiter, probabilistic sampling,
  internal metrics, and `mesh-sidecar` TLS mode.
- Updated `deploy/helm/spaceops/README.md`, `docs/runbooks/gcp_stage_deploy.md`, and
  `docs/monitoring-production-analysis.md`.

## Status

Done.
