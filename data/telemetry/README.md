# Telemetry NDJSON

Sample and ingest-output **telemetry** lines for `POST /ingest?source=telemetry` and agent triage.

| File | Role |
|------|------|
| `telemetry.ndjson` | Committed fixture (ts, channel, value, subsystem, unit). |
| `ingest_*.ndjson` | Written by ingest when NATS is off (legacy lab path). |

Schema and curl examples: [../README.md](../README.md).
