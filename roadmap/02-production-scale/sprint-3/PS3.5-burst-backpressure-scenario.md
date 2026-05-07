# PS3.5 — Burst / backpressure load scenario

| Field | Value |
|-------|-------|
| **Task ID** | PS3.5 |
| **Status** | Done |

---

## Description

Validate that **ingest and workers remain stable under burst load**: no crash loops, no offset corruption,
bounded memory growth. Aligns with sprint DoD: **backpressure does not crash ingest or corrupt offsets**.

---

## Requirements

- [x] Scripted benchmark reproducible locally (`python -m scripts.burst_ingest`).
- [x] Metrics/assertions: request success/failure, accepted/duplicates/rejected, p50/p95 latency, total duration, RPS, failure-rate threshold.
- [x] Thresholds and assumptions documented below.

---

## Checklist

- [x] Captured one baseline snapshot in `data/replay/baselines/ps35_burst_local.json`.

---

## Test / acceptance

- [x] Scenario passes on developer laptop profile (`--total-requests 150 --concurrency 20`).

---

## Delivered

- Load module: `apps/load/burst_ingest.py`
  - async burst executor for `POST /ingest?source=telemetry`
  - summary metrics (failure-rate, p50/p95, RPS, accepted/duplicates/rejected)
- CLI: `scripts/burst_ingest.py`
  - knobs: `--total-requests`, `--concurrency`, `--timeout-seconds`
  - pass/fail gates: `--max-failure-rate`, `--max-p95-ms`
  - baseline output: `--output-json <path>`
- Tests:
  - `tests/test_burst_backpressure.py` (summary + local ASGI/TestClient burst smoke)

## Baseline and thresholds (local laptop, Compose API)

Example command:

```bash
python -m scripts.burst_ingest \
  --api-base-url http://localhost:8000 \
  --total-requests 150 \
  --concurrency 20 \
  --max-failure-rate 0.20 \
  --max-p95-ms 2500 \
  --output-json data/replay/baselines/ps35_burst_local.json
```

Observed baseline snapshot (2026-05-07):

- requests: `150`, failures: `0` (failure_rate `0.0`)
- p95 latency: `~854 ms`
- throughput: `~164 req/s`

Interpretation:

- this profile passed without explicit shedding (all accepted by API path);
- if resource-constrained CI is added later, use smaller profile (e.g. `60/10`) with same script and tighter timeout guard.

---

## Dependencies

- **PS3.2** worker loop live enough to exercise under load.
