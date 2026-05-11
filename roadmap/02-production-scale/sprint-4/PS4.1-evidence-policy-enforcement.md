# PS4.1 — Evidence policy expansion and enforcement

| Field | Value |
|-------|-------|
| **Task ID** | PS4.1 |
| **Status** | Done |

---

## Description

Strengthen evidence-grounding rules so agent outputs cannot claim unsupported facts.
No invented citations; explicit fail-closed escalation when grounding quality is insufficient.

---

## Requirements

- [x] Define enforceable evidence policy for report/plan claims and citation references.
- [x] Add validation hook that rejects claims without evidence linkage.
- [x] Ensure escalation reasons distinguish `no_evidence` vs `tool_failure` vs policy reject.
- [x] Add low-cardinality observability fields for grounding outcomes.

---

## Checklist

- [x] Policy documented in `docs/`.
- [x] Unit tests for pass/fail policy paths.
- [x] Existing pipeline tests updated to reflect stricter semantics.

---

## Test / acceptance

- [x] Automated case fails on unsupported citation references (`evidence_policy_violation`).
- [x] Automated case passes with valid citation-grounded output.
- [x] Failure reason is explicit and stable (`evidence_policy_violation`).

Implemented artifacts:
- `apps/agent/nodes.py` (policy evaluator + report-stage fail-closed enforcement + observability attrs)
- `apps/agent/state.py` (policy status/reason state fields)
- `tests/test_evidence_policy_ps41.py`
- `docs/evidence_policy.md`

---

## Additional / follow-on (DX)

- **PS4.1.1** — [Makefile & CI parity for local checks](PS4.1.1-makefile-ci-parity.md): `make help` / `make check` aligned with CI (not part of evidence policy semantics).
