# PS1.6 — LLM gateway minimum contract

| Field | Value |
|-------|--------|
| **Task ID** | PS1.6 |
| **Status** | Done |

---

## Description

Consolidate all model calls behind a single gateway contract so provider changes do not leak into
agent nodes. Minimum scope: `generate()`/chat call abstraction plus metadata logging.

---

## Requirements

- [x] A single gateway interface is used by triage/decide/report paths.
- [x] Default backend remains OpenAI-compatible.
- [x] Gateway logs model ID/version/latency and core token metadata.
- [x] Gateway failure semantics are explicit (timeout/error -> escalation path compatibility).
- [x] Existing behavior remains backward compatible for current provider mode.

---

## Checklist

- [x] Extract direct model calls into gateway module.
- [x] Update nodes/evals to use gateway interface only.
- [x] Add structured metadata output for observability.
- [x] Add tests for success, timeout, and provider error propagation.
- [x] Document gateway contract and extension points.

---

## Test requirements

- [x] End-to-end runs succeed with gateway enabled.
- [x] Timeout/error paths preserve fail-closed behavior.
- [x] LLM call metadata appears in logs/observability records.
