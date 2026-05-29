# LLM cost guardrails (PS5.6)

This document defines cost telemetry and budget semantics for LLM calls.

## Budget modes

| Mode | Env | Storage | Semantics | Sprint default |
|------|-----|---------|-----------|----------------|
| **`process`** | `LLM_BUDGET_MODE=process` | In-process counter | Per API/worker process; **resets on restart**; suitable for **local lab / demo session guard** only | **Yes (default)** |
| **`postgres`** | `LLM_BUDGET_MODE=postgres` | `llm_usage_ledger` table (or reuse audit DB) | Shared across workers; survives restart; required for any claim of **hard daily org cap** | Optional in PS5.6; if not implemented, document defer to PS6 |

`process` mode must not be described as a financial or multi-worker daily spend limit.

## Metrics

- `llm_tokens_total{backend_actual,model_id,node}`
- `llm_estimated_cost_usd_total{backend_actual,model_id,node}` (estimate only)
- `llm_backend_fallback_total{from_backend,to_backend,reason}` (PS5.4 resilience context)

All labels are bounded and exclude incident/run identifiers.

## Process mode behavior

- Soft warning when usage reaches `LLM_BUDGET_SOFT_WARNING_RATIO * LLM_DAILY_TOKEN_BUDGET`
- Hard deny on subsequent `generate()` when current process usage is at/above budget
- Deny exception: `LLMBudgetExceededError`
- No backend fallback and no cross-backend retry on budget deny

## Postgres mode status

`LLM_BUDGET_MODE=postgres` is **deferred** per [ADR 0005](adr/0005-environment-strategy-dev-stage-prod.md): all PS6 environments use **`process`**. Selecting `postgres` raises an explicit configuration/runtime error until ledger + Helm wiring ship (trigger: shared org cap across replicas required).

## Defaults

Suggested defaults in local `.env`:

```env
LLM_BUDGET_MODE=process
LLM_DAILY_TOKEN_BUDGET=0
LLM_BUDGET_SOFT_WARNING_RATIO=0.8
```

Set `LLM_DAILY_TOKEN_BUDGET` to a positive integer to enforce process-mode guardrails.
