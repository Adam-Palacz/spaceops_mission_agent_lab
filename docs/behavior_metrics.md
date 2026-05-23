# Behavior metrics (PS4.6)

Release-readiness counters and histograms complement S2.9 operational metrics (`agent_runs_total`, `agent_run_duration_seconds`). They are emitted from the API after each `run_pipeline` completion on `POST /runs`, simulate endpoints, and `POST /runs/resume`.

**Endpoint:** `GET /metrics` (Prometheus text format, same scrape target as S2.9).

## Metric catalog

| Metric | Type | Labels | Meaning |
|--------|------|--------|---------|
| `agent_behavior_runs_total` | Counter | `outcome` | Run ended as `completed`, `escalated`, or `error` (pipeline exception). Denominator for escalation rate. |
| `agent_escalations_total` | Counter | `reason` | One increment per escalated run; `reason` is canonical (see below). |
| `agent_evidence_coverage_total` | Counter | `policy_status`, `has_citations` | Evidence policy outcome plus whether any citations were present (`true` / `false`). |
| `agent_stage_duration_seconds` | Histogram | `stage` | Wall time per LangGraph node from `stage_timings` (seconds). Use for p50/p95 per stage. |

### Canonical `reason` values (`agent_escalations_total`)

`no_evidence`, `conflicting_signals`, `tool_failure`, `policy_deny`, `prompt_injection_detected`, `evidence_policy_violation`, `output_schema_violation`, `token_limit`, `rate_limit`, `llm_timeout`, `llm_provider_error`, `run_timeout`, `other`.

Unknown reasons are bucketed as `other` to avoid high-cardinality labels.

### Canonical `stage` values (`agent_stage_duration_seconds`)

`triage`, `investigate`, `check_escalation`, `decide`, `act`, `build_report`. Unknown nodes are not recorded.

### `policy_status` values (`agent_evidence_coverage_total`)

`ok`, `violation`, `skipped_escalated`, `unknown` (from `evidence_policy_status` on agent state).

## Example PromQL

**Escalation rate (5m):**

```promql
sum(rate(agent_escalations_total[5m]))
/
sum(rate(agent_behavior_runs_total[5m]))
```

**Evidence policy OK share (5m):**

```promql
sum(rate(agent_evidence_coverage_total{policy_status="ok"}[5m]))
/
sum(rate(agent_evidence_coverage_total[5m]))
```

**Stage latency p95 — triage (5m):**

```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(agent_stage_duration_seconds_bucket{stage="triage"}[5m]))
)
```

**Stage latency p50 — investigate:**

```promql
histogram_quantile(
  0.50,
  sum by (le) (rate(agent_stage_duration_seconds_bucket{stage="investigate"}[5m]))
)
```

## Suggested alert thresholds (initial defaults)

Tune after baseline data in your environment.

| Alert | Expression | Default threshold | Notes |
|-------|------------|-------------------|-------|
| High escalation rate | `sum(rate(agent_escalations_total[15m])) / sum(rate(agent_behavior_runs_total[15m]))` | > 0.40 for 15m | Many runs failing closed; check MCP, KB, or policy changes. |
| Evidence violations | `sum(rate(agent_evidence_coverage_total{policy_status="violation"}[15m]))` | > 0.05 / min | Grounding regressions (PS4.1). |
| Injection escalations | `sum(rate(agent_escalations_total{reason="prompt_injection_detected"}[15m]))` | > 0 | Any sustained rate warrants review of untrusted inputs. |
| Slow triage p95 | `histogram_quantile(0.95, sum by (le)(rate(agent_stage_duration_seconds_bucket{stage="triage"}[15m])))` | > 30s | LLM or tool latency; compare with `agent_run_duration_seconds`. |

## Local validation (compose)

1. Start stack: `docker compose -f infra/docker-compose.yml --project-directory . up -d`
2. Run API: `python -m apps.api.main`
3. Trigger a run: `POST http://localhost:8000/runs` (see README).
4. Scrape: `curl -s http://localhost:8000/metrics | findstr agent_behavior`
5. Open Grafana (`http://localhost:3000`) — dashboard **SpaceOps Agent Metrics** includes PS4.6 panels.

## Implementation

- Module: `apps/behavior_metrics.py`
- Wired from: `apps/api/main.py` (`record_agent_run_behavior`, `record_agent_run_error`)
- Tests: `tests/test_behavior_metrics_ps46.py`
