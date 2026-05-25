# Guardrails minimum hardening (PS1.7)

Fail-closed guardrails for investigation and escalation. **For CI failures and step-by-step triage, start with [guardrails_quality_triage.md](guardrails_quality_triage.md) (PS4.8).**

## Escalation rules (must-escalate)

The agent must escalate and stop autonomous action when any of these conditions occur:

- `no_evidence`: no usable citations or only fallback "no data" hypothesis.
- `tool_failure`: at least one investigation tool returns `failure` (timeout/error).
- `conflicting_signals`: evidence contains contradictory signals (for example anomaly + nominal).
- existing limit failures from prior hardening: `token_limit`, `rate_limit`, `llm_timeout`, `llm_provider_error`, `run_timeout`.

## Tool outcome semantics

Investigation tools use normalized outcomes:

- `success`: tool returned usable evidence.
- `empty`: tool completed successfully but no matching results.
- `failure`: tool call failed (timeout/error/unavailable).

Only `failure` enforces hard fail-closed escalation (`tool_failure`).

## Traceability in audit log

Guardrail decisions are written to audit with:

- `tool=guardrail_escalation`
- `decision=escalate`
- `args.reason=<escalation reason>`

This enables clear root-cause attribution during incident review and replay diffing.

## Output schema enforcement (PS4.2)

Before returning node outputs:

- `check_escalation`, `act`, and `report` validate envelopes via `apps/contracts/output_validation.py`.
- Failures escalate with `output_schema_violation` (fail-closed); see [output_schema.md](../output_schema.md).
- API returns HTTP 422 with stable `detail.error` when a report fails the boundary check.

Schema validation failures must not silently pass; see `tests/test_output_schema_ps42.py`.

## Prompt injection hardening (PS4.3)

- Untrusted payload/KB text is scanned and sanitized before LLM prompts (`[BEGIN UNTRUSTED DATA]` fences).
- Critical patterns escalate with `prompt_injection_detected` (not silent drop); audit tool `prompt_injection_guard`.
- Plan `action_type` allowlist enforced at `decide` and `act`.
- See [prompt_injection_threat_model.md](../prompt_injection_threat_model.md) and `tests/test_prompt_injection_ps43.py`.

## Evidence policy (PS4.1)

- Grounded citations required for actionable plan steps; violations → `evidence_policy_violation`.
- See [evidence_policy.md](../evidence_policy.md) and `tests/test_evidence_policy_ps41.py`.

## Verification checklist

```bash
make safety-gates          # PS4.7: OPA, HITL, evidence, injection, schema (recommended)
make check                 # lint + typecheck + golden
pytest tests/test_guardrails_ps17.py -q
```

Full triage flow: [guardrails_quality_triage.md](guardrails_quality_triage.md).  
CI gate policy: [ci_gating_policy.md](ci_gating_policy.md).
