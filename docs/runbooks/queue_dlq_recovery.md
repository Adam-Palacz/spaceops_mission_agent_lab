# Queue + DLQ recovery runbook (PS3.8)

Operator playbook for queue incidents in telemetry ingest (JetStream + persister + `dlq_events`).

Related specs:
- [PS3.3 retry + DLQ](../../roadmap/02-production-scale/sprint-3/PS3.3-retry-workflow-dlq.md)
- [PS3.4 queue replay](../../roadmap/02-production-scale/sprint-3/PS3.4-replay-queued-events.md)
- [PS3.10 MCP lossy links](../../roadmap/02-production-scale/sprint-3/PS3.10-mcp-resilience-lossy-links.md)

## 1) Symptoms

Typical incident signals:
- Growing DLQ count (`GET /dlq/telemetry` returns many new rows).
- Backlog in stream consumer / delayed persistence.
- Increased retry logs from persister.
- Missing telemetry in `telemetry_events` for expected `event_id` range.

## 2) Fast triage checklist

1. Confirm core services are healthy:
   - `docker compose ps`
   - `docker compose logs --tail=100 api`
   - `docker compose logs --tail=100 telemetry-persister`
2. Check DLQ growth and reason mix:
   - `curl "http://localhost:8000/dlq/telemetry?limit=50"`
3. Confirm Postgres reachable from API container:
   - `docker compose exec -T api python -c "import psycopg2; import os; psycopg2.connect(os.getenv('POSTGRES_DSN')); print('ok')"`
4. Confirm NATS reachable from persister context:
   - `docker compose exec -T telemetry-persister python -c "import asyncio, nats, os; print(asyncio.run(nats.connect(servers=[os.getenv('NATS_URL')])).is_connected)"`

If any connectivity checks fail, fix infra first before replay.

## 3) Diagnostics (queries + logs)

### 3.1 DLQ inspection

API:
```bash
curl "http://localhost:8000/dlq/telemetry?limit=100"
```

Postgres direct query:
```bash
docker compose exec -T postgres psql -U app -d spaceops -c "
SELECT id, event_id, reason, retry_count, next_retry_at, created_at
FROM dlq_events
ORDER BY id DESC
LIMIT 50;"
```

Reason hot-spots:
```bash
docker compose exec -T postgres psql -U app -d spaceops -c "
SELECT reason, COUNT(*) AS cnt
FROM dlq_events
GROUP BY reason
ORDER BY cnt DESC;"
```

### 3.2 Persistence coverage check

```bash
docker compose exec -T postgres psql -U app -d spaceops -c "
SELECT COUNT(*) AS persisted
FROM telemetry_events
WHERE created_at >= NOW() - INTERVAL '30 minutes';"
```

### 3.3 Persister retry evidence

```bash
docker compose logs --tail=300 telemetry-persister
```

Look for repeated retry/backoff patterns vs permanent DLQ inserts.

## 4) Safe replay steps

Do replay in two phases: dry-run then apply.

### Step A: Dry-run candidate selection

By DLQ ids:
```bash
python -m scripts.replay_queue --dlq-ids 12,15,18
```

By time window:
```bash
python -m scripts.replay_queue --after 2026-05-05T00:00:00Z --before 2026-05-05T12:00:00Z
```

Review output fields:
- `loaded_candidates`
- `local_duplicates_filtered`
- `to_replay`

### Step B: Apply replay

```bash
python -m scripts.replay_queue --dlq-ids 12,15,18 --apply
```

Safety guarantees:
- Script filters local duplicates by `event_id`.
- Broker dedupe still applies through `Nats-Msg-Id=event_id`.
- Replay does not mutate DLQ rows; it republishes payloads.

### Step C: Verify recovery

1. Check replay summary (`published`, `broker_duplicates`).
2. Re-check DLQ and recent persistence counts.
3. Confirm no new fast-growing DLQ wave in next 5-15 minutes.

## 5) Rollback posture

If apply replay worsens symptoms:
- Stop replay activity (no more `--apply` runs).
- Keep evidence: command output JSON + relevant logs.
- Stabilize dependencies (NATS/Postgres/API/persister) first.
- Retry with smaller batches (`--dlq-ids` subset or tighter time window).

## 6) Escalation criteria

Escalate to senior/on-call if any condition holds:
- DLQ keeps growing after infra health is restored and at least one controlled replay.
- Replay apply repeatedly fails (`exit=1`) due to broker/database errors.
- Evidence suggests cross-system outage (NATS + DB + API instability).
- Symptoms match MCP storm/breaker-open behavior (tool failures, no-evidence escalations):
  use [PS3.10 MCP lossy links](../../roadmap/02-production-scale/sprint-3/PS3.10-mcp-resilience-lossy-links.md)
  triage bullets in parallel.

## 7) Junior-friendly execution order

1. `docker compose ps`
2. `curl /dlq/telemetry`
3. quick connectivity checks (DB + NATS)
4. `scripts.replay_queue` dry-run
5. `scripts.replay_queue --apply` on a small subset
6. verify persistence + DLQ trend
7. escalate if trend is still bad

## 8) MCP storm / breaker-open triage (PS3.10)

When symptoms suggest MCP transport degradation (timeouts, connect resets, repeated 5xx/421):

1. Confirm MCP services are reachable:
   - `docker compose logs --tail=150 telemetry-mcp`
   - `docker compose logs --tail=150 kb-mcp`
2. Check API/agent logs for repeated tool failures and circuit-open messages:
   - `docker compose logs --tail=300 api`
   - look for `http_resilience: circuit open for key=mcp_*`
3. Treat evidence as fail-closed while circuit is open:
   - expect `tool_failure` / `no_evidence` escalation paths,
   - do **not** force unsafe actions while MCP health is unknown.
4. Recovery sequence:
   - restore MCP connectivity first,
   - wait for breaker reset window,
   - run a small verification incident before full traffic.
