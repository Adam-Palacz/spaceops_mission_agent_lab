# LLM cost guardrails runbook (PS5.6)

Use this runbook when budget or cost telemetry indicates elevated spend or budget denials.

## Symptoms

- `LLMBudgetExceededError` spikes
- many escalations with `reason=budget_exceeded`
- fast growth of `llm_tokens_total`

## Immediate actions

1. Confirm mode and cap:
   - `LLM_BUDGET_MODE`
   - `LLM_DAILY_TOKEN_BUDGET`
2. If GPU instability also occurs, separate concerns:
   - fallback metrics: `llm_backend_fallback_total`
   - budget denials are not fallback events
3. Reduce load:
   - lower `AGENT_MAX_LLM_CALLS_PER_RUN`
   - tighten prompts/call paths where possible
4. If needed for continuity:
   - temporarily increase `LLM_DAILY_TOKEN_BUDGET`
   - or disable guard (`LLM_DAILY_TOKEN_BUDGET=0`) with explicit operator approval

## Mode guidance

- `process` mode: local demos/session caps; resets on restart; **dev default**
- `postgres` mode: shared UTC-day org cap across replicas; **stage/prod Helm default (PS7.6)**
- Run `infra/sql/002_llm_usage_ledger.sql` or Alembic before first postgres-mode deploy on a fresh DB

## Related docs

- `docs/llm_cost_guardrails.md`
- `docs/runbooks/llm_backend_rollout.md`
- `docs/runbooks/llm_backend_fallback.md`
