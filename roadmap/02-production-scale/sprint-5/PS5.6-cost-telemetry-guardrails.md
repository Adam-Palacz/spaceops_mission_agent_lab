# PS5.6 — Cost telemetry and guardrails

| Field | Value |
|-------|-------|
| **Task ID** | PS5.6 |
| **Status** | Todo |

---

## Description

Make LLM spend **visible** and apply **honest** guardrails: token usage from the gateway, optional
cost estimates, and budget limits whose semantics match storage — no claiming a “hard daily cap”
that resets on process restart.

Parent: [Phase 5 — Cost guardrails](../../02-production-scale.md#phase-5--llm-backends-vendor-agnostic--optional-gpu-off-by-default).

---

## Budget modes (required — pick explicitly in implementation)

| Mode | Env | Storage | Semantics | Sprint default |
|------|-----|---------|-----------|----------------|
| **`process`** | `LLM_BUDGET_MODE=process` | In-process counter | Per API/worker process; **resets on restart**; suitable for **local lab / demo session guard** only | **Yes (default)** |
| **`postgres`** | `LLM_BUDGET_MODE=postgres` | `llm_usage_ledger` table (or reuse audit DB) | Shared across workers; survives restart; required for any claim of **hard daily org cap** | Optional in PS5.6; if not implemented, document defer to PS6 |

**Do not** label `process` mode as a financial or multi-worker daily spend limit in docs or metrics.

### Budget deny ≠ backend fallback (PS5.4)

When a call is refused because the budget cap is exceeded:

- Raise **`LLMBudgetExceededError`** — **required** dedicated exception in `apps/llm_gateway.py`
  (subclass of a common gateway base or `Exception`; **not** `LLMGatewayProviderError`).
- **No fallback** to another backend (`gpu` over budget must **not** silently use `openai`).
- **No retry** on alternate backend.
- Agent nodes map `LLMBudgetExceededError` → escalation packet **`reason=budget_exceeded`** (PS5.4
  GPU→OpenAI path must not run).

This prevents budget guardrails from being bypassed via fallback.

---

## Requirements

- [ ] Emit `llm_tokens_total{backend_actual,model_id,node}` (or equivalent; avoid per-incident labels).
- [ ] Optional `llm_estimated_cost_usd` when rate card configured (estimates ≠ cloud invoice).
- [ ] **`process` mode:** soft warning at threshold; hard refuse further `generate()` in **this process** with **`LLMBudgetExceededError` only**.
- [ ] **`postgres` mode (if implemented):** same thresholds but ledger keyed by UTC date + optional scope; tests: restart does not reset count; two processes share ledger.
- [ ] Document which mode is enabled in compose/README defaults.

---

## Dependencies

- **PS5.2** — token usage normalization.
- **PS4.6** (done) — metrics patterns.

---

## Checklist

- [ ] Rate table in config with safe defaults (empty = no cost estimate).
- [ ] `docs/llm_cost_guardrails.md` — mode table above copied verbatim.
- [ ] Runbook: respond to alert (gpu-down, lower `AGENT_MAX_LLM_CALLS`, switch `LLM_BUDGET_MODE`).

---

## Test / acceptance

- [ ] Unit (`process`): token counter increments; hard cap blocks next call in same process.
- [ ] Unit (`process`): new process resets counter (documents non-persistence).
- [ ] Integration (`postgres`, if built): insert usage → restart app → cap still enforced.
- [ ] No high-cardinality Prometheus labels.
- [ ] Unit: `LLM_BACKEND=gpu`, budget exceeded → `LLMBudgetExceededError`; assert fallback adapter **not** invoked.
- [ ] Unit: `LLM_BACKEND=openai`, budget exceeded → same; no GPU path attempted.

---

## Deliverables (expected)

- `apps/llm_gateway.py` — `LLMBudgetExceededError` (exported)
- `apps/llm_cost.py`
- `config.py` — `llm_budget_mode`, `llm_daily_token_budget`, rate card fields
- `alembic/versions/*_llm_usage_ledger.py` (only if postgres mode shipped)
- `docs/llm_cost_guardrails.md`
- `tests/test_llm_cost_guardrails_ps56.py`
