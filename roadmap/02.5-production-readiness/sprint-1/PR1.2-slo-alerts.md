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

- [ ] SLO document added or updated.
- [ ] Alert rules added to Helm/GitOps or managed-monitoring config.
- [ ] Dashboard panels added or linked.
- [ ] Alert severity and routing policy documented.
- [ ] Synthetic trigger evidence recorded.

## Test requirements

- Static check for alert rule syntax where supported.
- Documentation link test.
- Optional: scripted synthetic metric trigger in stage.

