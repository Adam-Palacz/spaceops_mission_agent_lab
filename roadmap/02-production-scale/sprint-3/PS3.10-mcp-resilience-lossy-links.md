# PS3.10 — MCP client under lossy links (chaos + escalation)

| Field | Value |
|-------|-------|
| **Task ID** | PS3.10 |
| **Status** | Todo |

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

- [ ] Test module or tox/pytest marker runnable in CI (or nightly) without live OpenAI; use httpx
      mock / stub MCP or test double.
- [ ] Matrix: telemetry vs KB keys (`mcp_telemetry`, `mcp_kb_*`) to ensure per-key circuits.
- [ ] Update ops runbook (PS3.8 or link) with “MCP storm / breaker open” triage bullets.

---

## Dependencies

- Builds on existing `with_retry_async` / `http_resilience` config (`http_resilience_*` settings).
