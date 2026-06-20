# LLM cost guardrails (PS5.6)

This document defines cost telemetry and budget semantics for LLM calls.

## Budget modes

| Mode | Env | Storage | Semantics | Sprint default |
|------|-----|---------|-----------|----------------|
| **`process`** | `LLM_BUDGET_MODE=process` | In-process counter | Per API/worker process; **resets on restart**; suitable for **local lab / demo session guard** only | **Yes (default)** |
| **`postgres`** | `LLM_BUDGET_MODE=postgres` | `llm_usage_ledger` table (Postgres) | Shared UTC-day total across replicas; survives restart; **stage/prod Helm default (PS7.6)** | stage/prod when cap > 0 |

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

## Postgres mode behavior (PS7.6)

- Ledger table **`llm_usage_ledger`**: one row per **UTC calendar day**, column `tokens_used`.
- `enforce_budget_before_generate()` reads today's total; `record_llm_usage()` increments after each call.
- Soft warning uses the same `LLM_BUDGET_SOFT_WARNING_RATIO` threshold (logged once per process).
- Hard deny: `LLMBudgetExceededError` when today's total is already at/above `LLM_DAILY_TOKEN_BUDGET`
  before a new call. A call that pushes the ledger over the cap completes; the next call is denied.
- Bootstrap: `alembic upgrade head` or `infra/sql/002_llm_usage_ledger.sql` on lab Postgres.
- Helm stage/prod set `budgetMode: postgres` and positive `dailyTokenBudget` in values overlays.

Concurrent replicas may allow a small overshoot under heavy parallel load; tune budget accordingly.

## Postgres mode status

**Implemented (PS7.6).** Stage and prod Helm overlays default to `postgres` with configurable
`LLM_DAILY_TOKEN_BUDGET`. Dev/Compose default remains `process`.

## Defaults

Suggested defaults in local `.env`:

```env
LLM_BUDGET_MODE=process
LLM_DAILY_TOKEN_BUDGET=0
LLM_BUDGET_SOFT_WARNING_RATIO=0.8
```

Set `LLM_DAILY_TOKEN_BUDGET` to a positive integer to enforce process-mode guardrails.
