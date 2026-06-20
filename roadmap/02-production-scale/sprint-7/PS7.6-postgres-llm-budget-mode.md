# PS7.6 — Postgres LLM budget mode (PS7b)

| Field | Value |
|-------|--------|
| **Task ID** | PS7.6 |
| **Status** | Done |
| **ADR** | [0005](../../../docs/adr/0005-environment-strategy-dev-stage-prod.md) §5 trigger |

## Description

Implement `LLM_BUDGET_MODE=postgres` — shared UTC-day token cap in `llm_usage_ledger` across API
and agent-worker replicas. Wire Helm **stage/prod** overlays; keep **dev/compose** on `process`.

## Deliverables

- [x] `apps/llm_usage_ledger.py` + `apps/llm_cost.py` postgres path
- [x] `alembic/versions/20260603_0003_ps76_llm_usage_ledger.py`
- [x] `infra/sql/002_llm_usage_ledger.sql`
- [x] Helm: `api.llm.budgetMode`, `dailyTokenBudget`, env in `_api-env.tpl`
- [x] `values-stage.yaml` / `values-prod.yaml` → `postgres` + caps
- [x] Docs + tests

## Helm defaults

| Overlay | `budgetMode` | `dailyTokenBudget` |
|---------|--------------|-------------------|
| dev / base | `process` | `0` (disabled) |
| stage | `postgres` | `250000` |
| prod | `postgres` | `500000` |

Tune caps per org; `0` disables enforcement in any mode.

## Acceptance

- [x] Multi-replica stage/prod share one UTC-day counter (survives pod restart).
- [x] Budget deny raises `LLMBudgetExceededError` (no backend fallback).
- [x] `tests/test_llm_cost_postgres_ps76.py` green.

## References

- [llm_cost_guardrails.md](../../../docs/llm_cost_guardrails.md)
- [runbooks/llm_cost_guardrails.md](../../../docs/runbooks/llm_cost_guardrails.md)
