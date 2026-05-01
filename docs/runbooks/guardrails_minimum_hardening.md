# Guardrails minimum hardening (PS1.7)

This runbook documents the fail-closed guardrails required in production-scale Sprint 1.

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

## Output schema enforcement

Before returning node outputs:

- `check_escalation` validates escalation packet structure.
- `report` validates report structure (including escalation payload when present).

Schema validation failures are treated as code defects and should fail tests/CI.

## Verification checklist

- Run `pytest tests/test_guardrails_ps17.py`.
- Run `pytest tests/test_agent_pipeline.py -k escalation`.
- Optionally run full gate: `python -m evals.scoring`.
