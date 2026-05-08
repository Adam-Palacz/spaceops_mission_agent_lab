# PS3.10 — MCP client under lossy links (chaos + escalation)

| Field | Value |
|-------|-------|
| **Task ID** | PS3.10 |
| **Status** | Done |

---

## Problem statement

The codebase already has **retry + exponential backoff + circuit breaker** for MCP HTTP (`S3.4`,
`apps/common/http_resilience.py`, `apps/agent/mcp_client.py`). **Gap:** behaviour under **high
latency, packet loss, and intermittent LOS** is not **proven** in CI: e.g. circuit **open** must lead
to **fail-closed / escalation** (not spin, not partial silent success), aligned with escalation
path (S1.8 / investigate outcomes).

---

## Description

Add **targeted chaos or fault-injection tests** (or documented harness) for MCP calls: slow responses,
connection drops, repeated 5xx/421-class failures. Assert:

- circuit opens after configured failures;
- agent surfaces **tool failure** / empty evidence with **audit** semantics;
- escalation triggers when policy requires (e.g. no evidence + high risk), not infinite retries.

Document limits vs **PS3.6** (generic out-of-order/dup/drop for **events**): PS3.10 is **tool transport**
specific.

---

## Requirements

- [x] CI-safe pytest module added (no live OpenAI/MCP required; uses monkeypatch + test doubles).
- [x] Matrix validated for per-key circuits: `mcp_telemetry`, `mcp_kb_runbooks`, `mcp_kb_postmortems`.
- [x] Ops runbook updated with “MCP storm / breaker open” triage bullets.

Implemented artifacts:
- `tests/test_mcp_resilience_ps310.py`
- `apps/common/http_resilience.py` (`421` added to retryable transport statuses)
- `docs/runbooks/queue_dlq_recovery.md` (PS3.10 triage section)

---

## Dependencies

- Builds on existing `with_retry_async` / `http_resilience` config (`http_resilience_*` settings).
