# ADR 0004 — LLM backend rollout policy (`LLM_BACKEND`)

- Status: **Accepted**
- Date: 2026-05-28
- Related: PS5.1, PS5.3, PS5.4, PS5.5, PS5.8

## Context

The project now supports multiple LLM backends through one gateway contract:

- `openai` (default, cloud baseline)
- `cursor_sh` (optional cloud backend)
- `gpu` (optional local NVIDIA NIM backend)

PS5.3 proved GPU runtime, and PS5.4 added health/circuit fallback semantics. We need one rollout policy for environment configuration and migration from deprecated `LLM_PROVIDER`.

## Decision

1. **Canonical routing knob** is `LLM_BACKEND=openai|cursor_sh|gpu`.
2. `LLM_PROVIDER` remains **deprecated compatibility** only when `LLM_BACKEND` is unset.
3. Safe default in every environment is `openai` when neither knob is set.
4. GPU rollout is opt-in and reversible without deploy:
   - set `LLM_BACKEND=gpu`,
   - verify smoke and fallback metrics,
   - rollback by restoring `LLM_BACKEND=openai` and stopping NIM.
5. Fallback metadata is mandatory for observability and parity validity:
   - `backend_requested`, `backend_actual`, `fallback_used`, `fallback_reason`.
6. Budget rejections (`LLMBudgetExceededError`) are never fallback triggers.

## Environment matrix

- **dev**: `openai` default; `gpu` only for local smoke/canary sessions.
- **stage**: `openai` baseline with optional `gpu` canary on selected workers.
- **prod**: policy-controlled rollout; `openai` remains emergency baseline.

## Rollout / rollback policy

### Rollout (GPU canary)

1. `make gpu-up`
2. run NIM smoke (`python scripts/llm_gpu_smoke.py --health-only --generate`)
3. set `LLM_BACKEND=gpu` on one worker/process
4. monitor:
   - gateway logs (`backend_requested` vs `backend_actual`)
   - `llm_backend_fallback_total{from_backend="gpu",to_backend="openai",reason=...}`
5. expand only if fallback pressure remains low and quality checks pass.

### Emergency rollback

1. set `LLM_BACKEND=openai`
2. `make gpu-down`
3. verify new calls log `backend_actual=openai`.

## Migration timeline for `LLM_PROVIDER`

- **Now (PS5.5)**: keep support with deprecation warning.
- **Next phase (PS6):** [ADR 0005](0005-environment-strategy-dev-stage-prod.md) — `LLM_PROVIDER` frozen in K8s manifests; `.env.example` deprecated only.
- **Removal gate**: no active environment should rely on provider-only config.

## Consequences

- Consistent routing semantics across local, CI, and runtime environments.
- Fast rollback path without code changes.
- Clear parity/evidence interpretation when fallback occurs (PS5.8 invalidates GPU arm on fallback).
