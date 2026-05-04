# PS3.2 — Consumer offset store + idempotency keys

| Field | Value |
|-------|-------|
| **Task ID** | PS3.2 |
| **Status** | Done |

---

## Description

Implement **consumer progression** and **idempotency** so telemetry accepted at the API boundary can be processed without duplicate **`telemetry_events`** rows or duplicate downstream agent fan-out noise.

Per **[ADR 0002](../../../docs/adr/0002-ingest-nats-first-postgres-evidence-store.md)**, offsets are **JetStream durable-consumer ack positions** (not a Postgres `consumer_offsets` table). Idempotency at persistence uses **`event_id`** + `ON CONFLICT DO NOTHING`.

---

## Requirements

- [x] Persistence / progression model aligned with ADR 0002 — broker-native offsets + Postgres evidence store.
- [x] Idempotency key **`event_id`** (+ JetStream `Nats-Msg-Id` dedupe at publish).
- [x] Worker semantics documented — fetch → persist in **short DB txn** → ack JetStream (`telemetry_persister`).
- [x] Tests — mocked JetStream ingest (`202`) + unit helpers; duplicate NDJSON ingest unchanged when NATS unset.

---

## Checklist

- [x] **PS3.9:** When agents consume the same stream, correlate **`thread_id`** / `run_id` with `event_id` in that task — noted in `apps/ingest_jetstream.py` module docstring.

---

## Delivered

| Area | Location |
|------|----------|
| JetStream publish + lazy client | `apps/ingest_jetstream.py` |
| API telemetry branch `202` when `NATS_URL` set | `apps/api/main.py` |
| Idempotent Postgres insert | `apps/workers/telemetry_persist.py` |
| Persister worker | `apps/workers/telemetry_persister.py` |
| Config | `config.py` (`nats_url`, stream/subject/durable names) |
| Compose | `infra/docker-compose.yml` — `nats`, `telemetry-persister`, api `NATS_URL` |
| Deps | `requirements.txt` — `nats-py` |
| Tests | `tests/test_ingest_jetstream.py`, `tests/test_telemetry_persist.py`, `tests/conftest.py` |

---

## Test / acceptance

- [x] `pytest tests/test_api.py tests/test_ingest_jetstream.py tests/test_telemetry_persist.py` passes.

---

## Dependencies

- **PS3.1** superseded path documented in ADR 0002.
