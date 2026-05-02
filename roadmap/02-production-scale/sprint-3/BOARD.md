# PS3 — Board

| Task | Title | Status | Notes / spec |
|------|-------|--------|----------------|
| PS3.1 | Queue strategy decision (DB offsets vs NATS/Redpanda) | Todo | ADR with rationale and migration path. |
| PS3.2 | Consumer offset store + idempotency keys | Todo | Ensure exactly-once-ish behavior at app level. |
| PS3.3 | Retry workflow + DLQ table/topic | Todo | Capture reason, retry_count, next_retry_at. |
| PS3.4 | Replay tooling for queued events | Todo | Replay from offset range or DLQ subset. |
| PS3.5 | Burst/backpressure load scenario | Todo | Validate ingest and worker stability. |
| PS3.6 | Out-of-order/dup/drop simulation | Todo | Test **event** ordering robustness (telemetry stream). |
| PS3.7 | Contact-window simulation hooks | Todo | On/off downlink periods and buffered replay. |
| PS3.8 | Ops runbook for queue + DLQ recovery | Todo | Steps for triage, replay, and rollback. |
| PS3.9 | LangGraph durable checkpoint (Postgres) + resume | Todo | [PS3.9-langgraph-durable-checkpoint.md](PS3.9-langgraph-durable-checkpoint.md) — **not** covered by input replay alone. |
| PS3.10 | MCP resilience under lossy links + escalation proofs | Todo | [PS3.10-mcp-resilience-lossy-links.md](PS3.10-mcp-resilience-lossy-links.md) — extends S3.4 with CI-visible behaviour. |

**Status key:** Todo | In progress | Done | Blocked

**Carryover visibility:** PS3.9 / PS3.10 are indexed in [phase README — Cross-cutting](../README.md#cross-cutting-durability-safety-and-evals).
