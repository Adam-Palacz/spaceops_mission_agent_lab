# PS4.7 — CI gating policy for safety and quality

| Field | Value |
|-------|-------|
| **Task ID** | PS4.7 |
| **Status** | Todo |

---

## Description

Define and implement CI gate policy for safety/quality checks: which checks are hard blockers vs
soft signals, including OPA/HITL integration criteria for restricted actions.

---

## Requirements

- [ ] Define hard-gate vs soft-gate matrix for tests/evals/golden checks.
- [ ] Include explicit OPA fail-closed + approval/HITL integration criteria.
- [ ] Ensure CI output states exactly why a gate failed and how to recover.
- [ ] Document override/escalation process for emergency releases.

---

## Checklist

- [ ] CI workflow updated with deterministic gate ordering.
- [ ] Gate summary appears in job logs/artifacts.
- [ ] Policy documented in runbook/README for engineering and ops.

---

## Test / acceptance

- [ ] Simulated safety regression fails hard gate.
- [ ] Non-blocking quality drift is reported as soft signal.
- [ ] OPA/HITL integration test path is included in gating decision.
