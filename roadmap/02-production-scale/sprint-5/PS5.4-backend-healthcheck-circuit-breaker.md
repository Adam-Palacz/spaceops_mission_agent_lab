# PS5.4 — Backend healthcheck + circuit breaker

| Field | Value |
|-------|-------|
| **Task ID** | PS5.4 |
| **Status** | Todo |

---

## Description

When the GPU (NIM) backend is unhealthy or slow, the gateway must **fail closed safely**: probe
health, open a circuit after repeated failures, and **fall back to `LLM_BACKEND=openai`** (using
`OPENAI_*` credentials) so incident flow continues.

**Critical distinction:** fallback is correct **resilience** behavior but must **never** be
reported as a successful GPU call. PS5.1 metadata must show `backend_requested=gpu`,
`backend_actual=openai`, `fallback_used=true`, `fallback_reason=...`.

PS5.8 parity runs with `fallback_used=true` are **invalid for GPU promotion** (see PS5.8).

### Budget vs fallback (must not conflate — PS5.6)

**`LLMBudgetExceededError` is not a backend outage** (required type — see PS5.6). When the budget
guardrail refuses a call:

- **Do not** fall back from `gpu` to `openai` (or any other backend).
- **Do not** retry the same call on another backend.
- Propagate **`LLMBudgetExceededError`** unchanged → nodes escalate with **`reason=budget_exceeded`**
  (not `llm_provider_error`, not PS5.4 fallback).

Only **health / circuit / transport failures** on the requested GPU backend trigger
`fallback_used=true` to OpenAI.

---

## Requirements

- [ ] On-demand health check for NIM before first `LLM_BACKEND=gpu` call in a process (and after circuit half-open).
- [ ] Circuit breaker keyed `llm_gpu` with configurable failure threshold and reset window (reuse `http_resilience` patterns).
- [ ] When circuit open or health fails: fallback to **openai** adapter only if `OPENAI_API_KEY` present; else `LLMGatewayProviderError` → escalation.
- [ ] Every `generate()` returns PS5.1 fields: `backend_requested`, `backend_actual`, `fallback_used`, `fallback_reason`.
- [ ] Structured logs mirror response metadata (no silent backend swap).
- [ ] Metric: `llm_backend_fallback_total{from,to,reason}` (low cardinality).

---

## Dependencies

- **PS5.2** — OpenAI fallback target.
- **PS5.3** — NIM endpoint to probe.
- **PS3.10 / S3.4** — precedent for breaker semantics.

---

## Checklist

- [ ] Implement `healthcheck_gpu()` against NIM ready endpoint.
- [ ] Wire breaker around GPU adapter; set metadata on fallback path.
- [ ] Document fallback order: `gpu` → `openai` → escalate if both unavailable.
- [ ] Runbook: operators distinguish “GPU down + fallback OK” vs “GPU serving”.

---

## Test / acceptance

- [ ] Unit: simulated NIM 503 → breaker opens → next call has `fallback_used=true`, `backend_actual=openai`.
- [ ] Unit: response metadata on success path has `fallback_used=false`, `backend_actual=gpu`.
- [ ] Unit: breaker half-open recovery after reset interval.
- [ ] Chaos test (optional): GPU timeout does not exceed `agent_llm_call_timeout_seconds`.
- [ ] Unit: budget exceeded with `LLM_BACKEND=gpu` → `LLMBudgetExceededError`, **no** fallback,
      `llm_backend_fallback_total` not incremented for budget reason.
- [ ] Unit: budget exceeded with `LLM_BACKEND=openai` → same; no cross-backend retry.

---

## Deliverables (expected)

- `apps/llm_backends/resilience.py` (or gateway module) — health + breaker + fallback
- `config.py` — breaker thresholds
- `docs/runbooks/llm_backend_fallback.md`
- `tests/test_llm_backend_resilience_ps54.py`
