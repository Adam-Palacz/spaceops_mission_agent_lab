# Event NDJSON

Sample and ingest-output **event** lines for `POST /ingest?source=events`.

| File | Role |
|------|------|
| `events.ndjson` | Committed fixture (ts, event_type, subsystem, message). |
| `ingest_*.ndjson` | Written by ingest when NATS is off. |

See [../README.md](../README.md) for schema and ingest commands.
