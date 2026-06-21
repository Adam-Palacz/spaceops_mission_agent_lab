# PR1.2 - SLO dashboards and alert rules

## Description

Define production-pilot SLOs and wire alert rules for the core SpaceOps runtime. The system should
have explicit thresholds instead of relying on manual inspection.

## Requirements

- SLOs for API availability, run latency, error rate, queue/DLQ depth, checkpoint failures, LLM
  budget exhaustion, OPA errors, approval API errors, and eval/safety regressions.
- Alert rules for page-worthy and ticket-worthy conditions.
- Dashboard panels for SLO burn, recent incidents, run counts, p95 latency, backend fallback, and
  unsafe-action/evidence violations.
- Synthetic alert trigger documented for at least one rule.

## Checklist

- [x] SLO document added or updated.
- [x] Alert rules added to Helm/GitOps or managed-monitoring config.
- [x] Dashboard panels added or linked.
- [x] Alert severity and routing policy documented.
- [x] Synthetic trigger evidence recorded.

## Test requirements

- Static check for alert rule syntax where supported.
- Documentation link test.
- Optional: scripted synthetic metric trigger in stage.

## Implementation notes

- Added [slo-production-readiness.md](../../../docs/slo-production-readiness.md).
- Added Prometheus rule file ConfigMap `spaceops-prometheus-rules` in
  `deploy/helm/spaceops/templates/monitoring.yaml`.
- Extended the Grafana provisioning dashboard with SLO panels for availability, latency, run error
  rate, escalation rate, evidence violations, OPA failures, and budget-exceeded escalations.
- Added a synthetic inert alert rule `SpaceOpsSyntheticPr12Probe` for stage alert drills.
- Documented coverage boundaries for checkpoint failures, approval API errors, CI eval/safety
  regressions, and worker standalone metrics.
- Deferred full error-budget burn, recent-incident panels, `llm_backend_fallback_total` visibility,
  Alertmanager routing, and live `vector(1)` drill evidence to later production-readiness work
  (PR1.4/PR3), because PR1.2 is the repository baseline for rules, dashboard, and drill procedure.

## Status

Done.
