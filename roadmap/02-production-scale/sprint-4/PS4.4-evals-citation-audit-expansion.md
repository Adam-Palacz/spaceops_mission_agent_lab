# PS4.4 — Eval suite expansion for citation precision and audit outcomes

| Field | Value |
|-------|-------|
| **Task ID** | PS4.4 |
| **Status** | Todo |

---

## Description

Expand eval coverage for evidence/citation precision and audit semantics, especially around tool
failures and policy-deny/fail-closed branches.

---

## Requirements

- [ ] Add eval cases for citation precision (present, absent, wrong reference).
- [ ] Add eval cases for audit semantics (`tool_failure`, `policy_deny`, `no_evidence`).
- [ ] Ensure CI runs a deterministic minimum eval subset for gate decisions.
- [ ] Document optional future hooks for LLM-as-judge / RAGAS-style scoring (non-blocking).

---

## Checklist

- [ ] Eval fixtures are synthetic and CI-safe (no live provider dependency).
- [ ] Scoring output is actionable for engineers (clear failing rubric line).
- [ ] Mapping between eval case IDs and runbook triage is documented.

---

## Test / acceptance

- [ ] CI fails when citation/audit semantics regress.
- [ ] At least one eval asserts correct distinction between empty evidence and tool failure.
- [ ] Eval summary artifact includes per-case pass/fail details.
