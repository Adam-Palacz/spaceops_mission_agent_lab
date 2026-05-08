# PS4.6 — Behavior metrics emission

| Field | Value |
|-------|-------|
| **Task ID** | PS4.6 |
| **Status** | Todo |

---

## Description

Expose measurable quality/safety behavior metrics as release-readiness inputs: escalation rate,
evidence coverage, and stage latency percentiles.

---

## Requirements

- [ ] Define metric set and canonical labels for safety/quality dashboards.
- [ ] Emit escalation-rate and evidence-coverage counters.
- [ ] Emit p50/p95 stage timing metrics from pipeline timing data.
- [ ] Document metric semantics and interpretation for operators.

---

## Checklist

- [ ] Metrics avoid high-cardinality labels.
- [ ] API/agent metrics path validated in local compose.
- [ ] Alert-ready thresholds proposed (initial defaults acceptable).

---

## Test / acceptance

- [ ] Automated tests verify metric emission on success and escalation paths.
- [ ] Metric names/labels are stable and documented.
- [ ] Example dashboard/query snippet included in docs or runbook.
