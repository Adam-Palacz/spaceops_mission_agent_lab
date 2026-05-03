# Replay metadata (PS1.4)

Replay metadata provides deterministic-enough run fingerprints for regression triage
and golden-run workflows.

## Schema version

- Current schema: `v1`
- Persistence path: `data/replay/runs/<run_id>.json`

## Captured fields (`v1`)

- `run_id`: unique run identifier.
- `incident_id`: incident key used to trigger the run.
- `status`: `completed` | `error` | `timeout`.
- `payload_hash`: canonical SHA256 of the run payload.
- `input_refs`: extracted input references (`event_id`, `event_ids`, `input_ref`, `input_refs`, `telemetry_event_ids`).
- `trace_id`: trace identifier used by report/audit correlation.
- `audit_trace_id`: currently aligned with `trace_id`.
- `replay_source`: `api`, `eval_standard`, `eval_injection` (or future sources).
- `model`: provider + model id used by the agent.
- `prompts`: prompt id -> version mapping used by the pipeline.
- `runtime`: python/platform fingerprint.
- `llm_calls_used`: LLM call count captured from run state.

## API access

- Retrieve metadata: `GET /replays/{run_id}`
  - `200`: metadata exists and passes schema checks.
  - `404`: metadata not found for run id.
  - `422`: metadata exists but is incomplete/invalid.

## Replay assumptions and non-determinism

Replay metadata improves reproducibility, but results can still vary because:

- external dependencies change (MCP data, KB content, OPA responses);
- model backends can drift even with same model id;
- runtime/environment differences affect timings and tool behavior.

Use `payload_hash`, prompt versions, model id, and trace/audit linkage for
comparison and triage instead of expecting bit-identical outputs.

For **approved replay outcome pins** (golden baselines), see
[Golden-run baselines](golden_run_baselines.md) (PS2.8).
