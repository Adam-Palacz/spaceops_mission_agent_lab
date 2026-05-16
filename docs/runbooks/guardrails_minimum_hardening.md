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

## Output schema enforcement (PS4.2)

Before returning node outputs:

- `check_escalation`, `act`, and `report` validate envelopes via `apps/contracts/output_validation.py`.
- Failures escalate with `output_schema_violation` (fail-closed); see [output_schema.md](../output_schema.md).
- API returns HTTP 422 with stable `detail.error` when a report fails the boundary check.

Schema validation failures must not silently pass; see `tests/test_output_schema_ps42.py`.

## Verification checklist

- Run `pytest tests/test_guardrails_ps17.py`.
- Run `pytest tests/test_agent_pipeline.py -k escalation`.
- Optionally run full gate: `python -m evals.scoring`.
