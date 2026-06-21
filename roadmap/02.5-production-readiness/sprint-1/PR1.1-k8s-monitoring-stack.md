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

- [ ] K8s monitoring path implemented or managed-monitoring path documented with manifests.
- [ ] API and worker scrape targets visible.
- [ ] Postgres and queue metrics visible or explicitly tracked as accepted gaps with owners.
- [ ] OTLP TLS or sidecar/mesh termination configured for stage/prod path.
- [ ] Collector sampling and resource-limit policy documented.
- [ ] Grafana dashboards or managed dashboard links documented.
- [ ] Runbook updated: monitoring bring-up, access, and teardown.

## Test requirements

- Helm template/lint for monitoring-enabled values.
- A smoke command or runbook step showing scrape targets are up.
- Link/documentation test for new runbook references.
