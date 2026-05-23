# PS4.7 — CI gating policy for safety and quality

| Field | Value |
|-------|-------|
| **Task ID** | PS4.7 |
| **Status** | Done |

---

## Description

Define and implement CI gate policy for safety/quality checks: which checks are hard blockers vs
soft signals, including OPA/HITL integration criteria for restricted actions.

---

## Requirements

- [x] Define hard-gate vs soft-gate matrix for tests/evals/golden checks.
- [x] Include explicit OPA fail-closed + approval/HITL integration criteria.
- [x] Ensure CI output states exactly why a gate failed and how to recover.
- [x] Document override/escalation process for emergency releases.

---

## Checklist

- [x] CI workflow updated with deterministic gate ordering.
- [x] Gate summary appears in job logs/artifacts.
- [x] Policy documented in runbook/README for engineering and ops.

---

## Test / acceptance

- [x] Simulated safety regression fails hard gate.
- [x] Non-blocking quality drift is reported as soft signal.
- [x] OPA/HITL integration test path is included in gating decision.

---

## Deliverables

- `apps/ci_gating.py` — gate registry, runner, markdown summary
- `scripts/ci_gate_runner.py` — local ordered gate run
- `scripts/ci_gate_summary.py` — GitHub Actions aggregate + artifact
- `.github/workflows/ci.yml` — `golden-check`, `safety-gates`, `evals-hard`, `evals-soft`, `gate-summary`
- `docs/runbooks/ci_gating_policy.md`
- `evals/scoring.py` — `--injection-only`, `--soft-signal`
- `tests/test_ci_gating_ps47.py`
- `Makefile` — `safety-gates` target
