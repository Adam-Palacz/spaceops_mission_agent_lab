# PS1.6 — LLM gateway minimum contract

| Field | Value |
|-------|--------|
| **Task ID** | PS1.6 |
| **Status** | Todo |

---

## Description

Consolidate all model calls behind a single gateway contract so provider changes do not leak into
agent nodes. Minimum scope: `generate()`/chat call abstraction plus metadata logging.

---

## Requirements

- [ ] A single gateway interface is used by triage/decide/report paths.
- [ ] Default backend remains OpenAI-compatible.
- [ ] Gateway logs model ID/version/latency and core token metadata.
- [ ] Gateway failure semantics are explicit (timeout/error -> escalation path compatibility).
- [ ] Existing behavior remains backward compatible for current provider mode.

---

## Checklist

- [ ] Extract direct model calls into gateway module.
- [ ] Update nodes/evals to use gateway interface only.
- [ ] Add structured metadata output for observability.
- [ ] Add tests for success, timeout, and provider error propagation.
- [ ] Document gateway contract and extension points.

---

## Test requirements

- [ ] End-to-end runs succeed with gateway enabled.
- [ ] Timeout/error paths preserve fail-closed behavior.
- [ ] LLM call metadata appears in logs/observability records.
