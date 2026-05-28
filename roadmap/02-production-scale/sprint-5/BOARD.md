# PS5 — Board

| Task | Title | Status | Spec |
|------|-------|--------|------|
| PS5.1 | Gateway backend abstraction hardening | Done | [PS5.1](PS5.1-gateway-backend-abstraction-hardening.md) |
| PS5.2 | OpenAI backend adapter parity tests | Done | [PS5.2](PS5.2-openai-backend-adapter-parity-tests.md) |
| PS5.3 | Optional GPU backend adapter (NIM) | Done | [PS5.3](PS5.3-optional-gpu-backend-adapter.md) |
| PS5.4 | Backend healthcheck + circuit breaker | Todo | [PS5.4](PS5.4-backend-healthcheck-circuit-breaker.md) |
| PS5.5 | Backend feature flags and rollout policy | Todo | [PS5.5](PS5.5-backend-feature-flags-rollout-policy.md) |
| PS5.6 | Cost telemetry and guardrails | Todo | [PS5.6](PS5.6-cost-telemetry-guardrails.md) |
| PS5.7 | Idle TTL and scale-to-zero workflow | Todo | [PS5.7](PS5.7-idle-ttl-scale-to-zero.md) |
| PS5.8 | Parity eval suite and tolerance definition | Todo | [PS5.8](PS5.8-parity-eval-suite-tolerance.md) |

**Status key:** Todo | In progress | Done | Blocked

**Plan notes (post-review)**

- **Config:** `LLM_BACKEND=openai|cursor_sh|gpu`; `LLM_PROVIDER` deprecated with precedence in PS5.1.
- **GPU runtime:** NVIDIA NIM only for PS5.3 Done; manual smoke required, not placeholder compose.
- **Parity:** promotion requires complete `openai`/`gpu` case pairs with both arms valid (PS5.8).
- **Budget:** default `LLM_BUDGET_MODE=process` (not a financial daily cap); postgres mode optional.
- **Idle TTL:** host-run scripts + mandatory `last_gpu_call_at` from gateway.
- Default PR CI stays GPU-free; `gpu-smoke` / `backend-parity` = workflow_dispatch or nightly.
- **Idle TTL:** `./var:/app/var` mount; host script reads file after containerized API call.
- **Parity:** aggregate `llm_calls_provenance`; any fallback or mixed backend → invalid arm.
- **Parity baseline:** `invalid_backend_mismatch` in `openai` arm or a missing required arm blocks promotion.
- **Budget:** mandatory `LLMBudgetExceededError` → escalation `budget_exceeded`; no fallback.
- **Parity status:** `invalid_mixed_backends` (priority 1) vs `invalid_fallback` (priority 2).
