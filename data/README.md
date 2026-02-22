# Data — fixtures and ingest output

Reproducible fixtures and output from `POST /ingest` and run triggers. Same fixtures → same ingest outcome (goals.md §4.5).

## Layout

| Folder | Purpose |
|--------|---------|
| **telemetry/** | Telemetry NDJSON (ts, channel, value, subsystem, unit). Fixture: `telemetry.ndjson`. Ingest writes `ingest_*.ndjson`. |
| **events/** | Event NDJSON (ts, event_type, subsystem, message). Fixture: `events.ndjson`. Ingest writes `ingest_*.ndjson`. |
| **ground_logs/** | Ground segment log NDJSON (ts, source, level, message). Fixture: `ground_logs.ndjson`. Ingest writes `ingest_*.ndjson`. |
| **incidents/** | Run trigger payloads and incident artifacts (from `POST /runs`). |

## Fixture schema (minimal)

- **Telemetry:** `ts` (ISO8601), `channel`, `value`, optional `subsystem` (ADCS|Power|Thermal|Comms|Payload|Ground), `unit`.
- **Events:** `ts`, `event_type`, `subsystem`, `message`.
- **Ground logs:** `ts`, `source`, `level`, `message`.

Ingest accepts any JSON object per line; the above fields align with agent triage and pipeline (S1.7). Add more fields as needed.

## Ingest

```bash
curl -X POST "http://localhost:8000/ingest?source=telemetry" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @telemetry/telemetry.ndjson
```

Repeat for `source=events` and `source=ground_logs`.
