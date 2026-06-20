# Ground log NDJSON

Sample and ingest-output **ground segment log** lines for `POST /ingest?source=ground_logs`.

| File | Role |
|------|------|
| `ground_logs.ndjson` | Committed fixture (ts, source, level, message). |
| `ingest_*.ndjson` | Written by ingest when NATS is off. |

See [../README.md](../README.md) for schema and ingest commands.
