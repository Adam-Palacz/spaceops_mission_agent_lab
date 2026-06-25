# Production Readiness SLOs and Alerts (PR1.2)

This document defines the production-pilot SLO baseline for SpaceOps. It is intentionally scoped to
the current PR1.1 monitoring stack: Prometheus, Grafana, OTel Collector, NATS monitoring, and
postgres-exporter.

## SLO catalog

| Area | SLO | Indicator | Alert |
|------|-----|-----------|-------|
| API availability | >= 99% during pilot hours | `up{job="spaceops-api"}` | `SpaceOpsApiDown` |
| Run latency | p95 run duration <= 60s | `agent_run_duration_seconds_bucket` | `SpaceOpsSlowRunP95` |
| Run errors | error rate <= 5% over 15m | `agent_runs_total{status="error"}` / `agent_runs_total` | `SpaceOpsHighRunErrorRate` |
| Queue/DLQ visibility | NATS scrape target up | `up{job="spaceops-nats"}` | `SpaceOpsNatsScrapeDown` |
| Data plane visibility | Postgres exporter up | `up{job="spaceops-postgres"}` | `SpaceOpsPostgresExporterDown` |
| Evidence safety | zero sustained evidence violations | `agent_evidence_coverage_total{policy_status="violation"}` | `SpaceOpsEvidencePolicyViolations` |
| OPA/policy safety | zero OPA tool failures | `agent_tool_outcome_total{tool="opa_check",outcome="failure"}` | `SpaceOpsOpaToolFailures` |
| Escalation health | escalation rate <= 40% over 15m | `agent_escalations_total` / `agent_behavior_runs_total` | `SpaceOpsHighEscalationRate` |
| LLM budget | budget exhaustion must be investigated | `agent_escalations_total{reason="budget_exceeded"}` | `SpaceOpsLlmBudgetExceeded` |

## Coverage boundaries

The PR1.2 alert set uses metrics that exist today. These are acceptable production-pilot boundaries,
but they should be tightened in later PR work:

- Checkpoint failures are covered indirectly by run errors, traces, and PR1.4 failure tests until a
  dedicated checkpoint failure counter exists.
- Approval API errors are covered indirectly by API run/error visibility until approval endpoint
  request metrics are exported.
- Eval/safety regressions remain CI gates; Prometheus does not scrape CI results yet.
- Variant A `agent-worker` has no standalone `/metrics` endpoint; use API run metrics, queue/DLQ,
  and traces until a worker endpoint or metrics sidecar is added.

## Alert routing

| Severity | Meaning | Initial route |
|----------|---------|---------------|
| `page` | Production-pilot operation is unsafe or unavailable. | Platform owner plus mission-agent owner. |
| `ticket` | Needs investigation during business hours or next ops review. | Sprint/ops backlog. |

Route labels in rules are intentionally simple:

- `platform`: API/NATS/Prometheus target health.
- `data-plane`: Postgres exporter or storage visibility.
- `mission-agent`: run latency, run failures, escalation rate.
- `safety`: OPA and evidence policy violations.
- `cost`: LLM budget exhaustion.
- `synthetic`: explicit alert drill.

PR1.2 does not deploy Alertmanager yet. The labels are ready for Alertmanager or managed monitoring
routing in a later PR task.

## Deferred production dashboards

The PR1.2 Grafana board is a production-pilot baseline, not the final SRE dashboard. It covers the
available runtime signals: availability, p95 latency, run error rate, escalation rate, evidence
violations, OPA failures, budget exhaustion, run counts, and DLQ visibility proxy.

The following panels require either more metrics or an alert-routing backend and are intentionally
deferred:

- Error-budget burn calculations for formal SLO windows.
- Recent incidents, which should come from Alertmanager or managed alert history.
- `llm_backend_fallback_total` visibility and alerting.
- Dedicated checkpoint and approval API error counters.

## Synthetic alert trigger

The rules include `SpaceOpsSyntheticPr12Probe` with `expr: vector(0) == 1`, so it is inert by default.
During a stage drill:

1. Temporarily override the rule expression to `vector(1)` in a throwaway branch or one-off Helm
   overlay.
2. Deploy the monitoring overlay.
3. Open Prometheus alerts:

   ```bash
   kubectl port-forward -n spaceops-stage svc/spaceops-prometheus 9090:9090
   curl -s http://127.0.0.1:9090/api/v1/alerts
   ```

4. Confirm `SpaceOpsSyntheticPr12Probe` is firing.
5. Revert the expression to `vector(0) == 1` and redeploy.

Repo evidence for this task is static: Helm renders the rule file and tests assert the synthetic
rule, severity labels, dashboard panels, and PR1.2 documentation links.

## Files

- Helm rules and Grafana dashboard: [`../deploy/helm/spaceops/templates/monitoring.yaml`](../deploy/helm/spaceops/templates/monitoring.yaml)
- Monitoring overlay: [`../deploy/helm/spaceops/values-monitoring-stage.yaml`](../deploy/helm/spaceops/values-monitoring-stage.yaml)
- GKE runbook: [`runbooks/gcp_stage_deploy.md`](runbooks/gcp_stage_deploy.md)
- Metric catalog: [`behavior_metrics.md`](behavior_metrics.md)
