# PS4.4 — Eval suite expansion for citation precision and audit outcomes

| Field | Value |
|-------|-------|
| **Task ID** | PS4.4 |
| **Status** | Done |

---

## Description

Expand eval coverage for evidence/citation precision and audit semantics, especially around tool
failures and policy-deny/fail-closed branches.

---

## Requirements

- [x] Add eval cases for citation precision (present, absent, wrong reference).
- [x] Add eval cases for audit semantics (`tool_failure`, `policy_deny`, `no_evidence`).
- [x] Ensure CI runs a deterministic minimum eval subset for gate decisions.
- [x] Document optional future hooks for LLM-as-judge / RAGAS-style scoring (non-blocking).

---

## Checklist

- [x] Eval fixtures are synthetic and CI-safe (no live provider dependency).
- [x] Scoring output is actionable for engineers (clear failing rubric line).
- [x] Mapping between eval case IDs and runbook triage is documented.

---

## Test / acceptance

- [x] CI fails when citation/audit semantics regress.
- [x] At least one eval asserts correct distinction between empty evidence and tool failure.
- [x] Eval summary artifact includes per-case pass/fail details.

---

## Deliverables

- `evals/semantic_cases.yaml` + `evals/fixtures/semantic/*.json`
- `evals/semantic.py` — `python -m evals.semantic`
- `evals/scoring.py` — `expected_escalation_reason`, `expected_tool_outcomes`, `--semantic-only`
- CI job `semantic-evals` + artifact `eval-semantic-summary.json`
- `tests/test_semantic_evals_ps44.py`
- `make semantic-check`
- [docs/evals_llm_judge_hooks.md](../../../docs/evals_llm_judge_hooks.md)
- Runbook mapping in [guardrails_quality_triage.md](../../../docs/runbooks/guardrails_quality_triage.md)
