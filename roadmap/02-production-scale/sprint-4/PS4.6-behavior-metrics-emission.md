# PS4.6 — Behavior metrics emission



| Field | Value |

|-------|-------|

| **Task ID** | PS4.6 |

| **Status** | Done |



---



## Description



Expose measurable quality/safety behavior metrics as release-readiness inputs: escalation rate,

evidence coverage, and stage latency percentiles.



---



## Requirements



- [x] Define metric set and canonical labels for safety/quality dashboards.

- [x] Emit escalation-rate and evidence-coverage counters.

- [x] Emit p50/p95 stage timing metrics from pipeline timing data.

- [x] Document metric semantics and interpretation for operators.



---



## Checklist



- [x] Metrics avoid high-cardinality labels.

- [x] API/agent metrics path validated in local compose.

- [x] Alert-ready thresholds proposed (initial defaults acceptable).



---



## Test / acceptance



- [x] Automated tests verify metric emission on success and escalation paths.

- [x] Metric names/labels are stable and documented.

- [x] Example dashboard/query snippet included in docs or runbook.



---



## Deliverables



- `apps/behavior_metrics.py` — counters/histograms + canonical label normalization

- `apps/api/main.py` — record on `/runs`, simulate, `/runs/resume`

- `docs/behavior_metrics.md` — semantics, PromQL, alert defaults

- `infra/grafana/provisioning/dashboards/spaceops-dashboard.json` — PS4.6 panels

- `tests/test_behavior_metrics_ps46.py`

