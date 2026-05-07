# Replay workflow (PS1.5)

Minimal replay lets you re-run a stored incident input by `run_id` and compare:

- `subsystem`
- `escalated`
- `has_citations`
- `escalation_reason` (`report.escalation_packet.reason` when present)
- `citation_count` (length of citations, else `citation_refs`)

**Golden baselines (PS2.8):** pin approved replay outcomes for regression checks — see
[Golden-run baselines](../golden_run_baselines.md) (`scripts/golden_baseline.py`, `make golden-check`).

## API usage

1. Run a normal incident:

```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"incident_id":"inc-123","payload":{"message":"power anomaly"}}'
```

2. Get replay metadata:

```bash
curl http://localhost:8000/replays/<run_id>
```

3. Execute replay and diff:

```bash
curl -X POST http://localhost:8000/replays/<run_id>/run
```

## SpaceOps UI (PS2.6)

- **`/replays`**: enter pipeline **`run_id`** (UUID from `GET /runs/{run_key}` JSON, not the run *file* stem), **Load replay metadata** (`GET /replays/{run_id}`), then **Run replay & compare** (`POST /replays/{run_id}/run`). The page shows **`comparison.has_diff`** and field diffs — same semantics as `replay_by_run_id` / `scripts/replay_run.py` (CLI exit `0` vs `2`).
- **Incident run detail**: section **Replay from this run** when the artifact has `run_id` (disabled if the run file records a pipeline error).

## CLI usage

Run from repo root:

```bash
python scripts/replay_run.py --run-id <run_id>
```

Exit codes:

- `0`: replay succeeded and no core behavior diff
- `2`: replay succeeded and diff detected
- `1`: replay failed (missing metadata/input or runtime error)

## Queue replay (PS3.4)

PS1.5 replay (`scripts/replay_run.py`) re-runs a **single stored incident input** by `run_id` and
compares behavior. PS3.4 queue replay (`scripts/replay_queue.py`) re-drives **queued telemetry
messages** back into JetStream.

Examples:

```bash
# Dry-run DLQ subset by IDs (default mode; no publish)
python -m scripts.replay_queue --dlq-ids 12,15,18

# Dry-run by DLQ time window
python -m scripts.replay_queue --after 2026-05-05T00:00:00Z --before 2026-05-05T12:00:00Z

# Replay JetStream sequence range (offset-like)
python -m scripts.replay_queue --seq-start 100 --seq-end 130 --apply
```

Safety:

- `--apply` is required to publish; without it script is dry-run only.
- Local duplicates are filtered by `event_id` before publish.
- Broker dedupe still applies via `Nats-Msg-Id=event_id`.

## CI usage example

Replay a golden run and fail pipeline on regressions:

```bash
python scripts/replay_run.py --run-id <golden_run_id>
if [ $? -eq 2 ]; then
  echo "Replay regression detected"
  exit 1
fi
```

## Guardrails

- Missing replay metadata -> clear error (`404`/`1`).
- Incomplete metadata or non-replayable run artifact payload -> clear error (`422`/`1`).
- **Run artifact lookup:** replay resolves `data/incidents/run_*.json` by top-level **`run_id`**, or (if missing) by **`incident_id` + `payload_hash`** on **`run_*.json`**. The same hash match also applies to **`incident_*.json`** fixture files (e.g. `incident_test-inc-1.json`) so a stored replay can re-use the same `payload` without a `run_*.json` row.

## Troubleshooting: `Run artifact not found for run_id=…`

- Confirm a matching **`run_*.json`** or **`incident_*.json`** exists under `data/incidents/` (same machine / `DATA_DIR` as the API).
- If there is no **`run_id`** on the file, ensure **`incident_id`** and **`payload`** match **`payload_hash`** in `data/replay/runs/<run_id>.json` (canonical SHA256 of the `payload` object).
