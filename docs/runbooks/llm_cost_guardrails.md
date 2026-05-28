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

- `process` mode: good for local demos/session caps; resets on restart
- `postgres` mode: use only after PS6 implementation for shared multi-worker cap semantics

## Related docs

- `docs/llm_cost_guardrails.md`
- `docs/runbooks/llm_backend_rollout.md`
- `docs/runbooks/llm_backend_fallback.md`
